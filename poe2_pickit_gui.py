"""
ExileBot 2 Pickit Generator — GUI v6
Clean, flat dark UI. No animations, no canvas buttons, no particle effects.
Drop-in replacement for v5.

Fixes over v5:
  - Removed all animation/canvas widget code (AnimButton, ShimmerBar, ParticleHeader, PulseFrame, StatCard count-up)
  - Fixed AttributeError: _ovw_var only exists after settings page visit → initialised in _init_vars
  - Fixed TclError: cat_thresh[key].get() on empty entry → wrapped in try/except with fallback
  - Fixed broken _summary_vars lambda closure bug (removed entirely, stat labels updated directly)
  - Simplified to ttk.Button throughout for native OS rendering
"""

import sys, os, re, json, time, shutil, threading, datetime, traceback, subprocess, importlib, hashlib
from concurrent.futures import ThreadPoolExecutor as _TPE
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ── Optional imports ──────────────────────────────────────────────────────────

try:
    from PIL import Image, ImageTk as _ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import pystray as _pystray
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False

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

CONFIG_PATH      = os.path.join(_cfg_dir, "pickit_gui_config.json")
OUTPUT_DIR       = os.path.join(_cfg_dir, "pickit_output")
ICON_DIR         = os.path.join(_cfg_dir, "icon_cache")
PRESETS_DIR      = os.path.join(_cfg_dir, "presets")
WIKI_CACHE_FILE  = os.path.join(_cfg_dir, "wiki_icon_cache.json")
for _d in (OUTPUT_DIR, ICON_DIR, PRESETS_DIR):
    os.makedirs(_d, exist_ok=True)

