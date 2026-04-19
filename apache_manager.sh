#!/bin/bash
# ============================================================
# Apache2 Manager Backend - Shell Script
# ============================================================

BACKUP_DIR="/var/backups/apache2_manager"
APACHE_CONF="/etc/apache2"
SITES_AVAILABLE="$APACHE_CONF/sites-available"
SITES_ENABLED="$APACHE_CONF/sites-enabled"
SECURITY_CONF="$APACHE_CONF/conf-available/security.conf"
LOG_FILE="/var/log/apache2_manager.log"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_action() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE" 2>/dev/null
    echo "$1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "ERROR: Se requieren permisos de root (sudo)"
        exit 1
    fi
}

set_or_add_directive() {
    local file="$1"
    local directive="$2"
    local value="$3"

    [ -f "$file" ] || touch "$file"

    if grep -Eq "^[[:space:]]*${directive}[[:space:]]+" "$file"; then
        sed -Ei "s|^[[:space:]]*${directive}[[:space:]]+.*|${directive} ${value}|" "$file"
    else
        printf "\n%s %s\n" "$directive" "$value" >> "$file"
    fi
}

probe_server_header() {
    # Devuelve: URL|STATUS_LINE|SERVER_HEADER
    # Prioriza respuestas válidas (evita falso positivo de HTTP en puerto TLS).
    local urls=()
    local seen="|"

    _add_url() {
        local u="$1"
        [[ "$seen" == *"|$u|"* ]] && return
        seen+="$u|"
        urls+=("$u")
    }

    _add_url "http://127.0.0.1/"
    _add_url "https://127.0.0.1/"

    local port
    while IFS= read -r port; do
        [ -z "$port" ] && continue
        if [ "$port" = "443" ] || [ "$port" = "8443" ]; then
            _add_url "https://127.0.0.1:$port/"
        elif [ "$port" = "80" ] || [ "$port" = "8080" ]; then
            _add_url "http://127.0.0.1:$port/"
        else
            _add_url "http://127.0.0.1:$port/"
            _add_url "https://127.0.0.1:$port/"
        fi
    done < <(ss -tln 2>/dev/null | awk '{print $4}' | grep -oE '[0-9]+$' | sort -u)

    local first_with_header=""
    local url raw status server
    for url in "${urls[@]}"; do
        if [[ "$url" == https://* ]]; then
            raw=$(curl -k -si --max-time 4 "$url" 2>/dev/null | head -20)
        else
            raw=$(curl -si --max-time 4 "$url" 2>/dev/null | head -20)
        fi

        status=$(echo "$raw" | head -1 | tr -d '\r')
        server=$(echo "$raw" | awk -F': ' 'BEGIN{IGNORECASE=1} /^Server:/{print $2; exit}' | tr -d '\r')

        [ -z "$status" ] && continue
        [ -n "$server" ] && [ -z "$first_with_header" ] && first_with_header="$url|$status|$server"

        # Evita tomar como fuente principal un 400 típico de esquema incorrecto.
        if echo "$status" | grep -q " 400 "; then
            continue
        fi

        if [ -n "$server" ]; then
            echo "$url|$status|$server"
            return 0
        fi
    done

    [ -n "$first_with_header" ] && echo "$first_with_header" && return 0
    return 1
}

# ============================================================
# FUNCIÓN: Crear Virtual Host
# ============================================================
create_virtualhost() {
    local DOMAIN="$1"
    local DOC_ROOT="$2"
    local ADMIN_EMAIL="$3"
    local PORT="${4:-80}"
    local ENABLE_SSL="${5:-no}"

    if [ -z "$DOMAIN" ] || [ -z "$DOC_ROOT" ]; then
        echo "ERROR: Dominio y DocumentRoot son requeridos"
        exit 1
    fi

    check_root

    # Crear directorio DocumentRoot
    if [ ! -d "$DOC_ROOT" ]; then
        mkdir -p "$DOC_ROOT"
        chown www-data:www-data "$DOC_ROOT"
        chmod 755 "$DOC_ROOT"
        log_action "Directorio creado: $DOC_ROOT"
    fi

    # Crear index.html de prueba
    if [ ! -f "$DOC_ROOT/index.html" ]; then
        cat > "$DOC_ROOT/index.html" << HTML
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>$DOMAIN - Bienvenido</title></head>
<body>
<h1>Virtual Host: $DOMAIN</h1>
<p>Configurado exitosamente el $(date '+%d/%m/%Y %H:%M')</p>
</body>
</html>
HTML
        chown www-data:www-data "$DOC_ROOT/index.html"
    fi

    local CONF_FILE="$SITES_AVAILABLE/$DOMAIN.conf"

    # Crear configuración del VirtualHost
    cat > "$CONF_FILE" << VHOST
<VirtualHost *:$PORT>
    ServerName $DOMAIN
    ServerAlias www.$DOMAIN
    ServerAdmin ${ADMIN_EMAIL:-webmaster@$DOMAIN}
    DocumentRoot $DOC_ROOT

    <Directory $DOC_ROOT>
        Options -Indexes +FollowSymLinks
        AllowOverride All
        Require all granted

        # Seguridad: ocultar listado de directorios
        DirectoryIndex index.html index.php
    </Directory>

    ErrorLog \${APACHE_LOG_DIR}/$DOMAIN-error.log
    CustomLog \${APACHE_LOG_DIR}/$DOMAIN-access.log combined

    # Headers de seguridad
    Header always set X-Content-Type-Options nosniff
    Header always set X-Frame-Options DENY
    Header always set X-XSS-Protection "1; mode=block"
</VirtualHost>
VHOST

    # Habilitar el sitio
    a2ensite "$DOMAIN.conf" > /dev/null 2>&1
    a2enmod headers > /dev/null 2>&1

    # Agregar entrada en /etc/hosts si no existe
    if ! grep -q "$DOMAIN" /etc/hosts; then
        echo "127.0.0.1    $DOMAIN www.$DOMAIN" >> /etc/hosts
        log_action "Entrada agregada en /etc/hosts para $DOMAIN"
    fi

    # Verificar configuración de Apache
    if apache2ctl configtest > /dev/null 2>&1; then
        systemctl reload apache2 > /dev/null 2>&1
        log_action "VirtualHost creado exitosamente: $DOMAIN"
        echo "SUCCESS: VirtualHost '$DOMAIN' creado en $CONF_FILE"
        echo "DOCROOT: $DOC_ROOT"
        echo "PORT: $PORT"
    else
        echo "ERROR: Configuración de Apache inválida. Revirtiendo..."
        a2dissite "$DOMAIN.conf" > /dev/null 2>&1
        rm -f "$CONF_FILE"
        exit 1
    fi
}

# ============================================================
# FUNCIÓN: Leer Configuración de Apache
# ============================================================
read_config() {
    local CONFIG_TYPE="${1:-all}"

    case "$CONFIG_TYPE" in
        "status")
            echo "=== ESTADO DE APACHE2 ==="
            if systemctl is-active --quiet apache2; then
                echo "STATUS: ACTIVO"
            else
                echo "STATUS: INACTIVO"
            fi
            echo "VERSION_BINARIO: $(apache2 -v 2>/dev/null | head -1)"
            echo "UPTIME: $(systemctl show apache2 --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2)"
            echo ""
            echo "=== CONFIGURACIÓN DE VERSIÓN HTTP ==="
            local _tokens=""
            local _sig=""
            local _tokens_src="(default del sistema)"
            local _sig_src="(default del sistema)"
            if [ -f "$SECURITY_CONF" ]; then
                _t=$(grep "^ServerTokens" "$SECURITY_CONF" 2>/dev/null | awk '{print $2}')
                _s=$(grep "^ServerSignature" "$SECURITY_CONF" 2>/dev/null | awk '{print $2}')
                [ -n "$_t" ] && _tokens="$_t" && _tokens_src="security.conf"
                [ -n "$_s" ] && _sig="$_s"    && _sig_src="security.conf"
            fi
            if [ -z "$_tokens" ]; then
                _t=$(grep "^ServerTokens" "$APACHE_CONF/apache2.conf" 2>/dev/null | awk '{print $2}')
                [ -n "$_t" ] && _tokens="$_t" && _tokens_src="apache2.conf"
            fi
            if [ -z "$_sig" ]; then
                _s=$(grep "^ServerSignature" "$APACHE_CONF/apache2.conf" 2>/dev/null | awk '{print $2}')
                [ -n "$_s" ] && _sig="$_s" && _sig_src="apache2.conf"
            fi
            _tokens="${_tokens:-OS}"
            _sig="${_sig:-On}"
            echo "ServerTokens: $_tokens  [$_tokens_src]"
            echo "ServerSignature: $_sig  [$_sig_src]"
            if [ "$_tokens" = "Prod" ]; then
                echo "VERSION_HTTP: OCULTA  (cabecera mostrará solo 'Apache')"
            else
                echo "VERSION_HTTP: EXPUESTA  (modo: $_tokens)"
            fi
            echo ""
            echo "=== CABECERA HTTP REAL ==="
            if command -v curl &>/dev/null; then
                local _probe _url _status_line _server
                _probe=$(probe_server_header)
                if [ -n "$_probe" ]; then
                    _url=$(echo "$_probe" | cut -d'|' -f1)
                    _status_line=$(echo "$_probe" | cut -d'|' -f2)
                    _server=$(echo "$_probe" | cut -d'|' -f3-)
                    echo "URL probada: $_url"
                    echo "Respuesta HTTP: $_status_line"
                    echo "Server Header: ${_server:-'(no presente en respuesta)'}"
                else
                    echo "Server Header: (sin respuesta usable en localhost)"
                fi
            else
                echo "Server Header: (instale curl: apt-get install curl)"
            fi
            ;;
        "virtualhosts")
            echo "=== VIRTUAL HOSTS CONFIGURADOS ==="
            if ls "$SITES_AVAILABLE"/*.conf > /dev/null 2>&1; then
                for conf in "$SITES_AVAILABLE"/*.conf; do
                    local name=$(basename "$conf" .conf)
                    local enabled="DESHABILITADO"
                    if [ -L "$SITES_ENABLED/$name.conf" ]; then
                        enabled="HABILITADO"
                    fi
                    local domain=$(grep -i "ServerName" "$conf" 2>/dev/null | head -1 | awk '{print $2}')
                    local docroot=$(grep -i "DocumentRoot" "$conf" 2>/dev/null | head -1 | awk '{print $2}')
                    local port=$(grep -i "VirtualHost" "$conf" 2>/dev/null | head -1 | grep -oP ':\K[0-9]+')
                    echo "VHOST|$name|$domain|$docroot|${port:-80}|$enabled"
                done
            else
                echo "INFO: No hay VirtualHosts configurados"
            fi
            ;;
        "modules")
            echo "=== MÓDULOS ACTIVOS ==="
            apache2ctl -M 2>/dev/null | grep -v "^Loaded" | sort
            ;;
        "config")
            echo "=== CONFIGURACIÓN PRINCIPAL ==="
            echo "ServerRoot: $APACHE_CONF"
            echo "Sites Available: $(ls $SITES_AVAILABLE/*.conf 2>/dev/null | wc -l)"
            echo "Sites Enabled: $(ls $SITES_ENABLED/*.conf 2>/dev/null | wc -l)"
            echo "Error Log: $(grep -i ErrorLog $APACHE_CONF/apache2.conf 2>/dev/null | head -1)"
            echo "PID File: $(grep -i PidFile $APACHE_CONF/apache2.conf 2>/dev/null | head -1)"
            apache2ctl -S 2>/dev/null
            ;;
        "ports")
            echo "=== PUERTOS EN ESCUCHA ==="
            ss -tlnp | grep apache2 2>/dev/null || netstat -tlnp 2>/dev/null | grep apache2
            ;;
        *)
            read_config "status"
            echo ""
            read_config "virtualhosts"
            echo ""
            read_config "config"
            ;;
    esac
}

# ============================================================
# FUNCIÓN: Mostrar/Ocultar Versión de Apache
# ============================================================
toggle_version() {
    local ACTION="$1"  # show | hide

    check_root

    # Asegurar que security.conf existe
    if [ ! -f "$SECURITY_CONF" ]; then
        cp "$APACHE_CONF/conf-available/security.conf" "$SECURITY_CONF" 2>/dev/null || \
        cat > "$SECURITY_CONF" << 'EOF'
ServerTokens OS
ServerSignature On
EOF
    fi

    case "$ACTION" in
        "hide")
            set_or_add_directive "$SECURITY_CONF" "ServerTokens" "Prod"
            set_or_add_directive "$SECURITY_CONF" "ServerSignature" "Off"
            set_or_add_directive "$APACHE_CONF/apache2.conf" "ServerTokens" "Prod"
            set_or_add_directive "$APACHE_CONF/apache2.conf" "ServerSignature" "Off"
            a2enconf security > /dev/null 2>&1
            if ! apache2ctl configtest > /dev/null 2>&1; then
                echo "ERROR: Configuración inválida al ocultar versión"
                exit 1
            fi
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Versión de Apache OCULTADA"
            echo "SUCCESS: Versión de Apache ocultada (ServerTokens Prod, ServerSignature Off)"
            ;;
        "show")
            set_or_add_directive "$SECURITY_CONF" "ServerTokens" "Full"
            set_or_add_directive "$SECURITY_CONF" "ServerSignature" "On"
            set_or_add_directive "$APACHE_CONF/apache2.conf" "ServerTokens" "Full"
            set_or_add_directive "$APACHE_CONF/apache2.conf" "ServerSignature" "On"
            a2enconf security > /dev/null 2>&1
            if ! apache2ctl configtest > /dev/null 2>&1; then
                echo "ERROR: Configuración inválida al mostrar versión"
                exit 1
            fi
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Versión de Apache MOSTRADA"
            echo "SUCCESS: Versión de Apache visible (ServerTokens Full, ServerSignature On)"
            ;;
        "status")
            local tokens=$(grep -E "^[[:space:]]*ServerTokens[[:space:]]+" "$SECURITY_CONF" 2>/dev/null | tail -1 | awk '{print $2}')
            local sig=$(grep -E "^[[:space:]]*ServerSignature[[:space:]]+" "$SECURITY_CONF" 2>/dev/null | tail -1 | awk '{print $2}')
            local tokens_ap=$(grep -E "^[[:space:]]*ServerTokens[[:space:]]+" "$APACHE_CONF/apache2.conf" 2>/dev/null | tail -1 | awk '{print $2}')
            local sig_ap=$(grep -E "^[[:space:]]*ServerSignature[[:space:]]+" "$APACHE_CONF/apache2.conf" 2>/dev/null | tail -1 | awk '{print $2}')

            echo "ServerTokens (security.conf): ${tokens:-N/A}"
            echo "ServerSignature (security.conf): ${sig:-N/A}"
            echo "ServerTokens (apache2.conf): ${tokens_ap:-N/A}"
            echo "ServerSignature (apache2.conf): ${sig_ap:-N/A}"

            local server_hdr=""
            local server_url=""
            if command -v curl &>/dev/null; then
                local _probe
                _probe=$(probe_server_header)
                if [ -n "$_probe" ]; then
                    server_url=$(echo "$_probe" | cut -d'|' -f1)
                    server_hdr=$(echo "$_probe" | cut -d'|' -f3-)
                fi
            fi
            [ -n "$server_url" ] && echo "URL probada: $server_url"
            echo "Server Header: ${server_hdr:-N/A}"

            if [ -n "$server_hdr" ] && ! echo "$server_hdr" | grep -q '/'; then
                echo "ESTADO: OCULTA"
            else
                echo "ESTADO: VISIBLE"
            fi
            ;;
        *)
            echo "ERROR: Acción inválida. Use: show | hide | status"
            exit 1
            ;;
    esac
}

# ============================================================
# FUNCIÓN: Ocultar Listado de Directorios
# ============================================================
hide_directory_listing() {
    local ACTION="$1"   # enable | disable | global
    local VHOST="${2:-}"

    check_root

    case "$ACTION" in
        "global_hide")
            # Configuración global en apache2.conf
            local GLOBAL_CONF="$APACHE_CONF/conf-available/no-directory-listing.conf"
            cat > "$GLOBAL_CONF" << 'EOF'
# Deshabilitar listado de directorios globalmente
<Directory />
    Options -Indexes
</Directory>

<Directory /var/www/>
    Options -Indexes +FollowSymLinks
    DirectoryIndex index.html index.php index.htm
</Directory>
EOF
            a2enconf no-directory-listing > /dev/null 2>&1
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Listado de directorios OCULTADO globalmente"
            echo "SUCCESS: Listado de directorios ocultado en todo el servidor"
            ;;
        "global_show")
            a2disconf no-directory-listing > /dev/null 2>&1
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Listado de directorios HABILITADO globalmente"
            echo "SUCCESS: Listado de directorios habilitado"
            ;;
        "vhost_hide")
            if [ -z "$VHOST" ]; then
                echo "ERROR: Especifique el VirtualHost"
                exit 1
            fi
            local CONF="$SITES_AVAILABLE/$VHOST.conf"
            if [ ! -f "$CONF" ]; then
                echo "ERROR: VirtualHost '$VHOST' no encontrado"
                exit 1
            fi
            sed -i 's/Options.*Indexes/Options -Indexes/' "$CONF"
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Listado de directorios ocultado en VirtualHost: $VHOST"
            echo "SUCCESS: Listado de directorios ocultado en $VHOST"
            ;;
        "status")
            if [ -L "$APACHE_CONF/conf-enabled/no-directory-listing.conf" ]; then
                echo "ESTADO: Listado de directorios OCULTO (global)"
            else
                echo "ESTADO: Listado de directorios VISIBLE"
            fi
            ;;
    esac
}

# ============================================================
# FUNCIÓN: Crear Backup
# ============================================================
create_backup() {
    local BACKUP_NAME="${1:-backup_$(date '+%Y%m%d_%H%M%S')}"
    local BACKUP_TYPE="${2:-full}"  # full | config | vhosts

    check_root

    mkdir -p "$BACKUP_DIR"

    local TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    local BACKUP_FILE="$BACKUP_DIR/${BACKUP_NAME}_${TIMESTAMP}.tar.gz"

    echo "Iniciando backup: $BACKUP_TYPE"
    echo "Destino: $BACKUP_FILE"

    case "$BACKUP_TYPE" in
        "full")
            tar -czf "$BACKUP_FILE" \
                "$APACHE_CONF/" \
                /var/www/ \
                --exclude=/var/www/html/wp-content/cache \
                2>/dev/null
            ;;
        "config")
            tar -czf "$BACKUP_FILE" \
                "$APACHE_CONF/" \
                2>/dev/null
            ;;
        "vhosts")
            tar -czf "$BACKUP_FILE" \
                "$SITES_AVAILABLE/" \
                "$SITES_ENABLED/" \
                2>/dev/null
            ;;
    esac

    if [ $? -eq 0 ]; then
        local SIZE=$(du -sh "$BACKUP_FILE" | awk '{print $1}')
        local CHECKSUM=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')
        
        # Guardar metadata
        cat > "${BACKUP_FILE%.tar.gz}.meta" << META
BACKUP_FILE=$BACKUP_FILE
BACKUP_NAME=$BACKUP_NAME
BACKUP_TYPE=$BACKUP_TYPE
TIMESTAMP=$TIMESTAMP
DATE=$(date '+%Y-%m-%d %H:%M:%S')
SIZE=$SIZE
SHA256=$CHECKSUM
IMMUTABLE=no
CREATED_BY=$(who am i | awk '{print $1}')
META

        log_action "Backup creado: $BACKUP_FILE (Tamaño: $SIZE)"
        echo "SUCCESS: Backup creado exitosamente"
        echo "FILE: $BACKUP_FILE"
        echo "SIZE: $SIZE"
        echo "SHA256: $CHECKSUM"
        echo "TYPE: $BACKUP_TYPE"
    else
        echo "ERROR: Fallo al crear backup"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
}

# ============================================================
# FUNCIÓN: Listar Backups
# ============================================================
list_backups() {
    echo "=== BACKUPS DISPONIBLES ==="
    echo "Directorio: $BACKUP_DIR"
    echo ""

    if [ ! -d "$BACKUP_DIR" ] || [ -z "$(ls $BACKUP_DIR/*.tar.gz 2>/dev/null)" ]; then
        echo "INFO: No hay backups disponibles"
        exit 0
    fi

    local COUNT=0
    for backup in "$BACKUP_DIR"/*.tar.gz; do
        [ -f "$backup" ] || continue
        COUNT=$((COUNT + 1))
        
        local name=$(basename "$backup")
        local size=$(du -sh "$backup" 2>/dev/null | awk '{print $1}')
        local date=$(stat -c %y "$backup" 2>/dev/null | cut -d. -f1)
        local immutable="no"
        local btype="unknown"
        local checksum="N/A"
        
        # Leer metadata si existe
        local meta="${backup%.tar.gz}.meta"
        if [ -f "$meta" ]; then
            btype=$(grep "^BACKUP_TYPE=" "$meta" | cut -d= -f2)
            immutable=$(grep "^IMMUTABLE=" "$meta" | cut -d= -f2)
            checksum=$(grep "^SHA256=" "$meta" | cut -d= -f2 | cut -c1-16)
        fi
        
        # Verificar atributo inmutable real
        if lsattr "$backup" 2>/dev/null | grep -q "\-i\-"; then
            immutable="yes"
        fi

        echo "BACKUP|$name|$size|$date|$btype|$immutable|$checksum..."
    done

    echo "TOTAL: $COUNT backup(s)"
}

# ============================================================
# FUNCIÓN: Asegurar Inmutabilidad del Backup
# ============================================================
set_backup_immutable() {
    local BACKUP_FILE="$1"
    local ACTION="${2:-lock}"  # lock | unlock

    check_root

    if [ ! -f "$BACKUP_FILE" ]; then
        # Buscar en el directorio de backups
        BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
    fi

    if [ ! -f "$BACKUP_FILE" ]; then
        echo "ERROR: Archivo de backup no encontrado: $BACKUP_FILE"
        exit 1
    fi

    case "$ACTION" in
        "lock")
            chattr +i "$BACKUP_FILE" 2>/dev/null
            if [ $? -eq 0 ]; then
                # Actualizar metadata
                local meta="${BACKUP_FILE%.tar.gz}.meta"
                if [ -f "$meta" ]; then
                    sed -i 's/^IMMUTABLE=.*/IMMUTABLE=yes/' "$meta"
                    chattr +i "$meta" 2>/dev/null
                fi
                log_action "Backup BLOQUEADO (inmutable): $BACKUP_FILE"
                echo "SUCCESS: Backup marcado como INMUTABLE"
                echo "FILE: $BACKUP_FILE"
                echo "IMMUTABLE: yes"
                echo "INFO: Solo root puede eliminar el atributo inmutable"
            else
                echo "ERROR: No se pudo establecer atributo inmutable (¿sistema de archivos compatible?)"
                exit 1
            fi
            ;;
        "unlock")
            chattr -i "$BACKUP_FILE" 2>/dev/null
            # Desbloquear metadata también
            local meta="${BACKUP_FILE%.tar.gz}.meta"
            if [ -f "$meta" ]; then
                chattr -i "$meta" 2>/dev/null
                sed -i 's/^IMMUTABLE=.*/IMMUTABLE=no/' "$meta"
            fi
            log_action "Backup DESBLOQUEADO: $BACKUP_FILE"
            echo "SUCCESS: Atributo inmutable removido del backup"
            echo "IMMUTABLE: no"
            ;;
        "status")
            if lsattr "$BACKUP_FILE" 2>/dev/null | grep -q "\-i\-"; then
                echo "IMMUTABLE: yes"
            else
                echo "IMMUTABLE: no"
            fi
            ;;
    esac
}

