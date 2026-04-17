#!/usr/bin/env python3
# ============================================================
# Apache2 Manager - Frontend Tkinter
# Gestión completa de Apache2 en servidor Linux
# ============================================================

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import os
import sys
import threading
import json
from datetime import datetime
import shutil

# ─── Constantes de Configuración ───────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_SCRIPT = os.path.join(SCRIPT_DIR, "apache_manager.sh")
APP_VERSION = "1.0.0"

# ─── Paleta de colores (Dark Professional Theme) ────────────
COLORS = {
    "bg_dark":      "#0D1117",
    "bg_card":      "#161B22",
    "bg_panel":     "#1C2128",
    "bg_input":     "#21262D",
    "border":       "#30363D",
    "accent":       "#E8692A",
    "accent_dark":  "#B84E1A",
    "accent_glow":  "#FF7A35",
    "success":      "#2EA043",
    "success_light":"#56D364",
    "warning":      "#D29922",
    "warning_light":"#F0C040",
    "danger":       "#DA3633",
    "danger_light": "#F85149",
    "info":         "#1F6FEB",
    "info_light":   "#58A6FF",
    "text_primary": "#E6EDF3",
    "text_secondary":"#8B949E",
    "text_muted":   "#484F58",
    "white":        "#FFFFFF",
    "apache_red":   "#CC2222",
}

FONTS = {
    "title":    ("Courier New", 20, "bold"),
    "heading":  ("Courier New", 13, "bold"),
    "subhead":  ("Courier New", 11, "bold"),
    "body":     ("Courier New", 10),
    "small":    ("Courier New", 9),
    "mono":     ("Courier New", 10),
    "label":    ("Courier New", 10, "bold"),
    "btn":      ("Courier New", 10, "bold"),
    "icon":     ("Courier New", 16, "bold"),
}

# ─── Helper: Ejecutar comando shell ─────────────────────────
def run_command(command, use_sudo=True, timeout=30):
    """Ejecuta comandos shell con o sin sudo"""
    try:
        if use_sudo:
            cmd = ["sudo", "bash", BACKEND_SCRIPT] + command.split()
        else:
            cmd = ["bash", BACKEND_SCRIPT] + command.split()
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "ERROR: Tiempo de espera agotado", 1
    except Exception as e:
        return "", f"ERROR: {str(e)}", 1

def run_command_args(args, timeout=30):
    """Ejecuta comandos con lista de argumentos"""
    try:
        cmd = ["sudo", "bash", BACKEND_SCRIPT] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1


# ══════════════════════════════════════════════════════════════
# WIDGET BASE: Botón Estilizado
# ══════════════════════════════════════════════════════════════
class StyledButton(tk.Button):
    def __init__(self, parent, text, command=None, style="primary",
                 icon="", width=None, **kwargs):
        style_map = {
            "primary":  (COLORS["accent"],      COLORS["accent_dark"],  COLORS["white"]),
            "success":  (COLORS["success"],      "#237A33",              COLORS["white"]),
            "danger":   (COLORS["danger"],       "#A02020",              COLORS["white"]),
            "warning":  (COLORS["warning"],      "#A07015",              COLORS["white"]),
            "info":     (COLORS["info"],         "#1456B8",              COLORS["white"]),
            "ghost":    (COLORS["bg_input"],     COLORS["border"],       COLORS["text_primary"]),
            "dark":     (COLORS["bg_panel"],     COLORS["bg_card"],      COLORS["text_secondary"]),
        }
        bg, hover_bg, fg = style_map.get(style, style_map["primary"])

        lbl = f"  {icon} {text}  " if icon else f"  {text}  "
        w = {"width": width} if width else {}

        super().__init__(
            parent, text=lbl, command=command, fg=fg, bg=bg,
            font=FONTS["btn"], relief="flat", cursor="hand2",
            bd=0, activebackground=hover_bg, activeforeground=fg,
            **w, **kwargs
        )
        self._bg = bg
        self._hbg = hover_bg
        self.bind("<Enter>", lambda e: self.config(bg=self._hbg))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

    def update_style(self, style):
        style_map = {
            "primary":  (COLORS["accent"],  COLORS["accent_dark"]),
            "success":  (COLORS["success"], "#237A33"),
            "danger":   (COLORS["danger"],  "#A02020"),
            "ghost":    (COLORS["bg_input"],COLORS["border"]),
        }
        bg, hbg = style_map.get(style, style_map["ghost"])
        self._bg = bg
        self._hbg = hbg
        self.config(bg=bg)


# ══════════════════════════════════════════════════════════════
# WIDGET: Card con título
# ══════════════════════════════════════════════════════════════
class Card(tk.Frame):
    def __init__(self, parent, title="", accent_color=None, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"],
                         highlightbackground=COLORS["border"],
                         highlightthickness=1, **kwargs)
        if title:
            color = accent_color or COLORS["accent"]
            hdr = tk.Frame(self, bg=COLORS["bg_panel"],
                           highlightbackground=COLORS["border"],
                           highlightthickness=0)
            hdr.pack(fill="x")
            tk.Label(hdr, text=f"  {title}", font=FONTS["subhead"],
                     bg=COLORS["bg_panel"], fg=color).pack(
                side="left", pady=8)
            tk.Frame(hdr, bg=color, height=2).pack(
                side="bottom", fill="x")


