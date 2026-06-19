"""
PoE2 Pickit Generator — GUI v6 (Simple)
Clean, flat dark UI. No animations, no canvas buttons, no particle effects.
Drop-in replacement for v5.

Fixes over v5:
  - Removed all animation/canvas widget code (AnimButton, ShimmerBar, ParticleHeader, PulseFrame, StatCard count-up)
  - Fixed AttributeError: _ovw_var only exists after settings page visit → initialised in _init_vars
  - Fixed TclError: cat_thresh[key].get() on empty entry → wrapped in try/except with fallback
  - Fixed broken _summary_vars lambda closure bug (removed entirely, stat labels updated directly)
  - Simplified to ttk.Button throughout for native OS rendering
"""

import sys, os, re, json, time, shutil, threading, datetime, traceback, subprocess, importlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ── Optional Windows-only imports ─────────────────────────────────────────────
try:
    from win10toast import ToastNotifier
    _HAS_TOAST = True
except ImportError:
    _HAS_TOAST = False

# ── PyInstaller bundle path fix ───────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _bundle_dir = sys._MEIPASS
    if _bundle_dir not in sys.path:
        sys.path.insert(0, _bundle_dir)

try:
    import poe2_pickit_generator as gen
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing file",
        "poe2_pickit_generator.py not found.\n"
        "Place this GUI script in the same folder as poe2_pickit_generator.py.")
    sys.exit(1)

try:
    import requests
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing dependency",
        "Install requests:  pip install requests")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _cfg_dir = os.path.dirname(sys.executable)
else:
    _cfg_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH = os.path.join(_cfg_dir, "pickit_gui_config.json")
OUTPUT_DIR  = os.path.join(_cfg_dir, "pickit_output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

DEFAULT_CONFIG = {
    "league": "",
    "min_exalt": 10.0,
    "output_base": "poe2_pickit",
    "bot_folder": "",
    "auto_copy": False,
    "backup_count": 5,
    "category_enabled": {},
    "category_threshold": {},
    "history": [],

    "toast_on_complete": True,
    "start_minimized": False,
    "window_geometry": "",
    "confirm_overwrite_secs": 120,
    "include_bases": True,
    "base_quality": 28,
    "base_min_level": 75,
}

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ── Colours & fonts ───────────────────────────────────────────────────────────
BG        = "#1a1a22"
BG2       = "#22222e"
BG3       = "#2a2a38"
BORDER    = "#3a3a50"
GOLD      = "#c8a96e"
GOLD_LT   = "#e8c98e"
TEXT      = "#ece4d8"
TEXT_DIM  = "#888898"
TEXT_OK   = "#5dbb8a"
TEXT_ERR  = "#e05555"
TEXT_WARN = "#d4a84b"
TEXT_INFO = "#6ab0e8"

FONT      = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_MONO = ("Consolas",  9)
FONT_SM   = ("Segoe UI",  9)

ALL_CATEGORY_KEYS = [c[0] for c in gen.ALL_CATEGORIES]

# ── Helper widgets ────────────────────────────────────────────────────────────

def scrolled_text(parent, **kw):
    """Return (frame, Text widget) with both scrollbars."""
    frame = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    vsb = tk.Scrollbar(frame, orient="vertical",   bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=10)
    hsb = tk.Scrollbar(frame, orient="horizontal", bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=10)
    t = tk.Text(frame, bg=BG2, fg=TEXT, font=FONT_MONO,
                relief="flat", bd=0, wrap="none",
                highlightthickness=0, padx=6, pady=4,
                yscrollcommand=vsb.set, xscrollcommand=hsb.set, **kw)
    vsb.config(command=t.yview)
    hsb.config(command=t.xview)
    t.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1)
    frame.columnconfigure(0, weight=1)
    return frame, t

def sep(parent):
    return tk.Frame(parent, bg=BORDER, height=1)

def label(parent, text, fg=None, font=None, bg=None, **kw):
    return tk.Label(parent, text=text,
                    bg=bg or BG, fg=fg or TEXT,
                    font=font or FONT, **kw)

def entry(parent, var, width=None, **kw):
    e = tk.Entry(parent, textvariable=var,
                 bg=BG3, fg=TEXT, insertbackground=GOLD,
                 relief="flat", bd=0, font=FONT,
                 highlightthickness=1,
                 highlightbackground=BORDER,
                 highlightcolor=GOLD, **kw)
    if width:
        e.config(width=width)
    return e

def checkbtn(parent, text, var, bg=None):
    return tk.Checkbutton(parent, text=text, variable=var,
        bg=bg or BG2, fg=TEXT,
        selectcolor=BG3,
        activebackground=bg or BG2,
        activeforeground=TEXT,
        font=FONT, anchor="w")

def btn(parent, text, cmd, **kw):
    """Standard ttk button styled for dark theme."""
    b = ttk.Button(parent, text=text, command=cmd, **kw)
    return b

# ── ttk style setup (called once on app init) ─────────────────────────────────

