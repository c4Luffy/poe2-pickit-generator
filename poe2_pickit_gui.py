"""
ExileBot 2 Pickit Generator — GUI v7
Modern CustomTkinter UI. Always-visible top bar with league, thresholds, generate button.
Sidebar navigation with all categories accessible directly.
"""

import sys, os, re, json, time, shutil, threading, datetime, traceback, subprocess, importlib, hashlib
from concurrent.futures import ThreadPoolExecutor as _TPE
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing dependency",
        "CustomTkinter not found.\nInstall it:  pip install customtkinter")
    sys.exit(1)

try:
    from PIL import Image, ImageTk as _ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

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
        "Place this GUI in the same folder as poe2_pickit_generator.py.")
    sys.exit(1)

try:
    import requests
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing dependency", "Install requests:  pip install requests")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _cfg_dir = os.path.dirname(sys.executable)
else:
    _cfg_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH     = os.path.join(_cfg_dir, "pickit_gui_config.json")
OUTPUT_DIR      = os.path.join(_cfg_dir, "pickit_output")
ICON_DIR        = os.path.join(_cfg_dir, "icon_cache")
PRESETS_DIR     = os.path.join(_cfg_dir, "presets")
WIKI_CACHE_FILE = os.path.join(_cfg_dir, "wiki_icon_cache.json")
for _d in (OUTPUT_DIR, ICON_DIR, PRESETS_DIR):
    os.makedirs(_d, exist_ok=True)

DEFAULT_CONFIG = {
    "league": "", "min_exalt": 1.0, "min_exalt_gear": 5.0,
    "output_base": "poe2_pickit", "bot_folder": "", "auto_copy": False,
    "backup_count": 5, "category_enabled": {}, "category_threshold": {},
    "history": [], "start_minimized": False, "window_geometry": "",
    "confirm_overwrite_secs": 120, "include_bases": True,
    "base_quality": 28, "base_min_level": 75, "item_states": {},
}

def load_config():
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        cfg = dict(DEFAULT_CONFIG); cfg.update(data); return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

# ── Colors ────────────────────────────────────────────────────────────────────
BG="#1a1a22"; BG2="#22222e"; BG3="#2a2a38"; BORDER="#3a3a50"
GOLD="#c8a96e"; GOLD_LT="#e8c98e"; TEXT="#ece4d8"; TEXT_DIM="#888898"
TEXT_OK="#5dbb8a"; TEXT_ERR="#e05555"; TEXT_WARN="#d4a84b"; TEXT_INFO="#6ab0e8"
_CBAR="#16141a"; _CHOV="#252230"; _CSEL="#2d1f10"; _CSFG="#e8c878"
_CON="#25222e"; _COFF="#1a1820"; _CONB="#5a406a"; _COFB="#2e2a38"
_CTXON="#ece4d8"; _CTXOF="#505060"; _CVAL="#c8a050"

FONT=("Segoe UI",10); FONT_BOLD=("Segoe UI",10,"bold")
FONT_MONO=("Consolas",9); FONT_SM=("Segoe UI",9)

ALL_CATEGORY_KEYS = [c[0] for c in gen.ALL_CATEGORIES]

NAV_DASHBOARD="__dashboard__"; NAV_PREVIEW="__preview__"
NAV_HISTORY="__history__"; NAV_SETTINGS="__settings__"
NAV_DEBUG="__debug__"; NAV_GEAR="__gear__"

# ── Helpers ───────────────────────────────────────────────────────────────────
def scrolled_text(parent, **kw):
    frame = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    vsb = tk.Scrollbar(frame, orient="vertical", bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=10)
    hsb = tk.Scrollbar(frame, orient="horizontal", bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=10)
    t = tk.Text(frame, bg=BG2, fg=TEXT, font=FONT_MONO, relief="flat", bd=0, wrap="none",
                highlightthickness=0, padx=6, pady=4,
                yscrollcommand=vsb.set, xscrollcommand=hsb.set, **kw)
    vsb.config(command=t.yview); hsb.config(command=t.xview)
    t.grid(row=0, column=0, sticky="nsew"); vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    frame.rowconfigure(0, weight=1); frame.columnconfigure(0, weight=1)
    return frame, t

def _sep(parent, bg=BORDER, h=1):
    return tk.Frame(parent, bg=bg, height=h)

def _lbl(parent, text, fg=None, font=None, bg=None, **kw):
    return tk.Label(parent, text=text, bg=bg or BG2, fg=fg or TEXT, font=font or FONT, **kw)

def _entry(parent, var, width=None, **kw):
    e = tk.Entry(parent, textvariable=var, bg=BG3, fg=TEXT, insertbackground=GOLD,
                 relief="flat", bd=0, font=FONT, highlightthickness=1,
                 highlightbackground=BORDER, highlightcolor=GOLD, **kw)
    if width: e.config(width=width)
    return e

def _cbtn(parent, text, var, bg=None):
    return tk.Checkbutton(parent, text=text, variable=var,
        bg=bg or BG2, fg=TEXT, selectcolor=BG3,
        activebackground=bg or BG2, activeforeground=TEXT, font=FONT, anchor="w")

def setup_ttk_styles(root):
    s = ttk.Style(root); s.theme_use("clam")
    s.configure("Treeview", background=BG2, foreground=TEXT,
                fieldbackground=BG2, rowheight=22, font=FONT)
    s.configure("Treeview.Heading", background=BG3, foreground=GOLD,
                font=FONT_BOLD, relief="flat")
    s.map("Treeview", background=[("selected", BORDER)])

