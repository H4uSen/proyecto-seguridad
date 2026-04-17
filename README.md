# Apache2 Manager
## Herramienta de Administración de Apache2 — Frontend Tkinter + Backend Shell

---

## 📦 Archivos del Proyecto

```
apache2_manager/
├── apache2_manager.py    # Frontend Tkinter (Python 3)
├── apache_manager.sh     # Backend Shell Script (Bash)
├── install.sh            # Script de instalación
└── README.md             # Esta documentación
```

---

## ⚡ Instalación Rápida

```bash
# 1. Dar permisos de ejecución
chmod +x install.sh apache_manager.sh apache2_manager.py

# 2. Instalar (requiere sudo)
sudo bash install.sh

# 3. Ejecutar
apache2-manager
```

---

## 🚀 Funcionalidades

### 🌐 Tab 1 — Virtual Hosts
- **Crear** VirtualHosts con dominio, DocumentRoot, email y puerto
- **Habilitar** automáticamente el sitio en Apache
- **Listar** todos los VirtualHosts (habilitados/deshabilitados)
- **Eliminar** VirtualHosts con opción de borrar archivos
- Agrega automáticamente entradas en `/etc/hosts`
- Crea `index.html` de prueba en el DocumentRoot

### ⚙ Tab 2 — Configuración Apache
- **Estado** del servicio en tiempo real
- **Virtual Hosts** activos con detalles
- **Módulos** cargados
- **Configuración global** y puertos
- Control del servicio: **Iniciar / Detener / Reiniciar / Recargar**

### 🔒 Tab 3 — Seguridad
**Visibilidad de Versión:**
- `ServerTokens Prod` → Oculta la versión (recomendado)
- `ServerSignature Off` → Sin firma en páginas de error
- Indicador visual del estado actual

**Listado de Directorios:**
- `Options -Indexes` global → Oculta contenido sin index.html
- Aplicar a VirtualHost específico
- Indicador visual del estado

### 💾 Tab 4 — Backups
- **Crear** backups de: configuración, VHosts, o completo
- **Listar** backups con tamaño, fecha, tipo y hash SHA256
- **Inmutabilidad** con `chattr +i` — protección máxima
- Bloquear/Desbloquear archivo de backup
- Ver detalles completos de cada backup

---

## 🛠 Uso del Backend desde CLI

```bash
# Crear VirtualHost
sudo bash apache_manager.sh create_vhost dominio.local /var/www/dominio admin@dominio.local 80

# Ver configuración
sudo bash apache_manager.sh read_config status
sudo bash apache_manager.sh read_config virtualhosts

# Ocultar versión
sudo bash apache_manager.sh toggle_version hide

# Ocultar listado de directorios
sudo bash apache_manager.sh hide_listing global_hide

# Crear backup
sudo bash apache_manager.sh create_backup mi_backup config

# Listar backups
sudo bash apache_manager.sh list_backups

# Hacer inmutable un backup
sudo bash apache_manager.sh set_immutable mi_backup_20241201.tar.gz lock

# Control Apache
sudo bash apache_manager.sh apache_control restart
```

---

## 📋 Requisitos

| Componente    | Versión mínima |
|---------------|----------------|
| Python        | 3.7+           |
| Tkinter       | Incluido en Python |
| Apache2       | 2.4+           |
| Sistema       | Ubuntu/Debian  |
| Permisos      | sudo/root      |

```bash
# Instalar dependencias manualmente
sudo apt-get install apache2 python3 python3-tk
```

---

## 🔧 Configuración de Paths

Los directorios por defecto son:

```bash
BACKUP_DIR="/var/backups/apache2_manager"
APACHE_CONF="/etc/apache2"
LOG_FILE="/var/log/apache2_manager.log"
```

---

## 🔐 Seguridad

- Los comandos se ejecutan via `sudo` con política específica en sudoers
- Los backups con `chattr +i` no pueden ser eliminados ni modificados
- SHA256 checksum para verificar integridad de backups
- Metadata de cada backup guardada en archivo `.meta`

---

## 📝 Logs

```bash
# Ver log de actividad
tail -f /var/log/apache2_manager.log
```
