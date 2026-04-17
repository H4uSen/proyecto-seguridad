#!/bin/bash
# ============================================================
# Instalador - Apache2 Manager
# ============================================================

set -e

INSTALL_DIR="/opt/apache2_manager"
DESKTOP_FILE="/usr/share/applications/apache2-manager.desktop"
BIN_LINK="/usr/local/bin/apache2-manager"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}"
cat << 'BANNER'
 ┌─────────────────────────────────────────┐
 │        Apache2 Manager Installer        │
 │           Frontend + Backend            │
 └─────────────────────────────────────────┘
BANNER
echo -e "${NC}"

# Verificar root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}[ERROR]${NC} Ejecute como root: sudo bash install.sh"
    exit 1
fi

echo -e "${YELLOW}[1/6]${NC} Verificando dependencias..."
MISSING=""
for pkg in apache2 python3 python3-tk; do
    if ! dpkg -l "$pkg" &> /dev/null; then
        MISSING="$MISSING $pkg"
    fi
done

if [ -n "$MISSING" ]; then
    echo -e "${YELLOW}     Instalando:${NC}$MISSING"
    apt-get update -qq
    apt-get install -y $MISSING
fi
echo -e "${GREEN}     ✓ Dependencias OK${NC}"

echo -e "${YELLOW}[2/6]${NC} Creando directorio de instalación..."
mkdir -p "$INSTALL_DIR"
mkdir -p /var/backups/apache2_manager
mkdir -p /var/log
echo -e "${GREEN}     ✓ Directorios creados${NC}"

echo -e "${YELLOW}[3/6]${NC} Copiando archivos..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/apache2_manager.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/apache_manager.sh"  "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/apache_manager.sh"
chmod +x "$INSTALL_DIR/apache2_manager.py"
echo -e "${GREEN}     ✓ Archivos copiados${NC}"

echo -e "${YELLOW}[4/6]${NC} Configurando sudoers..."
SUDOERS_FILE="/etc/sudoers.d/apache2_manager"
cat > "$SUDOERS_FILE" << SUDOERS
# Apache2 Manager - Permisos sudo sin contraseña
%sudo ALL=(ALL) NOPASSWD: /bin/bash $INSTALL_DIR/apache_manager.sh *
%adm  ALL=(ALL) NOPASSWD: /bin/bash $INSTALL_DIR/apache_manager.sh *
SUDOERS
chmod 440 "$SUDOERS_FILE"
echo -e "${GREEN}     ✓ Sudoers configurado${NC}"

echo -e "${YELLOW}[5/6]${NC} Creando lanzador..."
cat > "$BIN_LINK" << LAUNCHER
#!/bin/bash
cd "$INSTALL_DIR"
exec python3 "$INSTALL_DIR/apache2_manager.py" "\$@"
LAUNCHER
chmod +x "$BIN_LINK"

cat > "$DESKTOP_FILE" << DESKTOP
[Desktop Entry]
Version=1.0
Type=Application
Name=Apache2 Manager
Comment=Gestión de Apache2 - VHosts, Config, Backups
Exec=$BIN_LINK
Icon=applications-internet
Categories=System;Administration;
Terminal=false
Keywords=apache;web;server;virtualhost;
DESKTOP
echo -e "${GREEN}     ✓ Lanzador creado${NC}"

echo -e "${YELLOW}[6/6]${NC} Verificando instalación..."
if python3 -c "import tkinter" 2>/dev/null; then
    echo -e "${GREEN}     ✓ Tkinter disponible${NC}"
else
    echo -e "${RED}     ✗ Tkinter no disponible${NC}"
fi
if systemctl is-active --quiet apache2; then
    echo -e "${GREEN}     ✓ Apache2 activo${NC}"
else
    echo -e "${YELLOW}     ⚠ Apache2 no está activo (inicie con: sudo systemctl start apache2)${NC}"
fi

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Instalación completada exitosamente!   ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Para ejecutar: ${BLUE}apache2-manager${NC}"
echo -e "  O directamente: ${BLUE}python3 $INSTALL_DIR/apache2_manager.py${NC}"
echo ""