def setup_styles(root):
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TButton",
        background=BG3, foreground=TEXT,
        font=FONT, relief="flat",
        borderwidth=1, focusthickness=0,
        padding=(10, 5))
    style.map("TButton",
        background=[("active", BORDER), ("pressed", BG)],
        foreground=[("active", TEXT)])

    style.configure("Gold.TButton",
        background=GOLD, foreground="#111",
        font=FONT_BOLD, relief="flat",
        borderwidth=0, padding=(14, 6))
    style.map("Gold.TButton",
        background=[("active", GOLD_LT), ("pressed", GOLD)])

    style.configure("TCombobox",
        fieldbackground=BG3, background=BG3,
        foreground=TEXT, selectbackground=BG3,
        selectforeground=TEXT, arrowcolor=GOLD,
        bordercolor=BORDER, padding=4)
    style.map("TCombobox", fieldbackground=[("readonly", BG3)],
                            foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background",       BG3)
    root.option_add("*TCombobox*Listbox.foreground",       TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", GOLD)
    root.option_add("*TCombobox*Listbox.selectForeground", "#111")

    style.configure("Treeview",
        background=BG2, foreground=TEXT,
        fieldbackground=BG2, rowheight=22, font=FONT)
    style.configure("Treeview.Heading",
        background=BG3, foreground=GOLD, font=FONT_BOLD, relief="flat")
    style.map("Treeview", background=[("selected", BORDER)])


# ══════════════════════════════════════════════════════════════════════════════
#  Main Application
# ══════════════════════════════════════════════════════════════════════════════

TABS = ["Generate", "Categories", "Preview", "History", "Settings", "Debug"]


class PickitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        setup_styles(self)

        self.title("PoE2 Pickit Generator  v6")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.minsize(900, 660)

        saved_geo = self.cfg.get("window_geometry", "")
        self.geometry(saved_geo if saved_geo else "1020x760")

        # Runtime state
        self._leagues         = []
        self._running         = False
        self._schedule_after  = None
        self._last_run_time   = time.time()
        self._last_output     = []
        self._preview_lines   = []
        self._generate_start  = 0.0
        self._tab_canvases    = {}
        self._active_canvas   = None

        self._init_vars()
        self._build_ui()
        self._fetch_leagues_async()
        self._schedule_tick()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-g>", lambda e: self._start_generate())
        self.bind_all("<Control-r>", lambda e: self._fetch_leagues_async())
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>",   self._on_wheel_up)
        self.bind_all("<Button-5>",   self._on_wheel_down)

        if self.cfg.get("start_minimized", False):
            self.after(100, self.iconify)

    # ── Variable init ─────────────────────────────────────────────────────────

    def _init_vars(self):
        self.league_var       = tk.StringVar(value=self.cfg.get("league") or "")
        self.min_exalt_var    = tk.DoubleVar(value=self.cfg.get("min_exalt", 10.0))
        self.output_var       = tk.StringVar(value=self.cfg.get("output_base", "poe2_pickit"))
        self.bot_folder_var   = tk.StringVar(value=self.cfg.get("bot_folder", ""))
        self.auto_copy_var    = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        self.backup_count_var = tk.IntVar(value=self.cfg.get("backup_count", 5))
        self.toast_var        = tk.BooleanVar(value=self.cfg.get("toast_on_complete", True))
        self.start_min_var    = tk.BooleanVar(value=self.cfg.get("start_minimized", False))
        self.ovw_var          = tk.IntVar(value=self.cfg.get("confirm_overwrite_secs", 120))

        self.include_bases_var  = tk.BooleanVar(value=True)
        self.base_quality_var   = tk.IntVar(value=self.cfg.get("base_quality", 28))
        self.base_min_level_var = tk.IntVar(value=self.cfg.get("base_min_level", 75))

        self.cat_enabled = {}
        self.cat_thresh  = {}
        enabled_cfg   = self.cfg.get("category_enabled", {})
        threshold_cfg = self.cfg.get("category_threshold", {})
        for key in ALL_CATEGORY_KEYS:
            self.cat_enabled[key] = tk.BooleanVar(value=enabled_cfg.get(key, True))
            self.cat_thresh[key]  = tk.DoubleVar(value=threshold_cfg.get(key, -1.0))

    # ── UI skeleton ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top header bar
        hdr = tk.Frame(self, bg=BG3, pady=0)
        hdr.pack(fill="x")
        label(hdr, "⚔  PoE2 Pickit Generator", fg=GOLD,
              font=("Segoe UI", 13, "bold"), bg=BG3, padx=16, pady=8).pack(side="left")
        self.status_lbl = label(hdr, "Ready", fg=TEXT_DIM, font=FONT_SM, bg=BG3, padx=16)
        self.status_lbl.pack(side="right")
        self.schedule_lbl = label(hdr, "", fg=TEXT_INFO, font=FONT_SM, bg=BG3, padx=8)
        self.schedule_lbl.pack(side="right")

        sep(self).pack(fill="x")

        # Tab bar
        tab_bar = tk.Frame(self, bg=BG2)
        tab_bar.pack(fill="x")
        self._tab_btns = []
        for i, name in enumerate(TABS):
            b = tk.Label(tab_bar, text=name, bg=BG2, fg=TEXT_DIM,
                         font=FONT, padx=14, pady=7, cursor="hand2")
            b.pack(side="left")
            b.bind("<Button-1>", lambda e, idx=i: self._show_tab(idx))
            b.bind("<Enter>",    lambda e, w=b, idx=i: w.config(fg=TEXT) if self._cur_tab != idx else None)
            b.bind("<Leave>",    lambda e, w=b, idx=i: w.config(fg=TEXT_DIM) if self._cur_tab != idx else None)
            self._tab_btns.append(b)

        sep(self).pack(fill="x")

        # Page container
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True)

        # Build all pages
        self._pages = []
        for i, builder in enumerate([
            self._build_generate_page,
            self._build_categories_page,
            self._build_preview_page,
            self._build_history_page,
            self._build_settings_page,
            self._build_debug_page,
        ]):
            page = tk.Frame(self._container, bg=BG)
            self._building_tab_idx = i
            builder(page)
            self._pages.append(page)
        self._building_tab_idx = None

        self._cur_tab = -1
        self._show_tab(0)

    def _show_tab(self, idx):
        for i, page in enumerate(self._pages):
            if i == idx:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        for i, b in enumerate(self._tab_btns):
            if i == idx:
                b.config(bg=BG3, fg=GOLD)
            else:
                b.config(bg=BG2, fg=TEXT_DIM)
        self._cur_tab = idx
        self._active_canvas = self._tab_canvases.get(idx)

    # ── Global mousewheel scroll ──────────────────────────────────────────────

    def _on_wheel(self, event):
        if isinstance(event.widget, (tk.Text, tk.Listbox, tk.Scale)):
            return
        c = self._active_canvas
        if c and c.winfo_exists() and c.yview() != (0.0, 1.0):
            c.yview_scroll(-1 if event.delta > 0 else 1, "units")

    def _on_wheel_up(self, event):
        if isinstance(event.widget, (tk.Text, tk.Listbox, tk.Scale)):
            return
        c = self._active_canvas
        if c and c.winfo_exists() and c.yview() != (0.0, 1.0):
            c.yview_scroll(-1, "units")

    def _on_wheel_down(self, event):
        if isinstance(event.widget, (tk.Text, tk.Listbox, tk.Scale)):
            return
        c = self._active_canvas
        if c and c.winfo_exists() and c.yview() != (0.0, 1.0):
            c.yview_scroll(1, "units")

    # ── Shared layout helpers ─────────────────────────────────────────────────

    def _section_frame(self, parent, title, pady=(12, 0)):
        outer = tk.Frame(parent, bg=BG)
        outer.pack(fill="x", padx=16, pady=pady)
        label(outer, title, fg=GOLD, font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
        inner = tk.Frame(outer, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        inner.pack(fill="x")
        return inner

    def _tab_desc(self, parent, text):
        """Thin description banner shown at the top of each tab."""
        bar = tk.Frame(parent, bg=BG3, highlightthickness=1, highlightbackground=BORDER)
        bar.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(bar, text=text, bg=BG3, fg=TEXT_DIM, font=FONT_SM,
                 anchor="w", padx=12, pady=7, wraplength=900, justify="left").pack(fill="x")

    def _make_slider(self, parent, var, from_, to, resolution, fmt, width=200):
        """
        A styled Scale + value label combo that also responds to the mouse wheel.
        Returns a Frame — just pack/grid it wherever you need it.
        """
        frame = tk.Frame(parent, bg=BG2)

        # Snap var to nearest resolution step on any change
        def _snap(*_):
            try:
                raw = var.get()
                snapped = round(raw / resolution) * resolution
                snapped = max(from_, min(to, snapped))
                if raw != snapped:
                    var.set(snapped)
                val_lbl.config(text=fmt.format(snapped))
            except (tk.TclError, ValueError):
                pass

        scale = tk.Scale(
            frame,
            variable=var,
            from_=from_, to=to,
            resolution=resolution,
            orient="horizontal",
            length=width,
            sliderlength=28,       # wider thumb — easier to grab
            width=14,              # taller track — easier to click
            showvalue=False,       # we display it ourselves in val_lbl
            bg=BG2, fg=TEXT,
            troughcolor=BG3,
            activebackground=GOLD,
            highlightthickness=0,
            bd=0,
            command=lambda v: val_lbl.config(text=fmt.format(float(v))),
        )
        scale.pack(side="left")

        val_lbl = tk.Label(frame, text=fmt.format(var.get()),
                           bg=BG2, fg=GOLD, font=FONT_BOLD, width=9, anchor="w")
        val_lbl.pack(side="left", padx=(6, 0))

        # Mouse-wheel on val_lbl / frame adjusts slider value.
        # The Scale widget handles its own wheel natively on Windows.
        # Page scrolling is handled globally by _on_wheel / bind_all.
        def _on_wheel(event):
            delta = 1 if event.delta > 0 else -1
            try:
                new_val = max(from_, min(to, var.get() + delta * resolution))
                var.set(new_val)
                val_lbl.config(text=fmt.format(new_val))
            except (tk.TclError, ValueError):
                pass

        def _on_wheel_up(event):
            try:
                new_val = max(from_, min(to, var.get() + resolution))
                var.set(new_val)
                val_lbl.config(text=fmt.format(new_val))
            except (tk.TclError, ValueError):
                pass

        def _on_wheel_down(event):
            try:
                new_val = max(from_, min(to, var.get() - resolution))
                var.set(new_val)
                val_lbl.config(text=fmt.format(new_val))
            except (tk.TclError, ValueError):
                pass

        for widget in (val_lbl, frame):
            widget.bind("<MouseWheel>", _on_wheel,     add="+")
            widget.bind("<Button-4>",   _on_wheel_up,  add="+")
            widget.bind("<Button-5>",   _on_wheel_down, add="+")

        var.trace_add("write", _snap)
        return frame

    def _scrollable(self, parent):
        """Return (scrollable inner Frame, outer Canvas).
        Mousewheel is handled globally via bind_all — see _on_wheel.
        """
        c = tk.Canvas(parent, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(parent, orient="vertical", command=c.yview,
                          bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        c.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        c.pack(side="left", fill="both", expand=True)
        inner = tk.Frame(c, bg=BG)
        _wid = c.create_window((0, 0), window=inner, anchor="nw")

        def _resize(e):
            c.configure(scrollregion=c.bbox("all"))
            c.itemconfig(_wid, width=e.width)
        c.bind("<Configure>", _resize)
        inner.bind("<Configure>", lambda e: c.configure(scrollregion=c.bbox("all")))

        tab_idx = getattr(self, '_building_tab_idx', None)
        if tab_idx is not None:
            self._tab_canvases[tab_idx] = c

        return inner, c

    # ══════════════════════════════════════════════════════════════════════════
    #  GENERATE PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_generate_page(self, page):
        self._tab_desc(page,
            "Generate your pickit file.  Select your league, set the minimum item value in Exalted Orbs, "
            "choose an output filename, then click ⚡ Generate.  The tool fetches live prices from poe.ninja "
            "and writes a ready-to-use .ipd file.  Stats and a real-time log appear below after each run.")
        inner, _ = self._scrollable(page)

        # ── League ───────────────────────────────────────────────────────────
        sec = self._section_frame(inner, "League")
        label(sec, "Your active PoE2 economy league. Prices are fetched from poe.ninja for this league only. "
                   "Auto-detected on startup — hit ↻ to refresh if the list is wrong or a new league launched.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 2))
        row = tk.Frame(sec, bg=BG2)
        row.pack(fill="x", padx=10, pady=(4, 10))
        row.columnconfigure(0, weight=1)
        self.league_cb = ttk.Combobox(row, textvariable=self.league_var,
                                       state="normal", font=FONT)
        self.league_cb.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        btn(row, "↻  Refresh", self._fetch_leagues_async).grid(row=0, column=1)

        # ── Threshold ────────────────────────────────────────────────────────
        sec2 = self._section_frame(inner, "Global Threshold (Exalted Orbs)")
        tr = tk.Frame(sec2, bg=BG2)
        tr.pack(fill="x", padx=10, pady=10)
        label(tr, "Items below this value are commented out. Per-category overrides on the Categories tab.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", pady=(0, 6))
        thresh_row = tk.Frame(tr, bg=BG2)
        thresh_row.pack(anchor="w")
        label(thresh_row, "Min value:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        entry(thresh_row, self.min_exalt_var, width=8).pack(side="left", padx=(6, 4), ipady=4)
        label(thresh_row, "ex", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        self.min_exalt_var.trace_add("write", self._clamp_threshold)

        # ── Output ───────────────────────────────────────────────────────────
        sec3 = self._section_frame(inner, "Output File")
        or_ = tk.Frame(sec3, bg=BG2)
        or_.pack(fill="x", padx=10, pady=10)
        label(or_, f"Saved to:  {OUTPUT_DIR}{os.sep}  (.ipd extension added automatically)",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", pady=(0, 6))
        or2 = tk.Frame(or_, bg=BG2)
        or2.pack(fill="x")
        or2.columnconfigure(0, weight=1)
        entry(or2, self.output_var).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        btn(or2, "Browse…", self._browse_output).grid(row=0, column=1)

        # ── Action buttons ───────────────────────────────────────────────────
        btn_f = tk.Frame(inner, bg=BG)
        btn_f.pack(fill="x", padx=10, pady=(14, 0))

        self.gen_btn = btn(btn_f, "⚡  Generate Pickit  (Ctrl+G)",
                           self._start_generate, style="Gold.TButton")
        self.gen_btn.pack(side="left")

        self.open_ipd_btn = btn(btn_f, "Open .ipd", lambda: self._open_file(".ipd"))
        self.open_ipd_btn.pack(side="left", padx=(8, 0))
        self.open_ipd_btn.state(["disabled"])

        btn(btn_f, "Open output folder", self._open_output_folder).pack(side="left", padx=(6, 0))

        # ── Progress ─────────────────────────────────────────────────────────
        self.progress_var = tk.StringVar(value="")
        self.progress_lbl = tk.Label(inner, textvariable=self.progress_var,
                                     bg=BG, fg=TEXT_INFO, font=FONT_SM)
        self.progress_lbl.pack(anchor="w", padx=10, pady=(6, 0))

        # ── Stats row ─────────────────────────────────────────────────────────
        sep(inner).pack(fill="x", padx=10, pady=(14, 0))
        stats_f = tk.Frame(inner, bg=BG)
        stats_f.pack(fill="x", padx=10, pady=10)

        self._stat_vars = {}
        stat_defs = [
            ("active",    "Active rules"),
            ("commented", "Commented out"),
            ("divine",    "Divine rate"),
            ("top",       "Top item"),
            ("duration",  "Run time"),
        ]
        for i, (key, title) in enumerate(stat_defs):
            card = tk.Frame(stats_f, bg=BG2, highlightthickness=1,
                            highlightbackground=BORDER)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            stats_f.columnconfigure(i, weight=1)
            label(card, title, fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 2))
            v = tk.StringVar(value="—")
            label(card, "", textvariable=v, fg=GOLD, font=("Segoe UI", 16, "bold"),
                  bg=BG2, wraplength=155, justify="left").pack(anchor="w", padx=10, pady=(0, 8))
            self._stat_vars[key] = v

        # ── Log ───────────────────────────────────────────────────────────────
        sep(inner).pack(fill="x", padx=10, pady=(4, 0))
        log_hdr = tk.Frame(inner, bg=BG)
        log_hdr.pack(fill="x", padx=10, pady=(8, 4))
        label(log_hdr, "Log", fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        btn(log_hdr, "Copy log", self._log_copy).pack(side="right")
        btn(log_hdr, "Clear", self._log_clear).pack(side="right", padx=(0, 6))

        log_wrap = tk.Frame(inner, bg=BG)
        log_wrap.pack(fill="both", expand=True, padx=10, pady=(0, 16))
        lf, self.log_text = scrolled_text(log_wrap, height=10, state="disabled")
        lf.pack(fill="both", expand=True)
        for tag, col in [("ok", TEXT_OK), ("err", TEXT_ERR), ("warn", TEXT_WARN),
                         ("info", TEXT_INFO), ("dim", TEXT_DIM), ("ts", "#404055")]:
            self.log_text.tag_config(tag, foreground=col)

    def _clamp_threshold(self, *_):
        try:
            v = self.min_exalt_var.get()
            if v < 0:
                self.min_exalt_var.set(0.0)
        except (tk.TclError, ValueError):
            pass  # user is mid-typing — leave the field alone

    # ══════════════════════════════════════════════════════════════════════════
    #  CATEGORIES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_categories_page(self, page):
        self._tab_desc(page,
            "Choose which item categories are included in your pickit and fine-tune their value thresholds.  "
            "Tick the checkbox to enable a category.  Set a custom threshold (in ex) to override the global "
            "minimum for that category only — use −1 to fall back to the global value, or 0 to pick up "
            "everything in the category regardless of price.  Use the Preset buttons to quickly switch "
            "between common configurations.")
        # Presets bar
        preset_f = tk.Frame(page, bg=BG)
        preset_f.pack(fill="x", padx=16, pady=10)
        label(preset_f, "Presets:", fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(0, 8))
        for lbl_text, fn in [
            ("All",             self._cat_enable_all),
            ("None",            self._cat_disable_all),
            ("Currency only",   self._cat_preset_currency),
            ("Uniques only",    self._cat_preset_uniques),
            ("Maps + Currency", self._cat_preset_maps),
        ]:
            btn(preset_f, lbl_text, fn).pack(side="left", padx=(0, 4))

        label(page,
              "Threshold: −1 = use global.  0 = pick all in this category.",
              fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=16)

        sep(page).pack(fill="x", padx=16, pady=(8, 0))

        inner, _ = self._scrollable(page)

        vcmd = (self.register(lambda v: v == "" or bool(re.fullmatch(r"-?\d*\.?\d*", v))), "%P")

        def cat_group(group_label, cats, unique=False, desc=""):
            lf = tk.Frame(inner, bg=BG)
            lf.pack(fill="x", pady=(12, 0))
            label(lf, group_label, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(16, 8))
            sep(lf).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)
            if desc:
                label(inner, desc, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=16, pady=(2, 4))

            row_bg = "#1e1e2a" if unique else BG2
            for key, _, lbl_text, _ in cats:
                row = tk.Frame(inner, bg=row_bg,
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", padx=16, pady=2)
                row.columnconfigure(1, weight=1)

                cb = tk.Checkbutton(row, text=lbl_text, variable=self.cat_enabled[key],
                    bg=row_bg, fg=TEXT_INFO if unique else TEXT,
                    selectcolor=BG3, activebackground=row_bg,
                    activeforeground=TEXT, font=FONT, anchor="w", padx=10, pady=6)
                cb.pack(side="left")

                thresh_f = tk.Frame(row, bg=row_bg)
                thresh_f.pack(side="right", padx=8)
                label(thresh_f, "ex  (−1 = global)", fg=TEXT_DIM, font=FONT_SM, bg=row_bg).pack(side="right")
                e = tk.Entry(thresh_f, textvariable=self.cat_thresh[key], width=7,
                    bg=BG3, fg=TEXT, insertbackground=GOLD,
                    relief="flat", bd=0, font=FONT,
                    highlightthickness=1, highlightbackground=BORDER,
                    validate="key", validatecommand=vcmd)
                e.pack(side="right", padx=(0, 4), ipady=4)
                label(thresh_f, "threshold:", fg=TEXT_DIM, font=FONT_SM, bg=row_bg).pack(side="right", padx=(0, 4))

        cat_group("Exchange Categories", gen.EXCHANGE_CATEGORIES, unique=False,
                  desc="Tradeable items fetched live from poe.ninja — currencies, runes, essences, gems and more.  "
                       "Each item's value is converted to Exalted Orbs and compared against your threshold.")
        cat_group("Unique Categories", gen.UNIQUE_CATEGORIES, unique=True,
                  desc="Unique items matched by base type and name.  "
                       "Rules use [UniqueName] so the bot only picks the exact unique, not any rare of the same base.")

        # ── Base Types (Poe2DB) ───────────────────────────────────────────────
        lf_b = tk.Frame(inner, bg=BG)
        lf_b.pack(fill="x", pady=(16, 0))
        label(lf_b, "Base Types  (Poe2DB)", fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(16, 8))
        sep(lf_b).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)

        sec_b = tk.Frame(inner, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        sec_b.pack(fill="x", padx=16, pady=(2, 12))

        label(sec_b,
              "Scrapes endgame weapon bases (level 80+) from poe2db.tw and generates Quality / Socket pickup rules.  "
              "Covers the 11 weapon types you selected.  Adds ~30 s to generate time.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))

        checkbtn(sec_b, "Include endgame base types in pickit", self.include_bases_var
                 ).pack(anchor="w", padx=10, pady=(0, 4))

        qrow = tk.Frame(sec_b, bg=BG2)
        qrow.pack(anchor="w", padx=10, pady=(0, 10))
        label(qrow, "Min quality:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        entry(qrow, self.base_quality_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        label(qrow, "%", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        label(qrow, "   Min item level:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left", padx=(16, 0))
        entry(qrow, self.base_min_level_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        label(qrow, "(80+ = endgame only)", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left", padx=(6, 0))

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_preview_page(self, page):
        self._tab_desc(page,
            "Browse the raw content of your last generated pickit file.  "
            "Active rules are shown in green, commented-out (below-threshold) rules in grey, "
            "and section headers in gold.  Use the Filter box to search by item name or any keyword.  "
            "Click 'Copy all' to copy the entire file to your clipboard.")
        ctrl = tk.Frame(page, bg=BG)
        ctrl.pack(fill="x", padx=16, pady=10)
        label(ctrl, "Filter:", fg=TEXT_DIM, font=FONT).pack(side="left", padx=(0, 6))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._filter_preview)
        entry(ctrl, self.filter_var, width=28).pack(side="left", ipady=4)
        self.preview_count_var = tk.StringVar(value="Generate to see rules")
        label(ctrl, "", textvariable=self.preview_count_var,
              fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(12, 0))
        btn(ctrl, "Copy all", self._preview_copy).pack(side="right")

        sep(page).pack(fill="x", padx=16)

        pf, self.preview_text = scrolled_text(page, state="disabled")
        pf.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        for tag, col, bg_col in [
            ("active",    TEXT_OK,   None),
            ("commented", TEXT_DIM,  None),
            ("header",    GOLD,      None),
            ("unique",    TEXT_INFO, None),
        ]:
            kw = {"foreground": col}
            if bg_col:
                kw["background"] = bg_col
            self.preview_text.tag_config(tag, **kw)

    def _populate_preview(self, lines):
        self._preview_lines = lines
        self._render_preview(lines)

    def _render_preview(self, lines):
        t = self.preview_text
        ypos = t.yview()[0]
        t.config(state="normal")
        t.delete("1.0", "end")
        active = commented = 0
        for line in lines:
            if line.startswith("////") or (line.startswith("//") and line.count("//") > 2):
                tag = "header"
            elif line.startswith("//"):
                tag = "commented"
                commented += 1
            elif "[StashItem]" in line:
                tag = "unique" if "[Rarity]" in line else "active"
                active += 1
            else:
                tag = ""
            t.insert("end", line + "\n", tag)
        t.config(state="disabled")
        t.yview_moveto(ypos)
        self.preview_count_var.set(f"{active} active rules  ·  {commented} commented out")

    def _filter_preview(self, *_):
        q = self.filter_var.get().lower()
        if not q or not self._preview_lines:
            if self._preview_lines:
                self._render_preview(self._preview_lines)
            return
        self._render_preview([l for l in self._preview_lines if q in l.lower()])

    def _preview_copy(self):
        if not self._preview_lines:
            return
        self.clipboard_clear()
        self.clipboard_append("\n".join(self._preview_lines))
        # Show a brief status in the preview count label
        prev = self.preview_count_var.get()
        self.preview_count_var.set("Copied to clipboard!")
        self.after(1500, lambda: self.preview_count_var.set(prev))

    # ══════════════════════════════════════════════════════════════════════════
    #  HISTORY PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_history_page(self, page):
        self._tab_desc(page,
            "A log of every pickit file you have generated in this session and across previous runs.  "
            "Each row shows the date and time, how many rules were active or commented out, the Divine Orb "
            "exchange rate at the time, the highest-value item found, and how long the run took.  "
            "The last 50 runs are kept.  Click 'Clear history' to wipe the log.")
        cols = ("Date/time", "Active", "Commented", "Divine rate", "Top item", "Duration")
        self._hist_tree = ttk.Treeview(page, columns=cols, show="headings", height=12)
        for c in cols:
            self._hist_tree.heading(c, text=c)
            self._hist_tree.column(c, width=120, anchor="w")
        self._hist_tree.pack(fill="both", expand=True, padx=16, pady=(12, 4))

        btn_f = tk.Frame(page, bg=BG)
        btn_f.pack(anchor="w", padx=16, pady=(4, 12))
        btn(btn_f, "Clear history", self._clear_history).pack(side="left")

        self._refresh_history_ui()

    def _add_history_entry(self, entry_dict):
        h = self.cfg.get("history", [])
        h.append(entry_dict)
        if len(h) > 50:
            h = h[-50:]
        self.cfg["history"] = h
        save_config(self.cfg)
        self.after(0, self._refresh_history_ui)

    def _refresh_history_ui(self):
        h = self.cfg.get("history", [])
        for row in self._hist_tree.get_children():
            self._hist_tree.delete(row)
        for e in reversed(h[-50:]):
            self._hist_tree.insert("", "end", values=(
                e.get("ts", ""),
                e.get("active", ""),
                e.get("commented", ""),
                f"{e.get('divine_rate', 0):.1f} ex",
                f"{e.get('top_item', '')}  ({e.get('top_value', 0):.0f}ex)",
                e.get("duration", ""),
            ))

    def _clear_history(self):
        if messagebox.askyesno("Clear history", "Delete all history entries?"):
            self.cfg["history"] = []
            save_config(self.cfg)
            self._refresh_history_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_settings_page(self, page):
        self._tab_desc(page,
            "Configure the tool's behaviour.  Point the bot folder to your Exiled Bot pickit directory "
            "and enable Auto-copy to have the .ipd file deployed there automatically after every generate.  "
            "Auto-Schedule re-generates on a timer so your pickit stays fresh without manual clicks.  "
            "Adjust backup count, notifications, and overwrite protection to suit your workflow, "
            "then click 'Save settings' to apply.")
        inner, _ = self._scrollable(page)

        # Bot folder
        sec = self._section_frame(inner, "Bot Integration")
        label(sec, "Set the path to your Exiled Bot 2 pickit folder. When Auto-copy is on, the generated .ipd "
                   "file is automatically deployed there after every run — no manual file copying needed.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))
        bf = tk.Frame(sec, bg=BG2)
        bf.pack(fill="x", padx=10, pady=(0, 6))
        bf.columnconfigure(0, weight=1)
        entry(bf, self.bot_folder_var).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        btn(bf, "Browse…", self._browse_bot_folder).grid(row=0, column=1)
        checkbtn(sec, "Auto-copy .ipd to bot folder after generate", self.auto_copy_var
                 ).pack(anchor="w", padx=10, pady=(0, 10))

        # Schedule
        sec2 = self._section_frame(inner, "Auto-Schedule")
        label(sec2, "Pickit automatically re-generates every 1 hour so your prices are always up to date. "
                    "This runs in the background as long as the app is open — no setup needed.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 10))

        # Backups
        sec3 = self._section_frame(inner, "Backups")
        label(sec3, "Keeps numbered copies of your previous pickit files before overwriting. "
                    "Lets you roll back to an earlier version if needed. Set to 0 to disable backups.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))
        bf2 = tk.Frame(sec3, bg=BG2)
        bf2.pack(fill="x", padx=10, pady=(0, 10))
        label(bf2, "Keep", fg=TEXT_DIM, bg=BG2).pack(side="left")
        self._make_slider(bf2, self.backup_count_var, from_=0, to=20, resolution=1,
                          fmt="{:.0f} backups", width=220).pack(side="left", padx=(10, 4))
        label(bf2, "(0 = disabled)", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left", padx=(6, 0))

        # Notifications
        sec4 = self._section_frame(inner, "Notifications")
        label(sec4, "Toast shows a Windows popup when generation finishes. "
                    "Launch minimized hides the window to the taskbar on startup so it doesn't cover your game.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))
        for lbl_text, var in [
            ("Toast notification (Windows, win10toast required)", self.toast_var),
            ("Launch minimized", self.start_min_var),
        ]:
            checkbtn(sec4, lbl_text, var).pack(anchor="w", padx=10, pady=2)
        tk.Frame(sec4, bg=BG2, height=6).pack()  # spacing

        # Overwrite protection
        sec5 = self._section_frame(inner, "Overwrite Protection")
        label(sec5, "Asks for confirmation before overwriting a file that was generated recently. "
                    "Prevents accidents if you click Generate twice by mistake. Set to 0 to always ask.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))
        of = tk.Frame(sec5, bg=BG2)
        of.pack(fill="x", padx=10, pady=(0, 10))
        label(of, "Confirm overwrite if file younger than", fg=TEXT_DIM, bg=BG2).pack(side="left")
        self._make_slider(of, self.ovw_var, from_=0, to=3600, resolution=30,
                          fmt="{:.0f} s", width=260).pack(side="left", padx=(10, 4))
        label(of, "(0 = always ask)", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left", padx=(6, 0))

        # Config file location
        sec6 = self._section_frame(inner, "Config File")
        label(sec6, "Where your settings, category toggles, and history are saved. "
                    "Click Open to inspect or manually edit. Deleting it resets everything to defaults.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))
        cf = tk.Frame(sec6, bg=BG2)
        cf.pack(fill="x", padx=10, pady=(0, 10))
        label(cf, CONFIG_PATH, fg=TEXT_DIM, font=FONT_MONO, bg=BG2).pack(side="left")
        btn(cf, "Open", lambda: self._open_file_path(CONFIG_PATH)).pack(side="left", padx=(8, 0))

        # Buttons
        bf3 = tk.Frame(inner, bg=BG)
        bf3.pack(fill="x", padx=16, pady=(16, 20))
        btn(bf3, "Save settings", self._save_settings, style="Gold.TButton").pack(side="left")
        btn(bf3, "Reset to defaults", self._reset_defaults).pack(side="left", padx=(8, 0))

    def _save_settings(self):
        self.cfg["bot_folder"]             = self.bot_folder_var.get()
        self.cfg["auto_copy"]              = self.auto_copy_var.get()
        self.cfg["backup_count"]           = self.backup_count_var.get()
        self.cfg["toast_on_complete"]      = self.toast_var.get()
        self.cfg["start_minimized"]        = self.start_min_var.get()
        self.cfg["confirm_overwrite_secs"] = self.ovw_var.get()
        self.cfg["include_bases"]          = self.include_bases_var.get()
        self.cfg["base_quality"]           = self.base_quality_var.get()
        self.cfg["base_min_level"]         = self.base_min_level_var.get()
        save_config(self.cfg)
        self._log("Settings saved.", "ok")

    def _reset_defaults(self):
        if messagebox.askyesno("Reset settings", "Reset all settings to defaults?"):
            self.cfg = dict(DEFAULT_CONFIG)
            save_config(self.cfg)
            # Re-sync all tk vars so the live UI reflects defaults immediately
            self.league_var.set(self.cfg.get("league", ""))
            self.min_exalt_var.set(self.cfg.get("min_exalt", 10.0))
            self.output_var.set(self.cfg.get("output_base", "poe2_pickit"))
            self.bot_folder_var.set(self.cfg.get("bot_folder", ""))
            self.auto_copy_var.set(self.cfg.get("auto_copy", False))
            self.backup_count_var.set(self.cfg.get("backup_count", 5))
            self.toast_var.set(self.cfg.get("toast_on_complete", True))
            self.start_min_var.set(self.cfg.get("start_minimized", False))
            self.ovw_var.set(self.cfg.get("confirm_overwrite_secs", 120))
            self.include_bases_var.set(True)
            self.base_quality_var.set(self.cfg.get("base_quality", 28))
            self.base_min_level_var.set(self.cfg.get("base_min_level", 75))
            for key in ALL_CATEGORY_KEYS:
                self.cat_enabled[key].set(True)
                self.cat_thresh[key].set(-1.0)
            self._log("Settings reset to defaults.", "warn")

    def _browse_bot_folder(self):
        folder = filedialog.askdirectory(title="Select Exiled Bot pickit folder")
        if folder:
            self.bot_folder_var.set(folder)

    # ══════════════════════════════════════════════════════════════════════════
    #  DEBUG PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_debug_page(self, page):
        self._tab_desc(page,
            "Troubleshooting tools for when something is not working.  'Run diagnostics' checks your Python "
            "environment, required modules, and poe.ninja connectivity.  'Test all API endpoints' pings every "
            "category endpoint and reports row counts and response times.  'Show config' dumps your current "
            "saved settings.  Share the output here when reporting a bug.")
        btn_f = tk.Frame(page, bg=BG)
        btn_f.pack(fill="x", padx=16, pady=10)
        btn(btn_f, "Run diagnostics", self._run_diagnostics).pack(side="left")
        btn(btn_f, "Test all API endpoints",
            lambda: threading.Thread(target=self._api_test_worker, daemon=True).start()
            ).pack(side="left", padx=(6, 0))
        btn(btn_f, "Show config", self._debug_show_config).pack(side="left", padx=(6, 0))
        btn(btn_f, "Clear", self._debug_clear).pack(side="left", padx=(6, 0))

        sep(page).pack(fill="x", padx=16)

        df, self.debug_text = scrolled_text(page, state="disabled")
        df.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        for tag, col in [("header", GOLD), ("ok", TEXT_OK), ("err", TEXT_ERR),
                         ("warn", TEXT_WARN), ("info", TEXT_INFO), ("dim", TEXT_DIM)]:
            self.debug_text.tag_config(tag, foreground=col)

    def _dlog(self, msg, tag=""):
        def _do():
            self.debug_text.config(state="normal")
            self.debug_text.insert("end", msg + "\n", tag)
            self.debug_text.see("end")
            self.debug_text.config(state="disabled")
        self.after(0, _do)

    def _debug_clear(self):
        self.debug_text.config(state="normal")
        self.debug_text.delete("1.0", "end")
        self.debug_text.config(state="disabled")

    def _run_diagnostics(self):
        self._debug_clear()
        threading.Thread(target=self._diag_worker, daemon=True).start()

    def _diag_worker(self):
        d = self._dlog
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        d(f"═══ PoE2 Pickit Generator — Diagnostics  ·  {now}", "header")
        d("")
        d("── 1. Python environment", "header")
        d(f"  Python   : {sys.version.split()[0]}", "info")
        d(f"  Platform : {sys.platform}", "info")
        frozen = getattr(sys, 'frozen', False)
        d(f"  Frozen   : {frozen}  ({'PyInstaller EXE' if frozen else '.py script'})", "info")
        d(f"  CWD      : {os.getcwd()}", "info")
        d("")
        d("── 2. Module checks", "header")
        for mod, required in [("tkinter", True), ("requests", True),
                               ("poe2_pickit_generator", True), ("win10toast", False)]:
            try:
                m = importlib.import_module(mod)
                ver = getattr(m, "__version__", "n/a")
                d(f"  ✓  {mod:<30} {ver}", "ok")
            except ImportError as e:
                d(f"  {'✗' if required else '⚠'}  {mod:<30} {'MISSING' if required else 'optional'} — {e}",
                  "err" if required else "warn")
        d("")
        d("── 3. Generator module", "header")
        try:
            d(f"  BASE_URL        : {gen.BASE_URL}", "info")
            d(f"  INDEX_STATE_URL : {gen.INDEX_STATE_URL}", "info")
            d(f"  MIN_EXALT       : {gen.MIN_EXALT}", "info")
            d(f"  Exchange cats   : {len(gen.EXCHANGE_CATEGORIES)}", "info")
            d(f"  Unique cats     : {len(gen.UNIQUE_CATEGORIES)}", "info")
            d("  ✓  Generator module healthy", "ok")
        except Exception as e:
            d(f"  ✗  {e}", "err")
        d("")
        d("── 4. poe.ninja connectivity", "header")
        try:
            t0 = time.time()
            data = gen.fetch_json(gen.INDEX_STATE_URL, {})
            d(f"  ✓  Reachable ({(time.time()-t0)*1000:.0f} ms)", "ok")
            leagues = data.get("economyLeagues", [])
            d(f"  Active leagues : {len(leagues)}", "info")
            for lg in leagues:
                d(f"    • {lg.get('name', '?')}", "dim")
        except Exception as e:
            d(f"  ✗  FAILED: {e}", "err")
        d("")
        d("── 5. Output paths", "header")
        base = self._output_base_path()
        ipd = base + ".ipd"
        out_dir = os.path.dirname(os.path.abspath(ipd)) or os.getcwd()
        d(f"  .ipd path   : {os.path.abspath(ipd)}", "info")
        d(f"  Dir writable: {os.access(out_dir, os.W_OK)}", "ok" if os.access(out_dir, os.W_OK) else "err")
        d(f"  .ipd exists : {os.path.isfile(ipd)}", "info")
        d("")
        d("═══ Diagnostics complete ═══", "header")

    def _api_test_worker(self):
        d = self._dlog
        d("── API endpoint test ──", "header")
        league = self._selected_league()
        if not league or league.startswith("Loading"):
            league = "Standard"
        d(f"League: {league}", "info")
        for key, ninja_type, label_text, is_unique in gen.ALL_CATEGORIES:
            try:
                t0 = time.time()
                payload = gen.fetch_category(league, key, ninja_type, is_unique)
                elapsed = time.time() - t0
                n_items = len(payload.get("items", payload.get("lines", [])))
                d(f"  ✓  {label_text:<30} {n_items:>4} rows  ({elapsed*1000:.0f} ms)", "ok")
                time.sleep(0.2)
            except Exception as e:
                d(f"  ✗  {label_text:<30} {e}", "err")
        d("── API test done ──", "header")

    def _debug_show_config(self):
        self._debug_clear()
        self._dlog("── Current config ──", "header")
        cfg_copy = dict(self.cfg)
        cfg_copy.pop("history", None)
        for k, v in cfg_copy.items():
            self._dlog(f"  {k:<28}: {json.dumps(v)}", "info")
        self._dlog(f"  {'history entries':<28}: {len(self.cfg.get('history', []))}", "dim")

    # ══════════════════════════════════════════════════════════════════════════
    #  League helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _fetch_leagues_async(self):
        self.league_var.set(self.league_var.get() or "Loading…")
        self.league_cb.config(state="disabled")
        threading.Thread(target=self._fetch_leagues, daemon=True).start()

    def _fetch_leagues(self):
        try:
            leagues = gen.fetch_live_leagues()
            self._leagues = leagues
            names = [f"{d}  [{n}]" for n, _, d in leagues]
            self.after(0, lambda: self._populate_leagues(names))
        except Exception as e:
            self.after(0, lambda: self._log(f"Could not fetch leagues: {e}", "err"))
            self.after(0, lambda: self.league_var.set(self.cfg.get("league") or ""))
            self.after(0, lambda: self.league_cb.config(state="normal"))

    def _populate_leagues(self, names):
        self.league_cb["values"] = names
        self.league_cb.config(state="normal")
        saved = self.cfg.get("league", "")
        matched = False
        if saved:
            for i, (n, _, d) in enumerate(self._leagues):
                if n == saved or d == saved:
                    self.league_cb.current(i)
                    matched = True
                    break
        if not matched and names:
            self.league_cb.current(0)
        self._log(f"Loaded {len(names)} leagues.", "ok")

    def _selected_league(self):
        raw = self.league_var.get().strip()
        if not self._leagues or raw.startswith("Loading"):
            return raw
        idx = self.league_cb.current()
        if 0 <= idx < len(self._leagues):
            return self._leagues[idx][0]
        if "[" in raw and raw.endswith("]"):
            return raw.split("[")[-1].rstrip("]").strip()
        return raw

    # ══════════════════════════════════════════════════════════════════════════
    #  Category presets
    # ══════════════════════════════════════════════════════════════════════════

    def _cat_enable_all(self):
        for v in self.cat_enabled.values(): v.set(True)

    def _cat_disable_all(self):
        for v in self.cat_enabled.values(): v.set(False)

    def _cat_preset_currency(self):
        self._cat_disable_all()
        self.cat_enabled["currency"].set(True)

    def _cat_preset_uniques(self):
        self._cat_disable_all()
        for key in [c[0] for c in gen.UNIQUE_CATEGORIES]:
            self.cat_enabled[key].set(True)

    def _cat_preset_maps(self):
        self._cat_disable_all()
        self.cat_enabled["currency"].set(True)
        self.cat_enabled["waystones"].set(True)
        self.cat_enabled["unique_maps"].set(True)

    # ══════════════════════════════════════════════════════════════════════════
    #  File helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _output_base_path(self):
        name = os.path.basename(os.path.splitext(self.output_var.get())[0])
        return os.path.join(OUTPUT_DIR, name)

    def _browse_output(self):
        """Let the user rename the output file base-name.
        The file is always written inside OUTPUT_DIR, so only the basename matters;
        any directory component chosen in the dialog is intentionally stripped.
        """
        path = filedialog.asksaveasfilename(
            defaultextension="",
            filetypes=[("All files", "*.*")],
            initialdir=OUTPUT_DIR,
            initialfile=self.output_var.get(),
            title="Choose output filename (saved in output folder)")
        if path:
            # Only keep the base-name; OUTPUT_DIR is always the destination.
            self.output_var.set(os.path.basename(os.path.splitext(path)[0]))

    def _open_file(self, ext):
        base = self._output_base_path()
        path = base + ext
        if not os.path.isfile(path):
            self._log(f"File not found: {path}", "warn")
            return
        self._open_file_path(path)

    def _open_output_folder(self):
        self._open_file_path(OUTPUT_DIR)

    def _open_file_path(self, path):
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self._log(f"Could not open: {e}", "err")

    # ══════════════════════════════════════════════════════════════════════════
    #  Log
    # ══════════════════════════════════════════════════════════════════════════

    def _log(self, msg, tag=""):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{ts}] ", "ts")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        self.after(0, _do)

    def _log_clear(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _log_copy(self):
        content = self.log_text.get("1.0", "end").strip()
        if not content:
            self._log("Log is empty — nothing to copy.", "warn")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self._log("Log copied to clipboard.", "ok")

    # ══════════════════════════════════════════════════════════════════════════
    #  Backup
    # ══════════════════════════════════════════════════════════════════════════

    def _backup_file(self, path, n=None):
        if n is None:
            n = self.backup_count_var.get()
        if n <= 0 or not os.path.isfile(path):
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(path)
        shutil.copy2(path, f"{base}_backup_{ts}{ext}")
        folder = os.path.dirname(path) or "."
        stem = os.path.basename(base)
        backups = sorted([
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.startswith(stem + "_backup_") and f.endswith(ext)
        ])
        while len(backups) > n:
            try:
                os.remove(backups.pop(0))
            except Exception:
                pass

    # ══════════════════════════════════════════════════════════════════════════
    #  Schedule
    # ══════════════════════════════════════════════════════════════════════════

    def _schedule_tick(self):
        if not self._running:
            now = time.time()
            if now - self._last_run_time >= 3600:
                self._start_generate(silent=True)
            remaining = int(3600 - (now - self._last_run_time))
            h, m = divmod(max(remaining, 0) // 60, 60)
            self.schedule_lbl.config(text=f"⏱ Next: {h}h {m}m")
        self._schedule_after = self.after(30_000, self._schedule_tick)

    # ══════════════════════════════════════════════════════════════════════════
    #  Rule helpers
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def _extract_rule_name(line):
        um = re.search(r'\[UniqueName\] == "([^"]+)"', line)
        if um:
            return um.group(1)
        nm = re.search(r'"([^"]+)"', line)
        return nm.group(1) if nm else None

    # ══════════════════════════════════════════════════════════════════════════
    #  GENERATE
    # ══════════════════════════════════════════════════════════════════════════

    def _start_generate(self, silent: bool = False):
        if self._running:
            return

        league = self._selected_league()
        if not league or league.startswith("Loading"):
            self._log("No league selected — wait for the league list to load or type a name manually.", "warn")
            return

        base_path = self._output_base_path()
        ipd_path  = base_path + ".ipd"
        if not silent and os.path.isfile(ipd_path):
            age   = time.time() - os.path.getmtime(ipd_path)
            limit = self.cfg.get("confirm_overwrite_secs", 120)
            if age < limit:
                if not messagebox.askyesno("Overwrite?",
                        f"The pickit was generated {int(age)}s ago.\nOverwrite it now?"):
                    return

        self._running = True
        self._generate_start = time.time()
        if silent:
            self._log("─" * 55, "dim")
            self._log("Auto-schedule triggered.", "info")
        else:
            self._log_clear()
        self.gen_btn.state(["disabled"])
        self.open_ipd_btn.state(["disabled"])
        self.status_lbl.config(text="Generating…", fg=TEXT_WARN)
        self.progress_var.set("Starting…")

        # Snapshot all Tk variables here on the main thread so the worker never
        # touches Tcl/Tk state from a background thread (avoids intermittent
        # freezes on non-Windows platforms where Tk is not thread-safe).
        snapshot = {
            "league":          league,
            "output_var":      self.output_var.get(),
            "auto_copy":       self.auto_copy_var.get(),
            "bot_folder":      self.bot_folder_var.get(),
            "toast":           self.toast_var.get(),
            "backup_count":    self.backup_count_var.get(),
            "cat_enabled":     {k: v.get() for k, v in self.cat_enabled.items()},
            "cat_thresh":      {},
            "include_bases":   self.include_bases_var.get(),
            "base_quality":    self.base_quality_var.get(),
            "base_min_level":  self.base_min_level_var.get(),
        }
        for k, v in self.cat_thresh.items():
            try:
                snapshot["cat_thresh"][k] = v.get()
            except tk.TclError:
                snapshot["cat_thresh"][k] = -1.0
        try:
            snapshot["min_exalt"] = self.min_exalt_var.get()
        except tk.TclError:
            snapshot["min_exalt"] = float(self.cfg.get("min_exalt", 10.0))
            self.min_exalt_var.set(snapshot["min_exalt"])
            self._log("Threshold field invalid — reset to saved value.", "warn")

        threading.Thread(target=self._generate, args=(snapshot,), daemon=True).start()

    def _generate(self, snapshot: dict):
        success = False
        try:
            league    = snapshot["league"]
            min_exalt = snapshot["min_exalt"]

            try:
                min_exalt = float(min_exalt)
            except (TypeError, ValueError):
                min_exalt = float(self.cfg.get("min_exalt", 10.0))
                self._log("Threshold field invalid — reset to saved value.", "warn")

            base_path = os.path.join(OUTPUT_DIR,
                                     os.path.basename(os.path.splitext(snapshot["output_var"])[0]))
            ipd_path  = base_path + ".ipd"

            self._log(f"League    : {league}")
            self._log(f"Threshold : {min_exalt:.0f} ex")
            self._log(f"Output    : {os.path.basename(base_path)}.ipd")
            self._log("─" * 55, "dim")

            categories = [cat for cat in gen.ALL_CATEGORIES
                          if snapshot["cat_enabled"].get(cat[0], True)]
            total_cats  = len(categories)

            _gen_ts  = datetime.datetime.now()
            _gen_id  = _gen_ts.strftime('%Y%m%d_%H%M%S')
            output_lines = [
                "/" * gen._W,
                "//" + f"  POE 2  |  PICKIT  |  ID: {_gen_id}".center(gen._W - 4) + "//",
                "/" * gen._W,
                f"// League    : {league}",
                f"// Generated : {_gen_ts.strftime('%Y-%m-%d %H:%M:%S')}",
                f"// Pickit ID : {_gen_id}",
                f"// Threshold : {min_exalt:.0f} ex",
                "/" * gen._W, "",
                # ── Configuration guide ───────────────────────────────────────
                "//",
                "// Exiled Bot 2 Pickit - Configuration Guide for Path of Exile 2",
                "//",
                "// This file defines which items your bot should pick up, identify, keep, or salvage.",
                "//",
                "// Important File:",
                "// - ModsList.html in the main bot folder contains all available mods",
                "//   (Use expressions from the right column, like local_minimum_added_physical_damage)",
                "//",
                "// Special Computed Values:",
                "// ----------------------",
                "// [TotalResistances] - Sums all resistance values on an item",
                '//   Example: [Category] == "Helmet" # [TotalResistances] > "50" && [StashItem] == "true"',
                "//",
                "// Defensive Calculations:",
                "// ---------------------",
                "// [ComputedArmour]       - Final armour value after all modifiers",
                "// [ComputedEvasion]      - Final evasion value after all modifiers",
                "// [ComputedEnergyShield] - Final ES value after all modifiers",
                "//",
                "// Damage Calculations:",
                "// ------------------",
                "// [DPS]         - Total weapon DPS (physical + elemental)",
                "// [ElementalDPS]  - Only elemental portion of weapon DPS",
                "// [PhysicalDPS]   - Only physical portion of weapon DPS",
                "//",
                "// Spell Damage Totals:",
                "// ------------------",
                "// [TotalSpellElementalDamage]  - Combined spell + elemental damage (%)",
                "// [TotalFireSpellDamage]       - Fire spell damage including general spell damage (%)",
                "// [TotalColdSpellDamage]       - Cold spell damage including general spell damage (%)",
                "// [TotalLightningSpellDamage]  - Lightning spell damage including general spell damage (%)",
                "//",
                "// Gems:",
                "// ----",
                "// [GemLevel] - Current level of the gem",
                '// Example: [Type] == "Uncut Support Gem" && [GemLevel] == "3" # [StashItem] == "true"',
                "//",
                "// UniqueName:",
                "// ----------",
                "// Matches specific unique items by their exact name",
                '// Example: [Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"',
                "//",
                "// ItemTier:",
                "// --------",
                "// Represents the tier of the item base type (higher is better)",
                '// Example: [Category] == "Ring" && [ItemTier] >= "2" # [StashItem] == "true"',
                "//",
                "// Quality:",
                "// -------",
                "// The quality percentage of an item (0-20 for most items)",
                '// Example: [Quality] >= "15" # [StashItem] == "true"',
                "//",
                "// WaystoneTier:",
                "// ------------",
                "// The tier of a waystone (1-16 at the moment)",
                '// Example: [Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"',
                "//",
                "// Basic Syntax:",
                "// -----------",
                "// Each line: [What to Check] Operator \"Value\"",
                "//",
                "// Operators: == != > >= < <=",
                "// Combine:   && (AND)  || (OR)  () (group)",
                "//",
                "// Available Categories:",
                '// Equipment : "BodyArmour", "Gloves", "Boots", "Belt", "Helmet", "Ring", "Amulet"',
                '// Weapons   : "Weapon", "1Handed", "2Handed", "OffHand"',
                '// Others    : "Flask", "Waystone", "Gem"',
                "//",
                "// WeaponCategory:",
                '// 1H : "Claw","Dagger","Wand","OneHandSword","OneHandAxe","OneHandMace","Sceptre","Spear","Flail"',
                '// 2H : "Bow","Staff","TwoHandSword","TwoHandAxe","TwoHandMace","Quarterstaff","Crossbow","Trap"',
                '// OH : "Quiver","Shield","Focus"',
                "//",
                "// Rarity Values:  \"Normal\", \"Magic\", \"Rare\", \"Unique\"",
                "//",
                "// Special Flags:",
                '// [StashItem]    == "true"  - Put item in stash',
                '// [StashUnid]    == "true"  - Stash without identifying',
                '// [Salvage]      == "true"  - Mark for salvaging',
                '// [IgnoreRitual] == "true"  - Ignore item from ritual rewards',
                "//",
                "// Rule split with #:",
                "// Before # = checked BEFORE identifying",
                "// After  # = checked AFTER  identifying",
                '// Example: [Rarity] == "Rare" # [TotalResistances] > "50" && [StashItem] == "true"',
                "//",
                "// Local vs Global Modifiers:",
                "// local_* mods (local_attack_speed_+%) affect only the item itself",
                "// regular mods (attack_speed_+%)       affect your entire character",
                "//",
                "/" * gen._W, "",
            ]
            self._log(f"Pickit ID : {_gen_id}", "info")

            self._log("Fetching currency rates…", "dim")
            currency_payload = gen.fetch_category(league, "currency", "Currency", False)
            gen._cache_set(league, "currency", currency_payload)
            items_by_id      = {i["id"]: i for i in currency_payload.get("items", [])}
            rate             = gen.exalted_rate(currency_payload)
            divine_rate_exalts = 1.0
            _divine_found = False
            for line in currency_payload.get("lines", []):
                item = items_by_id.get(line.get("id"))
                if item and item.get("name") == "Divine Orb":
                    pv = float(line.get("primaryValue") or 0.0)
                    divine_rate_exalts = pv * rate if rate else pv
                    _divine_found = True
                    break

            if not _divine_found:
                self._log("  ⚠ Divine Orb not found — divine conversion unavailable", "warn")
            if rate == 0:
                self._log("  ⚠ Exalted rate is 0 — item values may be inaccurate", "warn")

            self._log(f"1 Divine = {divine_rate_exalts:.1f} Exalted", "ok")
            output_lines += [f"// Conversion: 1 Divine = {divine_rate_exalts:.6f} Exalted", "",
                              gen.header_major("Economy Items"), ""]

            top_item    = ("", 0.0)
            report_rows = []

            # Fetch all non-currency categories in parallel
            non_currency_cats = [(k, t, l, u) for k, t, l, u in categories if k != "currency"]
            self._log(f"Fetching {len(non_currency_cats)} categories in parallel…", "dim")
            self.after(0, lambda n=len(non_currency_cats):
                       self.progress_var.set(f"Fetching {n} categories in parallel…"))
            all_payloads = gen.fetch_all_payloads(league, non_currency_cats)
            all_payloads["currency"] = currency_payload

            for cat_idx, (key, ninja_type, label_text, is_unique) in enumerate(categories, 1):
                self.after(0, lambda s=f"Building {cat_idx}/{total_cats}: {label_text}":
                           self.progress_var.set(s))

                # Per-category threshold from snapshot (already safely extracted on main thread)
                cat_thresh = snapshot["cat_thresh"].get(key, -1.0)
                if not isinstance(cat_thresh, (int, float)):
                    cat_thresh = -1.0
                effective_min = cat_thresh if cat_thresh >= 0 else min_exalt

                payload = all_payloads.get(key)

                if isinstance(payload, Exception):
                    e = payload
                    output_lines += [gen.header_sub(label_text), f"// Failed: {e}", ""]
                    self._log(f"  ✗ {label_text}: {type(e).__name__}", "err")
                    continue
                if payload is None:
                    output_lines += [gen.header_sub(label_text), f"// No data returned", ""]
                    self._log(f"  ? {label_text}: no data", "warn")
                    continue

                try:
                    if is_unique:
                        lines = gen.build_unique_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_unique_report_rows(label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    elif key == "uncut_gems":
                        lines = gen.build_uncut_gem_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_exchange_report_rows(label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    elif key == "waystones":
                        lines = gen.build_waystone_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_exchange_report_rows(label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    else:
                        pick_all = key in gen.PICK_ALL_CATEGORIES
                        lines = gen.build_exchange_lines(payload, divine_rate_exalts, pick_all=pick_all, min_exalt=effective_min)
                        report_rows.extend(gen.collect_exchange_report_rows(
                            label_text, payload, divine_rate_exalts, pick_all=pick_all, min_exalt=effective_min))

                    output_lines += [gen.header_sub(label_text), ""]
                    output_lines += lines if lines else [f"// poe.ninja returned no rows for {label_text}"]
                    output_lines.append("")

                    active_in_cat = sum(1 for l in lines if l and not l.startswith("//"))
                    self._log(f"  ✓ {label_text}: {active_in_cat} active", "ok")

                    for l in lines:
                        if l.startswith("//") or "[StashItem]" not in l:
                            continue
                        name = self._extract_rule_name(l)
                        vm   = re.search(r'([\d.]+) exalted', l)
                        if name and vm:
                            v = float(vm.group(1))
                            if v > top_item[1]:
                                top_item = (name, v)

                except Exception as e:
                    output_lines += [gen.header_sub(label_text), f"// Processing failed: {e}", ""]
                    self._log(f"  ✗ {label_text}: {e}", "err")

            output_lines.extend(gen.STATIC_TABLET_RULES.splitlines())

            # ── Base types (optional) ─────────────────────────────────────────
            if snapshot.get("include_bases"):
                min_q = int(snapshot.get("base_quality", 28))
                self._log("Fetching base types from Poe2DB…", "dim")
                def _base_prog(idx, total, title):
                    self.after(0, lambda s=f"Bases {idx}/{total}: {title}":
                               self.progress_var.set(s))
                    self._log(f"  [{idx}/{total}] {title}", "dim")
                try:
                    min_lvl   = int(snapshot.get("base_min_level", 75))
                    base_lines = gen.build_base_rules(min_quality=min_q,
                                                      min_level=min_lvl,
                                                      progress_callback=_base_prog)
                    output_lines.append("")
                    output_lines.append(gen.header_major("Base Types"))
                    output_lines.append("")
                    output_lines.extend(base_lines)
                    output_lines.append("")
                    rule_count = sum(1 for l in base_lines if l and not l.startswith("//"))
                    if any("static list" in l or "Additional Bases" in l for l in base_lines):
                        self._log("  ⚠ Some categories unavailable from poe2db — supplemented with built-in list", "warn")
                    self._log(f"  ✓ Base types: {rule_count} rules", "ok")
                except Exception as e:
                    self._log(f"  ✗ Base types failed: {e}", "err")

            self._last_output = list(output_lines)

            # Write files
            self._backup_file(ipd_path, n=snapshot["backup_count"])
            with open(ipd_path, "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            latest_path = os.path.join(OUTPUT_DIR, "latest.ipd")
            with open(latest_path, "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))

            csv_path = os.path.join(OUTPUT_DIR,
                                    os.path.splitext(os.path.basename(ipd_path))[0] + "_items.csv")
            with open(csv_path, "w", encoding="utf-8", newline="") as f:
                f.write(gen.build_csv_report(report_rows))
            self._log(f"Item report: {os.path.basename(csv_path)}", "dim")
            success = True

            # Auto-copy
            if snapshot["auto_copy"]:
                bot = snapshot["bot_folder"].strip()
                if bot and os.path.isdir(bot):
                    dest = os.path.join(bot, os.path.basename(ipd_path))
                    shutil.copy2(ipd_path, dest)
                    self._log(f"Copied to bot folder: {dest}", "ok")
                else:
                    self._log("Auto-copy: bot folder not set or not found.", "warn")

            # Stats
            active    = sum(1 for l in output_lines if l and not l.startswith("//") and "[StashItem]" in l)
            commented = sum(1 for l in output_lines if l.startswith("//") and "[StashItem]" in l)
            duration  = time.time() - self._generate_start
            dur_str   = f"{duration:.1f}s"

            def _update_stats():
                self._stat_vars["active"].set(str(active))
                self._stat_vars["commented"].set(str(commented))
                self._stat_vars["divine"].set(f"{divine_rate_exalts:.1f} ex")
                self._stat_vars["top"].set(
                    f"{top_item[0][:22]}\n{top_item[1]:.0f} ex" if top_item[0] else "—")
                self._stat_vars["duration"].set(dur_str)
            self.after(0, _update_stats)

            self._add_history_entry({
                "ts":          datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "active":      active,
                "commented":   commented,
                "divine_rate": divine_rate_exalts,
                "top_item":    top_item[0],
                "top_value":   top_item[1],
                "duration":    dur_str,
            })

            self.after(0, lambda: self._populate_preview(output_lines))

            self._log("─" * 55, "dim")
            self._log(f"Done in {dur_str}  ·  {active} active rules", "ok")

            # Notifications
            if snapshot["toast"] and _HAS_TOAST:
                def _toast():
                    try:
                        ToastNotifier().show_toast(
                            "PoE2 Pickit Generator",
                            f"Done — {active} active rules  ({dur_str})",
                            duration=4, threaded=True)
                    except Exception:
                        pass
                threading.Thread(target=_toast, daemon=True).start()

            # Save config (safe: we're using already-snapshotted plain Python values)
            self.cfg["league"]             = league
            self.cfg["min_exalt"]          = min_exalt
            self.cfg["output_base"]        = snapshot["output_var"]
            self.cfg["category_enabled"]   = dict(snapshot["cat_enabled"])
            self.cfg["category_threshold"] = dict(snapshot["cat_thresh"])
            save_config(self.cfg)

        except Exception as e:
            self._log(f"Error: {e}", "err")
            self._log(traceback.format_exc(), "dim")
        finally:
            self._last_run_time = time.time()  # advance regardless of success/failure
            self.after(0, lambda: self._generate_done(success))

    def _generate_done(self, success: bool = False):
        self._running = False
        self.gen_btn.state(["!disabled"])
        if success:
            self.open_ipd_btn.state(["!disabled"])
        self.status_lbl.config(
            text=f"Last run: {datetime.datetime.now().strftime('%H:%M:%S')}",
            fg=TEXT_OK if success else TEXT_ERR)
        self.progress_var.set("")

    # ══════════════════════════════════════════════════════════════════════════
    #  Close
    # ══════════════════════════════════════════════════════════════════════════

    def _on_close(self):
        if self._schedule_after:
            self.after_cancel(self._schedule_after)
        self.cfg["window_geometry"] = self.geometry()
        save_config(self.cfg)
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = PickitApp()
    app.mainloop()