# ============================================================
# FUNCIÓN: Gestión de Autenticación Básica en VirtualHost
# ============================================================
manage_basic_auth() {
    local ACTION="$1"      # add | remove | add_user | del_user | list_users | status
    local DOMAIN="$2"
    local AUTH_DIR="${3:-/}"       # Directorio a proteger dentro del VHost
    local USERNAME="$4"
    local PASSWORD="$5"

    check_root

    local CONF="$SITES_AVAILABLE/$DOMAIN.conf"
    local HTPASSWD_DIR="/etc/apache2/.htpasswd"
    local HTPASSWD_FILE="$HTPASSWD_DIR/$DOMAIN.htpasswd"

    if [ -z "$DOMAIN" ]; then
        echo "ERROR: Dominio requerido"
        exit 1
    fi

    case "$ACTION" in
        "add")
            # Habilitar autenticación básica en el .conf del VirtualHost
            if [ ! -f "$CONF" ]; then
                echo "ERROR: VirtualHost '$DOMAIN' no encontrado en $CONF"
                exit 1
            fi

            # Verificar que apache2-utils está instalado (provee htpasswd)
            if ! command -v htpasswd &>/dev/null; then
                echo "INFO: Instalando apache2-utils..."
                apt-get install -y apache2-utils > /dev/null 2>&1
            fi

            mkdir -p "$HTPASSWD_DIR"
            chmod 750 "$HTPASSWD_DIR"

            # Crear archivo htpasswd si no existe
            if [ ! -f "$HTPASSWD_FILE" ]; then
                touch "$HTPASSWD_FILE"
                chmod 640 "$HTPASSWD_FILE"
                chown root:www-data "$HTPASSWD_FILE"
                echo "INFO: Archivo htpasswd creado: $HTPASSWD_FILE"
            fi

            # Obtener DocumentRoot del VHost
            local DOCROOT=$(grep -i "DocumentRoot" "$CONF" | awk '{print $2}')
            local AUTH_PATH="$DOCROOT$AUTH_DIR"
            [ "$AUTH_DIR" = "/" ] && AUTH_PATH="$DOCROOT"

            # Detectar si ya existe bloque de autenticación en el conf
            if grep -q "AuthType Basic" "$CONF"; then
                echo "INFO: Autenticación básica ya configurada en $DOMAIN"
                echo "INFO: Use 'add_user' para agregar usuarios"
                exit 0
            fi

            # Inyectar directiva AuthType Basic en el bloque <Directory>
            # Buscamos el bloque <Directory DocRoot> y le agregamos auth
            python3 - "$CONF" "$DOCROOT" "$HTPASSWD_FILE" "$AUTH_DIR" << 'PYEOF'
