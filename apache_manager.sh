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
            echo "VERSION: $(apache2 -v 2>/dev/null | head -1)"
            echo "UPTIME: $(systemctl show apache2 --property=ActiveEnterTimestamp 2>/dev/null | cut -d= -f2)"
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
            sed -i 's/^ServerTokens.*/ServerTokens Prod/' "$SECURITY_CONF"
            sed -i 's/^ServerSignature.*/ServerSignature Off/' "$SECURITY_CONF"
            # También en apache2.conf
            if grep -q "ServerTokens" "$APACHE_CONF/apache2.conf" 2>/dev/null; then
                sed -i 's/^ServerTokens.*/ServerTokens Prod/' "$APACHE_CONF/apache2.conf"
            else
                echo "ServerTokens Prod" >> "$APACHE_CONF/apache2.conf"
            fi
            a2enconf security > /dev/null 2>&1
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Versión de Apache OCULTADA"
            echo "SUCCESS: Versión de Apache ocultada (ServerTokens Prod, ServerSignature Off)"
            ;;
        "show")
            sed -i 's/^ServerTokens.*/ServerTokens Full/' "$SECURITY_CONF"
            sed -i 's/^ServerSignature.*/ServerSignature On/' "$SECURITY_CONF"
            a2enconf security > /dev/null 2>&1
            systemctl reload apache2 > /dev/null 2>&1
            log_action "Versión de Apache MOSTRADA"
            echo "SUCCESS: Versión de Apache visible (ServerTokens Full, ServerSignature On)"
            ;;
        "status")
            local tokens=$(grep "^ServerTokens" "$SECURITY_CONF" 2>/dev/null | awk '{print $2}')
            local sig=$(grep "^ServerSignature" "$SECURITY_CONF" 2>/dev/null | awk '{print $2}')
            echo "ServerTokens: ${tokens:-OS (default)}"
            echo "ServerSignature: ${sig:-On (default)}"
            if [ "$tokens" = "Prod" ]; then
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
