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
# WIDGET: Frame con scroll vertical (para tabs con mucho contenido)
# ══════════════════════════════════════════════════════════════
class ScrollableFrame(tk.Frame):
    """Wrapper que envuelve cualquier contenido en un Canvas scrolleable."""
    def __init__(self, parent, bg=None, **kwargs):
        bg = bg or COLORS["bg_dark"]
        super().__init__(parent, bg=bg, **kwargs)

        self._canvas = tk.Canvas(self, bg=bg, highlightthickness=0)
        self._vbar   = ttk.Scrollbar(self, orient="vertical",
                                      command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._vbar.set)

        self._vbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner = tk.Frame(self._canvas, bg=bg)
        self._win  = self._canvas.create_window((0, 0),
                                                 window=self.inner,
                                                 anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        # Scroll con rueda del ratón
        for widget in (self._canvas, self.inner):
            widget.bind("<MouseWheel>",
                lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))
            widget.bind("<Button-4>",
                lambda e: self._canvas.yview_scroll(-1, "units"))
            widget.bind("<Button-5>",
                lambda e: self._canvas.yview_scroll(1, "units"))

    def _on_inner_configure(self, _):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self._canvas.itemconfig(self._win, width=e.width)

    def bind_scroll_to(self, widget):
        """Propaga el scroll de un widget hijo al canvas."""
        widget.bind("<MouseWheel>",
            lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))
        widget.bind("<Button-4>",
            lambda e: self._canvas.yview_scroll(-1, "units"))
        widget.bind("<Button-5>",
            lambda e: self._canvas.yview_scroll(1, "units"))