import sys, re

conf_file = sys.argv[1]
docroot   = sys.argv[2]
htpasswd  = sys.argv[3]
auth_dir  = sys.argv[4].rstrip("/") or "/"

with open(conf_file) as f:
    content = f.read()

auth_block = f"""
    # --- Autenticación Básica (Apache2 Manager) ---
    <Directory "{docroot}{'' if auth_dir == '/' else auth_dir}">
        AuthType Basic
        AuthName "Área Restringida - {docroot.split('/')[-1]}"
        AuthUserFile {htpasswd}
        Require valid-user
        # Heredar AllowOverride
        AllowOverride AuthConfig
    </Directory>
    # --- Fin Autenticación Básica ---"""

# Insertar justo antes de </VirtualHost>
content = re.sub(
    r'(</VirtualHost>)',
    auth_block + r'\n\1',
    content, count=1
)

with open(conf_file, 'w') as f:
    f.write(content)

print("PYOK")
PYEOF

            if [ $? -ne 0 ]; then
                echo "ERROR: No se pudo modificar el archivo de configuración"
                exit 1
            fi

            # Habilitar módulo auth_basic
            a2enmod auth_basic authn_file > /dev/null 2>&1

            # Verificar y recargar
            if apache2ctl configtest > /dev/null 2>&1; then
                systemctl reload apache2 > /dev/null 2>&1
                log_action "Autenticación básica ACTIVADA en $DOMAIN (dir: $AUTH_DIR)"
                echo "SUCCESS: Autenticación básica configurada en '$DOMAIN'"
                echo "HTPASSWD: $HTPASSWD_FILE"
                echo "INFO: Agregue usuarios con: manage_basic_auth add_user $DOMAIN <usuario> <contraseña>"
            else
                echo "ERROR: Configuración inválida. Revise $CONF"
                exit 1
            fi
            ;;

        "remove")
            if [ ! -f "$CONF" ]; then
                echo "ERROR: VirtualHost '$DOMAIN' no encontrado"
                exit 1
            fi

            # Eliminar bloque de autenticación básica del .conf
            python3 - "$CONF" << 'PYEOF'