# ══════════════════════════════════════════════════════════════
# WIDGET: Campo de entrada estilizado
# ══════════════════════════════════════════════════════════════
class LabeledEntry(tk.Frame):
    def __init__(self, parent, label, placeholder="", width=30, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)
        tk.Label(self, text=label, font=FONTS["label"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(
            anchor="w", pady=(4, 2))
        self.var = tk.StringVar()
        self.entry = tk.Entry(
            self, textvariable=self.var, width=width,
            bg=COLORS["bg_input"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"],
            font=FONTS["mono"], relief="flat", bd=6,
            highlightbackground=COLORS["border"],
            highlightcolor=COLORS["accent"],
            highlightthickness=1
        )
        self.entry.pack(fill="x", ipady=4)
        if placeholder:
            self.entry.insert(0, placeholder)
            self.entry.config(fg=COLORS["text_muted"])
            self.entry.bind("<FocusIn>",  lambda e: self._clear(placeholder))
            self.entry.bind("<FocusOut>", lambda e: self._restore(placeholder))

    def _clear(self, ph):
        if self.var.get() == ph:
            self.entry.delete(0, "end")
            self.entry.config(fg=COLORS["text_primary"])

    def _restore(self, ph):
        if not self.var.get():
            self.entry.insert(0, ph)
            self.entry.config(fg=COLORS["text_muted"])

    def get(self):
        return self.var.get()

    def set(self, val):
        self.var.set(val)


# ══════════════════════════════════════════════════════════════
# PANEL: Consola de Output
# ══════════════════════════════════════════════════════════════
class ConsolePanel(tk.Frame):
    def __init__(self, parent, height=10, **kwargs):
        super().__init__(parent, bg=COLORS["bg_card"], **kwargs)
        header = tk.Frame(self, bg=COLORS["bg_panel"])
        header.pack(fill="x")
        tk.Label(header, text="  ▶ CONSOLA DE SALIDA",
                 font=FONTS["small"], bg=COLORS["bg_panel"],
                 fg=COLORS["text_muted"]).pack(side="left", pady=5)
        StyledButton(header, "Limpiar", command=self.clear,
                     style="dark", icon="✕").pack(side="right", padx=5, pady=3)

        self.text = scrolledtext.ScrolledText(
            self, height=height, bg="#0A0E13",
            fg=COLORS["success_light"], font=("Courier New", 10),
            relief="flat", bd=0, wrap="word",
            insertbackground=COLORS["accent"],
            selectbackground=COLORS["accent_dark"]
        )
        self.text.pack(fill="both", expand=True, padx=2, pady=2)
        self.text.tag_config("success", foreground=COLORS["success_light"])
        self.text.tag_config("error",   foreground=COLORS["danger_light"])
        self.text.tag_config("warning", foreground=COLORS["warning_light"])
        self.text.tag_config("info",    foreground=COLORS["info_light"])
        self.text.tag_config("dim",     foreground=COLORS["text_muted"])
        self.text.tag_config("title",   foreground=COLORS["accent"],
                              font=("Courier New", 11, "bold"))

    def write(self, msg, tag=""):
        self.text.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.text.insert("end", f"[{ts}] ", "dim")
        self.text.insert("end", msg + "\n", tag)
        self.text.see("end")
        self.text.config(state="disabled")

    def clear(self):
        self.text.config(state="normal")
        self.text.delete("1.0", "end")
        self.text.config(state="disabled")

    def write_output(self, stdout, stderr, returncode):
        if stdout:
            for line in stdout.splitlines():
                if line.startswith("SUCCESS"):
                    self.write(line, "success")
                elif line.startswith("ERROR"):
                    self.write(line, "error")
                elif line.startswith("WARNING"):
                    self.write(line, "warning")
                elif line.startswith("INFO"):
                    self.write(line, "info")
                elif line.startswith("==="):
                    self.write(line, "title")
                else:
                    self.write(line)
        if stderr and returncode != 0:
            self.write(f"STDERR: {stderr}", "error")


# ══════════════════════════════════════════════════════════════
# TAB 1: Virtual Hosts
# ══════════════════════════════════════════════════════════════
class VHostTab(tk.Frame):
    def __init__(self, parent, console):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.console = console
        self._build()

    def _build(self):
        # Split: form + list
        paned = tk.PanedWindow(self, orient="horizontal",
                                bg=COLORS["bg_dark"], sashwidth=4,
                                sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Formulario Crear VHost ──
        form_card = Card(self, "➕  CREAR VIRTUAL HOST",
                         accent_color=COLORS["accent"])
        paned.add(form_card, minsize=350)

        body = tk.Frame(form_card, bg=COLORS["bg_card"])
        body.pack(fill="both", expand=True, padx=15, pady=10)

        self.f_domain   = LabeledEntry(body, "Dominio *",    "ejemplo.local", 28)
        self.f_docroot  = LabeledEntry(body, "DocumentRoot *","/var/www/ejemplo", 28)
        self.f_email    = LabeledEntry(body, "Admin Email",  "admin@ejemplo.local", 28)
        self.f_port     = LabeledEntry(body, "Puerto",       "80", 10)

        for w in [self.f_domain, self.f_docroot, self.f_email, self.f_port]:
            w.pack(fill="x", pady=3)

        # Botón para seleccionar directorio
        dir_frame = tk.Frame(body, bg=COLORS["bg_card"])
        dir_frame.pack(fill="x", pady=2)
        StyledButton(dir_frame, "Seleccionar Directorio",
                     command=self._browse_dir,
                     style="ghost", icon="📁").pack(side="left")

        tk.Frame(body, bg=COLORS["border"], height=1).pack(
            fill="x", pady=10)

        # Botones
        btn_frame = tk.Frame(body, bg=COLORS["bg_card"])
        btn_frame.pack(fill="x")
        StyledButton(btn_frame, "Crear VirtualHost",
                     command=self._create_vhost,
                     style="primary", icon="🚀").pack(
            side="left", padx=(0, 8))
        StyledButton(btn_frame, "Limpiar",
                     command=self._clear_form,
                     style="ghost", icon="🗑").pack(side="left")

        # Info box
        info = tk.Frame(body, bg=COLORS["bg_panel"],
                        highlightbackground=COLORS["info"],
                        highlightthickness=1)
        info.pack(fill="x", pady=(15, 0))
        tk.Label(info, text="ℹ  El VirtualHost será habilitado\n    automáticamente en Apache",
                 font=FONTS["small"], bg=COLORS["bg_panel"],
                 fg=COLORS["info_light"], justify="left").pack(
            padx=10, pady=8, anchor="w")

        # ── Lista de VHosts ──
        list_card = Card(self, "📋  VIRTUAL HOSTS ACTIVOS",
                         accent_color=COLORS["info"])
        paned.add(list_card, minsize=350)

        list_body = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_body.pack(fill="both", expand=True, padx=5, pady=5)

        # Toolbar
        toolbar = tk.Frame(list_body, bg=COLORS["bg_card"])
        toolbar.pack(fill="x", pady=(0, 5))
        StyledButton(toolbar, "Actualizar",
                     command=self._refresh_list,
                     style="info", icon="↻").pack(side="left", padx=2)
        StyledButton(toolbar, "Eliminar",
                     command=self._delete_vhost,
                     style="danger", icon="🗑").pack(side="left", padx=2)

        # Treeview
        cols = ("Dominio", "DocumentRoot", "Puerto", "Estado")
        self.tree = ttk.Treeview(list_body, columns=cols,
                                  show="headings", height=12)
        widths = [140, 160, 60, 90]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        scroll_y = ttk.Scrollbar(list_body, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")

        self._style_tree()
        self._refresh_list()

    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                         background=COLORS["bg_input"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["bg_input"],
                         rowheight=26, font=FONTS["small"],
                         borderwidth=0)
        style.configure("Treeview.Heading",
                         background=COLORS["bg_panel"],
                         foreground=COLORS["accent"],
                         font=FONTS["label"], borderwidth=0)
        style.map("Treeview",
                  background=[("selected", COLORS["accent_dark"])],
                  foreground=[("selected", COLORS["white"])])

    def _browse_dir(self):
        path = filedialog.askdirectory(title="Seleccionar DocumentRoot")
        if path:
            self.f_docroot.set(path)

    def _create_vhost(self):
        domain  = self.f_domain.get().strip()
        docroot = self.f_docroot.get().strip()
        email   = self.f_email.get().strip()
        port    = self.f_port.get().strip() or "80"

        if not domain or domain == "ejemplo.local":
            messagebox.showwarning("Validación", "El dominio es requerido")
            return
        if not docroot or docroot == "/var/www/ejemplo":
            messagebox.showwarning("Validación", "DocumentRoot es requerido")
            return

        self.console.write(f"Creando VirtualHost: {domain}...", "info")

        def task():
            args = ["create_vhost", domain, docroot]
            if email and email != "admin@ejemplo.local":
                args.append(email)
            else:
                args.append(f"webmaster@{domain}")
            args.append(port)
            out, err, code = run_command_args(args)
            self.after(0, lambda: self._on_create(out, err, code))

        threading.Thread(target=task, daemon=True).start()

    def _on_create(self, out, err, code):
        self.console.write_output(out, err, code)
        if code == 0:
            self._refresh_list()
            messagebox.showinfo("Éxito", "VirtualHost creado exitosamente")

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        def task():
            out, err, code = run_command_args(["read_config", "virtualhosts"])
            self.after(0, lambda: self._populate_tree(out))

        threading.Thread(target=task, daemon=True).start()

    def _populate_tree(self, output):
        for line in output.splitlines():
            if line.startswith("VHOST|"):
                parts = line.split("|")
                if len(parts) >= 6:
                    _, name, domain, docroot, port, status = parts[:6]
                    tag = "enabled" if status == "HABILITADO" else "disabled"
                    self.tree.insert("", "end",
                                      values=(domain, docroot, port, status),
                                      tags=(tag,))

        self.tree.tag_configure("enabled",  foreground=COLORS["success_light"])
        self.tree.tag_configure("disabled", foreground=COLORS["text_muted"])

    def _delete_vhost(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un VirtualHost")
            return
        domain = self.tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirmar",
                                f"¿Eliminar VirtualHost '{domain}'?"):
            out, err, code = run_command_args(["delete_vhost", domain])
            self.console.write_output(out, err, code)
            self._refresh_list()

    def _clear_form(self):
        for f in [self.f_domain, self.f_docroot, self.f_email, self.f_port]:
            f.set("")


# ══════════════════════════════════════════════════════════════
# TAB 2: Configuración Apache
# ══════════════════════════════════════════════════════════════
class ConfigTab(tk.Frame):
    def __init__(self, parent, console):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.console = console
        self._build()

    def _build(self):
        # Top: botones de sección
        top = tk.Frame(self, bg=COLORS["bg_dark"])
        top.pack(fill="x", padx=10, pady=(10, 5))

        tk.Label(top, text="Vista de Configuración:",
                 font=FONTS["label"], bg=COLORS["bg_dark"],
                 fg=COLORS["text_secondary"]).pack(side="left", padx=(0, 10))

        sections = [
            ("Estado",        "status",        "info"),
            ("Virtual Hosts", "virtualhosts",  "primary"),
            ("Módulos",       "modules",       "ghost"),
            ("Config Global", "config",        "ghost"),
            ("Puertos",       "ports",         "warning"),
        ]
        for label, section, style in sections:
            StyledButton(top, label,
                         command=lambda s=section: self._load_section(s),
                         style=style).pack(side="left", padx=3)

        # Control de Apache
        ctrl_frame = tk.Frame(self, bg=COLORS["bg_dark"])
        ctrl_frame.pack(fill="x", padx=10, pady=5)
        
        ctrl_card = Card(ctrl_frame, "⚙  CONTROL DEL SERVICIO APACHE",
                         accent_color=COLORS["apache_red"])
        ctrl_card.pack(fill="x")
        
        btn_row = tk.Frame(ctrl_card, bg=COLORS["bg_card"])
        btn_row.pack(fill="x", padx=15, pady=10)

        controls = [
            ("▶ Iniciar",    "start",   "success"),
            ("⏹ Detener",   "stop",    "danger"),
            ("↺ Reiniciar",  "restart", "warning"),
            ("↻ Recargar",   "reload",  "info"),
        ]
        for label, action, style in controls:
            StyledButton(btn_row, label,
                         command=lambda a=action: self._apache_control(a),
                         style=style).pack(side="left", padx=5)

        # Status indicator
        self.status_var = tk.StringVar(value="● Verificando...")
        self.status_label = tk.Label(btn_row, textvariable=self.status_var,
                                      font=FONTS["label"], bg=COLORS["bg_card"],
                                      fg=COLORS["text_muted"])
        self.status_label.pack(side="right", padx=10)

        # Output área
        output_card = Card(self, "📄  CONFIGURACIÓN",
                           accent_color=COLORS["text_secondary"])
        output_card.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.output = scrolledtext.ScrolledText(
            output_card, bg="#0A0E13", fg=COLORS["text_primary"],
            font=("Courier New", 10), relief="flat", bd=0,
            wrap="none", state="disabled"
        )
        self.output.pack(fill="both", expand=True, padx=5, pady=5)
        self.output.tag_config("key",   foreground=COLORS["info_light"])
        self.output.tag_config("value", foreground=COLORS["success_light"])
        self.output.tag_config("head",  foreground=COLORS["accent"],
                                font=("Courier New", 11, "bold"))
        self.output.tag_config("dim",   foreground=COLORS["text_muted"])

        self._load_section("status")
        self._update_status()

    def _load_section(self, section):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", f"Cargando {section}...\n", "dim")
        self.output.config(state="disabled")

        def task():
            out, err, code = run_command_args(["read_config", section])
            self.after(0, lambda: self._render_output(out, err))

        threading.Thread(target=task, daemon=True).start()

    def _render_output(self, out, err):
        self.output.config(state="normal")
        self.output.delete("1.0", "end")

        for line in out.splitlines():
            if line.startswith("==="):
                self.output.insert("end", f"\n{line}\n", "head")
            elif ":" in line and not line.startswith(" "):
                k, _, v = line.partition(":")
                self.output.insert("end", f"{k}:", "key")
                self.output.insert("end", f"{v}\n", "value")
            elif line.startswith("VHOST|"):
                parts = line.split("|")
                if len(parts) >= 6:
                    self.output.insert("end",
                        f"  → {parts[2]:<25} {parts[3]:<30} "
                        f":{parts[4]}  [{parts[5]}]\n", "value")
            else:
                self.output.insert("end", line + "\n")

        if err:
            self.output.insert("end", f"\nERROR: {err}\n", "dim")

        self.output.config(state="disabled")

    def _apache_control(self, action):
        self.console.write(f"Apache2 → {action.upper()}...", "info")

        def task():
            out, err, code = run_command_args(["apache_control", action])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._update_status()
            ))

        threading.Thread(target=task, daemon=True).start()

    def _update_status(self):
        def task():
            try:
                r = subprocess.run(
                    ["systemctl", "is-active", "apache2"],
                    capture_output=True, text=True, timeout=5
                )
                status = r.stdout.strip()
                self.after(0, lambda: self._set_status_label(status))
            except Exception:
                self.after(0, lambda: self._set_status_label("unknown"))

        threading.Thread(target=task, daemon=True).start()

    def _set_status_label(self, status):
        if status == "active":
            self.status_var.set("● Apache2 ACTIVO")
            self.status_label.config(fg=COLORS["success_light"])
        elif status == "inactive":
            self.status_var.set("● Apache2 DETENIDO")
            self.status_label.config(fg=COLORS["danger_light"])
        else:
            self.status_var.set("● Estado desconocido")
            self.status_label.config(fg=COLORS["text_muted"])


# ══════════════════════════════════════════════════════════════
# TAB 3: Seguridad (Versión + Directorios)
# ══════════════════════════════════════════════════════════════
class SecurityTab(tk.Frame):
    def __init__(self, parent, console):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.console = console
        self._version_state = "unknown"
        self._listing_state = "unknown"
        self._build()

    def _build(self):
        container = tk.Frame(self, bg=COLORS["bg_dark"])
        container.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Columna izquierda: Versión ──
        left = tk.Frame(container, bg=COLORS["bg_dark"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))

        ver_card = Card(left, "🔒  VISIBILIDAD DE VERSIÓN",
                        accent_color=COLORS["warning"])
        ver_card.pack(fill="both", expand=True)

        vb = tk.Frame(ver_card, bg=COLORS["bg_card"])
        vb.pack(fill="both", expand=True, padx=15, pady=15)

        # Estado
        self.ver_indicator = tk.Label(
            vb, text="◉  VERIFICANDO...",
            font=("Courier New", 14, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["text_muted"]
        )
        self.ver_indicator.pack(pady=(10, 5))

        desc = """ServerTokens controla qué información
del servidor se envía en las cabeceras HTTP.

• Prod   → Solo "Apache" (recomendado)
• OS     → Apache + Sistema Operativo
• Full   → Versión completa (inseguro)

ServerSignature controla el pie de página
en páginas de error de Apache."""

        desc_box = tk.Label(vb, text=desc, font=FONTS["small"],
                             bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
                             justify="left", wraplength=260)
        desc_box.pack(fill="x", pady=10, ipady=10, ipadx=10)

        tk.Frame(vb, bg=COLORS["border"], height=1).pack(fill="x", pady=10)

        btn_row = tk.Frame(vb, bg=COLORS["bg_card"])
        btn_row.pack()

        StyledButton(btn_row, "OCULTAR Versión",
                     command=lambda: self._toggle_version("hide"),
                     style="success", icon="🛡").pack(
            side="left", padx=5, pady=5)
        StyledButton(btn_row, "MOSTRAR Versión",
                     command=lambda: self._toggle_version("show"),
                     style="warning", icon="👁").pack(
            side="left", padx=5, pady=5)

        StyledButton(vb, "Verificar Estado",
                     command=self._check_version_status,
                     style="ghost", icon="↻").pack(pady=5)

        # ── Columna derecha: Directorios ──
        right = tk.Frame(container, bg=COLORS["bg_dark"])
        right.pack(side="right", fill="both", expand=True, padx=(5, 0))

        dir_card = Card(right, "📁  LISTADO DE DIRECTORIOS",
                        accent_color=COLORS["info"])
        dir_card.pack(fill="both", expand=True)

        db = tk.Frame(dir_card, bg=COLORS["bg_card"])
        db.pack(fill="both", expand=True, padx=15, pady=15)

        self.dir_indicator = tk.Label(
            db, text="◉  VERIFICANDO...",
            font=("Courier New", 14, "bold"),
            bg=COLORS["bg_card"], fg=COLORS["text_muted"]
        )
        self.dir_indicator.pack(pady=(10, 5))

        dir_desc = """Cuando un directorio no tiene archivo
index.html, Apache puede mostrar su
contenido completo.

Opciones -Indexes impide que los usuarios
vean la estructura de archivos del servidor.

Se recomienda SIEMPRE deshabilitar el
listado de directorios en producción."""

        dir_desc_box = tk.Label(
            db, text=dir_desc, font=FONTS["small"],
            bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
            justify="left", wraplength=260
        )
        dir_desc_box.pack(fill="x", pady=10, ipady=10, ipadx=10)

        tk.Frame(db, bg=COLORS["border"], height=1).pack(fill="x", pady=10)

        btn_row2 = tk.Frame(db, bg=COLORS["bg_card"])
        btn_row2.pack()

        StyledButton(btn_row2, "OCULTAR Listado",
                     command=lambda: self._toggle_listing("global_hide"),
                     style="success", icon="🔒").pack(
            side="left", padx=5, pady=5)
        StyledButton(btn_row2, "MOSTRAR Listado",
                     command=lambda: self._toggle_listing("global_show"),
                     style="danger", icon="🔓").pack(
            side="left", padx=5, pady=5)

        # VHost específico
        vhost_frame = tk.Frame(db, bg=COLORS["bg_card"])
        vhost_frame.pack(fill="x", pady=5)

        self.vhost_entry = LabeledEntry(
            vhost_frame, "Aplicar a VHost específico:",
            "dominio.local", 20)
        self.vhost_entry.pack(fill="x")

        StyledButton(db, "Ocultar en VHost",
                     command=self._hide_vhost_listing,
                     style="ghost", icon="🔒").pack(pady=3)

        self._check_version_status()
        self._check_listing_status()

    def _toggle_version(self, action):
        def task():
            out, err, code = run_command_args(["toggle_version", action])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._check_version_status()
            ))
        threading.Thread(target=task, daemon=True).start()

    def _check_version_status(self):
        def task():
            out, err, code = run_command_args(["toggle_version", "status"])
            self.after(0, lambda: self._update_ver_indicator(out))
        threading.Thread(target=task, daemon=True).start()

    def _update_ver_indicator(self, output):
        if "OCULTA" in output:
            self.ver_indicator.config(
                text="🛡  VERSIÓN OCULTA", fg=COLORS["success_light"])
        elif "VISIBLE" in output:
            self.ver_indicator.config(
                text="⚠  VERSIÓN VISIBLE", fg=COLORS["warning_light"])
        else:
            self.ver_indicator.config(
                text="?  DESCONOCIDO", fg=COLORS["text_muted"])

    def _toggle_listing(self, action):
        def task():
            out, err, code = run_command_args(["hide_listing", action])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._check_listing_status()
            ))
        threading.Thread(target=task, daemon=True).start()

    def _check_listing_status(self):
        def task():
            out, err, code = run_command_args(["hide_listing", "status"])
            self.after(0, lambda: self._update_dir_indicator(out))
        threading.Thread(target=task, daemon=True).start()

    def _update_dir_indicator(self, output):
        if "OCULTO" in output:
            self.dir_indicator.config(
                text="🔒  LISTADO OCULTO", fg=COLORS["success_light"])
        else:
            self.dir_indicator.config(
                text="⚠  LISTADO VISIBLE", fg=COLORS["warning_light"])

    def _hide_vhost_listing(self):
        vhost = self.vhost_entry.get().strip()
        if not vhost or vhost == "dominio.local":
            messagebox.showwarning("Aviso", "Ingrese el nombre del VirtualHost")
            return
        out, err, code = run_command_args(
            ["hide_listing", "vhost_hide", vhost])
        self.console.write_output(out, err, code)