# ══════════════════════════════════════════════════════════════════════════════
class PickitApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        setup_ttk_styles(self)

        self.title("ExileBot 2 Pickit Generator  v7")
        self.configure(fg_color=BG)
        self.resizable(True, True)
        self.minsize(1000, 680)
        saved_geo = self.cfg.get("window_geometry", "")
        self.geometry(saved_geo if saved_geo else "1220x800")

        self._leagues = []; self._running = False
        self._schedule_after = None; self._last_run_time = time.time()
        self._last_output = []; self._preview_lines = []
        self._generate_start = 0.0; self._active_nav = None
        self._active_canvas = None

        self._init_vars()
        self._build_ui()
        self._fetch_leagues_async()
        self._schedule_tick()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-g>", lambda e: self._start_generate())
        self.bind_all("<Control-r>", lambda e: self._fetch_leagues_async())
        self.bind_all("<MouseWheel>", self._on_wheel)
        if self.cfg.get("start_minimized", False):
            self.after(100, self.iconify)

    # ── Vars ──────────────────────────────────────────────────────────────────
    def _init_vars(self):
        self.league_var         = tk.StringVar(value=self.cfg.get("league") or "")
        self.min_exalt_var      = tk.DoubleVar(value=self.cfg.get("min_exalt", 1.0))
        self.min_exalt_gear_var = tk.DoubleVar(value=self.cfg.get("min_exalt_gear", 5.0))
        self.output_var         = tk.StringVar(value=self.cfg.get("output_base", "poe2_pickit"))
        self.bot_folder_var     = tk.StringVar(value=self.cfg.get("bot_folder", ""))
        self.auto_copy_var      = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        self.backup_count_var   = tk.IntVar(value=self.cfg.get("backup_count", 5))
        self.start_min_var      = tk.BooleanVar(value=self.cfg.get("start_minimized", False))
        self.ovw_var            = tk.IntVar(value=self.cfg.get("confirm_overwrite_secs", 120))
        self.include_bases_var  = tk.BooleanVar(value=True)
        self.base_quality_var   = tk.IntVar(value=self.cfg.get("base_quality", 28))
        self.base_min_level_var = tk.IntVar(value=self.cfg.get("base_min_level", 75))

        self.cat_enabled = {}; self.cat_thresh = {}
        for key in ALL_CATEGORY_KEYS:
            self.cat_enabled[key] = tk.BooleanVar(
                value=self.cfg.get("category_enabled", {}).get(key, True))
            self.cat_thresh[key]  = tk.DoubleVar(
                value=self.cfg.get("category_threshold", {}).get(key, -1.0))

        self._item_states = dict(self.cfg.get("item_states", {}))
        self._price_unit = "ex"; self._item_prices = {}
        self._cat_cards = {}; self._active_cat = None
        self._price_unit_btns = {}

        self._wiki_icon_cache = {}
        if os.path.exists(WIKI_CACHE_FILE):
            try:
                with open(WIKI_CACHE_FILE, encoding="utf-8") as f:
                    self._wiki_icon_cache = json.load(f)
            except Exception:
                pass

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_topbar()
        _sep(self).pack(fill="x")

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True)

        self._sidebar_frame = tk.Frame(body, bg=_CBAR, width=175)
        self._sidebar_frame.pack(side="left", fill="y")
        self._sidebar_frame.pack_propagate(False)
        self._build_sidebar()

        _sep(body, bg=BORDER).pack(side="left", fill="y")

        self._content = tk.Frame(body, bg=BG)
        self._content.pack(side="left", fill="both", expand=True)
        self._build_pages()

        _sep(self).pack(fill="x")
        self._build_bottombar()

        self._show_nav(NAV_DASHBOARD)

    # ── Top bar ───────────────────────────────────────────────────────────────
    def _build_topbar(self):
        bar = tk.Frame(self, bg=BG3, height=52)
        bar.pack(fill="x"); bar.pack_propagate(False)

        tk.Label(bar, text="ExileBot 2 Pickit", bg=BG3, fg=GOLD,
                 font=("Segoe UI", 13, "bold"), padx=14).pack(side="left")
        _sep(bar, bg=BORDER).pack(side="left", fill="y", pady=10)

        tk.Label(bar, text="League:", bg=BG3, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="left")
        self.league_cb = ttk.Combobox(bar, textvariable=self.league_var,
                                       state="normal", font=FONT, width=20)
        self.league_cb.pack(side="left", ipady=3)
        s = ttk.Style(); s.theme_use("clam")
        s.configure("TCombobox", fieldbackground=BG3, background=BG3, foreground=TEXT,
                    selectbackground=BG3, selectforeground=TEXT, arrowcolor=GOLD,
                    bordercolor=BORDER, padding=4)
        s.map("TCombobox", fieldbackground=[("readonly", BG3)], foreground=[("readonly", TEXT)])
        self.tk_setPalette(background=BG3)
        self.option_add("*TCombobox*Listbox.background", BG3)
        self.option_add("*TCombobox*Listbox.foreground", TEXT)
        self.option_add("*TCombobox*Listbox.selectBackground", GOLD)
        self.option_add("*TCombobox*Listbox.selectForeground", "#111")

        tk.Button(bar, text="↻", bg=BG2, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=6, pady=2, cursor="hand2",
                  activebackground=BORDER, activeforeground=TEXT,
                  command=self._fetch_leagues_async).pack(side="left", padx=(4, 10))

        _sep(bar, bg=BORDER).pack(side="left", fill="y", pady=10)

        tk.Label(bar, text="Currency:", bg=BG3, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="left")
        _entry(bar, self.min_exalt_var, width=6).pack(side="left", ipady=3)
        tk.Label(bar, text="ex", bg=BG3, fg=TEXT_DIM, font=FONT_SM, padx=4).pack(side="left")

        tk.Label(bar, text="Gear:", bg=BG3, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="left")
        _entry(bar, self.min_exalt_gear_var, width=6).pack(side="left", ipady=3)
        tk.Label(bar, text="ex", bg=BG3, fg=TEXT_DIM, font=FONT_SM, padx=4).pack(side="left")

        _sep(bar, bg=BORDER).pack(side="left", fill="y", pady=10)

        self.gen_btn = tk.Button(bar, text="  Generate  (Ctrl+G)  ",
                                  bg=GOLD, fg="#111", relief="flat", bd=0,
                                  font=("Segoe UI", 11, "bold"), cursor="hand2",
                                  activebackground=GOLD_LT, activeforeground="#111",
                                  pady=6, padx=4,
                                  command=self._start_generate)
        self.gen_btn.pack(side="left", padx=12)

        self.schedule_lbl = tk.Label(bar, text="", bg=BG3, fg=TEXT_INFO, font=FONT_SM, padx=8)
        self.schedule_lbl.pack(side="right")
        self.status_lbl = tk.Label(bar, text="Ready", bg=BG3, fg=TEXT_DIM, font=FONT_SM, padx=8)
        self.status_lbl.pack(side="right")

    # ── Bottom bar ────────────────────────────────────────────────────────────
    def _build_bottombar(self):
        bar = tk.Frame(self, bg=BG2, height=26)
        bar.pack(fill="x"); bar.pack_propagate(False)
        self.progress_var = tk.StringVar(value="")
        tk.Label(bar, textvariable=self.progress_var, bg=BG2,
                 fg=TEXT_INFO, font=FONT_SM, anchor="w", padx=12).pack(fill="x")

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        self._nav_btns = {}

        sb_canvas = tk.Canvas(self._sidebar_frame, bg=_CBAR, highlightthickness=0, bd=0)
        sb_scroll = tk.Scrollbar(self._sidebar_frame, orient="vertical",
                                  command=sb_canvas.yview, bg=_CBAR,
                                  troughcolor=_CBAR, relief="flat", bd=0, width=6)
        sb_canvas.configure(yscrollcommand=sb_scroll.set)
        sb_scroll.pack(side="right", fill="y")
        sb_canvas.pack(fill="both", expand=True)

        inner = tk.Frame(sb_canvas, bg=_CBAR)
        _win = sb_canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: sb_canvas.configure(scrollregion=sb_canvas.bbox("all")))
        sb_canvas.bind("<Configure>", lambda e: sb_canvas.itemconfig(_win, width=e.width))

        for w in (sb_canvas, inner):
            w.bind("<MouseWheel>", lambda e: sb_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units"))

        def section(text):
            tk.Label(inner, text=text, bg=_CBAR, fg=TEXT_DIM,
                     font=("Segoe UI", 8, "bold"), anchor="w",
                     padx=12, pady=0).pack(fill="x", pady=(10, 0))
            _sep(inner, bg=BORDER).pack(fill="x", padx=8, pady=(2, 0))

        def nav_btn(text, key):
            f = tk.Frame(inner, bg=_CBAR, cursor="hand2")
            lbl = tk.Label(f, text=text, bg=_CBAR, fg=TEXT_DIM,
                           font=("Segoe UI", 10), anchor="w", padx=14, pady=6)
            lbl.pack(fill="x")
            def _enter(e=None):
                if self._active_nav != key:
                    f.config(bg=_CHOV); lbl.config(bg=_CHOV)
            def _leave(e=None):
                if self._active_nav != key:
                    f.config(bg=_CBAR); lbl.config(bg=_CBAR)
            def _click(e=None): self._show_nav(key)
            for w in (f, lbl):
                w.bind("<Enter>", _enter); w.bind("<Leave>", _leave)
                w.bind("<Button-1>", _click)
                w.bind("<MouseWheel>",
                       lambda e: sb_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units"))
            f.pack(fill="x", pady=1)
            self._nav_btns[key] = (f, lbl)

        section("NAVIGATE")
        nav_btn("Dashboard", NAV_DASHBOARD)
        section("EXCHANGE")
        for key, _, lbl_text, _ in gen.EXCHANGE_CATEGORIES:
            nav_btn(lbl_text, key)
        section("GEAR")
        nav_btn("Gear & Bases", NAV_GEAR)
        section("TOOLS")
        nav_btn("Preview", NAV_PREVIEW)
        nav_btn("History", NAV_HISTORY)
        nav_btn("Settings", NAV_SETTINGS)
        nav_btn("Debug", NAV_DEBUG)

    def _set_nav_active(self, key, active):
        if key not in self._nav_btns:
            return
        f, lbl = self._nav_btns[key]
        if active:
            f.config(bg=_CSEL); lbl.config(bg=_CSEL, fg=_CSFG)
        else:
            f.config(bg=_CBAR); lbl.config(bg=_CBAR, fg=TEXT_DIM)

    def _show_nav(self, key):
        if self._active_nav:
            self._set_nav_active(self._active_nav, False)
        self._active_nav = key
        self._set_nav_active(key, True)

        shown = set()
        for pk, frame in self._pages.items():
            fid = id(frame)
            if pk == key:
                if fid not in shown:
                    frame.pack(fill="both", expand=True)
                    shown.add(fid)
            else:
                if fid not in shown:
                    frame.pack_forget()
                    shown.add(fid)

        # If exchange category, load it
        exchange_keys = {c[0] for c in gen.EXCHANGE_CATEGORIES}
        if key in exchange_keys:
            self._show_cat(key)
            self._active_canvas = self._cat_canvas
        else:
            self._active_canvas = None

    def _on_wheel(self, event):
        if isinstance(event.widget, (tk.Text, tk.Listbox)):
            return
        if self._active_canvas and self._active_canvas.winfo_exists():
            self._active_canvas.yview_scroll(-3 if event.delta > 0 else 3, "units")

    # ── Pages builder ─────────────────────────────────────────────────────────
    def _build_pages(self):
        self._pages = {}

        p = tk.Frame(self._content, bg=BG); self._build_dashboard_page(p)
        self._pages[NAV_DASHBOARD] = p

        p = tk.Frame(self._content, bg=BG); self._build_exchange_page(p)
        for key, _, _, _ in gen.EXCHANGE_CATEGORIES:
            self._pages[key] = p

        p = tk.Frame(self._content, bg=BG); self._build_gear_page(p)
        self._pages[NAV_GEAR] = p

        p = tk.Frame(self._content, bg=BG); self._build_preview_page(p)
        self._pages[NAV_PREVIEW] = p

        p = tk.Frame(self._content, bg=BG); self._build_history_page(p)
        self._pages[NAV_HISTORY] = p

        p = tk.Frame(self._content, bg=BG); self._build_settings_page(p)
        self._pages[NAV_SETTINGS] = p

        p = tk.Frame(self._content, bg=BG); self._build_debug_page(p)
        self._pages[NAV_DEBUG] = p

    # ══════════════════════════════════════════════════════════════════════════
    #  DASHBOARD PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_dashboard_page(self, page):
        # Stats row
        stats_f = tk.Frame(page, bg=BG)
        stats_f.pack(fill="x", padx=16, pady=(14, 0))
        self._stat_vars = {}
        for i, (key, title) in enumerate([
            ("active", "Active rules"), ("commented", "Commented out"),
            ("divine", "Divine rate"), ("top", "Top item"), ("duration", "Run time"),
        ]):
            card = tk.Frame(stats_f, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0))
            stats_f.columnconfigure(i, weight=1)
            tk.Label(card, text=title, bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=10, pady=(8, 2))
            v = tk.StringVar(value="—")
            tk.Label(card, textvariable=v, bg=BG2, fg=GOLD,
                     font=("Segoe UI", 16, "bold"), wraplength=150,
                     justify="left").pack(anchor="w", padx=10, pady=(0, 8))
            self._stat_vars[key] = v

        # Output file
        of = tk.Frame(page, bg=BG)
        of.pack(fill="x", padx=16, pady=(12, 0))
        tk.Label(of, text=f"Output:  {OUTPUT_DIR}{os.sep}", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w")
        of2 = tk.Frame(of, bg=BG)
        of2.pack(fill="x", pady=(4, 0))
        of2.columnconfigure(0, weight=1)
        _entry(of2, self.output_var, bg=BG3).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        tk.Button(of2, text="Browse…", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=8, pady=3, cursor="hand2",
                  activebackground=BORDER, activeforeground=TEXT,
                  command=self._browse_output).grid(row=0, column=1)
        _entry_btn = tk.Button(of2, text="Open .ipd", bg=BG3, fg=TEXT_DIM,
                                relief="flat", bd=1, font=FONT_SM, padx=8, pady=3,
                                cursor="hand2", activebackground=BORDER,
                                command=lambda: self._open_file(".ipd"))
        _entry_btn.grid(row=0, column=2, padx=(4, 0))
        self.open_ipd_btn = _entry_btn

        tk.Button(of2, text="Open folder", bg=BG3, fg=TEXT_DIM, relief="flat", bd=1,
                  font=FONT_SM, padx=8, pady=3, cursor="hand2",
                  activebackground=BORDER,
                  command=self._open_output_folder).grid(row=0, column=3, padx=(4, 0))

        # Log
        _sep(page).pack(fill="x", padx=16, pady=(12, 0))
        log_hdr = tk.Frame(page, bg=BG)
        log_hdr.pack(fill="x", padx=16, pady=(6, 2))
        tk.Label(log_hdr, text="Log", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        tk.Button(log_hdr, text="Copy", bg=BG3, fg=TEXT_DIM, relief="flat",
                  bd=1, font=FONT_SM, padx=6, pady=1, command=self._log_copy).pack(side="right")
        tk.Button(log_hdr, text="Clear", bg=BG3, fg=TEXT_DIM, relief="flat",
                  bd=1, font=FONT_SM, padx=6, pady=1, command=self._log_clear).pack(side="right", padx=(0, 4))

        log_wrap = tk.Frame(page, bg=BG)
        log_wrap.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        lf, self.log_text = scrolled_text(log_wrap, height=10, state="disabled")
        lf.pack(fill="both", expand=True)
        for tag, col in [("ok", TEXT_OK), ("err", TEXT_ERR), ("warn", TEXT_WARN),
                         ("info", TEXT_INFO), ("dim", TEXT_DIM), ("ts", "#404055")]:
            self.log_text.tag_config(tag, foreground=col)

    # ══════════════════════════════════════════════════════════════════════════
    #  EXCHANGE PAGE (shared by all exchange categories)
    # ══════════════════════════════════════════════════════════════════════════
    def _build_exchange_page(self, page):
        # Header bar
        self._cat_header_var = tk.StringVar(value="")
        self._cat_count_var  = tk.StringVar(value="")
        self._cat_search_var = tk.StringVar()
        self._cat_search_var.trace_add("write", self._cat_filter)

        hdr_bar = tk.Frame(page, bg=BG2)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, textvariable=self._cat_header_var, bg=BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold"), padx=16, pady=8).pack(side="left")
        tk.Label(hdr_bar, textvariable=self._cat_count_var, bg=BG2,
                 fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="right", padx=8)
        _sep(page).pack(fill="x")

        # Toolbar
        tbar = tk.Frame(page, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 4))

        tk.Label(tbar, text="Search:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        _entry(tbar, self._cat_search_var, width=18).pack(side="left", padx=(4, 10), ipady=3)

        for txt, cmd in [("Enable All", lambda: self._cat_items_set_all(True)),
                         ("Disable All", lambda: self._cat_items_set_all(False)),
                         ("Reset", self._cat_items_reset)]:
            tk.Button(tbar, text=txt, bg=BG3, fg=TEXT, relief="flat", bd=1,
                      font=FONT_SM, padx=7, pady=2, cursor="hand2",
                      activebackground=BORDER, activeforeground=TEXT,
                      command=cmd).pack(side="left", padx=(0, 3))

        tk.Label(tbar, text="Value:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(10, 4))
        for uk, ul in (("ex", "Exalt"), ("chaos", "Chaos"), ("div", "Divine")):
            ub = tk.Button(tbar, text=ul, bg=BG3, fg=TEXT_DIM,
                           activebackground=BORDER, activeforeground=TEXT,
                           relief="flat", bd=1, font=FONT_SM, padx=7, pady=2, cursor="hand2",
                           command=lambda u=uk: self._set_price_unit(u))
            ub.pack(side="left", padx=1)
            self._price_unit_btns[uk] = ub
        self._update_price_unit_btns()

        tk.Frame(tbar, bg=BORDER, width=1).pack(side="left", padx=10, fill="y")
        for txt, cmd in [("Save Preset", self._preset_save), ("Load Preset", self._preset_load),
                         ("Export", self._preset_export), ("Import", self._preset_import)]:
            tk.Button(tbar, text=txt, bg=BG3, fg=TEXT, relief="flat", bd=1,
                      font=FONT_SM, padx=7, pady=2, cursor="hand2",
                      activebackground=BORDER, activeforeground=TEXT,
                      command=cmd).pack(side="left", padx=(0, 3))

        # Per-category threshold (right side)
        tk.Frame(tbar, bg=BORDER, width=1).pack(side="right", padx=10, fill="y")
        tk.Label(tbar, text="ex  (-1 = global)", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="right")
        vcmd = (self.register(lambda v: v == "" or bool(re.fullmatch(r"-?\d*\.?\d*", v))), "%P")
        self._cat_thresh_entry = tk.Entry(tbar, width=6, bg=BG3, fg=TEXT,
            insertbackground=GOLD, relief="flat", bd=0, font=FONT,
            highlightthickness=1, highlightbackground=BORDER,
            validate="key", validatecommand=vcmd)
        self._cat_thresh_entry.pack(side="right", padx=(0, 4), ipady=4)
        tk.Label(tbar, text="Threshold:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="right", padx=(0, 4))

        _sep(page).pack(fill="x")

        # Loading label
        self._cat_loading_lbl = tk.Label(page, text="Select a category",
                                          bg=BG, fg=TEXT_DIM, font=("Segoe UI", 11))

        # Card grid canvas
        self._cat_canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        _csb = tk.Scrollbar(page, orient="vertical", command=self._cat_canvas.yview,
                            bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        self._cat_canvas.configure(yscrollcommand=_csb.set)
        _csb.pack(side="right", fill="y")
        self._cat_canvas.pack(fill="both", expand=True, padx=(8, 0), pady=8)

        self._cat_grid_frame = tk.Frame(self._cat_canvas, bg=BG)
        self._cat_grid_win = self._cat_canvas.create_window(
            (0, 0), window=self._cat_grid_frame, anchor="nw")
        self._cat_grid_frame.bind("<Configure>",
            lambda e: self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all")))
        self._cat_canvas.bind("<Configure>",
            lambda e: self._cat_canvas.itemconfig(self._cat_grid_win, width=e.width))

        for w in (self._cat_canvas, self._cat_grid_frame):
            w.bind("<MouseWheel>",
                   lambda e: self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units"))

    # ══════════════════════════════════════════════════════════════════════════
    #  GEAR PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_gear_page(self, page):
        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(page, orient="vertical", command=canvas.yview,
                          bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        _wid = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(_wid, width=e.width))

        vcmd = (self.register(lambda v: v == "" or bool(re.fullmatch(r"-?\d*\.?\d*", v))), "%P")

        def cat_group(grp_label, cats, unique=False):
            lf = tk.Frame(inner, bg=BG)
            lf.pack(fill="x", pady=(14, 0))
            tk.Label(lf, text=grp_label, bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(16, 8))
            _sep(lf).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)
            row_bg = "#1e1e2a" if unique else BG2
            for key, _, lbl_text, _ in cats:
                row = tk.Frame(inner, bg=row_bg, highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", padx=16, pady=2)
                tk.Checkbutton(row, text=lbl_text, variable=self.cat_enabled[key],
                    bg=row_bg, fg=TEXT_INFO if unique else TEXT,
                    selectcolor=BG3, activebackground=row_bg,
                    activeforeground=TEXT, font=FONT, anchor="w",
                    padx=10, pady=6).pack(side="left")
                tf = tk.Frame(row, bg=row_bg); tf.pack(side="right", padx=8)
                tk.Label(tf, text="ex  (-1 = global)", bg=row_bg,
                         fg=TEXT_DIM, font=FONT_SM).pack(side="right")
                tk.Entry(tf, textvariable=self.cat_thresh[key], width=7,
                    bg=BG3, fg=TEXT, insertbackground=GOLD,
                    relief="flat", bd=0, font=FONT,
                    highlightthickness=1, highlightbackground=BORDER,
                    validate="key", validatecommand=vcmd
                ).pack(side="right", padx=(0, 4), ipady=4)
                tk.Label(tf, text="threshold:", bg=row_bg,
                         fg=TEXT_DIM, font=FONT_SM).pack(side="right", padx=(0, 4))

        cat_group("Unique Categories", gen.UNIQUE_CATEGORIES, unique=True)

        lf_b = tk.Frame(inner, bg=BG); lf_b.pack(fill="x", pady=(16, 0))
        tk.Label(lf_b, text="Base Types  (Poe2DB)", bg=BG, fg=TEXT_DIM,
                 font=FONT_SM).pack(side="left", padx=(16, 8))
        _sep(lf_b).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)

        sec_b = tk.Frame(inner, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        sec_b.pack(fill="x", padx=16, pady=(2, 20))
        tk.Label(sec_b, text="Scrapes endgame bases (level 75+) from poe2db.tw.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=10, pady=(8, 4))
        _cbtn(sec_b, "Include endgame base types in pickit",
              self.include_bases_var).pack(anchor="w", padx=10, pady=(0, 4))
        qrow = tk.Frame(sec_b, bg=BG2); qrow.pack(anchor="w", padx=10, pady=(0, 10))
        tk.Label(qrow, text="Min quality:", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        _entry(qrow, self.base_quality_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        tk.Label(qrow, text="%   Min item level:", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(4, 0))
        _entry(qrow, self.base_min_level_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        tk.Label(qrow, text="(75+ = endgame)", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(4, 0))

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_preview_page(self, page):
        ctrl = tk.Frame(page, bg=BG); ctrl.pack(fill="x", padx=16, pady=10)
        tk.Label(ctrl, text="Filter:", bg=BG, fg=TEXT_DIM, font=FONT).pack(side="left", padx=(0, 6))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._filter_preview)
        _entry(ctrl, self.filter_var, width=28).pack(side="left", ipady=4)
        self.preview_count_var = tk.StringVar(value="Generate to see rules")
        tk.Label(ctrl, textvariable=self.preview_count_var, bg=BG,
                 fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(12, 0))
        tk.Button(ctrl, text="Copy all", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=8, pady=2, command=self._preview_copy).pack(side="right")
        _sep(page).pack(fill="x", padx=16)
        pf, self.preview_text = scrolled_text(page, state="disabled")
        pf.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        for tag, col in [("active", TEXT_OK), ("commented", TEXT_DIM),
                         ("header", GOLD), ("unique", TEXT_INFO)]:
            self.preview_text.tag_config(tag, foreground=col)

    # ══════════════════════════════════════════════════════════════════════════
    #  HISTORY PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_history_page(self, page):
        cols = ("Date/time", "Active", "Commented", "Divine rate", "Top item", "Duration")
        self._hist_tree = ttk.Treeview(page, columns=cols, show="headings", height=12)
        for c in cols:
            self._hist_tree.heading(c, text=c)
            self._hist_tree.column(c, width=120, anchor="w")
        self._hist_tree.pack(fill="both", expand=True, padx=16, pady=(12, 4))
        btn_f = tk.Frame(page, bg=BG); btn_f.pack(anchor="w", padx=16, pady=(4, 12))
        tk.Button(btn_f, text="Clear history", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=8, pady=3, command=self._clear_history).pack(side="left")
        self._refresh_history_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_settings_page(self, page):
        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(page, orient="vertical", command=canvas.yview,
                          bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); canvas.pack(fill="both", expand=True)
        inner = tk.Frame(canvas, bg=BG)
        _wid = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(_wid, width=e.width))

        def sec(title):
            f = tk.Frame(inner, bg=BG); f.pack(fill="x", padx=16, pady=(14, 0))
            tk.Label(f, text=title, bg=BG, fg=GOLD, font=FONT_BOLD).pack(anchor="w", pady=(0, 4))
            box = tk.Frame(f, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
            box.pack(fill="x"); return box

        s1 = sec("Bot Integration")
        tk.Label(s1, text="Path to Exiled Bot 2 pickit folder. Auto-copy deploys the .ipd there after each run.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=10, pady=(8, 4))
        bf = tk.Frame(s1, bg=BG2); bf.pack(fill="x", padx=10, pady=(0, 6))
        bf.columnconfigure(0, weight=1)
        _entry(bf, self.bot_folder_var).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        tk.Button(bf, text="Browse…", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=8, pady=3, command=self._browse_bot_folder).grid(row=0, column=1)
        _cbtn(s1, "Auto-copy .ipd to bot folder after generate", self.auto_copy_var).pack(anchor="w", padx=10)
        _cbtn(s1, "Launch minimized", self.start_min_var).pack(anchor="w", padx=10, pady=(0, 10))

        s2 = sec("Backups")
        tk.Label(s2, text="Keep numbered copies of previous pickit files. 0 = disabled.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=10, pady=(8, 4))
        bf2 = tk.Frame(s2, bg=BG2); bf2.pack(anchor="w", padx=10, pady=(0, 10))
        tk.Label(bf2, text="Keep", bg=BG2, fg=TEXT_DIM, font=FONT).pack(side="left")
        _entry(bf2, self.backup_count_var, width=5).pack(side="left", padx=(8, 4), ipady=4)
        tk.Label(bf2, text="backups  (0 = disabled)", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")

        s3 = sec("Overwrite Protection")
        tk.Label(s3, text="Confirms before overwriting a recently-generated file.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", padx=10, pady=(8, 4))
        bf3 = tk.Frame(s3, bg=BG2); bf3.pack(anchor="w", padx=10, pady=(0, 10))
        tk.Label(bf3, text="Confirm if file younger than", bg=BG2, fg=TEXT_DIM, font=FONT).pack(side="left")
        _entry(bf3, self.ovw_var, width=6).pack(side="left", padx=(8, 4), ipady=4)
        tk.Label(bf3, text="seconds  (0 = always ask)", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")

        s4 = sec("Config File")
        cf = tk.Frame(s4, bg=BG2); cf.pack(fill="x", padx=10, pady=(8, 10))
        tk.Label(cf, text=CONFIG_PATH, bg=BG2, fg=TEXT_DIM, font=FONT_MONO).pack(side="left")
        tk.Button(cf, text="Open", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=8, pady=2,
                  command=lambda: self._open_file_path(CONFIG_PATH)).pack(side="left", padx=(8, 0))

        bf4 = tk.Frame(inner, bg=BG); bf4.pack(fill="x", padx=16, pady=(16, 20))
        tk.Button(bf4, text="Save settings", bg=GOLD, fg="#111", relief="flat",
                  font=FONT_BOLD, padx=14, pady=6, cursor="hand2",
                  activebackground=GOLD_LT, activeforeground="#111",
                  command=self._save_settings).pack(side="left")
        tk.Button(bf4, text="Reset to defaults", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=10, pady=5, cursor="hand2",
                  activebackground=BORDER,
                  command=self._reset_defaults).pack(side="left", padx=(8, 0))

    # ══════════════════════════════════════════════════════════════════════════
    #  DEBUG PAGE
    # ══════════════════════════════════════════════════════════════════════════
    def _build_debug_page(self, page):
        btn_f = tk.Frame(page, bg=BG); btn_f.pack(fill="x", padx=16, pady=10)
        for txt, cmd in [
            ("Run diagnostics", self._run_diagnostics),
            ("Test all API endpoints",
             lambda: threading.Thread(target=self._api_test_worker, daemon=True).start()),
            ("Show config", self._debug_show_config),
            ("Clear", self._debug_clear),
        ]:
            tk.Button(btn_f, text=txt, bg=BG3, fg=TEXT, relief="flat", bd=1,
                      font=FONT_SM, padx=10, pady=4, cursor="hand2",
                      activebackground=BORDER, activeforeground=TEXT,
                      command=cmd).pack(side="left", padx=(0, 6))
        _sep(page).pack(fill="x", padx=16)
        df, self.debug_text = scrolled_text(page, state="disabled")
        df.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        for tag, col in [("header", GOLD), ("ok", TEXT_OK), ("err", TEXT_ERR),
                         ("warn", TEXT_WARN), ("info", TEXT_INFO), ("dim", TEXT_DIM)]:
            self.debug_text.tag_config(tag, foreground=col)

    # ══════════════════════════════════════════════════════════════════════════
    #  CATEGORY SWITCHING
    # ══════════════════════════════════════════════════════════════════════════
    def _show_cat(self, key):
        self._cat_search_var.set("")
        self._cat_cards.pop("_search", None)
        self._active_cat = key

        if hasattr(self, "_cat_thresh_entry"):
            if key in self.cat_thresh:
                self._cat_thresh_entry.config(textvariable=self.cat_thresh[key], state="normal")
            else:
                self._cat_thresh_entry.config(state="disabled")

        lbl_text = next((l for k, _, l, _ in gen.EXCHANGE_CATEGORIES if k == key), key)
        self._cat_header_var.set(lbl_text)

        league  = self._selected_league() or "Mercenaries"
        payload = gen._cache_get(league, key)
        if payload and not isinstance(payload, Exception):
            self._populate_cat_grid(key, payload)
        else:
            self._clear_cat_grid()
            self._cat_loading_lbl.config(text=f"Loading {lbl_text}...")
            self._cat_loading_lbl.place(relx=0.5, rely=0.4, anchor="center")
            self._cat_count_var.set("Fetching from poe.ninja...")
            threading.Thread(target=self._load_cat_async, args=(key,), daemon=True).start()

    def _load_cat_async(self, key):
        entry_ = next((e for e in gen.EXCHANGE_CATEGORIES if e[0] == key), None)
        if not entry_: return
        _, ninja_type, _, is_unique = entry_
        league = self._selected_league() or "Mercenaries"
        try:
            payload = gen.fetch_category(league, key, ninja_type, is_unique)
            gen._cache_set(league, key, payload)
            self.after(0, lambda: self._populate_cat_grid(key, payload))
        except Exception as exc:
            self.after(0, lambda: self._cat_count_var.set(f"Failed: {exc}"))

    def _clear_cat_grid(self):
        for w in self._cat_grid_frame.winfo_children():
            w.destroy()

    def _populate_cat_grid(self, key, payload):
        if self._active_cat != key: return
        self._cat_loading_lbl.place_forget()
        self._clear_cat_grid()

        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        rate        = gen.exalted_rate(payload)
        league      = self._selected_league() or "Mercenaries"
        div_rate    = self._get_divine_rate(league)

        rows = []
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if not item or not item.get("name"): continue
            raw_name = item["name"]
            if raw_name in gen.ITEM_NAME_SKIP: continue
            name = gen.ITEM_NAME_CORRECTIONS.get(raw_name, raw_name)
            pv   = float(line.get("primaryValue") or 0.0)
            ex   = pv * rate if rate else pv
            raw_img = item.get("image") or item.get("icon") or ""
            rows.append((name, pv, ex, div_rate, self._decode_ninja_image(raw_img)))

        if key == "essences":
            rows.sort(key=lambda r: gen._essence_tier_key(r[0]))
        elif key == "uncut_gems":
            _ORDER = {"Support": 0, "Spirit": 1, "Skill": 2}
            def _gem_sort(r):
                m = re.search(r'\(Level (\d+)\)', r[0]); lvl = int(m.group(1)) if m else 0
                for t, ti in _ORDER.items():
                    if f"Uncut {t} Gem" in r[0]: return (ti, lvl)
                return (99, lvl)
            rows.sort(key=_gem_sort)
        elif key == "expedition":
            def _exp_sort(r):
                m = re.search(r'\(Level (\d+)\)', r[0])
                if "Thaumaturgic Flux" in r[0] and m: return (1, int(m.group(1)))
                return (0, -r[2])
            rows.sort(key=_exp_sort)
        else:
            rows.sort(key=lambda r: -r[2])

        self._item_prices[key] = {
            name: {"ex": ex, "chaos": chaos, "div": (ex / div_rate if div_rate else 0.0)}
            for name, chaos, ex, div_rate, _ in rows
        }
        if key not in self._item_states: self._item_states[key] = {}
        states = self._item_states[key]
        NCOLS = 3; self._cat_cards[key] = []

        if key == "uncut_gems":
            _LABELS = {"Support": "Uncut Support Gems", "Spirit": "Uncut Spirit Gems", "Skill": "Uncut Skill Gems"}
            _ORDER  = {"Support": 0, "Spirit": 1, "Skill": 2}
            grid_row = 0; col = 0; current_type = None
            for name, chaos, ex, _dr, icon_url in rows:
                gem_type = next((t for t in _ORDER if f"Uncut {t} Gem" in name), None)
                if gem_type != current_type:
                    if col != 0: grid_row += 1; col = 0
                    hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
                    tk.Label(hdr, text=_LABELS.get(gem_type, gem_type), bg="#16141a",
                             fg=GOLD, font=("Segoe UI", 9, "bold"), padx=8, pady=5, anchor="w").pack(fill="x")
                    hdr.grid(in_=self._cat_grid_frame, row=grid_row, column=0,
                             columnspan=3, padx=3, pady=(10, 2), sticky="ew")
                    grid_row += 1; current_type = gem_type
                div_val = ex / _dr if _dr else 0.0
                enabled = states.get(name, {}).get("enabled", True)
                card = self._make_item_card(key, name, chaos, ex, div_val, icon_url, enabled)
                card.grid(in_=self._cat_grid_frame, row=grid_row, column=col, padx=3, pady=3, sticky="ew")
                self._cat_cards[key].append(card)
                col += 1
                if col >= NCOLS: col = 0; grid_row += 1
        elif key == "expedition":
            grid_row = 0; col = 0; shown_flux = False
            for name, chaos, ex, _dr, icon_url in rows:
                is_flux = "Thaumaturgic Flux" in name
                if is_flux and not shown_flux:
                    if col != 0: grid_row += 1; col = 0
                    hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
                    tk.Label(hdr, text="Thaumaturgic Flux", bg="#16141a",
                             fg=GOLD, font=("Segoe UI", 9, "bold"), padx=8, pady=5, anchor="w").pack(fill="x")
                    hdr.grid(in_=self._cat_grid_frame, row=grid_row, column=0,
                             columnspan=3, padx=3, pady=(10, 2), sticky="ew")
                    grid_row += 1; shown_flux = True
                div_val = ex / _dr if _dr else 0.0
                enabled = states.get(name, {}).get("enabled", True)
                card = self._make_item_card(key, name, chaos, ex, div_val, icon_url, enabled)
                card.grid(in_=self._cat_grid_frame, row=grid_row, column=col, padx=3, pady=3, sticky="ew")
                self._cat_cards[key].append(card)
                col += 1
                if col >= NCOLS: col = 0; grid_row += 1
        else:
            for i, (name, chaos, ex, _dr, icon_url) in enumerate(rows):
                div_val = ex / _dr if _dr else 0.0
                enabled = states.get(name, {}).get("enabled", True)
                r_, c_ = divmod(i, NCOLS)
                card = self._make_item_card(key, name, chaos, ex, div_val, icon_url, enabled)
                card.grid(in_=self._cat_grid_frame, row=r_, column=c_, padx=3, pady=3, sticky="ew")
                self._cat_cards[key].append(card)

        for c_ in range(NCOLS):
            self._cat_grid_frame.columnconfigure(c_, weight=1, uniform="catcol")
        self._update_cat_count(key)
        self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
        self._cat_canvas.yview_moveto(0)
        threading.Thread(target=self._resolve_wiki_icons, args=(key, rows), daemon=True).start()

    def _make_item_card(self, cat_key, name, chaos, ex_val, div_val, icon_url, enabled):
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame = tk.Frame(self._cat_grid_frame, bg=bg, cursor="hand2",
                         highlightthickness=1, highlightbackground=bdr)
        frame._cat_key = cat_key; frame._name = name; frame._enabled = enabled
        frame._chaos = chaos; frame._ex = ex_val; frame._div = div_val

        ph = tk.PhotoImage(width=36, height=36); ph.put("#3a3050", to=(0, 0, 36, 36))
        icon_lbl = tk.Label(frame, image=ph, bg=bg, width=36, height=36, bd=0)
        icon_lbl.pack(side="left", padx=(6, 3), pady=5)
        icon_lbl._ph = ph; frame._icon_lbl = icon_lbl

        name_lbl = tk.Label(frame, text=name, bg=bg, fg=fg, font=("Segoe UI", 9), anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True, padx=(0, 4))
        frame._name_lbl = name_lbl

        val_lbl = tk.Label(frame, text=self._fmt_price(chaos, ex_val, div_val),
                           bg=bg, fg=_CVAL, font=("Segoe UI", 8), anchor="e", width=11)
        val_lbl.pack(side="right", padx=(0, 4)); frame._val_lbl = val_lbl

        dot_lbl = tk.Label(frame, text="●" if enabled else "○", bg=bg,
                           fg=GOLD if enabled else TEXT_DIM, font=("Segoe UI", 11))
        dot_lbl.pack(side="right", padx=(0, 2)); frame._dot_lbl = dot_lbl

        def _click(e=None, f=frame): self._toggle_card(f)
        def _scroll(e): self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units")
        for w in (frame, icon_lbl, name_lbl, val_lbl, dot_lbl):
            w.bind("<Button-1>", _click)
            w.bind("<MouseWheel>", _scroll)
        return frame

    def _toggle_card(self, frame):
        enabled = not frame._enabled; frame._enabled = enabled
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._icon_lbl.config(bg=bg); frame._val_lbl.config(bg=bg)
        frame._dot_lbl.config(bg=bg, text="●" if enabled else "○",
                               fg=GOLD if enabled else TEXT_DIM)
        key = frame._cat_key; name = frame._name
        if key not in self._item_states: self._item_states[key] = {}
        self._item_states[key][name] = {"enabled": enabled}
        self._update_cat_count(key)
        self.after(0, self._save_states_now)

    def _update_cat_count(self, key):
        cards = self._cat_cards.get(key, [])
        enabled = sum(1 for c in cards if c._enabled)
        self._cat_count_var.set(f"{enabled} / {len(cards)} enabled")

    def _fmt_price(self, chaos, ex, div):
        if self._price_unit == "chaos": return f"{chaos:.0f}c"
        if self._price_unit == "div":   return f"{div:.3f} div"
        return f"{ex:.2f} ex"

    def _set_price_unit(self, unit):
        self._price_unit = unit; self._update_price_unit_btns()
        key = self._active_cat
        if not key: return
        for card in self._cat_cards.get(key, []) + self._cat_cards.get("_search", []):
            card._val_lbl.config(text=self._fmt_price(card._chaos, card._ex, card._div))

    def _update_price_unit_btns(self):
        for unit, b in self._price_unit_btns.items():
            b.config(bg=GOLD if unit == self._price_unit else BG3,
                     fg="#111" if unit == self._price_unit else TEXT_DIM)

    def _cat_filter(self, *_):
        q = self._cat_search_var.get().strip().lower()
        key = self._active_cat
        if not key: return
        if not q:
            self._cat_cards.pop("_search", None)
            league  = self._selected_league() or "Mercenaries"
            payload = gen._cache_get(league, key)
            if payload and not isinstance(payload, Exception):
                self._populate_cat_grid(key, payload)
            return
        self._clear_cat_grid(); self._cat_cards["_search"] = []
        NCOLS = 3; grid_row = 0; col = 0; found_any = False
        for cat_key, _, cat_label, _ in gen.EXCHANGE_CATEGORIES:
            prices = self._item_prices.get(cat_key, {})
            if not prices: continue
            matches = sorted([(n, d) for n, d in prices.items() if q in n.lower()],
                             key=lambda x: -x[1].get("ex", 0))
            if not matches: continue
            found_any = True
            if col != 0: grid_row += 1; col = 0
            hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
            tk.Label(hdr, text=cat_label.upper(), bg="#16141a", fg=GOLD,
                     font=("Segoe UI", 9, "bold"), padx=8, pady=5, anchor="w").pack(fill="x")
            hdr.grid(in_=self._cat_grid_frame, row=grid_row, column=0,
                     columnspan=3, padx=3, pady=(10, 2), sticky="ew")
            grid_row += 1
            states = self._item_states.get(cat_key, {})
            for name, data in matches:
                enabled = states.get(name, {}).get("enabled", True)
                card = self._make_item_card(cat_key, name,
                    data.get("chaos", 0), data.get("ex", 0), data.get("div", 0),
                    self._wiki_icon_cache.get(name, ""), enabled)
                card.grid(in_=self._cat_grid_frame, row=grid_row, column=col,
                          padx=3, pady=3, sticky="ew")
                self._cat_cards["_search"].append(card)
                col += 1
                if col >= NCOLS: col = 0; grid_row += 1
        if not found_any:
            tk.Label(self._cat_grid_frame, text="No results", bg=BG, fg=TEXT_DIM,
                     font=("Segoe UI", 11)).grid(row=0, column=0, columnspan=3, pady=30)
        for c_ in range(NCOLS):
            self._cat_grid_frame.columnconfigure(c_, weight=1, uniform="catcol")
        self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
        self._cat_canvas.yview_moveto(0)
        for card in self._cat_cards["_search"]:
            url = self._wiki_icon_cache.get(card._name, "")
            if url:
                threading.Thread(target=self._fetch_icon,
                                 args=("_search", card._name, url), daemon=True).start()
        count = len(self._cat_cards["_search"])
        self._cat_count_var.set(f"{count} result{'s' if count != 1 else ''} across all categories")

    def _cat_items_set_all(self, enabled: bool):
        key = self._active_cat
        if not key: return
        if key not in self._item_states: self._item_states[key] = {}
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        for card in self._cat_cards.get(key, []):
            card._enabled = enabled
            card.config(bg=bg, highlightbackground=bdr)
            card._name_lbl.config(bg=bg, fg=fg)
            card._icon_lbl.config(bg=bg); card._val_lbl.config(bg=bg)
            card._dot_lbl.config(bg=bg, text="●" if enabled else "○",
                                  fg=GOLD if enabled else TEXT_DIM)
            self._item_states[key][card._name] = {"enabled": enabled}
        self._update_cat_count(key); self.after(0, self._save_states_now)

    def _cat_items_reset(self):
        key = self._active_cat
        if not key: return
        self._item_states.pop(key, None)
        for card in self._cat_cards.get(key, []):
            card._enabled = True
            card.config(bg=_CON, highlightbackground=_CONB)
            card._name_lbl.config(bg=_CON, fg=_CTXON)
            card._icon_lbl.config(bg=_CON); card._val_lbl.config(bg=_CON)
            card._dot_lbl.config(bg=_CON, text="●", fg=GOLD)
        self._update_cat_count(key); self.after(0, self._save_states_now)

    def _get_divine_rate(self, league):
        payload = gen._cache_get(league, "currency")
        if not payload or isinstance(payload, Exception): return 1.0
        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        rate = gen.exalted_rate(payload)
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if item and item.get("name") == "Divine Orb":
                pv = float(line.get("primaryValue") or 0.0)
                return pv * rate if rate else pv
        return 1.0

    def _save_states_now(self):
        self.cfg["item_states"] = self._item_states
        save_config(self.cfg)

    # ══════════════════════════════════════════════════════════════════════════
    #  ICON LOADING
    # ══════════════════════════════════════════════════════════════════════════
    _ICON_HEADERS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0"),
        "Referer": "https://poe.ninja/",
        "Accept": "image/png,image/webp,*/*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    @staticmethod
    def _decode_ninja_image(raw: str) -> str:
        if not raw: return ""
        if raw.startswith("/"): return "https://poe.ninja" + raw
        if raw.startswith("http"): return raw
        return ""

    _WIKI_API = "https://www.poe2wiki.net/api.php"

    @staticmethod
    def _wiki_base_name(name: str) -> str:
        return re.sub(r'\s*\(Level \d+\)\s*$', '', name).strip()

    @staticmethod
    def _wiki_tier_base(name: str) -> str:
        return re.sub(r'^(Greater|Perfect)\s+', '', name, flags=re.IGNORECASE).strip()

    def _batch_wiki_query(self, file_to_items: dict) -> dict:
        found = {}
        unique_titles = list(file_to_items.keys())
        for i in range(0, len(unique_titles), 50):
            batch = unique_titles[i:i + 50]
            try:
                r = requests.get(self._WIKI_API, params={
                    "action": "query", "titles": "|".join(batch),
                    "prop": "imageinfo", "iiprop": "url", "format": "json",
                }, timeout=15, headers={"User-Agent": gen.USER_AGENT})
                for page in r.json().get("query", {}).get("pages", {}).values():
                    if page.get("pageid", -1) != -1 and "imageinfo" in page:
                        found[page["title"]] = page["imageinfo"][0]["url"]
            except Exception:
                pass
        return found

    def _resolve_wiki_icons(self, cat_key, rows):
        names = [r[0] for r in rows]
        ninja_by_name = {r[0]: r[4] for r in rows}
        to_fetch = [n for n in names if n not in self._wiki_icon_cache]
        if to_fetch:
            file_to_items: dict = {}
            for n in to_fetch:
                title = f"File:{self._wiki_base_name(n)} inventory icon.png"
                file_to_items.setdefault(title, []).append(n)
            found = self._batch_wiki_query(file_to_items)
            for title, url in found.items():
                for item_name in file_to_items.get(title, []):
                    self._wiki_icon_cache[item_name] = url
            if cat_key == "currency":
                _tier_re = re.compile(r'^(Greater|Perfect)\s+', re.IGNORECASE)
                still_missing = [n for n in to_fetch
                                 if n not in self._wiki_icon_cache and _tier_re.match(n)]
                if still_missing:
                    fallback_map: dict = {}
                    for n in still_missing:
                        title = f"File:{self._wiki_tier_base(n)} inventory icon.png"
                        fallback_map.setdefault(title, []).append(n)
                    found2 = self._batch_wiki_query(fallback_map)
                    for title, url in found2.items():
                        for item_name in fallback_map.get(title, []):
                            self._wiki_icon_cache[item_name] = url
            for n in to_fetch:
                if n not in self._wiki_icon_cache:
                    self._wiki_icon_cache[n] = ninja_by_name.get(n, "")
            try:
                with open(WIKI_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._wiki_icon_cache, f, indent=2)
            except Exception:
                pass
        to_load = [(name, self._wiki_icon_cache.get(name) or ninja_by_name.get(name, ""))
                   for name in names
                   if self._wiki_icon_cache.get(name) or ninja_by_name.get(name, "")]
        if to_load:
            def _load_all(items=to_load, key=cat_key):
                with _TPE(max_workers=8) as pool:
                    for n, u in items:
                        pool.submit(self._fetch_icon, key, n, u)
            threading.Thread(target=_load_all, daemon=True).start()

    def _fetch_icon(self, key, name, url):
        if not url: return
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
        for card in self._cat_cards.get(key, []):
            if card._name != name: continue
            try:
                if _HAS_PIL:
                    img   = Image.open(path).resize((36, 36), Image.LANCZOS)
                    photo = _ImageTk.PhotoImage(img)
                else:
                    photo = tk.PhotoImage(file=path)
                    w, h  = photo.width(), photo.height()
                    factor = max(1, max(w, h) // 36)
                    if factor > 1: photo = photo.subsample(factor, factor)
                card._icon_lbl.config(image=photo, width=photo.width(), height=photo.height())
                card._icon_lbl._ph = photo
            except Exception:
                pass
            break

    # ══════════════════════════════════════════════════════════════════════════
    #  PRESETS
    # ══════════════════════════════════════════════════════════════════════════
    def _preset_save(self):
        name = simpledialog.askstring("Save Preset", "Preset name:", parent=self)
        if not name: return
        data = {"_meta": {"name": name, "created": datetime.datetime.now().isoformat(),
                          "league": self._selected_league() or ""},
                "item_states": self._item_states}
        path = os.path.join(PRESETS_DIR, re.sub(r'[^\w\-. ]', '_', name) + ".json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Saved", f"Preset '{name}' saved.", parent=self)

    def _preset_load(self):
        files = [f for f in os.listdir(PRESETS_DIR) if f.endswith(".json")]
        if not files:
            messagebox.showinfo("No Presets", "No saved presets.\nUse Save or Import first.", parent=self); return
        dlg = tk.Toplevel(self); dlg.title("Load Preset"); dlg.configure(bg=BG); dlg.grab_set()
        tk.Label(dlg, text="Select a preset:", bg=BG, fg=TEXT, font=FONT, padx=16, pady=10).pack(anchor="w")
        lb = tk.Listbox(dlg, bg=BG3, fg=TEXT, selectbackground=GOLD, selectforeground="#111",
                        font=FONT, width=36, height=min(len(files), 12))
        for f in files: lb.insert("end", f[:-5])
        lb.pack(padx=16, pady=(0, 8)); lb.selection_set(0)
        def _apply():
            sel = lb.curselection()
            if not sel: return
            try:
                with open(os.path.join(PRESETS_DIR, files[sel[0]]), encoding="utf-8") as fp:
                    data = json.load(fp)
                self._item_states = data.get("item_states", data)
                self.cfg["item_states"] = self._item_states; save_config(self.cfg); dlg.destroy()
                key = self._active_cat
                if key:
                    payload = gen._cache_get(self._selected_league() or "Mercenaries", key)
                    if payload: self._populate_cat_grid(key, payload)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=dlg)
        bf = tk.Frame(dlg, bg=BG); bf.pack(fill="x", padx=16, pady=(0, 12))
        tk.Button(bf, text="Load", bg=GOLD, fg="#111", relief="flat", font=FONT_BOLD,
                  padx=10, pady=4, command=_apply).pack(side="left", padx=(0, 6))
        tk.Button(bf, text="Cancel", bg=BG3, fg=TEXT, relief="flat", bd=1,
                  font=FONT_SM, padx=10, pady=4, command=dlg.destroy).pack(side="left")

    def _preset_export(self):
        path = filedialog.asksaveasfilename(defaultextension=".json",
            filetypes=[("JSON preset", "*.json")], title="Export Preset", parent=self)
        if not path: return
        data = {"_meta": {"name": os.path.splitext(os.path.basename(path))[0],
                          "created": datetime.datetime.now().isoformat(),
                          "league": self._selected_league() or ""},
                "item_states": self._item_states}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Exported", f"Exported to:\n{path}", parent=self)

    def _preset_import(self):
        path = filedialog.askopenfilename(filetypes=[("JSON preset", "*.json")],
                                          title="Import Preset", parent=self)
        if not path: return
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self._item_states = data.get("item_states", data)
            self.cfg["item_states"] = self._item_states; save_config(self.cfg)
            dest = os.path.join(PRESETS_DIR, os.path.basename(path))
            if not os.path.exists(dest): shutil.copy2(path, dest)
            key = self._active_cat
            if key:
                payload = gen._cache_get(self._selected_league() or "Mercenaries", key)
                if payload: self._populate_cat_grid(key, payload)
            messagebox.showinfo("Imported", "Preset imported and applied.", parent=self)
        except Exception as e:
            messagebox.showerror("Import Failed", str(e), parent=self)

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW
    # ══════════════════════════════════════════════════════════════════════════
    def _populate_preview(self, lines):
        self._preview_lines = lines; self._render_preview(lines)

    def _render_preview(self, lines):
        t = self.preview_text; ypos = t.yview()[0]
        t.config(state="normal"); t.delete("1.0", "end")
        active = commented = 0
        for line in lines:
            if line.startswith("////") or (line.startswith("//") and line.count("//") > 2):
                tag = "header"
            elif line.startswith("//"):
                tag = "commented"; commented += 1
            elif "[StashItem]" in line:
                tag = "unique" if "[Rarity]" in line else "active"; active += 1
            else:
                tag = ""
            t.insert("end", line + "\n", tag)
        t.config(state="disabled"); t.yview_moveto(ypos)
        self.preview_count_var.set(f"{active} active rules  ·  {commented} commented out")

    def _filter_preview(self, *_):
        q = self.filter_var.get().lower()
        if not q or not self._preview_lines:
            if self._preview_lines: self._render_preview(self._preview_lines)
            return
        self._render_preview([l for l in self._preview_lines if q in l.lower()])

    def _preview_copy(self):
        if not self._preview_lines: return
        self.clipboard_clear(); self.clipboard_append("\n".join(self._preview_lines))
        prev = self.preview_count_var.get()
        self.preview_count_var.set("Copied to clipboard!")
        self.after(1500, lambda: self.preview_count_var.set(prev))

    # ══════════════════════════════════════════════════════════════════════════
    #  HISTORY
    # ══════════════════════════════════════════════════════════════════════════
    def _add_history_entry(self, entry_dict):
        h = self.cfg.get("history", []); h.append(entry_dict)
        if len(h) > 50: h = h[-50:]
        self.cfg["history"] = h; save_config(self.cfg)
        self.after(0, self._refresh_history_ui)

    def _refresh_history_ui(self):
        for row in self._hist_tree.get_children():
            self._hist_tree.delete(row)
        for e in reversed(self.cfg.get("history", [])[-50:]):
            self._hist_tree.insert("", "end", values=(
                e.get("ts", ""), e.get("active", ""), e.get("commented", ""),
                f"{e.get('divine_rate', 0):.1f} ex",
                f"{e.get('top_item', '')}  ({e.get('top_value', 0):.0f}ex)",
                e.get("duration", ""),
            ))

    def _clear_history(self):
        if messagebox.askyesno("Clear history", "Delete all history entries?"):
            self.cfg["history"] = []; save_config(self.cfg); self._refresh_history_ui()

    # ══════════════════════════════════════════════════════════════════════════
    #  SETTINGS
    # ══════════════════════════════════════════════════════════════════════════
    def _save_settings(self):
        self.cfg.update({
            "bot_folder": self.bot_folder_var.get(),
            "auto_copy": self.auto_copy_var.get(),
            "backup_count": self.backup_count_var.get(),
            "start_minimized": self.start_min_var.get(),
            "confirm_overwrite_secs": self.ovw_var.get(),
            "include_bases": self.include_bases_var.get(),
            "base_quality": self.base_quality_var.get(),
            "base_min_level": self.base_min_level_var.get(),
            "min_exalt_gear": self.min_exalt_gear_var.get(),
        })
        save_config(self.cfg); self._log("Settings saved.", "ok")

    def _reset_defaults(self):
        if messagebox.askyesno("Reset settings", "Reset all settings to defaults?"):
            self.cfg = dict(DEFAULT_CONFIG); save_config(self.cfg)
            self.league_var.set(""); self.min_exalt_var.set(1.0)
            self.min_exalt_gear_var.set(5.0); self.output_var.set("poe2_pickit")
            self.bot_folder_var.set(""); self.auto_copy_var.set(False)
            self.backup_count_var.set(5); self.start_min_var.set(False)
            self.ovw_var.set(120); self.include_bases_var.set(True)
            self.base_quality_var.set(28); self.base_min_level_var.set(75)
            for key in ALL_CATEGORY_KEYS:
                self.cat_enabled[key].set(True); self.cat_thresh[key].set(-1.0)
            self._log("Settings reset to defaults.", "warn")

    def _browse_bot_folder(self):
        folder = filedialog.askdirectory(title="Select Exiled Bot pickit folder")
        if folder: self.bot_folder_var.set(folder)

    # ══════════════════════════════════════════════════════════════════════════
    #  DEBUG
    # ══════════════════════════════════════════════════════════════════════════
    def _dlog(self, msg, tag=""):
        def _do():
            self.debug_text.config(state="normal")
            self.debug_text.insert("end", msg + "\n", tag)
            self.debug_text.see("end"); self.debug_text.config(state="disabled")
        self.after(0, _do)

    def _debug_clear(self):
        self.debug_text.config(state="normal"); self.debug_text.delete("1.0", "end")
        self.debug_text.config(state="disabled")

    def _run_diagnostics(self):
        self._debug_clear()
        threading.Thread(target=self._diag_worker, daemon=True).start()

    def _diag_worker(self):
        d = self._dlog
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        d(f"=== ExileBot 2 Pickit Generator - Diagnostics  {now}", "header"); d("")
        d("-- 1. Python environment", "header")
        d(f"  Python   : {sys.version.split()[0]}", "info")
        d(f"  Platform : {sys.platform}", "info")
        frozen = getattr(sys, 'frozen', False)
        d(f"  Frozen   : {frozen}  ({'EXE' if frozen else 'script'})", "info"); d("")
        d("-- 2. Modules", "header")
        for mod, required in [("tkinter", True), ("requests", True),
                               ("customtkinter", True), ("poe2_pickit_generator", True)]:
            try:
                m = importlib.import_module(mod); ver = getattr(m, "__version__", "n/a")
                d(f"  OK  {mod:<32} {ver}", "ok")
            except ImportError as e:
                d(f"  {'FAIL' if required else 'SKIP'}  {mod:<32} {e}",
                  "err" if required else "warn")
        d(""); d("-- 3. poe.ninja connectivity", "header")
        try:
            t0 = time.time(); data = gen.fetch_json(gen.INDEX_STATE_URL, {})
            d(f"  OK  Reachable ({(time.time()-t0)*1000:.0f} ms)", "ok")
            for lg in data.get("economyLeagues", []):
                d(f"    * {lg.get('name', '?')}", "dim")
        except Exception as e:
            d(f"  FAIL: {e}", "err")
        d(""); d("=== Diagnostics complete ===", "header")

    def _api_test_worker(self):
        d = self._dlog; d("-- API endpoint test --", "header")
        league = self._selected_league() or "Standard"
        d(f"League: {league}", "info")
        for key, ninja_type, label_text, is_unique in gen.ALL_CATEGORIES:
            try:
                t0 = time.time()
                payload = gen.fetch_category(league, key, ninja_type, is_unique)
                elapsed = time.time() - t0
                n = len(payload.get("items", payload.get("lines", [])))
                d(f"  OK  {label_text:<30} {n:>4} rows  ({elapsed*1000:.0f} ms)", "ok")
                time.sleep(0.2)
            except Exception as e:
                d(f"  FAIL  {label_text:<30} {e}", "err")
        d("-- API test done --", "header")

    def _debug_show_config(self):
        self._debug_clear(); self._dlog("-- Current config --", "header")
        cfg_copy = dict(self.cfg); cfg_copy.pop("history", None)
        for k, v in cfg_copy.items():
            self._dlog(f"  {k:<28}: {json.dumps(v)}", "info")
        self._dlog(f"  {'history entries':<28}: {len(self.cfg.get('history', []))}", "dim")

    # ══════════════════════════════════════════════════════════════════════════
    #  LEAGUE
    # ══════════════════════════════════════════════════════════════════════════
    def _fetch_leagues_async(self):
        self.league_var.set(self.league_var.get() or "Loading...")
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
        self.league_cb["values"] = names; self.league_cb.config(state="normal")
        saved = self.cfg.get("league", ""); matched = False
        if saved:
            for i, (n, _, d) in enumerate(self._leagues):
                if n == saved or d == saved:
                    self.league_cb.current(i); matched = True; break
        if not matched and names:
            self.league_cb.current(0)
        self._log(f"Loaded {len(names)} leagues.", "ok")

    def _selected_league(self):
        raw = self.league_var.get().strip()
        if not self._leagues or raw.startswith("Loading"): return raw
        idx = self.league_cb.current()
        if 0 <= idx < len(self._leagues): return self._leagues[idx][0]
        if "[" in raw and raw.endswith("]"): return raw.split("[")[-1].rstrip("]").strip()
        return raw

    # ══════════════════════════════════════════════════════════════════════════
    #  LOG
    # ══════════════════════════════════════════════════════════════════════════
    def _log(self, msg, tag=""):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        def _do():
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{ts}] ", "ts")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end"); self.log_text.config(state="disabled")
        self.after(0, _do)

    def _log_clear(self):
        self.log_text.config(state="normal"); self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")

    def _log_copy(self):
        content = self.log_text.get("1.0", "end").strip()
        if not content: self._log("Log is empty.", "warn"); return
        self.clipboard_clear(); self.clipboard_append(content)
        self._log("Log copied to clipboard.", "ok")

    # ══════════════════════════════════════════════════════════════════════════
    #  BACKUP / SCHEDULE
    # ══════════════════════════════════════════════════════════════════════════
    def _backup_file(self, path, n=None):
        if n is None: n = self.backup_count_var.get()
        if n <= 0 or not os.path.isfile(path): return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(path)
        shutil.copy2(path, f"{base}_backup_{ts}{ext}")
        folder = os.path.dirname(path) or "."; stem = os.path.basename(base)
        backups = sorted([os.path.join(folder, f) for f in os.listdir(folder)
                          if f.startswith(stem + "_backup_") and f.endswith(ext)])
        while len(backups) > n:
            try: os.remove(backups.pop(0))
            except Exception: pass

    def _schedule_tick(self):
        if not self._running:
            now = time.time()
            if now - self._last_run_time >= 3600:
                self._start_generate(silent=True)
            remaining = int(3600 - (now - self._last_run_time))
            h, m = divmod(max(remaining, 0) // 60, 60)
            self.schedule_lbl.config(text=f"Next: {h}h {m}m")
        self._schedule_after = self.after(30_000, self._schedule_tick)

    # ══════════════════════════════════════════════════════════════════════════
    #  FILE HELPERS
    # ══════════════════════════════════════════════════════════════════════════
    def _output_base_path(self):
        name = os.path.basename(os.path.splitext(self.output_var.get())[0])
        return os.path.join(OUTPUT_DIR, name)

    def _browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension="", filetypes=[("All files", "*.*")],
            initialdir=OUTPUT_DIR, initialfile=self.output_var.get(),
            title="Choose output filename")
        if path: self.output_var.set(os.path.basename(os.path.splitext(path)[0]))

    def _open_file(self, ext):
        path = self._output_base_path() + ext
        if not os.path.isfile(path): self._log(f"File not found: {path}", "warn"); return
        self._open_file_path(path)

    def _open_output_folder(self):
        self._open_file_path(OUTPUT_DIR)

    def _open_file_path(self, path):
        try:
            if sys.platform == "win32": os.startfile(path)
            elif sys.platform == "darwin": subprocess.Popen(["open", path])
            else: subprocess.Popen(["xdg-open", path])
        except Exception as e:
            self._log(f"Could not open: {e}", "err")

    @staticmethod
    def _extract_rule_name(line):
        um = re.search(r'\[UniqueName\] == "([^"]+)"', line)
        if um: return um.group(1)
        nm = re.search(r'"([^"]+)"', line)
        return nm.group(1) if nm else None

    # ══════════════════════════════════════════════════════════════════════════
    #  GENERATE
    # ══════════════════════════════════════════════════════════════════════════
    def _start_generate(self, silent: bool = False):
        if self._running: return
        league = self._selected_league()
        if not league or league.startswith("Loading"):
            self._log("No league selected.", "warn"); return

        base_path = self._output_base_path(); ipd_path = base_path + ".ipd"
        if not silent and os.path.isfile(ipd_path):
            age = time.time() - os.path.getmtime(ipd_path)
            limit = self.cfg.get("confirm_overwrite_secs", 120)
            if limit == 0 or age < limit:
                if not messagebox.askyesno("Overwrite?",
                        f"Pickit generated {int(age)}s ago. Overwrite?"): return

        self._running = True; self._generate_start = time.time()
        if silent:
            self._log("-" * 55, "dim"); self._log("Auto-schedule triggered.", "info")
        else:
            self._log_clear()
        self.gen_btn.config(state="disabled")
        self.status_lbl.config(text="Generating...", fg=TEXT_WARN)
        self.progress_var.set("Starting...")

        snapshot = {
            "league": league, "output_var": self.output_var.get(),
            "auto_copy": self.auto_copy_var.get(),
            "bot_folder": self.bot_folder_var.get(),
            "backup_count": self.backup_count_var.get(),
            "cat_enabled": {k: v.get() for k, v in self.cat_enabled.items()},
            "cat_thresh": {},
            "include_bases": self.include_bases_var.get(),
            "base_quality": self.base_quality_var.get(),
            "base_min_level": self.base_min_level_var.get(),
            "item_states": dict(self._item_states),
        }
        for k, v in self.cat_thresh.items():
            try: snapshot["cat_thresh"][k] = v.get()
            except tk.TclError: snapshot["cat_thresh"][k] = -1.0
        try: snapshot["min_exalt"] = self.min_exalt_var.get()
        except tk.TclError:
            snapshot["min_exalt"] = float(self.cfg.get("min_exalt", 1.0))
            self.min_exalt_var.set(snapshot["min_exalt"])
        try: snapshot["min_exalt_gear"] = self.min_exalt_gear_var.get()
        except tk.TclError:
            snapshot["min_exalt_gear"] = float(self.cfg.get("min_exalt_gear", 5.0))
            self.min_exalt_gear_var.set(snapshot["min_exalt_gear"])

        threading.Thread(target=self._generate, args=(snapshot,), daemon=True).start()

    def _generate(self, snapshot: dict):
        success = False
        try:
            league = snapshot["league"]
            try: min_exalt = float(snapshot["min_exalt"])
            except (TypeError, ValueError): min_exalt = 1.0
            try: min_exalt_gear = float(snapshot.get("min_exalt_gear", 5.0))
            except (TypeError, ValueError): min_exalt_gear = 5.0

            base_path = os.path.join(OUTPUT_DIR,
                         os.path.basename(os.path.splitext(snapshot["output_var"])[0]))
            ipd_path = base_path + ".ipd"

            self._log(f"League    : {league}")
            self._log(f"Threshold : {min_exalt:.0f} ex (currency)  |  {min_exalt_gear:.0f} ex (gear)")
            self._log(f"Output    : {os.path.basename(base_path)}.ipd")
            self._log("-" * 55, "dim")

            categories = [cat for cat in gen.ALL_CATEGORIES
                          if snapshot["cat_enabled"].get(cat[0], True)]
            total_cats = len(categories)

            _gen_ts = datetime.datetime.now()
            _gen_id = _gen_ts.strftime('%Y%m%d_%H%M%S')
            output_lines = [
                "/" * gen._W,
                "//" + f"  EXILEBOT 2  |  PICKIT  |  ID: {_gen_id}".center(gen._W - 4) + "//",
                "/" * gen._W,
                f"// League    : {league}",
                f"// Generated : {_gen_ts.strftime('%Y-%m-%d %H:%M:%S')}",
                f"// Pickit ID : {_gen_id}",
                f"// Threshold : {min_exalt:.0f} ex (currency)  |  {min_exalt_gear:.0f} ex (gear/uniques)",
                "/" * gen._W, "",
                "//", "// Exiled Bot 2 Pickit - Configuration Guide for Path of Exile 2", "//",
                "// [StashItem] == \"true\"   pick up and stash",
                "// [StashUnid] == \"true\"   stash without identifying",
                "// [Salvage]   == \"true\"   mark for salvaging",
                "// [IgnoreRitual] == \"true\" ignore from ritual rewards",
                "//",
                "// Operators: == != > >= < <=   |   Combine: && (AND)  || (OR)  () (group)",
                "// Before # = checked BEFORE identifying  |  After # = checked AFTER identifying",
                "/" * gen._W, "",
            ]
            self._log(f"Pickit ID : {_gen_id}", "info")
            self._log("Fetching currency rates...", "dim")

            currency_payload = gen.fetch_category(league, "currency", "Currency", False)
            gen._cache_set(league, "currency", currency_payload)
            items_by_id = {i["id"]: i for i in currency_payload.get("items", [])}
            rate = gen.exalted_rate(currency_payload)
            divine_rate_exalts = 1.0; _divine_found = False
            for line in currency_payload.get("lines", []):
                item = items_by_id.get(line.get("id"))
                if item and item.get("name") == "Divine Orb":
                    pv = float(line.get("primaryValue") or 0.0)
                    divine_rate_exalts = pv * rate if rate else pv
                    _divine_found = True; break

            if not _divine_found:
                self._log("  Divine Orb not found in currency data", "warn")
            self._log(f"1 Divine = {divine_rate_exalts:.1f} Exalted", "ok")
            output_lines += [f"// Conversion: 1 Divine = {divine_rate_exalts:.6f} Exalted", "",
                             gen.header_major("Economy Items"), ""]

            top_item = ("", 0.0); report_rows = []
            non_currency_cats = [(k, t, l, u) for k, t, l, u in categories if k != "currency"]
            self._log(f"Fetching {len(non_currency_cats)} categories in parallel...", "dim")
            self.after(0, lambda n=len(non_currency_cats):
                       self.progress_var.set(f"Fetching {n} categories..."))
            all_payloads = gen.fetch_all_payloads(league, non_currency_cats)
            all_payloads["currency"] = currency_payload

            for cat_idx, (key, ninja_type, label_text, is_unique) in enumerate(categories, 1):
                self.after(0, lambda s=f"Building {cat_idx}/{total_cats}: {label_text}":
                           self.progress_var.set(s))

                cat_thresh = snapshot["cat_thresh"].get(key, -1.0)
                if not isinstance(cat_thresh, (int, float)): cat_thresh = -1.0
                global_min = min_exalt_gear if is_unique else min_exalt
                effective_min = cat_thresh if cat_thresh >= 0 else global_min

                payload = all_payloads.get(key)
                if isinstance(payload, Exception):
                    output_lines += [gen.header_sub(label_text), f"// Failed: {payload}", ""]
                    self._log(f"  FAIL {label_text}: {type(payload).__name__}", "err"); continue
                if payload is None:
                    output_lines += [gen.header_sub(label_text), "// No data returned", ""]
                    self._log(f"  ? {label_text}: no data", "warn"); continue

                try:
                    _cat_states = snapshot.get("item_states", {}).get(key, {})
                    if _cat_states and not is_unique:
                        _items_in_payload = {
                            gen.ITEM_NAME_CORRECTIONS.get(i["name"], i["name"])
                            for i in payload.get("items", []) if i.get("name")
                        }
                        _disabled = {n for n, s in _cat_states.items() if not s.get("enabled", True)}
                        enabled_names = _items_in_payload - _disabled
                    else:
                        enabled_names = None

                    if is_unique:
                        lines = gen.build_unique_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_unique_report_rows(
                            label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    elif key == "uncut_gems":
                        lines = gen.build_uncut_gem_lines(payload, divine_rate_exalts,
                                                          min_exalt=effective_min, enabled_names=enabled_names)
                        report_rows.extend(gen.collect_exchange_report_rows(
                            label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    elif key == "waystones":
                        lines = gen.build_waystone_lines(payload, divine_rate_exalts, min_exalt=effective_min)
                        report_rows.extend(gen.collect_exchange_report_rows(
                            label_text, payload, divine_rate_exalts, min_exalt=effective_min))
                    else:
                        pick_all  = key in gen.PICK_ALL_CATEGORIES
                        tier_sort = (key == "essences")
                        always    = gen.ALWAYS_PICK_CURRENCY if key == "currency" else None
                        ritual_th = min_exalt_gear if key == "omens" else None
                        lines = gen.build_exchange_lines(payload, divine_rate_exalts,
                                                         pick_all=pick_all, min_exalt=effective_min,
                                                         tier_sort=tier_sort, enabled_names=enabled_names,
                                                         always_names=always, ritual_threshold=ritual_th)
                        report_rows.extend(gen.collect_exchange_report_rows(
                            label_text, payload, divine_rate_exalts,
                            pick_all=pick_all, min_exalt=effective_min))

                    output_lines += [gen.header_sub(label_text), ""]
                    output_lines += lines if lines else [f"// poe.ninja returned no rows for {label_text}"]
                    output_lines.append("")
                    active_in_cat = sum(1 for l in lines if l and not l.startswith("//"))
                    self._log(f"  OK {label_text}: {active_in_cat} active", "ok")

                    for l in lines:
                        if l.startswith("//") or "[StashItem]" not in l: continue
                        name = self._extract_rule_name(l)
                        vm   = re.search(r'ExValue = ([\d.]+)', l)
                        if name and vm:
                            v = float(vm.group(1))
                            if v > top_item[1]: top_item = (name, v)
                except Exception as e:
                    output_lines += [gen.header_sub(label_text), f"// Processing failed: {e}", ""]
                    self._log(f"  FAIL {label_text}: {e}", "err")

            output_lines.extend(gen.STATIC_TABLET_RULES.splitlines())

            if snapshot.get("include_bases"):
                min_q = int(snapshot.get("base_quality", 28))
                self._log("Fetching base types from Poe2DB...", "dim")
                def _base_prog(idx, total, title):
                    self.after(0, lambda s=f"Bases {idx}/{total}: {title}":
                               self.progress_var.set(s))
                    self._log(f"  [{idx}/{total}] {title}", "dim")
                try:
                    min_lvl = int(snapshot.get("base_min_level", 75))
                    base_lines = gen.build_base_rules(min_quality=min_q, min_level=min_lvl,
                                                      progress_callback=_base_prog)
                    output_lines.append(""); output_lines.append(gen.header_major("Base Types"))
                    output_lines.append(""); output_lines.extend(base_lines); output_lines.append("")
                    rule_count = sum(1 for l in base_lines if l and not l.startswith("//"))
                    if any("static list" in l or "Additional Bases" in l for l in base_lines):
                        self._log("  Some categories supplemented with built-in list", "warn")
                    self._log(f"  OK Base types: {rule_count} rules", "ok")
                except Exception as e:
                    self._log(f"  FAIL Base types: {e}", "err")

            self._last_output = list(output_lines)
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

            if snapshot["auto_copy"]:
                bot = snapshot["bot_folder"].strip()
                if bot and os.path.isdir(bot):
                    dest = os.path.join(bot, os.path.basename(ipd_path))
                    shutil.copy2(ipd_path, dest); self._log(f"Copied to bot: {dest}", "ok")
                else:
                    self._log("Auto-copy: bot folder not set or not found.", "warn")

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
                "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "active": active, "commented": commented,
                "divine_rate": divine_rate_exalts,
                "top_item": top_item[0], "top_value": top_item[1], "duration": dur_str,
            })
            self.after(0, lambda: self._populate_preview(output_lines))
            self._log("-" * 55, "dim")
            self._log(f"Done in {dur_str}  *  {active} active rules", "ok")

            def _apply_cfg():
                self.cfg.update({
                    "league": league, "min_exalt": min_exalt, "min_exalt_gear": min_exalt_gear,
                    "output_base": snapshot["output_var"],
                    "category_enabled": dict(snapshot["cat_enabled"]),
                    "category_threshold": dict(snapshot["cat_thresh"]),
                })
                save_config(self.cfg)
            self.after(0, _apply_cfg)

        except Exception as e:
            self._log(f"Error: {e}", "err"); self._log(traceback.format_exc(), "dim")
        finally:
            self._last_run_time = time.time()
            self.after(0, lambda: self._generate_done(success))

    def _generate_done(self, success: bool = False):
        self._running = False
        self.gen_btn.config(state="normal")
        self.status_lbl.config(
            text=f"Last run: {datetime.datetime.now().strftime('%H:%M:%S')}",
            fg=TEXT_OK if success else TEXT_ERR)
        self.progress_var.set("")

    # ══════════════════════════════════════════════════════════════════════════
    #  CLOSE
    # ══════════════════════════════════════════════════════════════════════════
    def _on_close(self):
        if self._schedule_after: self.after_cancel(self._schedule_after)
        self.cfg["window_geometry"] = self.geometry()
        save_config(self.cfg); self.destroy()


if __name__ == "__main__":
    app = PickitApp()
    app.mainloop()