import sys, re
conf_file = sys.argv[1]
with open(conf_file) as f:
    content = f.read()

# Eliminar el bloque inyectado entre los comentarios marcadores
content = re.sub(
    r'\n\s*# --- Autenticación Básica.*?# --- Fin Autenticación Básica ---\n',
    '\n',
    content, flags=re.DOTALL
)
with open(conf_file, 'w') as f:
    f.write(content)
print("PYOK")
PYEOF

            if apache2ctl configtest > /dev/null 2>&1; then
                systemctl reload apache2 > /dev/null 2>&1
                log_action "Autenticación básica ELIMINADA de $DOMAIN"
                echo "SUCCESS: Autenticación básica eliminada de '$DOMAIN'"
                echo "INFO: El archivo htpasswd NO fue eliminado: $HTPASSWD_FILE"
            else
                echo "ERROR: Configuración inválida tras eliminar auth"
                exit 1
            fi
            ;;

        "add_user")
            # Argumentos: add_user <domain> <username> <password>
            # $1=ACTION $2=DOMAIN → aquí ya estamos dentro del case
            # USERNAME y PASSWORD vienen de $3 y $4 cuando se llama como:
            #   manage_basic_auth add_user <domain> <user> <pass>
            # Pero la función los recibe como $4 y $5 desde el dispatcher
            # Reasignamos localmente para claridad:
            local _USER="$3"
            local _PASS="$4"
            # Si vinieron en posición $4/$5 (llamada con AUTH_DIR vacío), usar esos
            [ -z "$_USER" ] && _USER="$USERNAME"
            [ -z "$_PASS" ] && _PASS="$PASSWORD"

            if [ -z "$_USER" ] || [ -z "$_PASS" ]; then
                echo "ERROR: Usuario y contraseña son requeridos"
                echo "DEBUG: USER='$_USER' PASS_LEN=${#_PASS}"
                exit 1
            fi
            mkdir -p "$HTPASSWD_DIR"

            if [ ! -f "$HTPASSWD_FILE" ]; then
                htpasswd -cb "$HTPASSWD_FILE" "$_USER" "$_PASS"
            else
                htpasswd -b "$HTPASSWD_FILE" "$_USER" "$_PASS"
            fi

            if [ $? -eq 0 ]; then
                chown root:www-data "$HTPASSWD_FILE"
                chmod 640 "$HTPASSWD_FILE"
                log_action "Usuario '$_USER' agregado a $DOMAIN"
                echo "SUCCESS: Usuario '$_USER' agregado en $DOMAIN"
                echo "HTPASSWD: $HTPASSWD_FILE"
            else
                echo "ERROR: Fallo al agregar usuario"
                exit 1
            fi
            ;;

        "del_user")
            # Argumentos: del_user <domain> <username>
            local _USER="$3"
            [ -z "$_USER" ] && _USER="$USERNAME"

            if [ -z "$_USER" ]; then
                echo "ERROR: Usuario requerido"
                exit 1
            fi
            if [ ! -f "$HTPASSWD_FILE" ]; then
                echo "ERROR: No existe archivo htpasswd para $DOMAIN"
                exit 1
            fi
            htpasswd -D "$HTPASSWD_FILE" "$_USER"
            if [ $? -eq 0 ]; then
                log_action "Usuario '$_USER' eliminado de $DOMAIN"
                echo "SUCCESS: Usuario '$_USER' eliminado"
            else
                echo "ERROR: No se pudo eliminar el usuario '$_USER' (¿existe?)"
                exit 1
            fi
            ;;

        "list_users")
            echo "=== USUARIOS HTPASSWD: $DOMAIN ==="
            echo "ARCHIVO: $HTPASSWD_FILE"
            if [ -f "$HTPASSWD_FILE" ]; then
                local COUNT=0
                while IFS=: read -r user _rest; do
                    [ -n "$user" ] && echo "USER|$user" && COUNT=$((COUNT+1))
                done < "$HTPASSWD_FILE"
                echo "TOTAL: $COUNT usuario(s)"
            else
                echo "INFO: Sin usuarios configurados (htpasswd no existe)"
            fi
            ;;

        "status")
            echo "=== ESTADO AUTH BÁSICA: $DOMAIN ==="
            if [ ! -f "$CONF" ]; then
                echo "AUTH: VirtualHost no encontrado"
                exit 1
            fi
            if grep -q "AuthType Basic" "$CONF"; then
                echo "AUTH: ACTIVA"
                local auth_name=$(grep "AuthName" "$CONF" | head -1 | sed 's/.*AuthName\s*//' | tr -d '"')
                local auth_file=$(grep "AuthUserFile" "$CONF" | head -1 | awk '{print $2}')
                echo "AuthName: $auth_name"
                echo "AuthUserFile: $auth_file"
                # Contar usuarios
                if [ -f "${auth_file:-$HTPASSWD_FILE}" ]; then
                    local USERS=$(grep -c "." "${auth_file:-$HTPASSWD_FILE}" 2>/dev/null || echo 0)
                    echo "USUARIOS: $USERS registrado(s)"
                else
                    echo "USUARIOS: Sin archivo htpasswd aún"
                fi
            else
                echo "AUTH: INACTIVA"
            fi
            ;;

        *)
            echo "ERROR: Acción desconocida: $ACTION"
            exit 1
            ;;
    esac
}