# ══════════════════════════════════════════════════════════════
# TAB 1: Virtual Hosts
# ══════════════════════════════════════════════════════════════
class VHostTab(tk.Frame):
    def __init__(self, parent, console):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.console = console
        self._build()

    def _build(self):
        paned = tk.PanedWindow(self, orient="horizontal",
                                bg=COLORS["bg_dark"], sashwidth=5,
                                sashrelief="flat")
        paned.pack(fill="both", expand=True, padx=10, pady=10)

        # ══ COLUMNA IZQUIERDA: formulario con scroll ══════════
        form_outer = tk.Frame(paned, bg=COLORS["bg_dark"])
        paned.add(form_outer, minsize=380)

        # Canvas + scrollbar para la columna izquierda completa
        form_canvas = tk.Canvas(form_outer, bg=COLORS["bg_dark"],
                                 highlightthickness=0)
        form_scroll = ttk.Scrollbar(form_outer, orient="vertical",
                                     command=form_canvas.yview)
        form_canvas.configure(yscrollcommand=form_scroll.set)
        form_scroll.pack(side="right", fill="y")
        form_canvas.pack(side="left", fill="both", expand=True)

        # Frame interior scrolleable
        self._form_inner = tk.Frame(form_canvas, bg=COLORS["bg_dark"])
        self._form_win = form_canvas.create_window(
            (0, 0), window=self._form_inner, anchor="nw")

        def _on_form_configure(e):
            form_canvas.configure(scrollregion=form_canvas.bbox("all"))
        def _on_canvas_resize(e):
            form_canvas.itemconfig(self._form_win, width=e.width)

        self._form_inner.bind("<Configure>", _on_form_configure)
        form_canvas.bind("<Configure>", _on_canvas_resize)
        form_canvas.bind("<MouseWheel>",
            lambda e: form_canvas.yview_scroll(-1*(e.delta//120), "units"))
        form_canvas.bind("<Button-4>",
            lambda e: form_canvas.yview_scroll(-1, "units"))
        form_canvas.bind("<Button-5>",
            lambda e: form_canvas.yview_scroll(1, "units"))

        self._build_form(self._form_inner)

        # ══ COLUMNA DERECHA: lista de VHosts ══════════════════
        list_card = Card(paned, "📋  VIRTUAL HOSTS ACTIVOS",
                         accent_color=COLORS["info"])
        paned.add(list_card, minsize=350)

        list_body = tk.Frame(list_card, bg=COLORS["bg_card"])
        list_body.pack(fill="both", expand=True, padx=5, pady=5)

        toolbar = tk.Frame(list_body, bg=COLORS["bg_card"])
        toolbar.pack(fill="x", pady=(0, 5))
        StyledButton(toolbar, "Actualizar",
                     command=self._refresh_list,
                     style="info", icon="↻").pack(side="left", padx=2)
        StyledButton(toolbar, "Eliminar",
                     command=self._delete_vhost,
                     style="danger", icon="🗑").pack(side="left", padx=2)
        StyledButton(toolbar, "Auth Básica →",
                     command=self._load_auth_for_selected,
                     style="warning", icon="🔑").pack(side="left", padx=2)

        cols = ("Dominio", "DocRoot", "Puerto", "Estado", "Auth")
        self.tree = ttk.Treeview(list_body, columns=cols,
                                  show="headings", height=10)
        widths = [130, 140, 55, 90, 60]
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

    # ─── Formulario principal (dentro del canvas scroll) ─────
    def _build_form(self, parent):
        # ── Sección: Datos básicos ──
        basic_card = Card(parent, "➕  CREAR VIRTUAL HOST",
                          accent_color=COLORS["accent"])
        basic_card.pack(fill="x", pady=(0, 8))

        body = tk.Frame(basic_card, bg=COLORS["bg_card"])
        body.pack(fill="x", padx=15, pady=10)

        self.f_domain  = LabeledEntry(body, "Dominio *",     "ejemplo.local",       30)
        self.f_docroot = LabeledEntry(body, "DocumentRoot *","/var/www/ejemplo",     30)
        self.f_email   = LabeledEntry(body, "Admin Email",   "admin@ejemplo.local",  30)
        self.f_port    = LabeledEntry(body, "Puerto",        "80",                   10)

        for w in [self.f_domain, self.f_docroot, self.f_email, self.f_port]:
            w.pack(fill="x", pady=3)

        dir_row = tk.Frame(body, bg=COLORS["bg_card"])
        dir_row.pack(fill="x", pady=2)
        StyledButton(dir_row, "Seleccionar Directorio",
                     command=self._browse_dir,
                     style="ghost", icon="📁").pack(side="left")

        tk.Frame(body, bg=COLORS["border"], height=1).pack(fill="x", pady=10)

        btn_row = tk.Frame(body, bg=COLORS["bg_card"])
        btn_row.pack(fill="x")
        StyledButton(btn_row, "Crear VirtualHost",
                     command=self._create_vhost,
                     style="primary", icon="🚀").pack(side="left", padx=(0, 8))
        StyledButton(btn_row, "Limpiar",
                     command=self._clear_form,
                     style="ghost", icon="🗑").pack(side="left")

        info = tk.Frame(body, bg=COLORS["bg_panel"],
                        highlightbackground=COLORS["info"], highlightthickness=1)
        info.pack(fill="x", pady=(10, 0))
        tk.Label(info, text="ℹ  El VirtualHost será habilitado automáticamente en Apache",
                 font=FONTS["small"], bg=COLORS["bg_panel"],
                 fg=COLORS["info_light"], justify="left").pack(
            padx=10, pady=6, anchor="w")

        # ── Sección: Autenticación Básica ──
        auth_card = Card(parent, "🔑  AUTENTICACIÓN BÁSICA (HTTP AUTH)",
                         accent_color=COLORS["warning"])
        auth_card.pack(fill="x", pady=(0, 8))

        ab = tk.Frame(auth_card, bg=COLORS["bg_card"])
        ab.pack(fill="x", padx=15, pady=10)

        # Selector de VHost a configurar
        self.auth_domain_var = tk.StringVar()
        vhost_row = tk.Frame(ab, bg=COLORS["bg_card"])
        vhost_row.pack(fill="x", pady=3)
        tk.Label(vhost_row, text="VirtualHost a configurar:",
                 font=FONTS["label"], bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"]).pack(anchor="w")
        self.auth_domain_combo = ttk.Combobox(
            vhost_row, textvariable=self.auth_domain_var,
            values=[], width=28, state="readonly", font=FONTS["body"])
        self.auth_domain_combo.pack(side="left", pady=2)
        self.auth_domain_combo.bind("<<ComboboxSelected>>",
                                     lambda e: self._refresh_auth_users())
        StyledButton(vhost_row, "↻", command=self._refresh_vhost_combo,
                     style="ghost").pack(side="left", padx=4)

        # Directorio a proteger — con botón de ayuda
        auth_dir_frame = tk.Frame(ab, bg=COLORS["bg_card"])
        auth_dir_frame.pack(fill="x", pady=3)

        dir_label_row = tk.Frame(auth_dir_frame, bg=COLORS["bg_card"])
        dir_label_row.pack(fill="x")
        tk.Label(dir_label_row, text="Directorio protegido (relativo al DocRoot):",
                 font=FONTS["label"], bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"]).pack(side="left")

        help_btn = tk.Label(dir_label_row, text=" ❓ ",
                            font=FONTS["small"], bg=COLORS["warning"],
                            fg=COLORS["white"], cursor="hand2")
        help_btn.pack(side="left", padx=4)
        help_btn.bind("<Button-1>", lambda e: self._show_auth_dir_help())

        self.auth_dir = LabeledEntry(auth_dir_frame, "",  "/", 28)
        self.auth_dir.pack(fill="x")

        # Caja informativa siempre visible
        dir_info = tk.Frame(ab, bg="#1A1F2C",
                            highlightbackground=COLORS["info"],
                            highlightthickness=1)
        dir_info.pack(fill="x", pady=(0, 6))
        tk.Label(dir_info,
                 text=("ℹ  Use  /  para proteger todo el sitio.\n"
                       "   Use  /admin  para proteger solo esa subcarpeta.\n"
                       "   Ejemplo: DocRoot=/var/www/mi-sitio  +  Dir=/privado\n"
                       "   → protege  /var/www/mi-sitio/privado"),
                 font=FONTS["small"], bg="#1A1F2C",
                 fg=COLORS["info_light"], justify="left").pack(
            padx=10, pady=6, anchor="w")

        # Botones de activar/desactivar auth
        auth_toggle_row = tk.Frame(ab, bg=COLORS["bg_card"])
        auth_toggle_row.pack(fill="x", pady=6)
        StyledButton(auth_toggle_row, "✔ Activar Auth Básica",
                     command=self._enable_basic_auth,
                     style="success").pack(side="left", padx=(0, 6))
        StyledButton(auth_toggle_row, "✖ Desactivar",
                     command=self._disable_basic_auth,
                     style="danger").pack(side="left", padx=(0, 6))
        StyledButton(auth_toggle_row, "Estado",
                     command=self._check_auth_status,
                     style="ghost").pack(side="left")

        # Estado rápido
        self.auth_status_var = tk.StringVar(value="◉  Seleccione un VirtualHost")
        tk.Label(ab, textvariable=self.auth_status_var,
                 font=FONTS["label"], bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"]).pack(anchor="w", pady=(4, 8))

        tk.Frame(ab, bg=COLORS["border"], height=1).pack(fill="x", pady=4)

        # ── Gestión de usuarios ──
        tk.Label(ab, text="Gestión de Usuarios:",
                 font=FONTS["label"], bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"]).pack(anchor="w", pady=(4, 2))

        self.auth_user = LabeledEntry(ab, "Usuario:", "", 20)
        self.auth_pass = LabeledEntry(ab, "Contraseña:", "", 20)
        for w in [self.auth_user, self.auth_pass]:
            w.pack(fill="x", pady=2)
        # Ocultar contraseña
        self.auth_pass.entry.config(show="●")

        user_btns = tk.Frame(ab, bg=COLORS["bg_card"])
        user_btns.pack(fill="x", pady=6)
        StyledButton(user_btns, "➕ Agregar Usuario",
                     command=self._add_user,
                     style="success").pack(side="left", padx=(0, 4))
        StyledButton(user_btns, "🗑 Eliminar Usuario",
                     command=self._del_user,
                     style="danger").pack(side="left")

        # Lista de usuarios actuales
        tk.Label(ab, text="Usuarios registrados:",
                 font=FONTS["small"], bg=COLORS["bg_card"],
                 fg=COLORS["text_muted"]).pack(anchor="w", pady=(6, 2))

        user_list_frame = tk.Frame(ab, bg=COLORS["bg_card"])
        user_list_frame.pack(fill="x")

        self.user_listbox = tk.Listbox(
            user_list_frame, height=5, bg=COLORS["bg_input"],
            fg=COLORS["text_primary"], font=FONTS["mono"],
            selectbackground=COLORS["warning"],
            selectforeground=COLORS["white"],
            relief="flat", bd=0,
            highlightbackground=COLORS["border"],
            highlightthickness=1
        )
        self.user_listbox.pack(side="left", fill="x", expand=True)
        user_sb = ttk.Scrollbar(user_list_frame, orient="vertical",
                                 command=self.user_listbox.yview)
        self.user_listbox.configure(yscrollcommand=user_sb.set)
        user_sb.pack(side="right", fill="y")
        self.user_listbox.bind("<<ListboxSelect>>", self._on_user_select)

        StyledButton(ab, "↻ Actualizar lista",
                     command=self._refresh_auth_users,
                     style="dark").pack(anchor="w", pady=4)

        # Poblar combo al inicio
        self._refresh_vhost_combo()

    # ─── Helpers de VHost básico ─────────────────────────────
    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                         background=COLORS["bg_input"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["bg_input"],
                         rowheight=26, font=FONTS["small"], borderwidth=0)
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
            args = ["create_vhost", domain, docroot,
                    email if (email and email != "admin@ejemplo.local")
                    else f"webmaster@{domain}", port]
            out, err, code = run_command_args(args)
            self.after(0, lambda: self._on_create(out, err, code))

        threading.Thread(target=task, daemon=True).start()

    def _on_create(self, out, err, code):
        self.console.write_output(out, err, code)
        if code == 0:
            self._refresh_list()
            self._refresh_vhost_combo()
            messagebox.showinfo("Éxito", "VirtualHost creado exitosamente")

    def _refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        def task():
            out, err, code = run_command_args(["read_config", "virtualhosts"])
            self.after(0, lambda: self._populate_tree(out))

        threading.Thread(target=task, daemon=True).start()

    def _populate_tree(self, output):
        # También actualiza el combo de auth
        domains = []
        for line in output.splitlines():
            if line.startswith("VHOST|"):
                parts = line.split("|")
                if len(parts) >= 6:
                    _, name, domain, docroot, port, status = parts[:6]
                    domains.append(domain or name)
                    tag = "enabled" if status == "HABILITADO" else "disabled"
                    self.tree.insert("", "end",
                                      values=(domain, docroot, port, status, "…"),
                                      tags=(tag,))
        self.tree.tag_configure("enabled",  foreground=COLORS["success_light"])
        self.tree.tag_configure("disabled", foreground=COLORS["text_muted"])
        # Actualizar combo
        self.auth_domain_combo.config(values=domains)
        self._refresh_auth_status_in_tree()

    def _refresh_auth_status_in_tree(self):
        """Consulta estado auth de cada vhost y actualiza columna Auth"""
        items = self.tree.get_children()
        if not items:
            return

        def task():
            results = {}
            for item in items:
                domain = self.tree.item(item)["values"][0]
                out, _, _ = run_command_args(["basic_auth", "status", str(domain)])
                results[item] = "✔ Sí" if "AUTH: ACTIVA" in out else "No"
            self.after(0, lambda: self._apply_auth_status(results))

        threading.Thread(target=task, daemon=True).start()

    def _apply_auth_status(self, results):
        for item, auth_val in results.items():
            vals = list(self.tree.item(item)["values"])
            if len(vals) >= 5:
                vals[4] = auth_val
                self.tree.item(item, values=vals)

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
            self._refresh_vhost_combo()

    def _load_auth_for_selected(self):
        """Carga el dominio seleccionado en el panel de auth"""
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un VirtualHost en la lista")
            return
        domain = str(self.tree.item(sel[0])["values"][0])
        self.auth_domain_var.set(domain)
        self._check_auth_status()
        self._refresh_auth_users()

    def _clear_form(self):
        for f in [self.f_domain, self.f_docroot, self.f_email, self.f_port]:
            f.set("")

    # ─── Helpers de Auth Básica ──────────────────────────────
    def _get_auth_domain(self):
        d = self.auth_domain_var.get().strip()
        if not d:
            messagebox.showwarning("Aviso", "Seleccione un VirtualHost")
        return d

    def _refresh_vhost_combo(self):
        def task():
            out, _, _ = run_command_args(["read_config", "virtualhosts"])
            domains = []
            for line in out.splitlines():
                if line.startswith("VHOST|"):
                    parts = line.split("|")
                    if len(parts) >= 3:
                        domains.append(parts[2] or parts[1])
            self.after(0, lambda: self.auth_domain_combo.config(values=domains))
        threading.Thread(target=task, daemon=True).start()

    def _enable_basic_auth(self):
        domain = self._get_auth_domain()
        if not domain:
            return
        auth_dir = self.auth_dir.get().strip() or "/"
        self.console.write(f"Activando auth básica en {domain} ({auth_dir})...", "info")

        def task():
            out, err, code = run_command_args(
                ["basic_auth", "add", domain, auth_dir])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._check_auth_status(),
                self._refresh_list()
            ))
        threading.Thread(target=task, daemon=True).start()

    def _disable_basic_auth(self):
        domain = self._get_auth_domain()
        if not domain:
            return
        if not messagebox.askyesno("Confirmar",
                                    f"¿Desactivar autenticación básica en '{domain}'?"):
            return
        def task():
            out, err, code = run_command_args(
                ["basic_auth", "remove", domain])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._check_auth_status(),
                self._refresh_list()
            ))
        threading.Thread(target=task, daemon=True).start()

    def _check_auth_status(self):
        domain = self._get_auth_domain()
        if not domain:
            return
        def task():
            out, _, _ = run_command_args(["basic_auth", "status", domain])
            self.after(0, lambda: self._update_auth_indicator(out))
        threading.Thread(target=task, daemon=True).start()

    def _update_auth_indicator(self, output):
        if "AUTH: ACTIVA" in output:
            self.auth_status_var.set("🔒  AUTH ACTIVA")
            # parse extra info
            lines = [l for l in output.splitlines()
                     if l.startswith("AuthName") or l.startswith("USUARIOS")]
            if lines:
                self.auth_status_var.set("🔒  AUTH ACTIVA  —  " + "  |  ".join(lines))
        elif "AUTH: INACTIVA" in output:
            self.auth_status_var.set("🔓  AUTH INACTIVA")
        else:
            self.auth_status_var.set("◉  " + output.splitlines()[0] if output else "?")

    def _add_user(self):
        domain = self._get_auth_domain()
        user   = self.auth_user.get().strip()
        passwd = self.auth_pass.get().strip()
        if not domain:
            return
        if not user or not passwd:
            messagebox.showwarning("Validación", "Usuario y contraseña son requeridos")
            return
        def task():
            # Orden: basic_auth add_user <domain> <user> <password>
            # En shell: $1=add_user $2=domain $3=user $4=password
            out, err, code = run_command_args(
                ["basic_auth", "add_user", domain, user, passwd])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._refresh_auth_users()
            ))
        threading.Thread(target=task, daemon=True).start()

    def _del_user(self):
        domain = self._get_auth_domain()
        if not domain:
            return
        sel = self.user_listbox.curselection()
        user = self.auth_user.get().strip()
        if sel:
            user = self.user_listbox.get(sel[0]).strip()
        if not user:
            messagebox.showwarning("Aviso", "Seleccione un usuario de la lista o escríbalo")
            return
        if not messagebox.askyesno("Confirmar", f"¿Eliminar usuario '{user}'?"):
            return
        def task():
            # Orden: basic_auth del_user <domain> <user>
            # En shell: $1=del_user $2=domain $3=user
            out, err, code = run_command_args(
                ["basic_auth", "del_user", domain, user])
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._refresh_auth_users()
            ))
        threading.Thread(target=task, daemon=True).start()

    def _refresh_auth_users(self):
        domain = self.auth_domain_var.get().strip()
        if not domain:
            return
        self.user_listbox.delete(0, "end")
        def task():
            out, _, _ = run_command_args(["basic_auth", "list_users", domain])
            users = [l.split("|")[1] for l in out.splitlines()
                     if l.startswith("USER|")]
            self.after(0, lambda: [self.user_listbox.insert("end", f"  {u}")
                                    for u in users])
            self.after(0, lambda: self._check_auth_status())
        threading.Thread(target=task, daemon=True).start()

    def _on_user_select(self, event):
        sel = self.user_listbox.curselection()
        if sel:
            self.auth_user.set(self.user_listbox.get(sel[0]).strip())

    def _show_auth_dir_help(self):
        msg = (
            "📁  CAMPO: Directorio Protegido\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Este campo indica qué carpeta dentro del VirtualHost\n"
            "quedará protegida con usuario y contraseña.\n\n"
            "El valor es RELATIVO al DocumentRoot del VirtualHost.\n\n"
            "EJEMPLOS:\n\n"
            "  /   → Protege TODO el sitio web\n"
            "        (el usuario verá login al entrar a cualquier página)\n\n"
            "  /admin   → Solo protege la carpeta 'admin'\n"
            "             El resto del sitio sigue siendo público\n\n"
            "  /privado → Solo protege la carpeta 'privado'\n\n"
            "FLUJO RECOMENDADO:\n\n"
            "  1. Seleccione el VirtualHost en el combo\n"
            "  2. Escriba el directorio (o deje / para todo)\n"
            "  3. Haga clic en '✔ Activar Auth Básica'\n"
            "  4. Agregue al menos un usuario con ➕\n"
            "  5. Pruebe en el navegador — debería pedir login\n\n"
            "NOTA: Si la carpeta no existe, Apache la ignorará.\n"
            "Asegúrese de que el directorio exista en el servidor."
        )
        win = tk.Toplevel(self)
        win.title("Ayuda — Directorio Protegido")
        win.geometry("500x420")
        win.configure(bg=COLORS["bg_card"])
        win.resizable(False, False)

        tk.Label(win, text="  📁  Ayuda: Directorio Protegido",
                 font=FONTS["subhead"], bg=COLORS["bg_panel"],
                 fg=COLORS["accent"]).pack(fill="x", ipady=8)

        txt = tk.Text(win, bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                      font=FONTS["small"], relief="flat", bd=0,
                      wrap="word", padx=15, pady=10, state="normal")
        txt.insert("1.0", msg)
        txt.config(state="disabled")
        txt.pack(fill="both", expand=True, padx=5, pady=5)

        StyledButton(win, "Entendido", command=win.destroy,
                     style="primary").pack(pady=(0, 10))


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
        self.output.tag_config("key",     foreground=COLORS["info_light"])
        self.output.tag_config("value",   foreground=COLORS["success_light"])
        self.output.tag_config("warn",    foreground=COLORS["warning_light"])
        self.output.tag_config("hdr_val", foreground=COLORS["accent"],
                                font=("Courier New", 10, "bold"))
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

        for raw_line in out.splitlines():
            line = raw_line.strip("\r")   # eliminar \r de respuestas HTTP
            if line.startswith("==="):
                self.output.insert("end", f"\n{line}\n", "head")
            elif line.startswith("VERSION_HTTP:"):
                if "OCULTA" in line:
                    self.output.insert("end", line + "\n", "value")
                else:
                    self.output.insert("end", line + "\n", "warn")
            elif line.startswith("Server Header:"):
                # Extraer solo el valor después de los dos puntos
                val = line.split(":", 1)[1].strip() if ":" in line else line
                self.output.insert("end", "Server Header: ", "key")
                if val:
                    self.output.insert("end", val + "\n", "hdr_val")
                else:
                    self.output.insert("end", "(vacío)\n", "dim")
            elif line.startswith("Respuesta HTTP:"):
                val = line.split(":", 1)[1].strip() if ":" in line else line
                self.output.insert("end", "Respuesta HTTP: ", "key")
                self.output.insert("end", val + "\n", "value")
            elif line.startswith("Puerto detectado:"):
                val = line.split(":", 1)[1].strip() if ":" in line else line
                self.output.insert("end", "Puerto detectado: ", "key")
                self.output.insert("end", val + "\n", "value")
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
        sf = ScrollableFrame(self)
        sf.pack(fill="both", expand=True)
        container = tk.Frame(sf.inner, bg=COLORS["bg_dark"])
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
        sf = ScrollableFrame(self)
        sf.pack(fill="both", expand=True)

        # Top split: form + actions
        top = tk.Frame(sf.inner, bg=COLORS["bg_dark"])
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
        list_card = Card(sf.inner, "📋  BACKUPS DISPONIBLES",
                         accent_color=COLORS["info"])
        list_card.pack(fill="x", padx=10, pady=(0, 10))

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
        self.tab_vhost  = VHostTab(self.notebook,     self.console)
        self.tab_config = ConfigTab(self.notebook,    self.console)
        self.tab_sec    = SecurityTab(self.notebook,  self.console)
        self.tab_backup = BackupTab(self.notebook,    self.console)
        self.tab_cron   = CronRsyncTab(self.notebook, self.console)

        tab_defs = [
            (self.tab_vhost,  "  🌐  Virtual Hosts  "),
            (self.tab_config, "  ⚙  Configuración  "),
            (self.tab_sec,    "  🔒  Seguridad      "),
            (self.tab_backup, "  💾  Backups        "),
            (self.tab_cron,   "  🕐  Cron + Rsync   "),
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
# TAB 5: Backup Programado — Rsync + Cron
# ══════════════════════════════════════════════════════════════
class CronRsyncTab(tk.Frame):
    """Tab completo para programar backups con cron.d y rsync"""

    FRECUENCIAS = {
        "Cada hora":         ("0",  "*",  "*", "*", "*"),
        "Cada 6 horas":      ("0",  "*/6","*", "*", "*"),
        "Cada 12 horas":     ("0",  "*/12","*","*", "*"),
        "Diario (medianoche)":("0", "0",  "*", "*", "*"),
        "Diario (02:00 AM)": ("0",  "2",  "*", "*", "*"),
        "Lunes - Semanal":   ("0",  "3",  "*", "*", "1"),
        "Mensual (día 1)":   ("0",  "4",  "1", "*", "*"),
        "Personalizado":     ("",   "",   "",  "",  ""),
    }

    def __init__(self, parent, console):
        super().__init__(parent, bg=COLORS["bg_dark"])
        self.console = console
        self._build()

    def _build(self):
        # ── Layout: izquierda=formularios, derecha=jobs
        main = tk.Frame(self, bg=COLORS["bg_dark"])
        main.pack(fill="both", expand=True, padx=10, pady=10)

        left = tk.Frame(main, bg=COLORS["bg_dark"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right = tk.Frame(main, bg=COLORS["bg_dark"])
        right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ══ PANEL IZQUIERDO ══════════════════════════════════

        # ── Sección Rsync inmediato ──
        rsync_card = Card(left, "⚡  RSYNC BACKUP INMEDIATO",
                          accent_color=COLORS["accent"])
        rsync_card.pack(fill="x", pady=(0, 8))

        rb = tk.Frame(rsync_card, bg=COLORS["bg_card"])
        rb.pack(fill="x", padx=14, pady=10)

        self.rsync_src  = LabeledEntry(rb, "Origen  (src):",
                                        "/etc/apache2", 34)
        self.rsync_dest = LabeledEntry(rb, "Destino (dst):",
                                        "/var/backups/apache2_manager/rsync", 34)
        self.rsync_name = LabeledEntry(rb, "Nombre del backup:",
                                        "rsync_apache", 34)

        for w in [self.rsync_src, self.rsync_dest, self.rsync_name]:
            w.pack(fill="x", pady=2)

        # Opciones rsync
        opt_frame = tk.Frame(rb, bg=COLORS["bg_card"])
        opt_frame.pack(fill="x", pady=(6, 0))

        tk.Label(opt_frame, text="Opciones adicionales rsync:",
                 font=FONTS["label"], bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"]).pack(anchor="w")

        self.rsync_opts_var = tk.StringVar()
        opts_checks = tk.Frame(opt_frame, bg=COLORS["bg_card"])
        opts_checks.pack(fill="x")

        self._opt_delete  = tk.BooleanVar(value=True)
        self._opt_compress = tk.BooleanVar(value=False)
        self._opt_dryrun  = tk.BooleanVar(value=False)
        self._opt_verbose = tk.BooleanVar(value=True)

        for text, var in [
            ("--delete (eliminar huérfanos)", self._opt_delete),
            ("--compress (SSH remoto)",        self._opt_compress),
            ("--dry-run (simular)",            self._opt_dryrun),
            ("--verbose",                      self._opt_verbose),
        ]:
            tk.Checkbutton(opts_checks, text=text, variable=var,
                           bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                           selectcolor=COLORS["bg_input"],
                           activebackground=COLORS["bg_card"],
                           font=FONTS["small"]).pack(
                side="left", padx=4)

        tk.Frame(rb, bg=COLORS["border"], height=1).pack(
            fill="x", pady=8)

        rsync_btns = tk.Frame(rb, bg=COLORS["bg_card"])
        rsync_btns.pack(fill="x")
        StyledButton(rsync_btns, "Ejecutar Rsync Ahora",
                     command=self._run_rsync_now,
                     style="primary", icon="⚡").pack(
            side="left", padx=(0, 6), ipady=3)
        StyledButton(rsync_btns, "📁 Explorar Origen",
                     command=lambda: self._browse(self.rsync_src),
                     style="ghost").pack(side="left", padx=3)
        StyledButton(rsync_btns, "📁 Explorar Destino",
                     command=lambda: self._browse(self.rsync_dest),
                     style="ghost").pack(side="left", padx=3)

        # ── Sección Programar con Cron ──
        cron_card = Card(left, "🕐  PROGRAMAR BACKUP (CRON.D)",
                         accent_color=COLORS["info"])
        cron_card.pack(fill="both", expand=True)

        cb = tk.Frame(cron_card, bg=COLORS["bg_card"])
        cb.pack(fill="both", expand=True, padx=14, pady=10)

        # Fila: nombre del job
        self.cron_name = LabeledEntry(cb, "Nombre del Job:", "backup_diario", 28)
        self.cron_name.pack(fill="x", pady=2)

        # Frecuencia predefinida
        freq_row = tk.Frame(cb, bg=COLORS["bg_card"])
        freq_row.pack(fill="x", pady=(6, 2))
        tk.Label(freq_row, text="Frecuencia:", font=FONTS["label"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(
            side="left", padx=(0, 8))

        self.freq_var = tk.StringVar(value="Diario (02:00 AM)")
        freq_combo = ttk.Combobox(freq_row, textvariable=self.freq_var,
                                   values=list(self.FRECUENCIAS.keys()),
                                   width=22, state="readonly",
                                   font=FONTS["body"])
        freq_combo.pack(side="left")
        freq_combo.bind("<<ComboboxSelected>>", self._on_freq_change)

        # Expresión cron manual (se activa en "Personalizado")
        cron_expr_frame = tk.Frame(cb, bg=COLORS["bg_card"])
        cron_expr_frame.pack(fill="x", pady=4)

        tk.Label(cron_expr_frame, text="Expresión cron  [min hora dia mes diasem]:",
                 font=FONTS["label"], bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"]).pack(anchor="w")

        cron_fields = tk.Frame(cron_expr_frame, bg=COLORS["bg_card"])
        cron_fields.pack(fill="x")

        labels = ["Min", "Hora", "Día/Mes", "Mes", "Día/Sem"]
        defaults = ["0", "2", "*", "*", "*"]
        self.cron_fields = []
        for lbl, default in zip(labels, defaults):
            col = tk.Frame(cron_fields, bg=COLORS["bg_card"])
            col.pack(side="left", padx=3)
            tk.Label(col, text=lbl, font=FONTS["small"],
                     bg=COLORS["bg_card"], fg=COLORS["text_muted"]).pack()
            e = tk.Entry(col, width=7, bg=COLORS["bg_input"],
                         fg=COLORS["text_primary"],
                         insertbackground=COLORS["accent"],
                         font=FONTS["mono"], relief="flat", bd=4,
                         highlightbackground=COLORS["border"],
                         highlightcolor=COLORS["accent"],
                         highlightthickness=1)
            e.insert(0, default)
            e.pack()
            self.cron_fields.append(e)

        # Referencia rápida cron
        ref = tk.Label(cb,
            text="* = cualquier  */n = cada n  1-5 = rango  1,3,5 = lista",
            font=FONTS["small"], bg=COLORS["bg_panel"],
            fg=COLORS["text_muted"])
        ref.pack(fill="x", ipady=4, ipadx=6, pady=(2, 6))

        # Tipo y método
        tm_row = tk.Frame(cb, bg=COLORS["bg_card"])
        tm_row.pack(fill="x", pady=4)

        left_col = tk.Frame(tm_row, bg=COLORS["bg_card"])
        left_col.pack(side="left", fill="both", expand=True)
        right_col = tk.Frame(tm_row, bg=COLORS["bg_card"])
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))

        tk.Label(left_col, text="Método:", font=FONTS["label"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w")
        self.cron_method = tk.StringVar(value="rsync")
        for text, val in [("Rsync (incremental)", "rsync"), ("Tar.gz (comprimido)", "tar")]:
            tk.Radiobutton(left_col, text=text, variable=self.cron_method,
                           value=val, command=self._toggle_cron_method,
                           bg=COLORS["bg_card"], fg=COLORS["text_primary"],
                           selectcolor=COLORS["bg_input"],
                           activebackground=COLORS["bg_card"],
                           font=FONTS["small"]).pack(anchor="w")

        tk.Label(right_col, text="Tipo (tar):", font=FONTS["label"],
                 bg=COLORS["bg_card"], fg=COLORS["text_secondary"]).pack(anchor="w")
        self.cron_type = tk.StringVar(value="config")
        for text, val in [("Configuración", "config"),
                           ("VirtualHosts",  "vhosts"),
                           ("Completo",       "full")]:
            tk.Radiobutton(right_col, text=text, variable=self.cron_type,
                           value=val, bg=COLORS["bg_card"],
                           fg=COLORS["text_muted"],
                           selectcolor=COLORS["bg_input"],
                           activebackground=COLORS["bg_card"],
                           font=FONTS["small"],
                           state="disabled").pack(anchor="w")
        self._tar_radios = right_col.winfo_children()[1:]  # los radiobuttons

        # Origen/Destino para cron rsync
        self.cron_src  = LabeledEntry(cb, "Origen (cron rsync):",
                                       "/etc/apache2", 34)
        self.cron_dest = LabeledEntry(cb, "Destino (cron rsync):",
                                       "/var/backups/apache2_manager/rsync", 34)
        self.cron_src.pack(fill="x", pady=2)
        self.cron_dest.pack(fill="x", pady=2)

        tk.Frame(cb, bg=COLORS["border"], height=1).pack(fill="x", pady=8)

        cron_btns = tk.Frame(cb, bg=COLORS["bg_card"])
        cron_btns.pack(fill="x")
        StyledButton(cron_btns, "➕ Agregar Job",
                     command=self._add_cron_job,
                     style="success", icon="").pack(side="left", padx=(0, 6))
        StyledButton(cron_btns, "Ver cron.d",
                     command=self._view_cron_file,
                     style="ghost").pack(side="left", padx=3)

        # Previsualización de expresión
        self.preview_var = tk.StringVar(value="")
        tk.Label(cb, textvariable=self.preview_var, font=FONTS["small"],
                 bg=COLORS["bg_card"], fg=COLORS["accent"]).pack(
            anchor="w", pady=(4, 0))

        for f in self.cron_fields:
            f.bind("<KeyRelease>", lambda e: self._update_preview())
        self._on_freq_change()

        # ══ PANEL DERECHO ═════════════════════════════════════

        # ── Lista de jobs programados ──
        jobs_card = Card(right, "📋  JOBS PROGRAMADOS",
                         accent_color=COLORS["success"])
        jobs_card.pack(fill="both", expand=True, pady=(0, 8))

        jb = tk.Frame(jobs_card, bg=COLORS["bg_card"])
        jb.pack(fill="both", expand=True, padx=5, pady=5)

        j_toolbar = tk.Frame(jb, bg=COLORS["bg_card"])
        j_toolbar.pack(fill="x", pady=(0, 5))
        StyledButton(j_toolbar, "↻ Actualizar",
                     command=self._refresh_jobs,
                     style="info").pack(side="left", padx=2)
        StyledButton(j_toolbar, "▶ Ejecutar Ya",
                     command=self._run_selected_now,
                     style="success").pack(side="left", padx=2)
        StyledButton(j_toolbar, "🗑 Eliminar",
                     command=self._remove_job,
                     style="danger").pack(side="left", padx=2)

        j_cols = ("Job", "Schedule", "Método", "Tipo")
        self.jtree = ttk.Treeview(jb, columns=j_cols,
                                   show="headings", height=8)
        j_widths = [140, 130, 80, 80]
        for col, w in zip(j_cols, j_widths):
            self.jtree.heading(col, text=col)
            self.jtree.column(col, width=w, anchor="center")

        jscroll = ttk.Scrollbar(jb, orient="vertical",
                                 command=self.jtree.yview)
        self.jtree.configure(yscrollcommand=jscroll.set)
        self.jtree.pack(side="left", fill="both", expand=True)
        jscroll.pack(side="right", fill="y")

        # ── Logs de ejecución ──
        log_card = Card(right, "📄  LOG DE EJECUCIONES",
                        accent_color=COLORS["text_muted"])
        log_card.pack(fill="both", expand=True)

        log_tb = tk.Frame(log_card, bg=COLORS["bg_card"])
        log_tb.pack(fill="x", padx=5, pady=3)
        StyledButton(log_tb, "↻ Ver Logs",
                     command=self._refresh_logs,
                     style="ghost").pack(side="left", padx=2)
        StyledButton(log_tb, "Limpiar Vista",
                     command=lambda: (self.log_text.config(state="normal"),
                                      self.log_text.delete("1.0", "end"),
                                      self.log_text.config(state="disabled")),
                     style="dark").pack(side="left", padx=2)

        self.log_text = scrolledtext.ScrolledText(
            log_card, height=9, bg="#0A0E13",
            fg=COLORS["text_secondary"], font=("Courier New", 9),
            relief="flat", bd=0, state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        self.log_text.tag_config("ok",  foreground=COLORS["success_light"])
        self.log_text.tag_config("err", foreground=COLORS["danger_light"])
        self.log_text.tag_config("hdr", foreground=COLORS["accent"])

        self._refresh_jobs()

    # ── helpers ─────────────────────────────────────────────
    def _browse(self, entry_widget):
        path = filedialog.askdirectory(title="Seleccionar directorio")
        if path:
            entry_widget.set(path)

    def _on_freq_change(self, event=None):
        key = self.freq_var.get()
        values = self.FRECUENCIAS.get(key, ("", "", "", "", ""))
        for field, val in zip(self.cron_fields, values):
            field.delete(0, "end")
            field.insert(0, val)
            state = "normal" if key == "Personalizado" else "readonly"
            field.config(state=state,
                          fg=COLORS["text_primary"] if key == "Personalizado"
                          else COLORS["text_muted"])
        self._update_preview()

    def _update_preview(self):
        vals = [f.get() for f in self.cron_fields]
        expr = " ".join(vals)
        self.preview_var.set(f"  → Expresión cron: {expr}")

    def _toggle_cron_method(self):
        method = self.cron_method.get()
        # Habilitar/deshabilitar radios de tipo tar
        for rb in self._tar_radios:
            rb.config(state="normal" if method == "tar" else "disabled",
                      fg=COLORS["text_primary"] if method == "tar"
                      else COLORS["text_muted"])
        # Mostrar/ocultar campos src/dest
        state = "normal" if method == "rsync" else "disabled"
        self.cron_src.entry.config(state=state)
        self.cron_dest.entry.config(state=state)

    def _build_rsync_opts(self):
        opts = []
        if self._opt_delete.get():   opts.append("--delete")
        if self._opt_compress.get(): opts.append("--compress")
        if self._opt_dryrun.get():   opts.append("--dry-run")
        if self._opt_verbose.get():  opts.append("--verbose")
        return " ".join(opts)

    # ── Acciones ────────────────────────────────────────────
    def _run_rsync_now(self):
        src  = self.rsync_src.get().strip()
        dest = self.rsync_dest.get().strip()
        name = self.rsync_name.get().strip() or "rsync_manual"
        opts = self._build_rsync_opts()

        if not src or not dest:
            messagebox.showwarning("Validación", "Origen y Destino son requeridos")
            return

        self.console.write(f"Rsync: {src} → {dest}", "info")

        def task():
            args = ["rsync_backup", src, dest, name, opts]
            out, err, code = run_command_args(args, timeout=120)
            self.after(0, lambda: self.console.write_output(out, err, code))

        threading.Thread(target=task, daemon=True).start()

    def _add_cron_job(self):
        name   = self.cron_name.get().strip()
        method = self.cron_method.get()
        btype  = self.cron_type.get()
        src    = self.cron_src.get().strip()
        dest   = self.cron_dest.get().strip()

        if not name:
            messagebox.showwarning("Validación", "Nombre del job es requerido")
            return

        min_v, hr_v, dom_v, mon_v, dow_v = [f.get().strip()
                                               for f in self.cron_fields]
        if not all([min_v, hr_v, dom_v, mon_v, dow_v]):
            messagebox.showwarning("Validación", "Complete la expresión cron")
            return

        if method == "rsync" and (not src or not dest):
            messagebox.showwarning("Validación",
                                   "Origen y Destino son requeridos para rsync")
            return

        self.console.write(f"Programando job: {name} ({min_v} {hr_v} {dom_v} {mon_v} {dow_v})", "info")

        def task():
            args = [
                "schedule_backup", "add",
                name, min_v, hr_v, dom_v, mon_v, dow_v,
                btype, src if method == "rsync" else "",
                dest if method == "rsync" else "",
                method
            ]
            out, err, code = run_command_args(args)
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._refresh_jobs()
            ))

        threading.Thread(target=task, daemon=True).start()

    def _refresh_jobs(self):
        for item in self.jtree.get_children():
            self.jtree.delete(item)

        def task():
            out, err, code = run_command_args(["schedule_backup", "list_jobs"])
            self.after(0, lambda: self._populate_jobs(out))

        threading.Thread(target=task, daemon=True).start()

    def _populate_jobs(self, output):
        for line in output.splitlines():
            if line.startswith("JOB|"):
                parts = line.split("|")
                if len(parts) >= 5:
                    _, name, schedule, btype, method = parts[:5]
                    tag = "rsync" if method == "rsync" else "tar"
                    self.jtree.insert("", "end",
                                       values=(name, schedule, method, btype),
                                       tags=(tag,))

        self.jtree.tag_configure("rsync", foreground=COLORS["accent"])
        self.jtree.tag_configure("tar",   foreground=COLORS["info_light"])

    def _get_selected_job(self):
        sel = self.jtree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un job de la lista")
            return None
        return self.jtree.item(sel[0])["values"][0]

    def _run_selected_now(self):
        name = self._get_selected_job()
        if not name:
            return
        self.console.write(f"Ejecutando job manualmente: {name}", "info")

        def task():
            out, err, code = run_command_args(
                ["schedule_backup", "run_now", name], timeout=120)
            self.after(0, lambda: (
                self.console.write_output(out, err, code),
                self._refresh_logs()
            ))

        threading.Thread(target=task, daemon=True).start()

    def _remove_job(self):
        name = self._get_selected_job()
        if not name:
            return
        if not messagebox.askyesno("Confirmar",
                                    f"¿Eliminar job programado '{name}'?"):
            return
        out, err, code = run_command_args(
            ["schedule_backup", "remove", name])
        self.console.write_output(out, err, code)
        self._refresh_jobs()

    def _view_cron_file(self):
        out, err, code = run_command_args(
            ["schedule_backup", "view_cron"])
        # Mostrar en ventana modal
        win = tk.Toplevel(self)
        win.title("Contenido de /etc/cron.d/apache2_manager_backup")
        win.geometry("760x400")
        win.configure(bg=COLORS["bg_dark"])
        txt = scrolledtext.ScrolledText(
            win, bg="#0A0E13", fg=COLORS["success_light"],
            font=("Courier New", 10), relief="flat"
        )
        txt.pack(fill="both", expand=True, padx=8, pady=8)
        txt.insert("end", out if out else "(vacío o sin permisos)")
        txt.config(state="disabled")

    def _refresh_logs(self):
        def task():
            out, err, code = run_command_args(
                ["schedule_backup", "list_logs"])
            self.after(0, lambda: self._render_logs(out))

        threading.Thread(target=task, daemon=True).start()

    def _render_logs(self, output):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        for line in output.splitlines():
            if "===" in line:
                self.log_text.insert("end", line + "\n", "hdr")
            elif "SUCCESS" in line or "completado" in line.lower():
                self.log_text.insert("end", line + "\n", "ok")
            elif "ERROR" in line or "falló" in line.lower():
                self.log_text.insert("end", line + "\n", "err")
            else:
                self.log_text.insert("end", line + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")


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