DEFAULT_CONFIG = {
    "league": "",
    "min_exalt": 1.0,
    "min_exalt_gear": 5.0,
    "output_base": "poe2_pickit",
    "bot_folder": "",
    "auto_copy": False,
    "backup_count": 5,
    "category_enabled": {},
    "category_threshold": {},
    "history": [],

    "start_minimized": False,
    "tray_on_close": True,
    "window_geometry": "",
    "confirm_overwrite_secs": 120,
    "include_bases": True,
    "base_quality": 28,
    "base_min_level": 75,
    "item_states":  {},
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

# ── Category card UI colours ──────────────────────────────────────────────────
_CBAR   = "#16141a"   # sidebar bg
_CBTN   = "#1c1a22"   # sidebar button normal bg
_CHOV   = "#252230"   # sidebar button hover
_CSEL   = "#2d1f10"   # sidebar button selected bg
_CSFG   = "#e8c878"   # selected button text
_CON    = "#25222e"   # item card enabled bg
_COFF   = "#1a1820"   # item card disabled bg
_CONB   = "#5a406a"   # item card enabled border
_COFB   = "#2e2a38"   # item card disabled border
_CTXON  = "#ece4d8"   # item card enabled text
_CTXOF  = "#505060"   # item card disabled text
_CWARN  = "#221a06"   # disabled-but-valuable bg
_CWARNB = "#b87820"   # disabled-but-valuable border (amber)
_CTXWRN = "#7a6840"   # disabled-but-valuable text
_CVAL   = "#c8a050"   # value text

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

TABS = ["General", "Categories", "Preview", "History", "Settings", "Debug"]

VERSION       = "1.6.1"
GITHUB_REPO   = "c4Luffy/poe2-pickit-generator"
VERSION_URL   = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.txt"
RELEASES_URL  = f"https://github.com/{GITHUB_REPO}/releases"


class PickitApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        setup_styles(self)

        self.title(f"ExileBot 2 Pickit Generator  v{VERSION}")
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
        self._check_update_async()
        self._schedule_tick()
        threading.Thread(target=self._fetch_divine_rate_async, daemon=True).start()
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
        self.min_exalt_var      = tk.DoubleVar(value=self.cfg.get("min_exalt", 1.0))
        self.min_exalt_gear_var = tk.DoubleVar(value=self.cfg.get("min_exalt_gear", 5.0))
        self.output_var       = tk.StringVar(value=self.cfg.get("output_base", "poe2_pickit"))
        self.bot_folder_var   = tk.StringVar(value=self.cfg.get("bot_folder", ""))
        self.auto_copy_var    = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        self.backup_count_var = tk.IntVar(value=self.cfg.get("backup_count", 5))
        self.start_min_var    = tk.BooleanVar(value=self.cfg.get("start_minimized", False))
        self.tray_close_var   = tk.BooleanVar(value=self.cfg.get("tray_on_close", True))
        self.ovw_var          = tk.IntVar(value=self.cfg.get("confirm_overwrite_secs", 120))

        self.include_bases_var  = tk.BooleanVar(value=True)
        self.base_quality_var   = tk.IntVar(value=self.cfg.get("base_quality", 28))
        self.base_min_level_var = tk.IntVar(value=self.cfg.get("base_min_level", 75))

        self._divine_rate_var = tk.StringVar(value="—")

        self.cat_enabled = {}
        self.cat_thresh  = {}
        enabled_cfg   = self.cfg.get("category_enabled", {})
        threshold_cfg = self.cfg.get("category_threshold", {})
        for key in ALL_CATEGORY_KEYS:
            self.cat_enabled[key] = tk.BooleanVar(value=enabled_cfg.get(key, True))
            self.cat_thresh[key]  = tk.DoubleVar(value=threshold_cfg.get(key, -1.0))

        # Per-item category card state
        self._item_states     = dict(self.cfg.get("item_states", {}))
        self._price_unit      = "ex"
        self._item_prices     = {}   # {cat_key: {name: {ex, chaos, div}}}
        self._cat_prev_prices = dict(self.cfg.get("cat_prev_prices", {}))  # persisted across sessions
        self._cat_cards       = {}   # {cat_key: [card_frame, ...]}
        self._active_cat       = None
        self._cat_last_fetched = {}   # {cat_key: "HH:MM"} shown in count label
        self._price_unit_btns  = {}

        # Wiki icon URL cache
        self._wiki_icon_cache = {}
        if os.path.exists(WIKI_CACHE_FILE):
            try:
                with open(WIKI_CACHE_FILE, encoding="utf-8") as _f:
                    self._wiki_icon_cache = json.load(_f)
            except Exception:
                pass

    # ── UI skeleton ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top header bar
        hdr = tk.Frame(self, bg=BG3, pady=0)
        hdr.pack(fill="x")
        label(hdr, f"⚔  ExileBot 2 Pickit Generator  v{VERSION}", fg=GOLD,
              font=("Segoe UI", 13, "bold"), bg=BG3, padx=16, pady=8).pack(side="left")
        self.status_lbl = label(hdr, "Ready", fg=TEXT_DIM, font=FONT_SM, bg=BG3, padx=16)
        self.status_lbl.pack(side="right")
        self.schedule_lbl = label(hdr, "", fg=TEXT_INFO, font=FONT_SM, bg=BG3, padx=8)
        self.schedule_lbl.pack(side="right")

        # Update banner (hidden until a newer version is found)
        self._update_bar = tk.Frame(self, bg="#2a1e00", pady=4)
        self._update_lbl = tk.Label(self._update_bar, text="", bg="#2a1e00",
                                    fg="#f0c060", font=FONT_BOLD, cursor="hand2")
        self._update_lbl.pack(side="left", padx=12)
        self._update_lbl.bind("<Button-1>", lambda e: self._open_releases())
        _close_btn = tk.Label(self._update_bar, text="✕", bg="#2a1e00", fg="#888",
                              font=FONT_SM, cursor="hand2")
        _close_btn.pack(side="right", padx=8)
        _close_btn.bind("<Button-1>", lambda e: self._update_bar.pack_forget())

        sep(self).pack(fill="x")

        # Update bar lives here (hidden by default — shown by _check_update_async)

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
        if c and c.winfo_exists():
            c.yview_scroll(-3 if event.delta > 0 else 3, "units")

    def _on_wheel_up(self, event):
        if isinstance(event.widget, (tk.Text, tk.Listbox, tk.Scale)):
            return
        c = self._active_canvas
        if c and c.winfo_exists():
            c.yview_scroll(-3, "units")

    def _on_wheel_down(self, event):
        if isinstance(event.widget, (tk.Text, tk.Listbox, tk.Scale)):
            return
        c = self._active_canvas
        if c and c.winfo_exists():
            c.yview_scroll(3, "units")

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

        def _on_league_select(event=None):
            if self._active_cat and self._active_cat != "_gear":
                self.after(50, lambda: self._show_cat(self._active_cat))

        self.league_cb.bind("<<ComboboxSelected>>", _on_league_select)
        self.league_cb.bind("<Return>", _on_league_select)

        # ── Thresholds ───────────────────────────────────────────────────────
        sec2 = self._section_frame(inner, "Thresholds (Exalted Orbs)")
        tr = tk.Frame(sec2, bg=BG2)
        tr.pack(fill="x", padx=10, pady=10)
        label(tr, "Items below their threshold are commented out in the pickit.  "
                  "Per-category overrides are available on the Categories tab.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", pady=(0, 8))

        def _thresh_row(parent, lbl_text, var, trace_cmd):
            row = tk.Frame(parent, bg=BG2)
            row.pack(anchor="w", pady=2)
            label(row, f"{lbl_text}:", fg=TEXT_DIM, font=FONT_SM, bg=BG2,
                  width=22, anchor="w").pack(side="left")
            entry(row, var, width=7).pack(side="left", padx=(4, 4), ipady=4)
            label(row, "ex", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
            var.trace_add("write", trace_cmd)

        _thresh_row(tr, "Currency & Exchange items", self.min_exalt_var,
                    self._clamp_threshold)
        _thresh_row(tr, "Gear  (Unique weapons / armour)", self.min_exalt_gear_var,
                    self._clamp_threshold_gear)

        div_row = tk.Frame(tr, bg=BG2)
        div_row.pack(anchor="w", pady=(6, 0))
        label(div_row, "Divine rate:", fg=TEXT_DIM, font=FONT_SM, bg=BG2,
              width=22, anchor="w").pack(side="left")
        label(div_row, "", textvariable=self._divine_rate_var,
              fg=TEXT_OK, font=FONT_SM, bg=BG2).pack(side="left", padx=(4, 0))

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

        self.force_btn = btn(btn_f, "⟳  Force Refresh", self._force_refresh_generate)
        self.force_btn.pack(side="left", padx=(8, 0))

        self.open_ipd_btn = btn(btn_f, "Open .ipd", lambda: self._open_file(".ipd"))
        self.open_ipd_btn.pack(side="left", padx=(8, 0))
        self.open_ipd_btn.state(["disabled"])

        btn(btn_f, "Open output folder", self._open_output_folder).pack(side="left", padx=(6, 0))

        # ── Progress ─────────────────────────────────────────────────────────
        self.progress_var = tk.StringVar(value="")
        self.progress_lbl = tk.Label(inner, textvariable=self.progress_var,
                                     bg=BG, fg=TEXT_INFO, font=FONT_SM)
        self.progress_lbl.pack(anchor="w", padx=10, pady=(6, 0))
        self.progress_bar = ttk.Progressbar(inner, mode="indeterminate", length=400)
        self.progress_bar.pack(anchor="w", padx=10, pady=(3, 0))
        self.progress_bar.pack_forget()   # hidden until generate starts

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
            ("last_gen",  "Last Generated"),
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

    def _clamp_threshold_gear(self, *_):
        try:
            v = self.min_exalt_gear_var.get()
            if v < 0:
                self.min_exalt_gear_var.set(0.0)
        except (tk.TclError, ValueError):
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  CATEGORIES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_categories_page(self, page):
        """Card-based category browser. Sidebar = categories, right = item grid."""
        # ── Horizontal split: sidebar | content ───────────────────────────────
        sidebar = tk.Frame(page, bg=_CBAR, width=168)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        right = tk.Frame(page, bg=BG)
        right.pack(side="left", fill="both", expand=True)

        self._build_cat_sidebar(sidebar)

        # ── Right: top toolbar ────────────────────────────────────────────────
        self._cat_header_var = tk.StringVar(value="")
        self._cat_count_var  = tk.StringVar(value="")
        self._cat_search_var = tk.StringVar()
        self._cat_search_var.trace_add("write", self._cat_filter)

        hdr_bar = tk.Frame(right, bg=BG2)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, textvariable=self._cat_header_var,
                 bg=BG2, fg=GOLD, font=("Segoe UI", 12, "bold"),
                 padx=16, pady=8).pack(side="left")
        tk.Label(hdr_bar, textvariable=self._cat_count_var,
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="right", padx=8)
        sep(right).pack(fill="x")

        tbar = tk.Frame(right, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 4))

        # Search box
        tk.Label(tbar, text="Search:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        entry(tbar, self._cat_search_var, width=18).pack(side="left", padx=(4, 10), ipady=3)

        # Enable/Disable all / Reset
        btn(tbar, "Enable All",  lambda: self._cat_items_set_all(True)).pack(side="left", padx=(0, 3))
        btn(tbar, "Disable All", lambda: self._cat_items_set_all(False)).pack(side="left", padx=(0, 3))
        btn(tbar, "Reset",       self._cat_items_reset).pack(side="left", padx=(0, 12))

        # Price unit selector
        tk.Label(tbar, text="Value:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(0, 4))
        for unit_key, unit_label in (("ex", "Exalt"), ("chaos", "Chaos"), ("div", "Divine")):
            ub = tk.Button(tbar, text=unit_label,
                           bg=BG3, fg=TEXT_DIM, activebackground=BORDER,
                           activeforeground=TEXT, relief="flat", bd=1,
                           font=FONT_SM, padx=7, pady=2,
                           command=lambda u=unit_key: self._set_price_unit(u))
            ub.pack(side="left", padx=1)
            self._price_unit_btns[unit_key] = ub
        self._update_price_unit_btns()

        # Preset buttons
        tk.Frame(tbar, bg=BORDER, width=1).pack(side="left", padx=10, fill="y")
        btn(tbar, "Save Preset",   self._preset_save).pack(side="left", padx=(0, 3))
        btn(tbar, "Load Preset",   self._preset_load).pack(side="left", padx=(0, 3))
        btn(tbar, "Export",        self._preset_export).pack(side="left", padx=(0, 3))
        btn(tbar, "Import",        self._preset_import).pack(side="left")

        # Per-category threshold (right side of toolbar)
        tk.Frame(tbar, bg=BORDER, width=1).pack(side="right", padx=10, fill="y")
        tk.Label(tbar, text="ex  (−1 = global)", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="right")
        vcmd_tbar = (self.register(lambda v: v == "" or bool(re.fullmatch(r"-?\d*\.?\d*", v))), "%P")
        self._cat_thresh_entry = tk.Entry(tbar, width=6,
            bg=BG3, fg=TEXT, insertbackground=GOLD,
            relief="flat", bd=0, font=FONT,
            highlightthickness=1, highlightbackground=BORDER,
            validate="key", validatecommand=vcmd_tbar)
        self._cat_thresh_entry.pack(side="right", padx=(0, 4), ipady=4)
        tk.Label(tbar, text="Threshold:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="right", padx=(0, 4))
        tk.Frame(tbar, bg=BORDER, width=1).pack(side="right", padx=6, fill="y")
        self._refresh_btn = btn(tbar, "↻ Refresh", self._refresh_cat_prices)
        self._refresh_btn.pack(side="right", padx=(0, 4))

        sep(right).pack(fill="x")

        # ── Right: content switcher ───────────────────────────────────────────
        self._cat_right = tk.Frame(right, bg=BG)
        self._cat_right.pack(fill="both", expand=True)

        # Panel A: item grid (exchange categories)
        self._cat_grid_outer = tk.Frame(self._cat_right, bg=BG)

        self._cat_loading_lbl = tk.Label(self._cat_grid_outer,
            text="Select a category", bg=BG, fg=TEXT_DIM,
            font=("Segoe UI", 11))
        self._cat_loading_lbl.place(relx=0.5, rely=0.4, anchor="center")

        self._cat_canvas = tk.Canvas(self._cat_grid_outer, bg=BG, highlightthickness=0)
        _csb = tk.Scrollbar(self._cat_grid_outer, orient="vertical",
                             command=self._cat_canvas.yview,
                             bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        self._cat_canvas.configure(yscrollcommand=_csb.set)
        _csb.pack(side="right", fill="y")
        self._cat_canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)

        self._cat_grid_frame = tk.Frame(self._cat_canvas, bg=BG)
        self._cat_grid_win   = self._cat_canvas.create_window(
            (0, 0), window=self._cat_grid_frame, anchor="nw")
        self._cat_grid_frame.bind("<Configure>",
            lambda e: self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all")))
        self._cat_canvas.bind("<Configure>",
            lambda e: self._cat_canvas.itemconfig(self._cat_grid_win, width=e.width))

        # Scroll wheel bound directly on the canvas and its inner frame
        for _w in (self._cat_canvas, self._cat_grid_frame):
            _w.bind("<MouseWheel>",
                    lambda e: self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units"))
            _w.bind("<Button-4>",  lambda e: self._cat_canvas.yview_scroll(-3, "units"))
            _w.bind("<Button-5>",  lambda e: self._cat_canvas.yview_scroll( 3, "units"))

        # Panel B: gear & bases (existing controls)
        self._cat_gear_outer = tk.Frame(self._cat_right, bg=BG)
        self._build_cat_gear_panel(self._cat_gear_outer)

        # Restore cat canvas as the active scroll target for this tab
        # (_build_cat_gear_panel calls _scrollable which overwrites _tab_canvases[1])
        self._tab_canvases[1] = self._cat_canvas

        # Show first exchange category
        self._show_cat(gen.EXCHANGE_CATEGORIES[0][0])

    # ── Category sidebar ──────────────────────────────────────────────────────

    def _build_cat_sidebar(self, sidebar):
        tk.Label(sidebar, text="CATEGORIES", bg=_CBAR, fg=GOLD,
                 font=("Segoe UI", 8, "bold"), pady=8).pack(fill="x")
        tk.Frame(sidebar, bg=BORDER, height=1).pack(fill="x")

        sb_cv = tk.Canvas(sidebar, bg=_CBAR, highlightthickness=0, bd=0)
        inner = tk.Frame(sb_cv, bg=_CBAR)
        _win  = sb_cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>",
                   lambda e: sb_cv.configure(scrollregion=sb_cv.bbox("all")))
        sb_cv.bind("<Configure>", lambda e: sb_cv.itemconfig(_win, width=e.width))
        sb_cv.pack(fill="both", expand=True)

        self._cat_sidebar_btns = {}
        for key, _, lbl_text, _ in gen.EXCHANGE_CATEGORIES:
            self._cat_sidebar_btns[key] = self._make_cat_btn(inner, lbl_text.upper(), key)

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", padx=8, pady=4)
        self._cat_sidebar_btns["_gear"] = self._make_cat_btn(inner, "GEAR & BASES", "_gear")

    def _make_cat_btn(self, parent, text, key):
        frame = tk.Frame(parent, bg=_CBTN, cursor="hand2")
        lbl   = tk.Label(frame, text=text, bg=_CBTN, fg=TEXT_DIM,
                         font=("Segoe UI", 9), anchor="w", padx=12, pady=7)
        lbl.pack(fill="x")

        def _enter(e=None):
            if self._active_cat != key:
                frame.config(bg=_CHOV); lbl.config(bg=_CHOV)
        def _leave(e=None):
            if self._active_cat != key:
                frame.config(bg=_CBTN); lbl.config(bg=_CBTN)
        def _click(e=None):
            self._show_cat(key)

        for w in (frame, lbl):
            w.bind("<Enter>", _enter)
            w.bind("<Leave>", _leave)
            w.bind("<Button-1>", _click)

        frame.pack(fill="x", pady=1)
        return frame

    # ── Category switching ────────────────────────────────────────────────────

    def _show_cat(self, key):
        # Clear search when switching categories so the new category shows normally
        self._cat_search_var.set("")
        self._cat_cards.pop("_search", None)

        # Deselect previous
        if self._active_cat and self._active_cat in self._cat_sidebar_btns:
            old = self._cat_sidebar_btns[self._active_cat]
            old.config(bg=_CBTN)
            for c in old.winfo_children():
                c.config(bg=_CBTN)
                if isinstance(c, tk.Label):
                    c.config(fg=TEXT_DIM)

        self._active_cat = key

        # Highlight selected button
        if key in self._cat_sidebar_btns:
            bf = self._cat_sidebar_btns[key]
            bf.config(bg=_CSEL)
            for c in bf.winfo_children():
                c.config(bg=_CSEL)
                if isinstance(c, tk.Label):
                    c.config(fg=_CSFG)

        # Update per-category threshold entry
        if hasattr(self, "_cat_thresh_entry"):
            if key != "_gear" and key in self.cat_thresh:
                self._cat_thresh_entry.config(
                    textvariable=self.cat_thresh[key], state="normal")
            else:
                self._cat_thresh_entry.config(state="disabled")

        if key == "_gear":
            self._cat_grid_outer.pack_forget()
            self._cat_gear_outer.pack(fill="both", expand=True)
            self._cat_header_var.set("Gear & Bases")
            self._cat_count_var.set("")
            self._active_canvas = self._cat_gear_canvas
        else:
            self._cat_gear_outer.pack_forget()
            self._cat_grid_outer.pack(fill="both", expand=True)
            self._active_canvas = self._cat_canvas
            lbl_text = next((l for k, _, l, _ in gen.EXCHANGE_CATEGORIES if k == key), key)
            self._cat_header_var.set(lbl_text)

            league  = self._selected_league() or "Mercenaries"
            payload = gen._cache_get(league, key)
            if payload and not isinstance(payload, Exception):
                self._populate_cat_grid(key, payload)
            else:
                self._clear_cat_grid()
                self._cat_loading_lbl.config(text=f"Loading {lbl_text}…")
                self._cat_loading_lbl.place(relx=0.5, rely=0.4, anchor="center")
                self._cat_count_var.set("Fetching from poe.ninja…")
                threading.Thread(target=self._load_cat_async,
                                 args=(key,), daemon=True).start()

    def _refresh_cat_prices(self):
        key = self._active_cat
        if not key or key == "_gear":
            return
        league = self._selected_league() or "Mercenaries"
        with gen._CACHE_LOCK:
            gen._PAYLOAD_CACHE.pop((league, key), None)
        self._refresh_btn.config(state="disabled", text="Refreshing…")
        self._show_cat(key)

    def _refresh_btn_ready(self):
        if hasattr(self, "_refresh_btn"):
            self._refresh_btn.config(state="normal", text="↻ Refresh")

    def _load_cat_async(self, key):
        entry_ = next((e for e in gen.EXCHANGE_CATEGORIES if e[0] == key), None)
        if not entry_:
            return
        _, ninja_type, _, is_unique = entry_
        league = self._selected_league() or "Mercenaries"
        try:
            payload = gen.fetch_category(league, key, ninja_type, is_unique)
            gen._cache_set(league, key, payload)
            self.after(0, lambda: self._populate_cat_grid(key, payload))
        except Exception as exc:
            self.after(0, lambda: self._cat_count_var.set(f"Failed: {exc}"))
            self.after(0, self._refresh_btn_ready)

    # ── Item grid population ──────────────────────────────────────────────────

    def _clear_cat_grid(self):
        for w in self._cat_grid_frame.winfo_children():
            w.destroy()

    def _populate_cat_grid(self, key, payload):
        if self._active_cat != key:
            return
        self._cat_loading_lbl.place_forget()
        self._clear_cat_grid()

        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        rate        = gen.exalted_rate(payload)
        league      = self._selected_league() or "Mercenaries"
        div_rate    = self._get_divine_rate(league)

        rows = []
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if not item or not item.get("name"):
                continue
            raw_name = item["name"]
            if raw_name in gen.ITEM_NAME_SKIP:
                continue
            name = gen.ITEM_NAME_CORRECTIONS.get(raw_name, raw_name)
            pv   = float(line.get("primaryValue") or 0.0)
            ex   = pv * rate if rate else pv
            raw_img = item.get("image") or item.get("icon") or ""
            rows.append((name, pv, ex, div_rate, self._decode_ninja_image(raw_img)))

        # Sort
        if key == "essences":
            rows.sort(key=lambda r: gen._essence_tier_key(r[0]))
        elif key == "uncut_gems":
            _GEM_TYPE_ORDER = {"Support": 0, "Spirit": 1, "Skill": 2}
            def _gem_sort(r):
                name = r[0]
                m = re.search(r'\(Level (\d+)\)', name)
                lvl = int(m.group(1)) if m else 0
                for t, ti in _GEM_TYPE_ORDER.items():
                    if f"Uncut {t} Gem" in name:
                        return (ti, lvl)
                return (99, lvl)
            rows.sort(key=_gem_sort)
        elif key == "expedition":
            def _exp_sort(r):
                m = re.search(r'\(Level (\d+)\)', r[0])
                if "Thaumaturgic Flux" in r[0] and m:
                    return (1, int(m.group(1)))
                return (0, -r[2])
            rows.sort(key=_exp_sort)
        else:
            rows.sort(key=lambda r: -r[2])

        # Save previous prices for trend arrows, then cache new prices
        self._cat_prev_prices[key] = {
            name: p["ex"] for name, p in self._item_prices.get(key, {}).items()
        }
        self._item_prices[key] = {
            name: {"ex": ex, "chaos": chaos, "div": (ex / div_rate if div_rate else 0.0)}
            for name, chaos, ex, div_rate, _ in rows
        }

        if key not in self._item_states:
            self._item_states[key] = {}
        states = self._item_states[key]

        NCOLS = 3
        self._cat_cards[key] = []

        # For sectioned categories (uncut gems / expedition): insert section headers
        if key == "uncut_gems":
            _GEM_LABELS = {"Support": "Uncut Support Gems",
                           "Spirit":  "Uncut Spirit Gems",
                           "Skill":   "Uncut Skill Gems"}
            _GEM_TYPE_ORDER = {"Support": 0, "Spirit": 1, "Skill": 2}
            grid_row = 0
            col = 0
            current_type = None
            for name, chaos, ex, _div_r, icon_url in rows:
                gem_type = None
                for t in _GEM_TYPE_ORDER:
                    if f"Uncut {t} Gem" in name:
                        gem_type = t
                        break
                if gem_type != current_type:
                    if col != 0:
                        grid_row += 1
                        col = 0
                    hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
                    tk.Label(hdr, text=_GEM_LABELS.get(gem_type, gem_type),
                             bg="#16141a", fg=GOLD,
                             font=("Segoe UI", 9, "bold"),
                             padx=8, pady=5, anchor="w").pack(fill="x")
                    hdr.grid(in_=self._cat_grid_frame, row=grid_row, column=0,
                             columnspan=3, padx=3, pady=(10, 2), sticky="ew")
                    grid_row += 1
                    current_type = gem_type
                div_val = ex / _div_r if _div_r else 0.0
                enabled = states.get(name, {}).get("enabled", True)
                trend   = self._price_trend(key, name, ex)
                card = self._make_item_card(key, name, chaos, ex, div_val, icon_url, enabled, trend)
                card.grid(in_=self._cat_grid_frame, row=grid_row, column=col,
                          padx=3, pady=3, sticky="ew")
                self._cat_cards[key].append(card)
                col += 1
                if col >= NCOLS:
                    col = 0
                    grid_row += 1
        elif key == "expedition":
            grid_row = 0
            col = 0
            shown_flux_hdr = False
            for name, chaos, ex, _div_r, icon_url in rows:
                is_flux = "Thaumaturgic Flux" in name
                if is_flux and not shown_flux_hdr:
                    if col != 0:
                        grid_row += 1
                        col = 0
                    hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
                    tk.Label(hdr, text="Thaumaturgic Flux",
                             bg="#16141a", fg=GOLD,
                             font=("Segoe UI", 9, "bold"),
                             padx=8, pady=5, anchor="w").pack(fill="x")
                    hdr.grid(in_=self._cat_grid_frame, row=grid_row, column=0,
                             columnspan=3, padx=3, pady=(10, 2), sticky="ew")
                    grid_row += 1
                    shown_flux_hdr = True
                div_val = ex / _div_r if _div_r else 0.0
                enabled = states.get(name, {}).get("enabled", True)
                trend   = self._price_trend(key, name, ex)
                card = self._make_item_card(key, name, chaos, ex, div_val, icon_url, enabled, trend)
                card.grid(in_=self._cat_grid_frame, row=grid_row, column=col,
                          padx=3, pady=3, sticky="ew")
                self._cat_cards[key].append(card)
                col += 1
                if col >= NCOLS:
                    col = 0
                    grid_row += 1
        else:
            for i, (name, chaos, ex, _div_r, icon_url) in enumerate(rows):
                div_val = ex / _div_r if _div_r else 0.0
                enabled = states.get(name, {}).get("enabled", True)
                r_, c_ = divmod(i, NCOLS)
                trend   = self._price_trend(key, name, ex)
                card = self._make_item_card(key, name, chaos, ex, div_val, icon_url, enabled, trend)
                card.grid(in_=self._cat_grid_frame, row=r_, column=c_,
                          padx=3, pady=3, sticky="ew")
                self._cat_cards[key].append(card)

        for c_ in range(NCOLS):
            self._cat_grid_frame.columnconfigure(c_, weight=1, uniform="catcol")

        self._cat_last_fetched[key] = datetime.datetime.now().strftime("%H:%M")
        self._update_cat_count(key)
        self._refresh_btn_ready()
        self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
        self._cat_canvas.yview_moveto(0)

        # Load icons in background via wiki (with poe.ninja fallback)
        threading.Thread(target=self._resolve_wiki_icons,
                         args=(key, rows), daemon=True).start()

    # ── Item card widget ──────────────────────────────────────────────────────

    def _effective_threshold(self, key):
        """Active ex floor for a category (per-cat override if set, else global)."""
        try:
            cat_t = self.cat_thresh[key].get()
            if cat_t >= 0:
                return cat_t
        except (tk.TclError, ValueError, KeyError):
            pass
        try:
            return self.min_exalt_var.get()
        except (tk.TclError, ValueError):
            return 1.0

    def _card_colors(self, cat_key, ex_val, enabled):
        """Return (bg, fg, bdr, dot_text, dot_fg) for a card given its state.

        Four visual states:
          enabled + above threshold  → gold/active
          enabled + below threshold  → dim (will be commented out in pickit)
          disabled + above threshold → amber warn (user hiding a valuable item)
          disabled + below threshold → dark/dim
        """
        thresh = self._effective_threshold(cat_key)
        if enabled:
            if ex_val >= thresh:
                return _CON, _CTXON, _CONB, "●", GOLD
            # Below threshold: item follows pricing but won't be active in pickit
            return _COFF, "#585868", _COFB, "●", "#4a4860"
        if ex_val >= thresh:
            return _CWARN, _CTXWRN, _CWARNB, "○", _CWARNB
        return _COFF, _CTXOF, _COFB, "○", TEXT_DIM

    def _price_trend(self, key, name, ex_val):
        prev = self._cat_prev_prices.get(key, {}).get(name)
        if prev is None:
            return ""
        delta = ex_val - prev
        if delta > prev * 0.03:    # >3% up
            return "up"
        if delta < -prev * 0.03:   # >3% down
            return "down"
        return ""

    def _make_item_card(self, cat_key, name, chaos, ex_val, div_val, icon_url, enabled, trend=""):
        bg, fg, bdr, dot_txt, dot_fg = self._card_colors(cat_key, ex_val, enabled)

        frame = tk.Frame(self._cat_grid_frame, bg=bg, cursor="hand2",
                         highlightthickness=1, highlightbackground=bdr)
        frame._cat_key = cat_key
        frame._name    = name
        frame._enabled = enabled
        frame._chaos   = chaos
        frame._ex      = ex_val
        frame._div     = div_val

        # Placeholder icon (coloured square)
        ph = tk.PhotoImage(width=36, height=36)
        ph.put("#3a3050", to=(0, 0, 36, 36))

        icon_lbl = tk.Label(frame, image=ph, bg=bg,
                            width=36, height=36, bd=0)
        icon_lbl.pack(side="left", padx=(6, 3), pady=5)
        icon_lbl._ph = ph
        frame._icon_lbl = icon_lbl

        name_lbl = tk.Label(frame, text=name, bg=bg, fg=fg,
                            font=("Segoe UI", 9), anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, padx=(0, 4))
        frame._name_lbl = name_lbl

        # Trend arrow (▲ green / ▼ red) — only shown after a refresh
        if trend == "up":
            arrow_lbl = tk.Label(frame, text="▲", bg=bg, fg="#5dbb8a", font=("Segoe UI", 7))
            arrow_lbl.pack(side="right", padx=(0, 1))
        elif trend == "down":
            arrow_lbl = tk.Label(frame, text="▼", bg=bg, fg="#e05555", font=("Segoe UI", 7))
            arrow_lbl.pack(side="right", padx=(0, 1))
        else:
            arrow_lbl = None

        val_str = self._fmt_price(chaos, ex_val, div_val)
        val_lbl = tk.Label(frame, text=val_str, bg=bg, fg=_CVAL,
                           font=("Segoe UI", 8), anchor="e", width=11)
        val_lbl.pack(side="right", padx=(0, 4))
        frame._val_lbl = val_lbl

        dot_lbl = tk.Label(frame, text=dot_txt, bg=bg, fg=dot_fg,
                           font=("Segoe UI", 11))
        dot_lbl.pack(side="right", padx=(0, 2))
        frame._dot_lbl = dot_lbl

        def _click(e=None, f=frame):
            self._toggle_card(f)

        def _right_click(e, f=frame):
            self._copy_card_rule(f)

        def _scroll(e):
            self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units")
        def _scroll_up(e):
            self._cat_canvas.yview_scroll(-3, "units")
        def _scroll_dn(e):
            self._cat_canvas.yview_scroll( 3, "units")

        widgets = [frame, icon_lbl, name_lbl, val_lbl, dot_lbl]
        if arrow_lbl:
            widgets.append(arrow_lbl)
        for w in widgets:
            w.bind("<Button-1>",    _click)
            w.bind("<Button-3>",    _right_click)
            w.bind("<Button-2>",    _right_click)
            w.bind("<MouseWheel>",  _scroll)
            w.bind("<Button-4>",    _scroll_up)
            w.bind("<Button-5>",    _scroll_dn)

        return frame

    def _copy_card_rule(self, frame):
        name = frame._name
        rule = f'[Type] == "{name}" # [StashItem] == "true"'
        self.clipboard_clear()
        self.clipboard_append(rule)
        # Brief visual flash on the card
        orig_bg = frame.cget("bg")
        frame.config(bg="#1e3a2a")
        for w in frame.winfo_children():
            try:
                w.config(bg="#1e3a2a")
            except Exception:
                pass
        def _restore():
            frame.config(bg=orig_bg)
            for w in frame.winfo_children():
                try:
                    w.config(bg=orig_bg)
                except Exception:
                    pass
        self.after(350, _restore)

    def _toggle_card(self, frame):
        key  = frame._cat_key
        name = frame._name
        if key not in self._item_states:
            self._item_states[key] = {}

        # Two-state toggle: disabled (excluded) ↔ default (follows threshold).
        # Re-enabling removes the state entry so the item returns to threshold
        # filtering rather than becoming a "forced" override.
        currently_disabled = not self._item_states[key].get(name, {}).get("enabled", True)
        if currently_disabled:
            # Back to default: remove from states entirely
            self._item_states[key].pop(name, None)
            enabled = True
        else:
            # Exclude this item regardless of threshold
            self._item_states[key][name] = {"enabled": False}
            enabled = False

        frame._enabled = enabled
        bg, fg, bdr, dot_txt, dot_fg = self._card_colors(frame._cat_key, frame._ex, enabled)
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._icon_lbl.config(bg=bg)
        frame._val_lbl.config(bg=bg)
        frame._dot_lbl.config(bg=bg, text=dot_txt, fg=dot_fg)

        self._update_cat_count(key)
        self.after(0, self._save_states_now)

    def _update_cat_count(self, key):
        cards   = self._cat_cards.get(key, [])
        enabled = sum(1 for c in cards if c._enabled)
        ts      = self._cat_last_fetched.get(key, "")
        suffix  = f"  ·  updated {ts}" if ts else ""
        self._cat_count_var.set(f"{enabled} / {len(cards)} enabled{suffix}")

    # ── Price unit switching ──────────────────────────────────────────────────

    def _fmt_price(self, chaos, ex, div):
        unit = self._price_unit
        if unit == "chaos":
            return f"{chaos:.0f}c"
        if unit == "div":
            return f"{div:.3f} div"
        return f"{ex:.2f} ex"

    def _set_price_unit(self, unit):
        self._price_unit = unit
        self._update_price_unit_btns()
        key = self._active_cat
        if not key or key == "_gear":
            return
        for card in self._cat_cards.get(key, []) + self._cat_cards.get("_search", []):
            card._val_lbl.config(text=self._fmt_price(card._chaos, card._ex, card._div))

    def _update_price_unit_btns(self):
        for unit, b in self._price_unit_btns.items():
            if unit == self._price_unit:
                b.config(bg=GOLD, fg="#111")
            else:
                b.config(bg=BG3, fg=TEXT_DIM)

    # ── Search / enable-all / disable-all ────────────────────────────────────

    def _cat_filter(self, *_):
        q   = self._cat_search_var.get().strip().lower()
        key = self._active_cat
        if not key or key == "_gear":
            return

        if not q:
            # Restore normal active-category view
            self._cat_cards.pop("_search", None)
            league  = self._selected_league() or "Mercenaries"
            payload = gen._cache_get(league, key)
            if payload and not isinstance(payload, Exception):
                self._populate_cat_grid(key, payload)
            return

        # ── Global search across ALL loaded categories ────────────────────
        self._clear_cat_grid()
        self._cat_cards["_search"] = []

        NCOLS     = 3
        grid_row  = 0
        col       = 0
        found_any = False

        for cat_key, _, cat_label, _ in gen.EXCHANGE_CATEGORIES:
            prices = self._item_prices.get(cat_key, {})
            if not prices:
                continue
            matches = sorted(
                [(n, d) for n, d in prices.items() if q in n.lower()],
                key=lambda x: -x[1].get("ex", 0)
            )
            if not matches:
                continue
            found_any = True

            # Section header
            if col != 0:
                grid_row += 1
                col = 0
            hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
            tk.Label(hdr, text=cat_label.upper(), bg="#16141a", fg=GOLD,
                     font=("Segoe UI", 9, "bold"), padx=8, pady=5, anchor="w").pack(fill="x")
            hdr.grid(in_=self._cat_grid_frame, row=grid_row, column=0,
                     columnspan=3, padx=3, pady=(10, 2), sticky="ew")
            grid_row += 1

            states = self._item_states.get(cat_key, {})
            for name, data in matches:
                enabled = states.get(name, {}).get("enabled", True)
                card = self._make_item_card(
                    cat_key, name,
                    data.get("chaos", 0), data.get("ex", 0), data.get("div", 0),
                    self._wiki_icon_cache.get(name, ""), enabled)
                card.grid(in_=self._cat_grid_frame, row=grid_row, column=col,
                          padx=3, pady=3, sticky="ew")
                self._cat_cards["_search"].append(card)
                col += 1
                if col >= NCOLS:
                    col = 0
                    grid_row += 1

        if not found_any:
            tk.Label(self._cat_grid_frame, text="No results",
                     bg=BG, fg=TEXT_DIM, font=("Segoe UI", 11)
                     ).grid(row=0, column=0, columnspan=3, pady=30)

        for c_ in range(NCOLS):
            self._cat_grid_frame.columnconfigure(c_, weight=1, uniform="catcol")
        self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
        self._cat_canvas.yview_moveto(0)

        # Show cached icons immediately for search results
        for card in self._cat_cards["_search"]:
            url = self._wiki_icon_cache.get(card._name, "")
            if url:
                threading.Thread(target=self._fetch_icon,
                                 args=("_search", card._name, url), daemon=True).start()

        count = len(self._cat_cards["_search"])
        self._cat_count_var.set(f"{count} result{'s' if count != 1 else ''} across all categories")

    def _cat_items_set_all(self, enabled: bool):
        key = self._active_cat
        if not key or key == "_gear":
            return

        if enabled:
            # "Enable All" = clear all exclusions so every item follows the threshold.
            # Use per-card colors so items below threshold still appear dim.
            self._item_states.pop(key, None)
            for card in self._cat_cards.get(key, []):
                card._enabled = True
                bg, fg, bdr, dot, dfg = self._card_colors(key, card._ex, True)
                card.config(bg=bg, highlightbackground=bdr)
                card._name_lbl.config(bg=bg, fg=fg)
                card._icon_lbl.config(bg=bg)
                card._val_lbl.config(bg=bg)
                card._dot_lbl.config(bg=bg, text=dot, fg=dfg)
        else:
            # "Disable All" = exclude every item in this category.
            if key not in self._item_states:
                self._item_states[key] = {}
            bg = _COFF; fg = _CTXOF; bdr = _COFB; dot = "○"; dfg = TEXT_DIM
            for card in self._cat_cards.get(key, []):
                card._enabled = False
                card.config(bg=bg, highlightbackground=bdr)
                card._name_lbl.config(bg=bg, fg=fg)
                card._icon_lbl.config(bg=bg)
                card._val_lbl.config(bg=bg)
                card._dot_lbl.config(bg=bg, text=dot, fg=dfg)
                self._item_states[key][card._name] = {"enabled": False}

        self._update_cat_count(key)
        self.after(0, self._save_states_now)

    def _cat_items_reset(self):
        """Reset all item states for the current category to default (all enabled)."""
        key = self._active_cat
        if not key or key == "_gear":
            return
        self._item_states.pop(key, None)
        for card in self._cat_cards.get(key, []):
            card._enabled = True
            card.config(bg=_CON, highlightbackground=_CONB)
            card._name_lbl.config(bg=_CON, fg=_CTXON)
            card._icon_lbl.config(bg=_CON)
            card._val_lbl.config(bg=_CON)
            card._dot_lbl.config(bg=_CON, text="●", fg=GOLD)
        self._update_cat_count(key)
        self.after(0, self._save_states_now)

    # ── Divine rate helper ────────────────────────────────────────────────────

    def _get_divine_rate(self, league):
        payload = gen._cache_get(league, "currency")
        if not payload or isinstance(payload, Exception):
            return 1.0
        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        rate = gen.exalted_rate(payload)
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if item and item.get("name") == "Divine Orb":
                pv = float(line.get("primaryValue") or 0.0)
                return pv * rate if rate else pv
        return 1.0

    # ── Icon loading ──────────────────────────────────────────────────────────

    _ICON_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"
        ),
        "Referer":         "https://poe.ninja/",
        "Accept":          "image/png,image/webp,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    @staticmethod
    def _decode_ninja_image(raw: str) -> str:
        """Convert poe.ninja image field → downloadable URL.
        poe.ninja stores images as /gen/image/{b64}/{hash}/{file}.png
        Serve directly from poe.ninja — they host all icons reliably.
        """
        if not raw:
            return ""
        if raw.startswith("/"):
            return "https://poe.ninja" + raw
        if raw.startswith("http"):
            return raw
        return ""

    _WIKI_API = "https://www.poe2wiki.net/api.php"

    @staticmethod
    def _wiki_base_name(name: str) -> str:
        """Strip '(Level X)' so all gem levels share one wiki file."""
        return re.sub(r'\s*\(Level \d+\)\s*$', '', name).strip()

    @staticmethod
    def _wiki_tier_base(name: str) -> str:
        """Strip 'Greater '/'Perfect ' prefix to get base currency name."""
        return re.sub(r'^(Greater|Perfect)\s+', '', name, flags=re.IGNORECASE).strip()

    def _batch_wiki_query(self, file_to_items: dict) -> dict:
        """Query poe2wiki.net for a title→items mapping; return title→url for found pages."""
        found = {}
        unique_titles = list(file_to_items.keys())
        batch_size = 50
        for i in range(0, len(unique_titles), batch_size):
            batch = unique_titles[i:i + batch_size]
            try:
                r = requests.get(self._WIKI_API, params={
                    "action": "query",
                    "titles": "|".join(batch),
                    "prop":   "imageinfo",
                    "iiprop": "url",
                    "format": "json",
                }, timeout=15, headers={"User-Agent": gen.USER_AGENT})
                for page in r.json().get("query", {}).get("pages", {}).values():
                    title = page.get("title", "")
                    if page.get("pageid", -1) != -1 and "imageinfo" in page:
                        found[title] = page["imageinfo"][0]["url"]
            except Exception:
                pass
        return found

    def _resolve_wiki_icons(self, cat_key, rows):
        """Background thread: batch-query poe2wiki.net for icon URLs, then fetch images.

        For currency: two-pass lookup for Greater/Perfect variants —
          pass 1: try the item's own wiki file (e.g. 'Greater Jeweller's Orb' → has its own icon)
          pass 2: if not found, try the base name (e.g. 'Greater Chaos Orb' → 'Chaos Orb')
        For gems: strip '(Level X)' so all levels share one wiki file.
        """
        names = [r[0] for r in rows]
        ninja_by_name = {r[0]: r[4] for r in rows}

        to_fetch = [n for n in names if n not in self._wiki_icon_cache]
        if to_fetch:
            # Pass 1: query each item by its own wiki file title (strip level suffix for gems)
            file_to_items: dict[str, list] = {}
            for n in to_fetch:
                base  = self._wiki_base_name(n)
                title = f"File:{base} inventory icon.png"
                file_to_items.setdefault(title, []).append(n)

            found = self._batch_wiki_query(file_to_items)
            for title, url in found.items():
                for item_name in file_to_items.get(title, []):
                    self._wiki_icon_cache[item_name] = url

            # Pass 2 (currency only): for Greater/Perfect items still not resolved,
            # try stripping the tier prefix and reuse the base item's icon
            if cat_key == "currency":
                _tier_re = re.compile(r'^(Greater|Perfect)\s+', re.IGNORECASE)
                still_missing = [n for n in to_fetch
                                 if n not in self._wiki_icon_cache and _tier_re.match(n)]
                if still_missing:
                    fallback_map: dict[str, list] = {}
                    for n in still_missing:
                        base  = self._wiki_tier_base(n)
                        title = f"File:{base} inventory icon.png"
                        fallback_map.setdefault(title, []).append(n)
                    found2 = self._batch_wiki_query(fallback_map)
                    for title, url in found2.items():
                        for item_name in fallback_map.get(title, []):
                            self._wiki_icon_cache[item_name] = url

            # Fallback to poe.ninja for anything still not resolved
            for n in to_fetch:
                if n not in self._wiki_icon_cache:
                    self._wiki_icon_cache[n] = ninja_by_name.get(n, "")

            try:
                with open(WIKI_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._wiki_icon_cache, f, indent=2)
            except Exception:
                pass

        # Fetch images: wiki URL if resolved, else poe.ninja fallback (bounded pool)
        to_load = [
            (name, self._wiki_icon_cache.get(name) or ninja_by_name.get(name, ""))
            for name in names
            if self._wiki_icon_cache.get(name) or ninja_by_name.get(name, "")
        ]
        if to_load:
            def _load_all(items=to_load, key=cat_key):
                with _TPE(max_workers=8) as pool:
                    for n, u in items:
                        pool.submit(self._fetch_icon, key, n, u)
            threading.Thread(target=_load_all, daemon=True).start()

    def _fetch_icon(self, key, name, url):
        """Worker thread: download icon → apply to matching card."""
        if not url:
            return
        try:
            slug = hashlib.md5(url.encode()).hexdigest()[:16]
            path = os.path.join(ICON_DIR, slug + ".png")
            if not os.path.exists(path):
                r = requests.get(url, timeout=10, headers=self._ICON_HEADERS)
                if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                    with open(path, "wb") as f:
                        f.write(r.content)
            if os.path.exists(path):
                self.after(0, lambda p=path: self._apply_icon(key, name, p))
        except Exception:
            pass

    def _apply_icon(self, key, name, path):
        """Main thread: set icon on matching card."""
        for card in self._cat_cards.get(key, []):
            if card._name != name:
                continue
            try:
                if _HAS_PIL:
                    img   = Image.open(path).resize((36, 36), Image.LANCZOS)
                    photo = _ImageTk.PhotoImage(img)
                else:
                    photo = tk.PhotoImage(file=path)
                    w, h  = photo.width(), photo.height()
                    factor = max(1, max(w, h) // 36)
                    if factor > 1:
                        photo = photo.subsample(factor, factor)
                card._icon_lbl.config(image=photo,
                                      width=photo.width(), height=photo.height())
                card._icon_lbl._ph = photo
            except Exception:
                pass
            break

    # ── State persistence ─────────────────────────────────────────────────────

    def _save_states_now(self):
        self.cfg["item_states"] = self._item_states
        save_config(self.cfg)

    # ── Preset system ─────────────────────────────────────────────────────────

    def _preset_save(self):
        name = simpledialog.askstring("Save Preset", "Preset name:", parent=self)
        if not name:
            return
        data = {
            "_meta": {
                "name":    name,
                "created": datetime.datetime.now().isoformat(),
                "league":  self._selected_league() or "",
            },
            "item_states": self._item_states,
        }
        path = os.path.join(PRESETS_DIR, re.sub(r'[^\w\-. ]', '_', name) + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=self)

    def _preset_load(self):
        files = [f for f in os.listdir(PRESETS_DIR) if f.endswith(".json")]
        if not files:
            messagebox.showinfo("No Presets",
                "No saved presets found.\nUse 'Save Preset' or 'Import' first.", parent=self)
            return
        dlg = tk.Toplevel(self)
        dlg.title("Load Preset")
        dlg.configure(bg=BG)
        dlg.grab_set()
        dlg.resizable(False, False)
        tk.Label(dlg, text="Select a preset to load:", bg=BG, fg=TEXT,
                 font=FONT, padx=16, pady=10).pack(anchor="w")
        lb = tk.Listbox(dlg, bg=BG3, fg=TEXT, selectbackground=GOLD,
                        selectforeground="#111", font=FONT, width=36, height=min(len(files), 12))
        for f in files:
            lb.insert("end", f[:-5])
        lb.pack(padx=16, pady=(0, 8))
        lb.selection_set(0)

        def _apply():
            sel = lb.curselection()
            if not sel:
                return
            fname = files[sel[0]]
            try:
                with open(os.path.join(PRESETS_DIR, fname), encoding="utf-8") as fp:
                    data = json.load(fp)
                self._item_states = data.get("item_states", data)
                self.cfg["item_states"] = self._item_states
                save_config(self.cfg)
                dlg.destroy()
                key = self._active_cat
                if key and key != "_gear":
                    league  = self._selected_league() or "Mercenaries"
                    payload = gen._cache_get(league, key)
                    if payload:
                        self._populate_cat_grid(key, payload)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)

        btn_f = tk.Frame(dlg, bg=BG)
        btn_f.pack(fill="x", padx=16, pady=(0, 12))
        btn(btn_f, "Load",   _apply).pack(side="left", padx=(0, 6))
        btn(btn_f, "Cancel", dlg.destroy).pack(side="left")

    def _preset_export(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON preset", "*.json"), ("All files", "*.*")],
            title="Export Preset", parent=self)
        if not path:
            return
        data = {
            "_meta": {
                "name":    os.path.splitext(os.path.basename(path))[0],
                "created": datetime.datetime.now().isoformat(),
                "league":  self._selected_league() or "",
            },
            "item_states": self._item_states,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Exported", f"Preset exported to:\n{path}", parent=self)

    def _preset_import(self):
        path = filedialog.askopenfilename(
            filetypes=[("JSON preset", "*.json"), ("All files", "*.*")],
            title="Import Preset", parent=self)
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            states = data.get("item_states", data)
            # Copy into presets folder too
            dest = os.path.join(PRESETS_DIR,
                                os.path.basename(path))
            if not os.path.exists(dest):
                shutil.copy2(path, dest)
            self._item_states = states
            self.cfg["item_states"] = states
            save_config(self.cfg)
            key = self._active_cat
            if key and key != "_gear":
                league  = self._selected_league() or "Mercenaries"
                payload = gen._cache_get(league, key)
                if payload:
                    self._populate_cat_grid(key, payload)
            messagebox.showinfo("Imported", "Preset imported and applied.", parent=self)
        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self)

    # ── Gear & Bases panel (existing controls) ────────────────────────────────

    def _build_cat_gear_panel(self, parent):
        """The old-style panel for unique categories and base types."""
        inner, c = self._scrollable(parent)
        self._cat_gear_canvas = c

        vcmd = (self.register(lambda v: v == "" or bool(re.fullmatch(r"-?\d*\.?\d*", v))), "%P")

        def cat_group(grp_label, cats, unique=False, desc=""):
            lf = tk.Frame(inner, bg=BG)
            lf.pack(fill="x", pady=(12, 0))
            label(lf, grp_label, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(16, 8))
            sep(lf).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)
            if desc:
                label(inner, desc, fg=TEXT_DIM, font=FONT_SM).pack(
                    anchor="w", padx=16, pady=(2, 4))
            row_bg = "#1e1e2a" if unique else BG2
            for key, _, lbl_text, _ in cats:
                row = tk.Frame(inner, bg=row_bg,
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", padx=16, pady=2)
                cb = tk.Checkbutton(row, text=lbl_text, variable=self.cat_enabled[key],
                    bg=row_bg, fg=TEXT_INFO if unique else TEXT,
                    selectcolor=BG3, activebackground=row_bg,
                    activeforeground=TEXT, font=FONT, anchor="w", padx=10, pady=6)
                cb.pack(side="left")
                tf = tk.Frame(row, bg=row_bg)
                tf.pack(side="right", padx=8)
                label(tf, "ex  (−1 = global)", fg=TEXT_DIM, font=FONT_SM, bg=row_bg).pack(side="right")
                tk.Entry(tf, textvariable=self.cat_thresh[key], width=7,
                    bg=BG3, fg=TEXT, insertbackground=GOLD,
                    relief="flat", bd=0, font=FONT,
                    highlightthickness=1, highlightbackground=BORDER,
                    validate="key", validatecommand=vcmd
                ).pack(side="right", padx=(0, 4), ipady=4)
                label(tf, "threshold:", fg=TEXT_DIM, font=FONT_SM, bg=row_bg).pack(
                    side="right", padx=(0, 4))

        cat_group("Unique Categories", gen.UNIQUE_CATEGORIES, unique=True,
                  desc="Unique items matched by exact name ([UniqueName]).  "
                       "Threshold and enable/disable apply at the whole-category level.")

        # Base Types
        lf_b = tk.Frame(inner, bg=BG)
        lf_b.pack(fill="x", pady=(16, 0))
        label(lf_b, "Base Types  (Game Data)", fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(16, 8))
        sep(lf_b).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)

        sec_b = tk.Frame(inner, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        sec_b.pack(fill="x", padx=16, pady=(2, 12))

        label(sec_b,
              "Adds endgame base type rules (245 bases across 25 categories) sourced from game data — "
              "weapons, armour, off-hands, plus Runeforged/Runemastered variants.  Instant, no network call.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))

        checkbtn(sec_b, "Include endgame base types in pickit",
                 self.include_bases_var).pack(anchor="w", padx=10, pady=(0, 4))

        qrow = tk.Frame(sec_b, bg=BG2)
        qrow.pack(anchor="w", padx=10, pady=(0, 10))
        label(qrow, "Min quality:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        entry(qrow, self.base_quality_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        label(qrow, "%", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        label(qrow, "   Min item level:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(
            side="left", padx=(16, 0))
        entry(qrow, self.base_min_level_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        label(qrow, "(75+ = endgame)", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(
            side="left", padx=(6, 0))

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
            "The last 50 runs are kept.  The chart below shows active rules and top-item value over time.")
        cols = ("Date/time", "Active", "Commented", "Divine rate", "Top item", "Duration")
        self._hist_tree = ttk.Treeview(page, columns=cols, show="headings", height=10)
        for c in cols:
            self._hist_tree.heading(c, text=c)
            self._hist_tree.column(c, width=120, anchor="w")
        self._hist_tree.pack(fill="both", expand=True, padx=16, pady=(12, 4))

        btn_f = tk.Frame(page, bg=BG)
        btn_f.pack(anchor="w", padx=16, pady=(4, 6))
        btn(btn_f, "Clear history", self._clear_history).pack(side="left")

        # Sparkline chart
        chart_frame = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        chart_frame.pack(fill="x", padx=16, pady=(4, 14))
        tk.Label(chart_frame, text="Active rules over time", bg=BG2,
                 fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=10, pady=(6, 2))
        self._hist_canvas = tk.Canvas(chart_frame, bg=BG2, height=80,
                                      highlightthickness=0, bd=0)
        self._hist_canvas.pack(fill="x", padx=10, pady=(0, 8))

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
        self._draw_history_sparkline(h)

    def _draw_history_sparkline(self, h):
        c = self._hist_canvas
        c.delete("all")
        pts = [e.get("active", 0) for e in h[-20:] if isinstance(e.get("active"), int)]
        if len(pts) < 2:
            c.create_text(10, 40, anchor="w", text="Not enough data yet — generate a few times to see the chart.",
                          fill=TEXT_DIM, font=FONT_SM)
            return
        c.update_idletasks()
        W = c.winfo_width() or 600
        H = 80
        pad_x, pad_y = 8, 8
        mn, mx = min(pts), max(pts)
        rng = mx - mn or 1

        def _x(i):  return pad_x + i * (W - 2*pad_x) / (len(pts) - 1)
        def _y(v):  return pad_y + (1 - (v - mn) / rng) * (H - 2*pad_y)

        # Shaded area under the line
        poly = [pad_x, H - pad_y]
        for i, v in enumerate(pts):
            poly += [_x(i), _y(v)]
        poly += [_x(len(pts)-1), H - pad_y]
        c.create_polygon(poly, fill="#1a3a28", outline="")

        # Line + dots
        for i in range(len(pts) - 1):
            c.create_line(_x(i), _y(pts[i]), _x(i+1), _y(pts[i+1]),
                          fill="#5dbb8a", width=2)
        for i, v in enumerate(pts):
            c.create_oval(_x(i)-3, _y(v)-3, _x(i)+3, _y(v)+3,
                          fill="#5dbb8a", outline="")

        # Labels: first, last, max
        c.create_text(_x(0)+2, _y(pts[0])-8, text=str(pts[0]),
                      fill=TEXT_DIM, font=FONT_SM, anchor="w")
        c.create_text(_x(len(pts)-1)-2, _y(pts[-1])-8, text=str(pts[-1]),
                      fill=TEXT_DIM, font=FONT_SM, anchor="e")
        peak_i = pts.index(mx)
        c.create_text(_x(peak_i), _y(mx)-8, text=f"peak {mx}",
                      fill=GOLD, font=FONT_SM, anchor="s")

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
                 ).pack(anchor="w", padx=10, pady=(0, 4))
        checkbtn(sec, "Launch minimized (hides to taskbar on startup)", self.start_min_var
                 ).pack(anchor="w", padx=10, pady=(0, 4))
        tray_row = checkbtn(sec, "Minimize to system tray when closing (keeps running in background)", self.tray_close_var)
        tray_row.pack(anchor="w", padx=10, pady=(0, 10))
        if not _HAS_TRAY:
            label(sec, "  ⚠  pystray not installed — run:  pip install pystray  to enable this option",
                  fg=TEXT_WARN, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(0, 8))

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
        self.cfg["start_minimized"]        = self.start_min_var.get()
        self.cfg["tray_on_close"]          = self.tray_close_var.get()
        self.cfg["confirm_overwrite_secs"] = self.ovw_var.get()
        self.cfg["include_bases"]          = self.include_bases_var.get()
        self.cfg["base_quality"]           = self.base_quality_var.get()
        self.cfg["base_min_level"]         = self.base_min_level_var.get()
        self.cfg["min_exalt_gear"]         = self.min_exalt_gear_var.get()
        self.cfg["min_exalt"]              = self.min_exalt_var.get()
        # Persist per-category thresholds so they survive without a generate
        thresh = {}
        for k, v in self.cat_thresh.items():
            try:
                thresh[k] = v.get()
            except (tk.TclError, ValueError):
                thresh[k] = -1.0
        self.cfg["category_threshold"] = thresh
        save_config(self.cfg)
        self._log("Settings saved.", "ok")

    def _reset_defaults(self):
        if messagebox.askyesno("Reset settings", "Reset all settings to defaults?"):
            self.cfg = dict(DEFAULT_CONFIG)
            save_config(self.cfg)
            # Re-sync all tk vars so the live UI reflects defaults immediately
            self.league_var.set(self.cfg.get("league", ""))
            self.min_exalt_var.set(self.cfg.get("min_exalt", 1.0))
            self.min_exalt_gear_var.set(self.cfg.get("min_exalt_gear", 5.0))
            self.output_var.set(self.cfg.get("output_base", "poe2_pickit"))
            self.bot_folder_var.set(self.cfg.get("bot_folder", ""))
            self.auto_copy_var.set(self.cfg.get("auto_copy", False))
            self.backup_count_var.set(self.cfg.get("backup_count", 5))
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
        d(f"═══ ExileBot 2 Pickit Generator — Diagnostics  ·  {now}", "header")
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
                               ("poe2_pickit_generator", True)]:
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
            d(f"  Scout cats      : {len(gen.SCOUT_CATEGORIES)}", "info")
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
    #  Auto-update checker
    # ══════════════════════════════════════════════════════════════════════════

    def _check_update_async(self):
        threading.Thread(target=self._check_update, daemon=True).start()

    def _check_update(self):
        try:
            r = requests.get(VERSION_URL, timeout=8,
                             headers={"User-Agent": f"poe2-pickit/{VERSION}"})
            if r.status_code != 200:
                return
            remote = r.text.strip()
            if self._ver_tuple(remote) > self._ver_tuple(VERSION):
                self.after(0, lambda: self._show_update_banner(remote))
        except Exception:
            pass

    @staticmethod
    def _ver_tuple(v: str):
        try:
            return tuple(int(x) for x in v.lstrip("v").split("."))
        except Exception:
            return (0,)

    def _show_update_banner(self, remote: str):
        self._update_lbl.config(
            text=f"⬆  Update available: v{remote}  —  click here to download  (you have v{VERSION})"
        )
        self._update_bar.pack(fill="x", after=self.winfo_children()[1])

    def _open_releases(self):
        import webbrowser
        webbrowser.open(RELEASES_URL)

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

    def _force_refresh_generate(self):
        """Clear current-league cache then generate fresh data."""
        league = self._selected_league()
        if league:
            with gen._CACHE_LOCK:
                stale = [k for k in gen._PAYLOAD_CACHE if k[0] == league]
                for k in stale:
                    del gen._PAYLOAD_CACHE[k]
        self._start_generate()

    def _fetch_divine_rate_async(self):
        """Background fetch of divine rate on startup so it shows before first generate."""
        try:
            league = self._selected_league() or "Mercenaries"
            payload = gen._cache_get(league, "currency")
            if payload is None:
                payload = gen.fetch_category(league, "currency", "Currency", False)
                gen._cache_set(league, "currency", payload)
            rate = gen.exalted_rate(payload)
            items_by_id = {i["id"]: i for i in payload.get("items", [])}
            for line in payload.get("lines", []):
                item = items_by_id.get(line.get("id"))
                if item and item.get("name") == "Divine Orb":
                    pv = float(line.get("primaryValue") or 0)
                    divine = pv * rate if rate else pv
                    self.after(0, lambda d=divine:
                               self._divine_rate_var.set(f"1 Divine = {d:.1f} ex"))
                    break
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
            if limit == 0 or age < limit:
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
        self.force_btn.state(["disabled"])
        self.open_ipd_btn.state(["disabled"])
        self.status_lbl.config(text="Generating…", fg=TEXT_WARN)
        self.progress_var.set("Starting…")
        self.progress_bar.pack(anchor="w", padx=10, pady=(3, 0))
        self.progress_bar.start(12)

        # Snapshot all Tk variables here on the main thread so the worker never
        # touches Tcl/Tk state from a background thread (avoids intermittent
        # freezes on non-Windows platforms where Tk is not thread-safe).
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        out_name = self.output_var.get()
        if silent:
            out_name = f"{out_name}_{ts}"

        snapshot = {
            "league":          league,
            "output_var":      out_name,
            "auto_copy":       self.auto_copy_var.get(),
            "bot_folder":      self.bot_folder_var.get(),
            "backup_count":    self.backup_count_var.get(),
            "cat_enabled":     {k: v.get() for k, v in self.cat_enabled.items()},
            "cat_thresh":      {},
            "include_bases":   self.include_bases_var.get(),
            "base_quality":    self.base_quality_var.get(),
            "base_min_level":  self.base_min_level_var.get(),
            "item_states":     dict(self._item_states),
        }
        for k, v in self.cat_thresh.items():
            try:
                snapshot["cat_thresh"][k] = v.get()
            except tk.TclError:
                snapshot["cat_thresh"][k] = -1.0
        try:
            snapshot["min_exalt"] = self.min_exalt_var.get()
        except tk.TclError:
            snapshot["min_exalt"] = float(self.cfg.get("min_exalt", 1.0))
            self.min_exalt_var.set(snapshot["min_exalt"])
            self._log("Currency threshold invalid — reset to saved value.", "warn")
        try:
            snapshot["min_exalt_gear"] = self.min_exalt_gear_var.get()
        except tk.TclError:
            snapshot["min_exalt_gear"] = float(self.cfg.get("min_exalt_gear", 5.0))
            self.min_exalt_gear_var.set(snapshot["min_exalt_gear"])
            self._log("Gear threshold invalid — reset to saved value.", "warn")

        threading.Thread(target=self._generate, args=(snapshot,), daemon=True).start()

    def _generate(self, snapshot: dict):
        success = False
        try:
            league    = snapshot["league"]
            min_exalt = snapshot["min_exalt"]
            min_exalt_gear = snapshot.get("min_exalt_gear", 5.0)

            try:
                min_exalt = float(min_exalt)
            except (TypeError, ValueError):
                min_exalt = float(self.cfg.get("min_exalt", 1.0))
                self._log("Currency threshold invalid — reset to saved value.", "warn")
            try:
                min_exalt_gear = float(min_exalt_gear)
            except (TypeError, ValueError):
                min_exalt_gear = float(self.cfg.get("min_exalt_gear", 5.0))
                self._log("Gear threshold invalid — reset to saved value.", "warn")

            base_path = os.path.join(OUTPUT_DIR,
                                     os.path.basename(os.path.splitext(snapshot["output_var"])[0]))
            ipd_path  = base_path + ".ipd"

            self._log(f"League    : {league}")
            self._log(f"Threshold : {min_exalt:.0f} ex  (currency/items)  |  {min_exalt_gear:.0f} ex  (gear)")
            self._log(f"Output    : {os.path.basename(base_path)}.ipd")
            self._log("─" * 55, "dim")

            categories = [cat for cat in gen.ALL_CATEGORIES
                          if snapshot["cat_enabled"].get(cat[0], True)]
            total_cats  = len(categories)

            _gen_ts  = datetime.datetime.now()
            _gen_id  = _gen_ts.strftime('%Y%m%d_%H%M%S')
            output_lines = [
                "/" * gen._W,
                "//" + f"  EXILEBOT 2  |  PICKIT  |  ID: {_gen_id}".center(gen._W - 4) + "//",
                "/" * gen._W,
                f"// League    : {league}",
                f"// Generated : {_gen_ts.strftime('%Y-%m-%d %H:%M:%S')}",
                f"// Pickit ID : {_gen_id}",
                f"// Threshold : {min_exalt:.0f} ex  (currency/items)  |  {min_exalt_gear:.0f} ex  (gear/uniques)",
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
            _cat_ok = 0
            _cat_fail = 0

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

                # Per-category threshold takes priority; fall back to the
                # appropriate global (gear vs currency) when not set (-1).
                cat_thresh = snapshot["cat_thresh"].get(key, -1.0)
                if not isinstance(cat_thresh, (int, float)):
                    cat_thresh = -1.0
                global_min = min_exalt_gear if is_unique else min_exalt
                effective_min = cat_thresh if cat_thresh >= 0 else global_min

                payload = all_payloads.get(key)

                if isinstance(payload, Exception):
                    e = payload
                    output_lines += [gen.header_sub(label_text), f"// Failed: {e}", ""]
                    self._log(f"  ✗ {label_text}: {type(e).__name__}", "err")
                    _cat_fail += 1
                    continue
                if payload is None:
                    output_lines += [gen.header_sub(label_text), f"// No data returned", ""]
                    self._log(f"  ? {label_text}: no data", "warn")
                    _cat_fail += 1
                    continue

                try:
                    # Build enabled_names from per-item states.
                    # Disabled items are excluded; everything else follows the threshold.
                    _cat_states = snapshot.get("item_states", {}).get(key, {})
                    if _cat_states and not is_unique:
                        _items_in_payload = {
                            gen.ITEM_NAME_CORRECTIONS.get(i["name"], i["name"])
                            for i in payload.get("items", []) if i.get("name")
                        }
                        _disabled = {n for n, s in _cat_states.items()
                                     if not s.get("enabled", True)}
                        enabled_names = _items_in_payload - _disabled
                    else:
                        enabled_names = None  # all items → use threshold (default)

                    if is_unique:
                        lines = gen.build_unique_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_unique_report_rows(label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    elif key == "uncut_gems":
                        lines = gen.build_uncut_gem_lines(payload, divine_rate_exalts, min_exalt=effective_min,
                                                          enabled_names=enabled_names)
                        report_rows.extend(gen.collect_exchange_report_rows(label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    elif key == "waystones":
                        lines = gen.build_waystone_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_exchange_report_rows(label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    else:
                        pick_all  = key in gen.PICK_ALL_CATEGORIES
                        tier_sort = (key == "essences")
                        always    = gen.ALWAYS_PICK_CURRENCY if key == "currency" else (gen.ALWAYS_PICK_RUNES if key == "runes" else None)
                        ritual_th = min_exalt_gear if key == "omens" else None
                        lines = gen.build_exchange_lines(payload, divine_rate_exalts,
                                                         pick_all=pick_all,
                                                         min_exalt=effective_min,
                                                         tier_sort=tier_sort,
                                                         enabled_names=enabled_names,
                                                         always_names=always,
                                                         ritual_threshold=ritual_th)
                        report_rows.extend(gen.collect_exchange_report_rows(
                            label_text, payload, divine_rate_exalts, pick_all=pick_all, min_exalt=effective_min))

                    output_lines += [gen.header_sub(label_text), ""]
                    output_lines += lines if lines else [f"// poe.ninja returned no rows for {label_text}"]
                    output_lines.append("")

                    active_in_cat = sum(1 for l in lines if l and not l.startswith("//"))
                    self._log(f"  ✓ {label_text}: {active_in_cat} active", "ok")
                    _cat_ok += 1

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
                    _cat_fail += 1

            # ── Game uniques not on poe.ninja ────────────────────────────────
            ninja_unique_names = set()
            for key, _, _, is_unique in gen.ALL_CATEGORIES:
                if not is_unique:
                    continue
                p = all_payloads.get(key)
                if isinstance(p, dict):
                    for ln in p.get("lines", []):
                        if ln.get("name"):
                            ninja_unique_names.add(ln["name"])
            supp = gen.build_game_unique_supplement(ninja_unique_names)
            if supp:
                output_lines += [gen.header_sub("Game Uniques (not on poe.ninja)"), ""] + supp
                self._log(f"  Game unique supplement: {len([l for l in supp if l.startswith('//')])- 1} items commented", "dim")

            # ── Scout (poe2scout.com) unique items ────────────────────────────
            self._log("Fetching Scout prices (poe2scout.com)…", "dim")
            scout_payloads = gen.fetch_all_scout_payloads(league)
            if scout_payloads:
                output_lines += [gen.header_major("Scout Unique Items"), ""]
                for key, cat_slug, label_text, _ in gen.SCOUT_CATEGORIES:
                    payload_items = scout_payloads.get(key)
                    if not payload_items:
                        continue
                    lines = gen.build_scout_lines(
                        payload_items.get("items", []),
                        divine_rate_exalts,
                        min_exalt=min_exalt_gear,
                    )
                    active = [l for l in lines if "[StashItem]" in l]
                    output_lines += [gen.header_sub(label_text), ""] + lines + [""]
                    self._log(f"  ✓ {label_text}: {len(active)} active", "ok")
            else:
                self._log("  Scout API unavailable for this league — skipped", "dim")

            output_lines.extend(gen.STATIC_TABLET_RULES.splitlines())
            output_lines.extend(gen.STATIC_WOMBGIFT_RULES.splitlines())
            output_lines.extend(gen.STATIC_SPECIAL_WAYSTONE_RULES.splitlines())

            # ── Base types (optional) ─────────────────────────────────────────
            if snapshot.get("include_bases"):
                min_q = int(snapshot.get("base_quality", 28))
                self._log("Building base type rules from game data…", "dim")
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
                    if any("Runeforged" in l for l in base_lines):
                        self._log("  ✓ Runeforged/Runemastered supplement included", "dim")
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

            try:
                _fsize_kb = os.path.getsize(ipd_path) // 1024
            except OSError:
                _fsize_kb = 0
            _gen_time_str = datetime.datetime.now().strftime("%H:%M")

            def _update_stats():
                self._stat_vars["active"].set(str(active))
                self._stat_vars["commented"].set(str(commented))
                self._stat_vars["divine"].set(f"{divine_rate_exalts:.1f} ex")
                self._stat_vars["top"].set(
                    f"{top_item[0][:22]}\n{top_item[1]:.0f} ex" if top_item[0] else "—")
                self._stat_vars["duration"].set(dur_str)
                self._stat_vars["last_gen"].set(f"{_gen_time_str}  ·  {_fsize_kb} KB")
                self._divine_rate_var.set(f"1 Divine = {divine_rate_exalts:.1f} ex")
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

            _fail_note = f"  ·  {_cat_fail} failed" if _cat_fail else ""
            self._log(f"  Categories: {_cat_ok} OK{_fail_note}", "ok" if not _cat_fail else "warn")
            self._log("─" * 55, "dim")
            self._log(f"Done in {dur_str}  ·  {active} active rules", "ok")

            # Update config on the main thread to avoid racing with _save_settings.
            _cfg_updates = {
                "league":             league,
                "min_exalt":          min_exalt,
                "min_exalt_gear":     min_exalt_gear,
                "output_base":        snapshot["output_var"],
                "category_enabled":   dict(snapshot["cat_enabled"]),
                "category_threshold": dict(snapshot["cat_thresh"]),
            }
            def _apply_cfg(updates=_cfg_updates):
                self.cfg.update(updates)
                save_config(self.cfg)
            self.after(0, _apply_cfg)

        except Exception as e:
            self._log(f"Error: {e}", "err")
            self._log(traceback.format_exc(), "dim")
        finally:
            self._last_run_time = time.time()  # advance regardless of success/failure
            self.after(0, lambda: self._generate_done(success))

    def _generate_done(self, success: bool = False):
        self._running = False
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.progress_var.set("")
        self.gen_btn.state(["!disabled"])
        self.force_btn.state(["!disabled"])
        if success:
            self.open_ipd_btn.state(["!disabled"])
        self.status_lbl.config(
            text=f"Last run: {datetime.datetime.now().strftime('%H:%M:%S')}",
            fg=TEXT_OK if success else TEXT_ERR)
        self.progress_var.set("")

    # ══════════════════════════════════════════════════════════════════════════
    #  Close / System tray
    # ══════════════════════════════════════════════════════════════════════════

    def _on_close(self):
        if _HAS_TRAY and self.cfg.get("tray_on_close", True):
            self._hide_to_tray()
        else:
            self._quit_app()

    def _quit_app(self):
        if hasattr(self, "_tray_icon") and self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None
        if self._schedule_after:
            self.after_cancel(self._schedule_after)
        self.cfg["window_geometry"]  = self.geometry()
        self.cfg["cat_prev_prices"]  = self._cat_prev_prices
        save_config(self.cfg)
        self.destroy()

    def _hide_to_tray(self):
        self.cfg["window_geometry"] = self.geometry()
        save_config(self.cfg)
        self.withdraw()
        if not getattr(self, "_tray_icon", None):
            self._tray_icon = self._create_tray_icon()
            threading.Thread(target=self._tray_icon.run, daemon=True).start()

    def _create_tray_icon(self):
        if _HAS_PIL:
            from PIL import ImageDraw
            S = 64
            img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            # Dark circle background
            d.ellipse([1, 1, S-2, S-2], fill="#1a1a22", outline="#c8a96e", width=2)
            # Sword blade (vertical, slightly tapered)
            d.polygon([(30, 8), (34, 8), (33, 46), (32, 50), (31, 46)], fill="#c8a96e")
            # Crossguard
            d.rectangle([18, 28, 46, 33], fill="#b87820")
            d.ellipse([16, 27, 21, 34], fill="#b87820")
            d.ellipse([43, 27, 48, 34], fill="#b87820")
            # Pommel
            d.ellipse([28, 50, 36, 58], fill="#c8a96e")
            d.ellipse([30, 52, 34, 56], fill="#8a5a10")
        else:
            img = Image.new("RGBA", (64, 64), (200, 169, 110, 255))

        def on_show(icon, item):
            icon.stop()
            self._tray_icon = None
            self.after(0, self._restore_from_tray)

        def on_quit(icon, item):
            icon.stop()
            self._tray_icon = None
            self.after(0, self._quit_app)

        menu = _pystray.Menu(
            _pystray.MenuItem("Show ExileBot 2 Pickit", on_show, default=True),
            _pystray.MenuItem("Quit", on_quit),
        )
        return _pystray.Icon("poe2pickit", img, "ExileBot 2 Pickit Generator", menu)

    def _restore_from_tray(self):
        self.deiconify()
        self.lift()
        self.focus_force()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = PickitApp()
    app.mainloop()