# ============================================================
# FUNCIÓN: Backup con Rsync
# ============================================================
rsync_backup() {
    local SRC="${1}"          # Origen
    local DEST="${2}"         # Destino (local o user@host:/path)
    local BACKUP_NAME="${3:-rsync_$(date '+%Y%m%d_%H%M%S')}"
    local EXTRA_OPTS="${4:-}"  # Opciones adicionales rsync

    check_root

    if [ -z "$SRC" ] || [ -z "$DEST" ]; then
        echo "ERROR: Se requieren origen y destino"
        exit 1
    fi

    # Verificar que rsync está instalado
    if ! command -v rsync &> /dev/null; then
        echo "INFO: Instalando rsync..."
        apt-get install -y rsync > /dev/null 2>&1
    fi

    mkdir -p "$BACKUP_DIR/rsync_logs"

    local TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    local LOG_RSYNC="$BACKUP_DIR/rsync_logs/${BACKUP_NAME}_${TIMESTAMP}.log"

    echo "Iniciando Rsync Backup..."
    echo "ORIGEN:  $SRC"
    echo "DESTINO: $DEST"

    # Construir comando rsync
    # -a  = archive (preserva permisos, timestamps, links, etc.)
    # -v  = verbose
    # -z  = compresión en tránsito
    # --progress         = progreso
    # --delete           = elimina en destino lo que no existe en origen
    # --backup           = conserva versiones anteriores
    # --backup-dir       = directorio para versiones antiguas con fecha
    # --link-dest        = hardlinks para backups incrementales eficientes
    # --exclude          = excluir patrones

    local BACKUP_VERSIONED="$DEST/.versions/$(date '+%Y-%m-%d_%H%M%S')"
    local LATEST_LINK="$DEST/.latest"

    # Detectar si es destino remoto (contiene @)
    if echo "$DEST" | grep -q "@"; then
        # Destino remoto SSH
        rsync -avz \
            --progress \
            --delete \
            --backup \
            --backup-dir="$BACKUP_VERSIONED" \
            --exclude="*.swp" \
            --exclude="*.tmp" \
            --exclude="__pycache__" \
            --log-file="$LOG_RSYNC" \
            $EXTRA_OPTS \
            "$SRC" "$DEST/current/" 2>&1 | tee -a "$LOG_RSYNC"
    else
        # Destino local — usa --link-dest para incrementales eficientes
        mkdir -p "$DEST/current" "$DEST/.versions"

        local PREV_LINK=""
        if [ -d "$DEST/current" ]; then
            PREV_LINK="--link-dest=$DEST/current"
        fi

        rsync -av \
            --progress \
            --delete \
            --backup \
            --backup-dir="$DEST/.versions/$(date '+%Y-%m-%d_%H%M%S')" \
            --exclude="*.swp" \
            --exclude="*.tmp" \
            --exclude="*.pid" \
            --exclude="cache/" \
            --log-file="$LOG_RSYNC" \
            $EXTRA_OPTS \
            "$SRC" "$DEST/current/" 2>&1 | tee -a "$LOG_RSYNC"
    fi

    local EXIT_CODE=$?
    local TRANSFERRED=$(grep "sent" "$LOG_RSYNC" 2>/dev/null | tail -1)

    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 23 ]; then
        # Guardar metadata del rsync
        cat > "$BACKUP_DIR/rsync_logs/${BACKUP_NAME}_${TIMESTAMP}.meta" << META