# ══════════════════════════════════════════════════════════════
# TAB 4: Backups
# ══════════════════════════════════════════════════════════════
class BackupTab(tk.Frame):
    def __init__(self, parent, console):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.console = console
        self._build()

    def _build(self):
        # Top split: form + actions
        top = tk.Frame(self, bg=COLORS["bg_dark"])
        top.pack(fill="x", padx=10, pady=10)

        # ── Crear Backup ──
        create_card = Card(top, "💾  CREAR BACKUP",
                           accent_color=COLORS["success"])
        create_card.pack(side="left", fill="both", expand=True, padx=(0, 5))

        cb = tk.Frame(create_card, bg=COLORS["bg_card"])
        cb.pack(fill="both", padx=15, pady=10)

        self.backup_name = LabeledEntry(
            cb, "Nombre del Backup:",
            f"backup_{datetime.now().strftime('%Y%m%d')}", 25)
        self.backup_name.pack(fill="x", pady=3)

        tk.Label(cb, text="Tipo de Backup:", font=FONTS["label"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(
            anchor="w", pady=(8, 3))

        self.backup_type = tk.StringVar(value="config")
        types = [
            ("Configuración Apache",  "config"),
            ("VirtualHosts solamente","vhosts"),
            ("Backup Completo",        "full"),
        ]
        for label, val in types:
            tk.Radiobutton(
                cb, text=label, variable=self.backup_type, value=val,
                bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                selectcolor=COLORS["bg_input"],
                activebackground=COLORS["bg_card"],
                font=FONTS["body"]
            ).pack(anchor="w", padx=10)

        tk.Frame(cb, bg=COLORS["border"], height=1).pack(
            fill="x", pady=10)

        StyledButton(cb, "Crear Backup Ahora",
                     command=self._create_backup,
                     style="success", icon="💾").pack(fill="x", ipady=4)

        # ── Inmutabilidad ──
        imm_card = Card(top, "🔐  INMUTABILIDAD",
                        accent_color=COLORS["warning"])
        imm_card.pack(side="right", fill="both", expand=True, padx=(5, 0))

        ib = tk.Frame(imm_card, bg=COLORS["bg_card"])
        ib.pack(fill="both", padx=15, pady=10)

        desc = ("El atributo inmutable (chattr +i) impide\n"
                "que el archivo sea modificado, renombrado\n"
                "o eliminado incluso por root.\n\n"
                "Solo puede ser removido con:\n"
                "  sudo chattr -i archivo")
        tk.Label(ib, text=desc, font=FONTS["small"],
                 bg=COLORS["bg_panel"], fg=COLORS["text_secondary"],
                 justify="left").pack(fill="x", ipady=8, ipadx=10, pady=5)

        imm_btn_row = tk.Frame(ib, bg=COLORS["bg_card"])
        imm_btn_row.pack(fill="x", pady=5)
        StyledButton(imm_btn_row, "🔒 BLOQUEAR",
                     command=lambda: self._set_immutable("lock"),
                     style="warning").pack(side="left", padx=3)
        StyledButton(imm_btn_row, "🔓 DESBLOQUEAR",
                     command=lambda: self._set_immutable("unlock"),
                     style="ghost").pack(side="left", padx=3)
        StyledButton(imm_btn_row, "Estado",
                     command=lambda: self._set_immutable("status"),
                     style="dark").pack(side="left", padx=3)

        # ── Lista de Backups ──
        list_card = Card(self, "📋  BACKUPS DISPONIBLES",
                         accent_color=COLORS["info"])
        list_card.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        lb_toolbar = tk.Frame(list_card, bg=COLORS["bg_card"])
        lb_toolbar.pack(fill="x", padx=5, pady=5)

        StyledButton(lb_toolbar, "↻ Actualizar",
                     command=self._refresh_backups,
                     style="info").pack(side="left", padx=3)
        StyledButton(lb_toolbar, "Ver Detalles",
                     command=self._show_backup_details,
                     style="ghost").pack(side="left", padx=3)

        lb_body = tk.Frame(list_card, bg=COLORS["bg_card"])
        lb_body.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        cols = ("Nombre", "Tamaño", "Fecha", "Tipo", "Inmutable", "SHA256")
        self.btree = ttk.Treeview(lb_body, columns=cols,
                                   show="headings", height=8)
        widths = [220, 70, 155, 90, 80, 140]
        for col, w in zip(cols, widths):
            self.btree.heading(col, text=col)
            self.btree.column(col, width=w, anchor="center")

        bscroll = ttk.Scrollbar(lb_body, orient="vertical",
                                 command=self.btree.yview)
        self.btree.configure(yscrollcommand=bscroll.set)
        self.btree.pack(side="left", fill="both", expand=True)
        bscroll.pack(side="right", fill="y")

        self._refresh_backups()

    def _create_backup(self):
        name = self.backup_name.get().strip()
        btype = self.backup_type.get()
        self.console.write(f"Creando backup ({btype}): {name}...", "info")

        def task():
            out, err, code = run_command_args(
                ["create_backup", name, btype])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._refresh_backups()
            ))

        threading.Thread(target=task, daemon=True).start()

    def _refresh_backups(self):
        for item in self.btree.get_children():
            self.btree.delete(item)

        def task():
            out, err, code = run_command_args(["list_backups"])
            self.after(0, lambda: self._populate_backups(out))

        threading.Thread(target=task, daemon=True).start()

    def _populate_backups(self, output):
        for line in output.splitlines():
            if line.startswith("BACKUP|"):
                parts = line.split("|")
                if len(parts) >= 7:
                    _, name, size, date, btype, immutable, sha = parts[:7]
                    tag = "immutable" if immutable == "yes" else ""
                    self.btree.insert("", "end",
                                       values=(name, size, date, btype,
                                               "🔒 SÍ" if immutable == "yes" else "No",
                                               sha + "..."),
                                       tags=(tag,))

        self.btree.tag_configure("immutable", foreground=COLORS["warning_light"])

    def _get_selected_backup(self):
        sel = self.btree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un backup de la lista")
            return None
        return self.btree.item(sel[0])["values"][0]

    def _set_immutable(self, action):
        name = self._get_selected_backup()
        if not name:
            return
        self.console.write(
            f"Inmutabilidad → {action.upper()}: {name}", "info")

        def task():
            out, err, code = run_command_args(
                ["set_immutable", name, action])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._refresh_backups()
            ))

        threading.Thread(target=task, daemon=True).start()

    def _show_backup_details(self):
        name = self._get_selected_backup()
        if not name:
            return
        sel = self.btree.selection()[0]
        vals = self.btree.item(sel)["values"]
        detail = (f"Archivo:    {vals[0]}\n"
                  f"Tamaño:     {vals[1]}\n"
                  f"Fecha:      {vals[2]}\n"
                  f"Tipo:       {vals[3]}\n"
                  f"Inmutable:  {vals[4]}\n"
                  f"SHA256:     {vals[5]}")
        messagebox.showinfo(f"Detalles: {vals[0]}", detail)