RSYNC_NAME=$BACKUP_NAME
TIMESTAMP=$TIMESTAMP
DATE=$(date '+%Y-%m-%d %H:%M:%S')
SOURCE=$SRC
DESTINATION=$DEST
EXIT_CODE=$EXIT_CODE
LOG=$LOG_RSYNC
TRANSFERRED=$TRANSFERRED
META
        log_action "Rsync completado: $SRC → $DEST"
        echo "SUCCESS: Rsync backup completado"
        echo "LOG: $LOG_RSYNC"
        echo "STATS: $TRANSFERRED"
    else
        echo "ERROR: Rsync falló con código $EXIT_CODE"
        echo "LOG: $LOG_RSYNC"
        exit 1
    fi
}

# ============================================================
# FUNCIÓN: Programar Backup con Cron
# ============================================================
CRON_FILE="/etc/cron.d/apache2_manager_backup"
CRON_SCRIPT="/usr/local/bin/apache2_backup_cron.sh"

schedule_backup() {
    local ACTION="$1"   # add | remove | list | run_now | list_jobs

    check_root

    case "$ACTION" in
        "add")
            # Parámetros: add <nombre> <minuto> <hora> <dia_mes> <mes> <dia_sem> <tipo> <src> <dest> [rsync|tar]
            local JOB_NAME="$2"
            local MINUTE="$3"
            local HOUR="$4"
            local DOM="$5"     # day of month
            local MONTH="$6"
            local DOW="$7"     # day of week
            local BTYPE="$8"   # config | vhosts | full | rsync
            local SRC="$9"
            local DEST="${10:-$BACKUP_DIR}"
            local METHOD="${11:-tar}"  # tar | rsync

            if [ -z "$JOB_NAME" ] || [ -z "$MINUTE" ]; then
                echo "ERROR: Parámetros insuficientes para programar el backup"
                exit 1
            fi

            # Crear script ejecutor del cron si no existe
            _create_cron_runner

            # Construir línea cron
            local CRON_CMD
            if [ "$METHOD" = "rsync" ]; then
                CRON_CMD="bash $CRON_SCRIPT rsync_backup \"$SRC\" \"$DEST\" \"$JOB_NAME\""
            else
                CRON_CMD="bash $CRON_SCRIPT create_backup \"$JOB_NAME\" \"$BTYPE\""
            fi

            # Agregar al archivo cron.d
            # Formato: minuto hora dia_mes mes dia_semana usuario comando
            local CRON_LINE="$MINUTE $HOUR $DOM $MONTH $DOW root $CRON_CMD >> /var/log/apache2_backup_cron.log 2>&1"

            # Verificar si ya existe un job con ese nombre
            if grep -q "# JOB:$JOB_NAME" "$CRON_FILE" 2>/dev/null; then
                # Remover el anterior
                sed -i "/# JOB:$JOB_NAME/,+1d" "$CRON_FILE"
            fi

            # Crear/agregar al archivo cron.d
            if [ ! -f "$CRON_FILE" ]; then
                cat > "$CRON_FILE" << CRONHEADER
# Apache2 Manager - Backup Programado
# Generado por Apache2 Manager
# NO EDITAR MANUALMENTE - Use la interfaz gráfica
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
CRONHEADER
            fi

            # Agregar línea con comentario identificador
            echo "" >> "$CRON_FILE"
            echo "# JOB:$JOB_NAME TYPE:$BTYPE METHOD:$METHOD SRC:$SRC DEST:$DEST" >> "$CRON_FILE"
            echo "$CRON_LINE" >> "$CRON_FILE"

            # Ajustar permisos del archivo cron.d
            chmod 644 "$CRON_FILE"
            chown root:root "$CRON_FILE"

            log_action "Backup programado creado: $JOB_NAME ($MINUTE $HOUR $DOM $MONTH $DOW)"
            echo "SUCCESS: Backup programado '$JOB_NAME'"
            echo "SCHEDULE: $MINUTE $HOUR $DOM $MONTH $DOW"
            echo "METHOD: $METHOD"
            echo "TYPE: $BTYPE"
            echo "SOURCE: $SRC"
            echo "DEST: $DEST"
            ;;

        "remove")
            local JOB_NAME="$2"
            if [ -z "$JOB_NAME" ]; then
                echo "ERROR: Especifique el nombre del job"
                exit 1
            fi
            if [ ! -f "$CRON_FILE" ]; then
                echo "ERROR: No hay jobs programados"
                exit 1
            fi
            if grep -q "# JOB:$JOB_NAME" "$CRON_FILE"; then
                sed -i "/^$/N;/# JOB:$JOB_NAME/,+1d" "$CRON_FILE"
                log_action "Job eliminado: $JOB_NAME"
                echo "SUCCESS: Job '$JOB_NAME' eliminado"
            else
                echo "ERROR: Job '$JOB_NAME' no encontrado"
                exit 1
            fi
            ;;

        "list_jobs")
            echo "=== JOBS DE BACKUP PROGRAMADOS ==="
            if [ ! -f "$CRON_FILE" ]; then
                echo "INFO: No hay jobs programados"
                exit 0
            fi
            local COUNT=0
            while IFS= read -r line; do
                if [[ "$line" == "# JOB:"* ]]; then
                    # Extraer metadatos del comentario
                    local job_name=$(echo "$line" | grep -oP 'JOB:\K\S+')
                    local job_type=$(echo "$line" | grep -oP 'TYPE:\K\S+')
                    local job_method=$(echo "$line" | grep -oP 'METHOD:\K\S+')
                    local job_src=$(echo "$line" | grep -oP 'SRC:\K\S+')
                    local job_dest=$(echo "$line" | grep -oP 'DEST:\K\S+')
                    # Leer la línea siguiente (la del cron real)
                    IFS= read -r cron_line
                    # Extraer expresión cron (primeros 5 campos)
                    local schedule=$(echo "$cron_line" | awk '{print $1,$2,$3,$4,$5}')
                    COUNT=$((COUNT + 1))
                    echo "JOB|$job_name|$schedule|$job_type|$job_method|$job_src|$job_dest"
                fi
            done < "$CRON_FILE"
            echo "TOTAL: $COUNT job(s)"
            ;;

        "run_now")
            local JOB_NAME="$2"
            if [ -z "$JOB_NAME" ]; then
                echo "ERROR: Especifique el nombre del job"
                exit 1
            fi
            if [ ! -f "$CRON_FILE" ]; then
                echo "ERROR: No hay jobs programados"
                exit 1
            fi
            # Extraer y ejecutar el comando del job
            local CMD=$(grep -A1 "# JOB:$JOB_NAME" "$CRON_FILE" 2>/dev/null | \
                        tail -1 | awk '{for(i=6;i<=NF;i++) printf $i" "; print ""}')
            if [ -z "$CMD" ]; then
                echo "ERROR: Job '$JOB_NAME' no encontrado"
                exit 1
            fi
            echo "Ejecutando job manualmente: $JOB_NAME"
            echo "Comando: $CMD"
            eval "$CMD"
            ;;

        "list_logs")
            echo "=== LOGS DE EJECUCIÓN ==="
            if [ -f "/var/log/apache2_backup_cron.log" ]; then
                tail -50 /var/log/apache2_backup_cron.log
            else
                echo "INFO: Sin registros de ejecución aún"
            fi
            ;;

        "view_cron")
            echo "=== CONTENIDO DE $CRON_FILE ==="
            if [ -f "$CRON_FILE" ]; then
                cat "$CRON_FILE"
            else
                echo "INFO: Archivo cron no existe"
            fi
            ;;

        *)
            echo "ERROR: Acción desconocida: $ACTION"
            exit 1
            ;;
    esac
}