# ══════════════════════════════════════════════════════════════
# APLICACIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════
class Apache2Manager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Apache2 Manager v{APP_VERSION}")
        self.geometry("1150x780")
        self.minsize(900, 650)
        self.configure(bg=COLORS["bg_dark"])
        self._set_icon()
        self._build_ui()
        self._check_backend()

    def _set_icon(self):
        try:
            self.iconbitmap("")
        except Exception:
            pass

    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=COLORS["bg_card"],
                           highlightbackground=COLORS["border"],
                           highlightthickness=1)
        header.pack(fill="x")

        logo_frame = tk.Frame(header, bg=COLORS["bg_card"])
        logo_frame.pack(side="left", padx=20, pady=12)

        tk.Label(logo_frame, text="⬡",
                 font=("Courier New", 28, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(
            side="left", padx=(0, 10))

        title_stack = tk.Frame(logo_frame, bg=COLORS["bg_card"])
        title_stack.pack(side="left")
        tk.Label(title_stack, text="APACHE2 MANAGER",
                 font=("Courier New", 16, "bold"),
                 bg=COLORS["bg_card"], fg=COLORS["text_primary"]).pack(
            anchor="w")
        tk.Label(title_stack,
                 text=f"Server Administration Tool  ·  v{APP_VERSION}",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"]).pack(anchor="w")

        # Status bar en header
        self.status_frame = tk.Frame(header, bg=COLORS["bg_card"])
        self.status_frame.pack(side="right", padx=20)

        self.apache_status = tk.Label(
            self.status_frame, text="● Comprobando...",
            font=FONTS["label"], bg=COLORS["bg_card"],
            fg=COLORS["text_muted"]
        )
        self.apache_status.pack()

        tk.Label(self.status_frame,
                 text=datetime.now().strftime("%d/%m/%Y"),
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"]).pack()

        # Línea de acento
        tk.Frame(self, bg=COLORS["accent"], height=2).pack(fill="x")

        # ── Notebook (Tabs) ──
        style = ttk.Style()
        style.configure("Custom.TNotebook",
                         background=COLORS["bg_dark"],
                         borderwidth=0)
        style.configure("Custom.TNotebook.Tab",
                         background=COLORS["bg_panel"],
                         foreground=COLORS["text_muted"],
                         padding=[18, 10],
                         font=FONTS["label"],
                         borderwidth=0)
        style.map("Custom.TNotebook.Tab",
                  background=[("selected", COLORS["bg_card"]),
                               ("active",  COLORS["bg_input"])],
                  foreground=[("selected", COLORS["accent"]),
                               ("active",  COLORS["text_primary"])])

        self.notebook = ttk.Notebook(self, style="Custom.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=0, pady=0)

        # ── Consola persistente ──
        self.console = ConsolePanel(self, height=8)
        self.console.pack(fill="x", padx=0, pady=0)

        # ── Crear Tabs ──
        self.tab_vhost  = VHostTab(self.notebook,    self.console)
        self.tab_config = ConfigTab(self.notebook,   self.console)
        self.tab_sec    = SecurityTab(self.notebook, self.console)
        self.tab_backup = BackupTab(self.notebook,   self.console)

        tab_defs = [
            (self.tab_vhost,  "  🌐  Virtual Hosts  "),
            (self.tab_config, "  ⚙  Configuración  "),
            (self.tab_sec,    "  🔒  Seguridad      "),
            (self.tab_backup, "  💾  Backups        "),
        ]
        for tab, label in tab_defs:
            self.notebook.add(tab, text=label)

        # Statusbar inferior
        sb = tk.Frame(self, bg=COLORS["bg_card"],
                       highlightbackground=COLORS["border"],
                       highlightthickness=1)
        sb.pack(fill="x", side="bottom")

        self.sb_msg = tk.Label(sb, text="  Listo",
                                font=FONTS["small"], bg=COLORS["bg_card"],
                                fg=COLORS["text_muted"])
        self.sb_msg.pack(side="left", pady=4)

        tk.Label(sb,
                 text=f"  Apache2 Manager · Ubuntu/Debian · {APP_VERSION}  ",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"]).pack(side="right")

    def _check_backend(self):
        """Verifica que el script backend existe y Apache está disponible"""
        if not os.path.exists(BACKEND_SCRIPT):
            messagebox.showerror(
                "Backend no encontrado",
                f"No se encontró el script backend:\n{BACKEND_SCRIPT}\n\n"
                "Asegúrese de que 'apache_manager.sh' esté en el mismo "
                "directorio que esta aplicación."
            )
        
        # Verificar que Apache2 está instalado
        def task():
            try:
                r = subprocess.run(
                    ["which", "apache2"],
                    capture_output=True, text=True, timeout=5
                )
                if r.returncode == 0:
                    self.after(0, lambda: self._set_apache_status("active"))
                else:
                    self.after(0, lambda: self._set_apache_status("not_found"))
            except Exception:
                self.after(0, lambda: self._set_apache_status("error"))

        threading.Thread(target=task, daemon=True).start()

        # Mensaje de bienvenida en consola
        self.after(500, self._welcome_message)

    def _set_apache_status(self, status):
        msgs = {
            "active":    ("● Apache2 Instalado",    COLORS["success_light"]),
            "not_found": ("● Apache2 No Instalado", COLORS["danger_light"]),
            "error":     ("● Error de Verificación",COLORS["text_muted"]),
        }
        msg, color = msgs.get(status, msgs["error"])
        self.apache_status.config(text=msg, fg=color)

    def _welcome_message(self):
        self.console.write("═══════════════════════════════════════", "dim")
        self.console.write("  Apache2 Manager - Iniciado", "title")
        self.console.write(f"  Directorio de trabajo: {SCRIPT_DIR}", "info")
        self.console.write(f"  Backend: {BACKEND_SCRIPT}", "info")
        self.console.write("═══════════════════════════════════════", "dim")


# ══════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # Verificar Python version
    if sys.version_info < (3, 7):
        print("ERROR: Se requiere Python 3.7 o superior")
        sys.exit(1)

    app = Apache2Manager()
    app.mainloop()