_create_cron_runner() {
    # Script que cron ejecuta directamente (carga el backend)
    cat > "$CRON_SCRIPT" << RUNNER
#!/bin/bash
# Apache2 Manager - Cron Runner
# Generado automáticamente - No editar

BACKEND="/usr/local/bin/apache_manager.sh"
# Buscar backend en ubicaciones conocidas
for path in /opt/apache2_manager/apache_manager.sh /usr/local/bin/apache_manager.sh; do
    [ -f "\$path" ] && BACKEND="\$path" && break
done

LOG="/var/log/apache2_backup_cron.log"
echo "[\\$(date '+%Y-%m-%d %H:%M:%S')] === Cron job ejecutado: \$@ ===" >> "\$LOG"
bash "\$BACKEND" "\$@" >> "\$LOG" 2>&1
echo "[\\$(date '+%Y-%m-%d %H:%M:%S')] Finalizado con código: \$?" >> "\$LOG"
RUNNER
    chmod +x "$CRON_SCRIPT"
}

# ============================================================
# FUNCIÓN: Eliminar VirtualHost
# ============================================================
delete_virtualhost() {
    local DOMAIN="$1"
    local DELETE_FILES="${2:-no}"

    check_root

    if [ -z "$DOMAIN" ]; then
        echo "ERROR: Dominio requerido"
        exit 1
    fi

    local CONF="$SITES_AVAILABLE/$DOMAIN.conf"
    if [ ! -f "$CONF" ]; then
        echo "ERROR: VirtualHost '$DOMAIN' no encontrado"
        exit 1
    fi

    # Deshabilitar sitio
    a2dissite "$DOMAIN.conf" > /dev/null 2>&1
    
    # Obtener DocumentRoot antes de eliminar
    local DOCROOT=$(grep -i "DocumentRoot" "$CONF" | awk '{print $2}')
    
    # Eliminar configuración
    rm -f "$CONF"
    
    # Eliminar de /etc/hosts
    sed -i "/$DOMAIN/d" /etc/hosts
    
    # Eliminar archivos si se solicita
    if [ "$DELETE_FILES" = "yes" ] && [ -n "$DOCROOT" ] && [ -d "$DOCROOT" ]; then
        rm -rf "$DOCROOT"
        echo "INFO: Archivos eliminados: $DOCROOT"
    fi

    systemctl reload apache2 > /dev/null 2>&1
    log_action "VirtualHost eliminado: $DOMAIN"
    echo "SUCCESS: VirtualHost '$DOMAIN' eliminado"
}

# ============================================================
# DISPATCHER - Manejo de argumentos
# ============================================================
COMMAND="$1"
shift

case "$COMMAND" in
    "create_vhost")
        create_virtualhost "$@"
        ;;
    "read_config")
        read_config "$@"
        ;;
    "toggle_version")
        toggle_version "$@"
        ;;
    "hide_listing")
        hide_directory_listing "$@"
        ;;
    "create_backup")
        create_backup "$@"
        ;;
    "list_backups")
        list_backups
        ;;
    "set_immutable")
        set_backup_immutable "$@"
        ;;
    "delete_vhost")
        delete_virtualhost "$@"
        ;;
    "apache_control")
        check_root
        case "$1" in
            start|stop|restart|reload|status)
                systemctl "$1" apache2
                echo "SUCCESS: apache2 $1 ejecutado"
                ;;
        esac
        ;;
    "rsync_backup")
        rsync_backup "$@"
        ;;
    "schedule_backup")
        schedule_backup "$@"
        ;;
    "basic_auth")
        manage_basic_auth "$@"
        ;;
    *)
        echo "Uso: $0 <comando> [argumentos]"
        echo ""
        echo "Comandos disponibles:"
        echo "  create_vhost <dominio> <docroot> [email] [puerto]"
        echo "  read_config [status|virtualhosts|modules|config|ports]"
        echo "  toggle_version <show|hide|status>"
        echo "  hide_listing <global_hide|global_show|vhost_hide|status> [vhost]"
        echo "  create_backup [nombre] [full|config|vhosts]"
        echo "  list_backups"
        echo "  set_immutable <archivo> [lock|unlock|status]"
        echo "  delete_vhost <dominio> [yes|no]"
        echo "  apache_control <start|stop|restart|reload|status>"
        echo "  rsync_backup <origen> <destino> [nombre] [opciones_extra]"
        echo "  schedule_backup <add|remove|list_jobs|run_now|list_logs|view_cron> [args...]"
        exit 1
        ;;
esac
