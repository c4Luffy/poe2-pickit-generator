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

import sys, os, re, json, time, shutil, threading, datetime, traceback, subprocess, importlib, hashlib, copy, tempfile
from concurrent.futures import ThreadPoolExecutor as _TPE
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

# ── Optional imports ──────────────────────────────────────────────────────────

try:
    from PIL import Image, ImageTk as _ImageTk
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ── PyInstaller bundle path fix ───────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _bundle_dir = sys._MEIPASS
    if _bundle_dir not in sys.path:
        sys.path.insert(0, _bundle_dir)

try:
    import poe2_pickit_generator as gen
    import pickit_assembly as asm
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
# Built EXE: keep everything in ONE tidy data folder next to the .exe instead of
# scattering config/caches/output loose beside it (e.g. all over the Desktop).
if getattr(sys, 'frozen', False):
    _exe_dir = os.path.dirname(sys.executable)
    _cfg_dir = os.path.join(_exe_dir, "ExileBot2PickitGenerator_data")
    os.makedirs(_cfg_dir, exist_ok=True)
    # One-time migration: move loose files from older versions into the data folder.
    for _name in ("pickit_gui_config.json", "wiki_icon_cache.json", "pickit_output",
                  "icon_cache", "presets", "price_cache", "latest.ipd"):
        _src = os.path.join(_exe_dir, _name)
        _dst = os.path.join(_cfg_dir, _name)
        if os.path.exists(_src) and not os.path.exists(_dst):
            try:
                shutil.move(_src, _dst)
            except Exception:
                pass
else:
    _cfg_dir = os.path.dirname(os.path.abspath(__file__))

CONFIG_PATH      = os.path.join(_cfg_dir, "pickit_gui_config.json")
OUTPUT_DIR       = os.path.join(_cfg_dir, "pickit_output")
ICON_DIR         = os.path.join(_cfg_dir, "icon_cache")
PRICE_CACHE_DIR  = os.path.join(_cfg_dir, "price_cache")
WIKI_CACHE_FILE  = os.path.join(_cfg_dir, "wiki_icon_cache.json")
for _d in (_cfg_dir, OUTPUT_DIR, ICON_DIR):
    os.makedirs(_d, exist_ok=True)

# ── Debug log ─────────────────────────────────────────────────────────────────
# The GUI swallows many background errors (icon fetches, network, file I/O) so the
# UI never crashes — but that also hid real bugs (e.g. the v2.6.0 icon crash). This
# rotating file log gives those silenced exceptions a breadcrumb. Open it from the
# Debug tab. Call log_exc("context") from inside an `except` block.
import logging
from logging.handlers import RotatingFileHandler

LOG_PATH = os.path.join(_cfg_dir, "debug.log")
logger = logging.getLogger("pickit")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    try:
        _lh = RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2, encoding="utf-8")
        _lh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(_lh)
    except Exception:
        logger.addHandler(logging.NullHandler())

def log_exc(context: str = ""):
    """Log the currently-handled exception (call from inside an `except`)."""
    try:
        logger.exception("EXC %s", context)
    except Exception:
        pass

def log_info(msg: str):
    try:
        logger.info(msg)
    except Exception:
        pass

log_info(f"=== app start (v{'?'}) cfg_dir={_cfg_dir} ===")

# Point the generator's offline cache at a local folder so prices survive
# restarts and can be reused when poe.ninja is unreachable.
gen.set_disk_cache_dir(PRICE_CACHE_DIR)

# Prune cache files older than 60 days on startup so stale league data
# from previous seasons doesn't accumulate indefinitely.
try:
    _pruned = gen.prune_disk_cache(max_age_days=60)
    if _pruned:
        log_info(f"prune_disk_cache: removed {_pruned} stale file(s)")
except Exception:
    pass


def _default_poe2_filter_dir() -> str:
    """Best-guess location of the PoE2 client loot-filter folder."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Documents", "My Games", "Path of Exile 2"),
        os.path.join(home, "OneDrive", "Documents", "My Games", "Path of Exile 2"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]

DEFAULT_CONFIG = {
    "league": "",
    "min_exalt": 0.0,
    "min_exalt_gear": 0.0,
    "min_exalt_unique": 0.0,
    "output_base": "poe2_pickit",
    "bot_folder": "",
    "auto_copy": False,
    "backup_count": 5,
    "category_enabled": {},
    "category_threshold": {},
    "history": [],

    "window_geometry": "",
    "confirm_overwrite_secs": 120,
    "auto_schedule": True,
    "include_bases": True,
    "base_quality": 28,
    "base_min_level": gen.CRAFT_BASE_MIN_ILVL,
    "item_states":  {},
    "cat_prev_prices": {},
    "last_gen_prices": {},
    "profiles": {},
    "active_profile": "",

    "copy_filter_to_game": True,
    "poe2_filter_dir": "",
}

def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data)
        # Migrate: the base-type item-level floor used to be silently ignored, so
        # the old default (75) never filtered. Bump it to the endgame default (82)
        # so high-ilvl crafting bases are kept and low-level white junk isn't.
        if cfg.get("base_min_level") == 75:
            cfg["base_min_level"] = gen.CRAFT_BASE_MIN_ILVL
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

from ui_common import *   # shared UI toolkit (colours, fonts, widgets, _SegBar, sparkline)
from tab_chance_bases import ChanceBasesTab
from tab_craft_bases import CraftBasesTab


# ══════════════════════════════════════════════════════════════════════════════
#  Main Application
# ══════════════════════════════════════════════════════════════════════════════

TABS = ["Generate", "Items", "Chance Bases", "Craft Bases", "Preview", "History", "Settings", "Debug"]

VERSION       = "2.6.16"
GITHUB_REPO   = "c4Luffy/poe2-pickit-generator"
VERSION_URL   = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version.txt"
RELEASES_URL  = f"https://github.com/{GITHUB_REPO}/releases"

# Built-in icon URLs (official PoE CDN) for items poe2wiki can't resolve via the
# usual "File:<name> inventory icon.png" lookup, so they still show an icon in the
# app. Seeded into the wiki icon cache on startup — only fills blanks, so a real
# resolved/cached URL always wins. Add new "item name": "url" entries as needed.
BUILTIN_ICON_URLS = {
    "Simulacrum": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvTWFwcy9EZWxpcml1bUZyYWdtZW50Iiwic2NhbGUiOjEsInJlYWxtIjoicG9lMiJ9XQ/9298d81279/DeliriumFragment.png",
    # Zarokh's Reliquary Key — appears under both a short and a full name in
    # poe.ninja data; key both so the icon resolves either way.
    "Against the Darkness": "https://web.poecdn.com/gen/image/WzI4LDE0LHsiZiI6IjJESXRlbXMvTWFwcy9Ud2lsaWdodE9yZGVyUmVsaXF1YXJ5S2V5U2FuY3R1bTIiLCJzY2FsZSI6MSwicmVhbG0iOiJwb2UyIn1d/67f96bbfc0/TwilightOrderReliquaryKeySanctum2.png",
    "Zarokh's Reliquary Key: Against the Darkness": "https://web.poecdn.com/gen/image/WzI4LDE0LHsiZiI6IjJESXRlbXMvTWFwcy9Ud2lsaWdodE9yZGVyUmVsaXF1YXJ5S2V5U2FuY3R1bTIiLCJzY2FsZSI6MSwicmVhbG0iOiJwb2UyIn1d/67f96bbfc0/TwilightOrderReliquaryKeySanctum2.png",
    # Lineage support gem (poe2db art MorrigansRefuge). Note the accented "ó".
    "Mórrigan's Insight": "https://web.poecdn.com/gen/image/WzI1LDE0LHsiZiI6IjJESXRlbXMvR2Vtcy9OZXcvTmV3U3VwcG9ydC9MaW5lYWdlL01vcnJpZ2Fuc1JlZnVnZSIsInNjYWxlIjoxLCJyZWFsbSI6InBvZTIifV0/38291028f0/MorrigansRefuge.png",
}


class PickitApp(tk.Tk, ChanceBasesTab, CraftBasesTab):
    def __init__(self):
        super().__init__()
        log_info(f"PickitApp init (v{VERSION})")
        self.cfg = load_config()

        # ── DPI scale factor ──────────────────────────────────────────────────
        # The process is DPI-aware (see _enable_dpi_awareness), so Tk renders at
        # native resolution and auto-scales point-based fonts. Fixed *pixel* sizes
        # (window geometry, the category sidebar, ttk row height/padding) do NOT
        # auto-scale, so multiply them by this factor to keep the layout in
        # proportion with the text.  1.0 @100%, 1.5 @150%, 2.5 @250%.
        try:
            scale = self.winfo_fpixels("1i") / 96.0
        except Exception:
            scale = 1.0
        scale = max(1.0, min(scale, 3.0))
        self._ui_scale = scale

        setup_styles(self, scale)

        self.title(f"ExileBot 2 Pickit Generator  v{VERSION}")
        # App icon (titlebar + taskbar). Bundled into the .exe via --add-data;
        # when run from source it sits next to this script.
        try:
            _icon_dir = getattr(sys, "_MEIPASS",
                                os.path.dirname(os.path.abspath(__file__)))
            _icon = os.path.join(_icon_dir, "appicon.ico")
            if os.path.exists(_icon):
                self.iconbitmap(default=_icon)
        except Exception:
            log_exc("set window icon")
        self.configure(bg=BG)
        self.resizable(True, True)

        base_w, base_h = 1020, 780
        self.minsize(int(900 * scale), int(640 * scale))

        # Clamp the default size to the usable screen so it never opens off-screen.
        scr_w = self.winfo_screenwidth()
        scr_h = self.winfo_screenheight()
        win_w = min(int(base_w * scale), scr_w - 40)
        win_h = min(int(base_h * scale), scr_h - 80)

        saved_geo = self.cfg.get("window_geometry", "")
        if saved_geo and self._geo_fits(saved_geo, scr_w, scr_h):
            self.geometry(saved_geo)
        else:
            self.geometry(f"{win_w}x{win_h}")

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


    # ── Variable init ─────────────────────────────────────────────────────────

    def _init_vars(self):
        self.league_var       = tk.StringVar(value=self.cfg.get("league") or "")
        self.min_exalt_var      = tk.DoubleVar(value=self.cfg.get("min_exalt", 0.0))
        self.min_exalt_gear_var = tk.DoubleVar(value=self.cfg.get("min_exalt_gear", 0.0))
        self.min_exalt_unique_var = tk.DoubleVar(value=self.cfg.get("min_exalt_unique", 0.0))
        self.output_var       = tk.StringVar(value=self.cfg.get("output_base", "poe2_pickit"))
        self.bot_folder_var   = tk.StringVar(value=self.cfg.get("bot_folder", ""))
        self.auto_copy_var    = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        self.copy_filter_var  = tk.BooleanVar(value=self.cfg.get("copy_filter_to_game", True))
        self.poe2_filter_dir_var = tk.StringVar(
            value=self.cfg.get("poe2_filter_dir") or _default_poe2_filter_dir())
        self.backup_count_var = tk.IntVar(value=self.cfg.get("backup_count", 5))
        self.confirm_ovw_var  = tk.BooleanVar(value=self.cfg.get("confirm_overwrite_secs", 120) > 0)
        self.auto_schedule_var = tk.BooleanVar(value=self.cfg.get("auto_schedule", True))

        self.include_bases_var  = tk.BooleanVar(value=True)
        self.base_quality_var   = tk.IntVar(value=self.cfg.get("base_quality", 28))
        self.base_min_level_var = tk.IntVar(value=self.cfg.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))

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
        self._last_gen_prices  = dict(self.cfg.get("last_gen_prices", {}))  # {league: {key: {name: ex}}}
        self._price_alerts: list = []

        # Output profiles — named bundles of {item_states, thresholds, output name}
        self._profiles = dict(self.cfg.get("profiles", {}))
        self._profile_var = tk.StringVar(value=self.cfg.get("active_profile", ""))

        # Chance Bases tab state
        self._chance_cards     = []
        self._chance_count_var = tk.StringVar(value="")
        self._chance_canvas    = None
        self._chance_frame     = None

        # Craft Bases tab state
        self._craftbase_cards     = []
        self._craftbase_count_var = tk.StringVar(value="")
        self._craftbase_canvas    = None
        self._craftbase_frame     = None

        # Sidebar badge labels {cat_key: tk.Label}
        self._cat_sidebar_badges: dict = {}

        # Preload state
        self._preload_league   = ""
        self._preload_done_count = 0
        self._preload_total    = 0

        # Last generate summary stats (populated after each run)
        self._last_gen_stats: dict = {}

        # Wiki icon URL cache. Guarded by a lock because several
        # _resolve_wiki_icons worker threads can run at once — without it, one
        # thread's json.dump could iterate the dict while another mutates it
        # ("dictionary changed size during iteration").
        self._wiki_cache_lock = threading.Lock()
        self._wiki_icon_cache = {}
        if os.path.exists(WIKI_CACHE_FILE):
            try:
                with open(WIKI_CACHE_FILE, encoding="utf-8") as _f:
                    self._wiki_icon_cache = json.load(_f)
            except Exception:
                pass
        # poe.ninja's image CDN is dead (404s), so any cached poe.ninja icon URL is
        # useless — drop them so those items re-resolve against poe2wiki instead.
        self._wiki_icon_cache = {
            n: u for n, u in self._wiki_icon_cache.items() if u and "poe.ninja" not in u
        }
        # Seed built-in icon URLs for items poe2wiki can't resolve (e.g. Simulacrum).
        # Only fill blanks so a real resolved/cached URL always takes precedence.
        for _n, _u in BUILTIN_ICON_URLS.items():
            if not self._wiki_icon_cache.get(_n):
                self._wiki_icon_cache[_n] = _u

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
            b.bind("<Enter>",    lambda e, w=b, idx=i: w.configure(fg=TEXT) if self._cur_tab != idx else None)
            b.bind("<Leave>",    lambda e, w=b, idx=i: w.configure(fg=TEXT_DIM) if self._cur_tab != idx else None)
            self._tab_btns.append(b)

        sep(self).pack(fill="x")

        # Page container
        self._container = tk.Frame(self, bg=BG)
        self._container.pack(fill="both", expand=True)

        # Build pages. Generate/Items/Preview/History are built up front because
        # startup tasks (league preload, badges) and background generates touch
        # them; the rest are built lazily on first open for a faster launch.
        self._tab_builders = [
            self._build_generate_page,
            self._build_categories_page,
            self._build_chance_page,
            self._build_craftbase_page,
            self._build_preview_page,
            self._build_history_page,
            self._build_settings_page,
            self._build_debug_page,
        ]
        _eager = {0, 1, 4, 5}   # Generate, Items, Preview, History
        self._pages = []
        self._tab_built = []
        for i, builder in enumerate(self._tab_builders):
            page = tk.Frame(self._container, bg=BG)
            self._pages.append(page)
            if i in _eager:
                self._building_tab_idx = i
                builder(page)
                self._tab_built.append(True)
            else:
                self._tab_built.append(False)
        self._building_tab_idx = None

        self._cur_tab = -1
        self._show_tab(0)

    def _show_tab(self, idx):
        # Lazy-build the page's content the first time it's opened.
        if not self._tab_built[idx]:
            self._building_tab_idx = idx
            self._tab_builders[idx](self._pages[idx])
            self._building_tab_idx = None
            self._tab_built[idx] = True
        for i, page in enumerate(self._pages):
            if i == idx:
                page.pack(fill="both", expand=True)
            else:
                page.pack_forget()
        for i, b in enumerate(self._tab_btns):
            if i == idx:
                b.configure(bg=BG3, fg=GOLD)
            else:
                b.configure(bg=BG2, fg=TEXT_DIM)
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
                val_lbl.configure(text=fmt.format(snapped))
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
            command=lambda v: val_lbl.configure(text=fmt.format(float(v))),
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
                val_lbl.configure(text=fmt.format(new_val))
            except (tk.TclError, ValueError):
                pass

        def _on_wheel_up(event):
            try:
                new_val = max(from_, min(to, var.get() + resolution))
                var.set(new_val)
                val_lbl.configure(text=fmt.format(new_val))
            except (tk.TclError, ValueError):
                pass

        def _on_wheel_down(event):
            try:
                new_val = max(from_, min(to, var.get() - resolution))
                var.set(new_val)
                val_lbl.configure(text=fmt.format(new_val))
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
            "Select your league, choose an output filename, then click ⚡ Generate.  "
            "The tool fetches live prices from poe.ninja and picks everything by default.  "
            "Use the Items tab to exclude specific items you don't want the bot to pick up.")
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
            new_league = self._selected_league() or ""
            # Reset all sidebar badges since we're switching leagues
            for k in self._cat_sidebar_badges:
                self._update_sidebar_badge(k)
            # Clear preload state so the new league gets preloaded fresh
            self._preload_league = ""
            self._preload_done_count = 0
            self._preload_update_hdr()
            # Refresh active category and start preloading the new league
            if self._active_cat and self._active_cat != "_gear":
                self.after(50, lambda: self._show_cat(self._active_cat))
            self.after(100, lambda: self._preload_all_cats_async(new_league))
            self.after(150, self._update_unique_conv)

        self.league_cb.bind("<<ComboboxSelected>>", _on_league_select)
        self.league_cb.bind("<Return>", _on_league_select)

        # ── Profiles ─────────────────────────────────────────────────────────
        secp = self._section_frame(inner, "Profile")
        label(secp, "Switch between saved setups — e.g. a \"Farmer\" profile and a \"Boss runner\" "
                    "profile, each with its own item selections, price floors and output file.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 2))
        prow = tk.Frame(secp, bg=BG2)
        prow.pack(fill="x", padx=10, pady=(4, 10))
        prow.columnconfigure(0, weight=1)
        self.profile_cb = ttk.Combobox(prow, textvariable=self._profile_var,
                                       state="readonly", font=FONT, values=[])
        self.profile_cb.grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        self.profile_cb.bind("<<ComboboxSelected>>", lambda e: self._profile_switch())
        btn(prow, "Save",   self._profile_save_current).grid(row=0, column=1, padx=(0, 4))
        btn(prow, "Delete", self._profile_delete).grid(row=0, column=2)
        self._refresh_profile_dropdown()

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

        # ── Unique gear value floor ───────────────────────────────────────────
        secu = self._section_frame(inner, "Unique Gear — Minimum Value")
        label(secu, "Only pick up unique items worth at least this much.  The value is in "
                    "Exalt, which already accounts for Divine and Chaos prices (every item's "
                    "price is converted to its Exalt equivalent before comparing).  Set to 0 to "
                    "pick up every unique.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2, wraplength=820, justify="left").pack(
                  anchor="w", padx=10, pady=(8, 2))
        urow = tk.Frame(secu, bg=BG2)
        urow.pack(fill="x", padx=10, pady=(2, 2))
        self._make_slider(urow, self.min_exalt_unique_var,
                          from_=0, to=1000, resolution=5,
                          fmt="{:.0f} ex", width=int(320 * self._ui_scale)).pack(side="left")
        self._unique_conv_lbl = label(secu, "", fg=GOLD, font=FONT_SM, bg=BG2)
        self._unique_conv_lbl.pack(anchor="w", padx=10, pady=(0, 10))
        self.min_exalt_unique_var.trace_add("write", self._on_unique_floor_change)
        self.after(300, self._update_unique_conv)

        # ── Exchange / non-unique gear value floor ───────────────────────────
        secg = self._section_frame(inner, "Exchange & Gear — Minimum Value")
        label(secg, "Only pick up exchange items (essences, fragments, etc.) and non-unique "
                    "gear bases worth at least this much in Exalt. Set to 0 to pick up everything.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2, wraplength=820, justify="left").pack(
                  anchor="w", padx=10, pady=(8, 2))
        grow = tk.Frame(secg, bg=BG2)
        grow.pack(fill="x", padx=10, pady=(2, 10))
        self._make_slider(grow, self.min_exalt_gear_var,
                          from_=0, to=500, resolution=5,
                          fmt="{:.0f} ex", width=int(320 * self._ui_scale)).pack(side="left")
        self.min_exalt_gear_var.trace_add("write", self._clamp_threshold_gear)

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
        self.open_ipd_btn.configure(state="disabled")

        self.open_filter_btn = btn(btn_f, "Open .filter", lambda: self._open_file(".filter"))
        self.open_filter_btn.pack(side="left", padx=(6, 0))
        self.open_filter_btn.configure(state="disabled")

        btn(btn_f, "Open output folder", self._open_output_folder).pack(side="left", padx=(6, 0))

        # ── API status banner (hidden unless poe.ninja was unreachable) ───────
        self.api_banner = tk.Label(
            inner, text="", bg="#3a2a1a", fg="#e8b84b", font=FONT_SM,
            anchor="w", padx=12, pady=6, justify="left")
        # not packed yet — shown only when offline_mode is set

        # ── Progress ─────────────────────────────────────────────────────────
        self.progress_var = tk.StringVar(value="")
        self.progress_lbl = tk.Label(inner, textvariable=self.progress_var,
                                     bg=BG, fg=TEXT_INFO, font=FONT_SM)
        self.progress_lbl.pack(anchor="w", padx=10, pady=(6, 0))
        self._seg_bar = _SegBar(inner, bar_height=10)
        self._seg_bar.pack(fill="x", padx=10, pady=(4, 0))
        self._seg_bar.pack_forget()   # hidden until generate starts

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

        # ── Post-generate summary card ────────────────────────────────────────
        self._gen_summary = tk.Frame(inner, bg=BG2, highlightthickness=1,
                                     highlightbackground=GOLD)
        # row 1: main stat line
        r1 = tk.Frame(self._gen_summary, bg=BG2)
        r1.pack(fill="x", padx=16, pady=(14, 4))
        self._sum_vars = {}
        for key, default in (
            ("check",    "✓"),
            ("duration", ""),
            ("dot1",     "  ·  "),
            ("rules",    ""),
            ("dot2",     "  ·  "),
            ("fsize",    ""),
        ):
            fg = TEXT_OK if key == "check" else (TEXT_DIM if key.startswith("dot") else TEXT)
            lbl = tk.Label(r1, text=default, bg=BG2, fg=fg,
                           font=("Segoe UI", 14, "bold"))
            lbl.pack(side="left")
            self._sum_vars[key] = lbl
        # row 2: top item line
        r2 = tk.Frame(self._gen_summary, bg=BG2)
        r2.pack(fill="x", padx=16, pady=(0, 12))
        tk.Label(r2, text="⚡", bg=BG2, fg=GOLD, font=("Segoe UI", 12)).pack(side="left")
        self._sum_top_lbl = tk.Label(r2, text="", bg=BG2, fg=GOLD, font=("Segoe UI", 12))
        self._sum_top_lbl.pack(side="left", padx=(4, 0))
        tk.Label(r2, text="  ·  ", bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 12)).pack(side="left")
        self._sum_cats_lbl = tk.Label(r2, text="", bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 12))
        self._sum_cats_lbl.pack(side="left")
        # row 3: biggest price movers (populated dynamically, hidden if none)
        self._sum_alerts_frame = tk.Frame(self._gen_summary, bg=BG2)
        self._gen_summary.pack_forget()  # hidden until first generate

        # The verbose generate Log was removed from this tab — progress shows in
        # the progress bar + summary box (full diagnostics live on the Debug tab).
        # _log() / _log_clear() no-op safely when log_text is None.
        self.log_text = None
        # bottom spacer so the last section isn't flush against the window edge
        tk.Frame(inner, bg=BG, height=8).pack(fill="x")

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

    def _on_unique_floor_change(self, *_):
        """Keep the unique-gear floor in cfg (so it survives restart) and refresh
        the divine/chaos readout under the slider."""
        try:
            self.cfg["min_exalt_unique"] = float(self.min_exalt_unique_var.get())
        except (tk.TclError, ValueError):
            pass
        self._update_unique_conv()

    def _update_unique_conv(self, *_):
        """Show the unique-gear floor's Divine and Chaos equivalents under the slider."""
        lbl = getattr(self, "_unique_conv_lbl", None)
        if lbl is None:
            return
        try:
            ex = float(self.min_exalt_unique_var.get())
        except (tk.TclError, ValueError):
            return
        if ex <= 0:
            lbl.configure(text="Picking up every unique (no value floor).")
            return
        league   = self._selected_league() or ""
        div_rate = self._get_divine_rate(league)      # ex per 1 divine (1.0 if no data)
        chaos_ex = self._get_chaos_ex_value(league)   # ex per 1 chaos  (0.0 if no data)
        parts = []
        if div_rate and div_rate > 1.0:
            parts.append(f"{ex / div_rate:.2f} divine")
        if chaos_ex and chaos_ex > 0:
            parts.append(f"~{ex / chaos_ex:.0f} chaos")
        if parts:
            lbl.configure(text="≈  " + "    ·    ".join(parts))
        else:
            lbl.configure(text="(Divine / Chaos equivalents shown once prices load)")

    # ══════════════════════════════════════════════════════════════════════════
    #  CATEGORIES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_categories_page(self, page):
        """Card-based category browser. Sidebar = categories, right = item grid."""
        # ── Horizontal split: sidebar | content ───────────────────────────────
        # Fixed pixel width with pack_propagate(False) won't auto-scale on high-DPI
        # monitors, so widen it by the DPI factor or category names get clipped.
        sidebar = tk.Frame(page, bg=_CBAR, width=int(168 * self._ui_scale))
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

        # Row 1 — item actions: search, enable/disable, min filter, value unit
        tbar = tk.Frame(right, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 2))

        tk.Label(tbar, text="Search:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        entry(tbar, self._cat_search_var, width=16).pack(side="left", padx=(4, 10), ipady=3)

        btn(tbar, "Enable All",  lambda: self._cat_items_set_all(True)).pack(side="left", padx=(0, 3))
        btn(tbar, "Disable All", lambda: self._cat_items_set_all(False)).pack(side="left", padx=(0, 3))
        btn(tbar, "Reset",       self._cat_items_reset).pack(side="left", padx=(0, 8))

        # Row 2 — value unit + refresh (right)
        tbar2 = tk.Frame(right, bg=BG)
        tbar2.pack(fill="x", padx=10, pady=(0, 4))

        # Refresh = rightmost; pack it first so side="right" anchors it to the edge
        self._refresh_btn = btn(tbar2, "↻ Refresh", self._refresh_cat_prices)
        self._refresh_btn.pack(side="right", padx=(0, 4))

        # Price unit selector — right side of row 2, just left of Refresh
        val_f = tk.Frame(tbar2, bg=BG)
        val_f.pack(side="right", padx=(0, 10))
        tk.Label(val_f, text="Value:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(0, 4))
        for unit_key, unit_label in (("ex", "Exalt"), ("chaos", "Chaos"), ("div", "Divine")):
            ub = tk.Button(val_f, text=unit_label,
                           bg=BG3, fg=TEXT_DIM, activebackground=BORDER,
                           activeforeground=TEXT, relief="flat", bd=1,
                           font=FONT_SM, padx=7, pady=2,
                           command=lambda u=unit_key: self._set_price_unit(u))
            ub.pack(side="left", padx=1)
            self._price_unit_btns[unit_key] = ub
        self._update_price_unit_btns()

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
        self._cat_sidebar_hdr = tk.Label(sidebar, text="CATEGORIES",
                 bg=_CBAR, fg=GOLD, font=("Segoe UI", 8, "bold"), pady=8)
        self._cat_sidebar_hdr.pack(fill="x")
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

        lbl = tk.Label(frame, text=text, bg=_CBTN, fg=TEXT_DIM,
                       font=("Segoe UI", 9), anchor="w", padx=12, pady=7)
        lbl.pack(side="left", fill="x", expand=True)

        badge = tk.Label(frame, text="", bg=_CBTN, fg="#555568",
                         font=("Segoe UI", 7), padx=6, pady=7, anchor="e")
        badge.pack(side="right")
        self._cat_sidebar_badges[key] = badge

        def _enter(e=None):
            if self._active_cat != key:
                bg = _CHOV
                frame.configure(bg=bg); lbl.configure(bg=bg); badge.configure(bg=bg)
        def _leave(e=None):
            if self._active_cat != key:
                bg = _CBTN
                frame.configure(bg=bg); lbl.configure(bg=bg); badge.configure(bg=bg)
        def _click(e=None):
            self._show_cat(key)

        for w in (frame, lbl, badge):
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
            old.configure(bg=_CBTN)
            for c in old.winfo_children():
                c.configure(bg=_CBTN)
                if isinstance(c, tk.Label):
                    c.configure(fg=TEXT_DIM)

        self._active_cat = key

        # Highlight selected button
        if key in self._cat_sidebar_btns:
            bf = self._cat_sidebar_btns[key]
            bf.configure(bg=_CSEL)
            for c in bf.winfo_children():
                c.configure(bg=_CSEL)
                if isinstance(c, tk.Label):
                    c.configure(fg=_CSFG)

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
                self._cat_loading_lbl.configure(text=f"Loading {lbl_text}…")
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
        self._refresh_btn.configure(state="disabled", text="Refreshing…")
        self._show_cat(key)

    def _refresh_btn_ready(self):
        if hasattr(self, "_refresh_btn"):
            self._refresh_btn.configure(state="normal", text="↻ Refresh")

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
            self.after(0, lambda msg=str(exc): self._cat_count_var.set(f"Failed: {msg}"))
            self.after(0, self._refresh_btn_ready)

    # ── Background preloader ──────────────────────────────────────────────────

    def _preload_all_cats_async(self, league: str):
        """Warm the poe.ninja cache for every exchange category in the background.

        Called after league is determined so clicking any sidebar tab is instant.
        A second call for the same league is a no-op (already cached / in flight).
        """
        if not league or league.startswith("Loading"):
            return
        if league == self._preload_league:
            return   # already fetched or in-flight for this league
        self._preload_league    = league
        self._preload_done_count = 0
        self._preload_total     = len(gen.ALL_CATEGORIES)
        self.after(0, self._preload_update_hdr)
        threading.Thread(target=self._preload_worker, args=(league,), daemon=True).start()

    def _preload_worker(self, league: str):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        cats = gen.ALL_CATEGORIES

        def _fetch_one(item):
            k, ninja_type, _, is_unique = item
            p = gen.fetch_category(league, k, ninja_type, is_unique)
            gen._cache_set(league, k, p)
            return k

        with ThreadPoolExecutor(max_workers=6) as ex:
            futures = {ex.submit(_fetch_one, c): c[0] for c in cats}
            for fut in as_completed(futures):
                key = futures[fut]
                try:
                    fut.result()
                except Exception:
                    log_exc(f"preload {key}")
                # Count + badge/header update both happen on the main thread, so the
                # counter is never touched off-thread (no race with the reset above).
                self.after(0, lambda k=key: self._on_preload_cat_ready(k))

        # All done
        self.after(0, self._on_preload_complete)

    def _on_preload_cat_ready(self, key: str):
        """Called on main thread when one category's data arrives."""
        self._preload_done_count += 1
        self._update_sidebar_badge(key)
        self._preload_update_hdr()
        # If this is the tab the user is already looking at (still showing spinner),
        # render it immediately now that we have the data
        if self._active_cat == key and not self._cat_cards.get(key):
            league  = self._selected_league() or "Mercenaries"
            payload = gen._cache_get(league, key)
            if payload and not isinstance(payload, Exception):
                self._populate_cat_grid(key, payload)

    def _on_preload_complete(self):
        self._preload_update_hdr()

    def _preload_update_hdr(self):
        done  = self._preload_done_count
        total = self._preload_total
        if not hasattr(self, "_cat_sidebar_hdr"):
            return
        if done >= total and total > 0:
            self._cat_sidebar_hdr.configure(text="CATEGORIES  ✓", fg=TEXT_OK)
        elif total > 0:
            self._cat_sidebar_hdr.configure(
                text=f"CATEGORIES  {done}/{total}", fg=TEXT_WARN)
        else:
            self._cat_sidebar_hdr.configure(text="CATEGORIES", fg=GOLD)

    # ── Item grid population ──────────────────────────────────────────────────

    def _clear_cat_grid(self):
        # Invalidate any in-flight chunked render (bump the generation counter) so
        # its queued ticks stop adding cards to the grid we're about to rebuild,
        # then drop its pending callback before destroying the old widgets.
        self._cat_render_seq = getattr(self, "_cat_render_seq", 0) + 1
        aid = getattr(self, "_cat_render_after", None)
        if aid is not None:
            try:
                self.after_cancel(aid)
            except Exception:
                pass
            self._cat_render_after = None
        for w in self._cat_grid_frame.winfo_children():
            w.destroy()

    def _populate_cat_grid(self, key, payload):
        if self._active_cat != key:
            return
        self._cat_loading_lbl.place_forget()
        self._clear_cat_grid()

        items_by_id   = {i["id"]: i for i in payload.get("items", [])}
        rate          = gen.exalted_rate(payload)
        league        = self._selected_league() or "Mercenaries"
        div_rate      = self._get_divine_rate(league)
        chaos_ex_val  = self._get_chaos_ex_value(league)  # ex value of 1 chaos

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
            # Convert ex → chaos: how many chaos does this item cost?
            # (primaryValue is in Divine units in POE2 API, not chaos)
            chaos = ex / chaos_ex_val if chaos_ex_val else ex
            raw_img = item.get("image") or item.get("icon") or ""
            spark_raw = line.get("sparkline") or {}
            sparkline = [float(v) for v in (spark_raw.get("data") or []) if v is not None]
            rows.append((name, chaos, ex, div_rate, self._decode_ninja_image(raw_img), sparkline))

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
            # Price sort, direction from the Items toolbar (High→Low default).
            rows.sort(key=lambda r: -r[2])   # price High -> Low (default, no UI control)

        # Save previous prices for trend arrows, then cache new prices
        self._cat_prev_prices[key] = {
            name: p["ex"] for name, p in self._item_prices.get(key, {}).items()
        }
        self._item_prices[key] = {
            name: {"ex": ex, "chaos": chaos, "div": (ex / div_rate if div_rate else 0.0)}
            for name, chaos, ex, div_rate, _, _sp in rows
        }

        if key not in self._item_states:
            self._item_states[key] = {}
        states = self._item_states[key]

        NCOLS = 3
        self._cat_cards[key] = []

        # ── Build a placement plan (grid positions only, no widgets yet) ──────
        # Widgets are created lazily in background chunks below, so opening a big
        # category (e.g. Gear & Bases, ~200 items) never freezes the UI. Each
        # entry is ("header", text, grid_row) or ("card", row_tuple, grid_row, col).
        placements = []
        if key == "uncut_gems":
            _GEM_LABELS = {"Support": "Uncut Support Gems",
                           "Spirit":  "Uncut Spirit Gems",
                           "Skill":   "Uncut Skill Gems"}
            _GEM_TYPE_ORDER = {"Support": 0, "Spirit": 1, "Skill": 2}
            grid_row = 0
            col = 0
            current_type = None
            for row in rows:
                name = row[0]
                gem_type = None
                for t in _GEM_TYPE_ORDER:
                    if f"Uncut {t} Gem" in name:
                        gem_type = t
                        break
                if gem_type != current_type:
                    if col != 0:
                        grid_row += 1
                        col = 0
                    placements.append(("header", _GEM_LABELS.get(gem_type, gem_type), grid_row))
                    grid_row += 1
                    current_type = gem_type
                placements.append(("card", row, grid_row, col))
                col += 1
                if col >= NCOLS:
                    col = 0
                    grid_row += 1
        elif key == "expedition":
            grid_row = 0
            col = 0
            shown_flux_hdr = False
            for row in rows:
                if "Thaumaturgic Flux" in row[0] and not shown_flux_hdr:
                    if col != 0:
                        grid_row += 1
                        col = 0
                    placements.append(("header", "Thaumaturgic Flux", grid_row))
                    grid_row += 1
                    shown_flux_hdr = True
                placements.append(("card", row, grid_row, col))
                col += 1
                if col >= NCOLS:
                    col = 0
                    grid_row += 1
        else:
            for i, row in enumerate(rows):
                r_, c_ = divmod(i, NCOLS)
                placements.append(("card", row, r_, c_))

        for c_ in range(NCOLS):
            self._cat_grid_frame.columnconfigure(c_, weight=1, uniform="catcol")

        self._cat_last_fetched[key] = datetime.datetime.now().strftime("%H:%M")
        self._cat_canvas.yview_moveto(0)

        # ── Render the placements in background chunks (first chunk now, rest via
        #    after() so the UI stays responsive). seq guards against a category
        #    switch / search starting a newer render mid-flight (see _clear_cat_grid).
        seq   = self._cat_render_seq
        CHUNK = 24

        def _render_chunk(start=0):
            if seq != self._cat_render_seq or self._active_cat != key:
                return  # superseded by a newer populate/search/clear — abort
            end = min(start + CHUNK, len(placements))
            for p in placements[start:end]:
                if p[0] == "header":
                    _, text, grow = p
                    hdr = tk.Frame(self._cat_grid_frame, bg="#16141a")
                    tk.Label(hdr, text=text, bg="#16141a", fg=GOLD,
                             font=("Segoe UI", 9, "bold"),
                             padx=8, pady=5, anchor="w").pack(fill="x")
                    hdr.grid(in_=self._cat_grid_frame, row=grow, column=0,
                             columnspan=3, padx=3, pady=(10, 2), sticky="ew")
                else:
                    _, (name, chaos, ex, _div_r, icon_url, sparkline), grow, gcol = p
                    div_val = ex / _div_r if _div_r else 0.0
                    enabled = states.get(name, {}).get("enabled", True)
                    trend   = self._price_trend(key, name, ex)
                    card = self._make_item_card(key, name, chaos, ex, div_val,
                                                icon_url, enabled, trend, sparkline)
                    card.grid(in_=self._cat_grid_frame, row=grow, column=gcol,
                              padx=3, pady=3, sticky="ew")
                    self._cat_cards[key].append(card)
            self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
            if end < len(placements):
                self._cat_render_after = self.after(1, lambda: _render_chunk(end))
            else:
                # All cards built — finalize counts and start icon loading now that
                # every card exists for _apply_icon to find by name.
                self._cat_render_after = None
                self._update_cat_count(key)
                self._refresh_btn_ready()
                threading.Thread(target=self._guarded,
                                 args=(self._resolve_wiki_icons, key, rows), daemon=True).start()

        _render_chunk(0)

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

        Two clear states:
          enabled  → bright card, gold ●  (item WILL be picked)
          disabled → gray card,   gray ✗  (item excluded — bot ignores it)
        Bonus: disabled + still above threshold → amber ✗ warning.
        """
        if enabled:
            return _CON, _CTXON, _CONB, "", GOLD
        thresh = self._effective_threshold(cat_key)
        if thresh > 0 and ex_val >= thresh:
            return _CWARN, _CTXWRN, _CWARNB, "✗", _CWARNB
        return _COFF, _CTXOF, _COFB, "✗", _CTXOF

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

    def _make_item_card(self, cat_key, name, chaos, ex_val, div_val, icon_url, enabled, trend="", sparkline=None):
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
        frame._arrow_lbl = arrow_lbl

        # Sparkline (7-day price chart)
        if sparkline and len(sparkline) >= 2:
            spark_cv = tk.Canvas(frame, width=52, height=18,
                                 bg=bg, bd=0, highlightthickness=0)
            spark_cv.pack(side="right", padx=(0, 4))
            spark_cv.after(20, lambda cv=spark_cv, d=sparkline: _draw_sparkline(cv, d, 52, 18))
            frame._spark_cv = spark_cv
        else:
            frame._spark_cv = None

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
        frame.configure(bg="#1e3a2a")
        for w in frame.winfo_children():
            try:
                w.configure(bg="#1e3a2a")
            except Exception:
                pass
        def _restore():
            frame.configure(bg=orig_bg)
            for w in frame.winfo_children():
                try:
                    w.configure(bg=orig_bg)
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
        frame.configure(bg=bg, highlightbackground=bdr)
        frame._name_lbl.configure(bg=bg, fg=fg)
        frame._icon_lbl.configure(bg=bg)
        frame._val_lbl.configure(bg=bg)
        frame._dot_lbl.configure(bg=bg, text=dot_txt, fg=dot_fg)
        if getattr(frame, "_arrow_lbl", None):
            frame._arrow_lbl.configure(bg=bg)
        if getattr(frame, "_spark_cv", None):
            frame._spark_cv.configure(bg=bg)

        self._update_cat_count(key)
        self.after(0, self._save_states_now)

    def _update_cat_count(self, key):
        cards   = self._cat_cards.get(key, [])
        enabled = sum(1 for c in cards if c._enabled)
        ts      = self._cat_last_fetched.get(key, "")
        suffix  = f"  ·  updated {ts}" if ts else ""
        self._cat_count_var.set(f"{enabled} / {len(cards)} enabled{suffix}")
        self._update_sidebar_badge(key)

    def _update_sidebar_badge(self, key):
        badge = self._cat_sidebar_badges.get(key)
        if not badge:
            return
        cards = self._cat_cards.get(key, [])
        if cards:
            # Rendered: show actual enabled/total count
            enabled = sum(1 for c in cards if c._enabled)
            total   = len(cards)
            color   = TEXT_OK if enabled == total else (TEXT_WARN if enabled > 0 else TEXT_ERR)
            badge.configure(text=f"{enabled}/{total}", fg=color)
        else:
            # Not rendered yet — check if data is cached and ready to go
            league = self._selected_league() or "Mercenaries"
            if gen._cache_get(league, key) is not None:
                badge.configure(text="●", fg=GOLD)   # cached, click to render
            else:
                badge.configure(text="", fg="#555568")  # not fetched yet

    # ── Price unit switching ──────────────────────────────────────────────────

    def _set_api_banner(self, offline: bool):
        """Show or hide the 'poe.ninja unreachable' banner on the Generate tab."""
        banner = getattr(self, "api_banner", None)
        if banner is None:
            return
        if offline:
            banner.configure(text="⚠  poe.ninja was unreachable — this pickit used cached prices. "
                               "They may be out of date. Try Force Refresh when the site is back up.")
            banner.pack(fill="x", padx=10, pady=(10, 0), before=self.progress_lbl)
        else:
            banner.pack_forget()

    @staticmethod
    def _geo_fits(geo: str, scr_w: int, scr_h: int) -> bool:
        """True if a saved 'WxH+X+Y' geometry sits within the current screen.
        Guards against a geometry saved on a larger/other-DPI monitor opening
        off-screen or oversized after a resolution or scaling change."""
        m = re.match(r"(\d+)x(\d+)(?:([+-]\d+)([+-]\d+))?", geo or "")
        if not m:
            return False
        w, h = int(m.group(1)), int(m.group(2))
        if w > scr_w or h > scr_h or w < 400 or h < 300:
            return False
        if m.group(3) is not None:
            x, y = int(m.group(3)), int(m.group(4))
            if x < -50 or y < -50 or x > scr_w - 100 or y > scr_h - 100:
                return False
        return True

    @staticmethod
    def _fmt_age(secs) -> str:
        """Human-readable age, e.g. '3m', '2h', '5d'."""
        try:
            secs = float(secs or 0)
        except (TypeError, ValueError):
            return "?"
        if secs < 90:
            return f"{int(secs)}s"
        if secs < 5400:
            return f"{int(secs / 60)}m"
        if secs < 172800:
            return f"{int(secs / 3600)}h"
        return f"{int(secs / 86400)}d"

    def _fmt_price(self, chaos, ex, div):
        unit = self._price_unit
        if unit == "chaos":
            if chaos >= 10:
                return f"{chaos:.0f}c"
            if chaos >= 0.1:
                return f"{chaos:.1f}c"
            return f"{chaos:.2f}c"
        if unit == "div":
            if div >= 10:
                return f"{div:.1f} div"
            if div >= 1:
                return f"{div:.2f} div"
            return f"{div:.3f} div"
        return f"{ex:.2f} ex"

    def _set_price_unit(self, unit):
        self._price_unit = unit
        self._update_price_unit_btns()
        key = self._active_cat
        if not key or key == "_gear":
            return
        for card in self._cat_cards.get(key, []) + self._cat_cards.get("_search", []):
            card._val_lbl.configure(text=self._fmt_price(card._chaos, card._ex, card._div))

    def _update_price_unit_btns(self):
        for unit, b in self._price_unit_btns.items():
            if unit == self._price_unit:
                b.configure(bg=GOLD, fg="#111")
            else:
                b.configure(bg=BG3, fg=TEXT_DIM)

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
        league    = self._selected_league() or "Mercenaries"

        for cat_key, _, cat_label, _ in gen.EXCHANGE_CATEGORIES:
            prices = self._item_prices.get(cat_key)
            if not prices:
                # Category not opened yet — derive prices from the cached payload
                # so global search covers everything the preloader has warmed.
                prices = self._prices_from_payload(gen._cache_get(league, cat_key), league)
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
            self._item_states.pop(key, None)
            bg = _CON; fg = _CTXON; bdr = _CONB; dot = ""; dfg = GOLD
            for card in self._cat_cards.get(key, []):
                card._enabled = True
                card.configure(bg=bg, highlightbackground=bdr)
                card._name_lbl.configure(bg=bg, fg=fg)
                card._icon_lbl.configure(bg=bg)
                card._val_lbl.configure(bg=bg)
                card._dot_lbl.configure(bg=bg, text=dot, fg=dfg)
                if getattr(card, "_spark_cv", None): card._spark_cv.configure(bg=bg)
        else:
            if key not in self._item_states:
                self._item_states[key] = {}
            bg = _COFF; fg = _CTXOF; bdr = _COFB; dot = "✗"; dfg = _CTXOF
            for card in self._cat_cards.get(key, []):
                card._enabled = False
                card.configure(bg=bg, highlightbackground=bdr)
                card._name_lbl.configure(bg=bg, fg=fg)
                card._icon_lbl.configure(bg=bg)
                card._val_lbl.configure(bg=bg)
                card._dot_lbl.configure(bg=bg, text=dot, fg=dfg)
                if getattr(card, "_spark_cv", None): card._spark_cv.configure(bg=bg)
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
            card.configure(bg=_CON, highlightbackground=_CONB)
            card._name_lbl.configure(bg=_CON, fg=_CTXON)
            card._icon_lbl.configure(bg=_CON)
            card._val_lbl.configure(bg=_CON)
            card._dot_lbl.configure(bg=_CON, text="", fg=GOLD)
            if getattr(card, "_spark_cv", None): card._spark_cv.configure(bg=_CON)
        self._update_cat_count(key)
        self.after(0, self._save_states_now)

    # ── Min price filter ──────────────────────────────────────────────────────

    def _extract_cat_prices(self, key: str, payload: dict) -> dict:
        """Return {name: chaos} from a raw poe.ninja payload, using cached rates."""
        league       = self._selected_league() or "Mercenaries"
        rate         = gen.exalted_rate(payload)
        chaos_ex_val = self._get_chaos_ex_value(league)
        items_by_id  = {i["id"]: i for i in payload.get("items", [])}
        prices = {}
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if not item or not item.get("name"):
                continue
            raw_name = item["name"]
            if raw_name in gen.ITEM_NAME_SKIP:
                continue
            name  = gen.ITEM_NAME_CORRECTIONS.get(raw_name, raw_name)
            pv    = float(line.get("primaryValue") or 0.0)
            ex    = pv * rate if rate else pv
            chaos = ex / chaos_ex_val if chaos_ex_val else ex
            prices[name] = chaos
        return prices

    # ── Output profiles ───────────────────────────────────────────────────────

    def _refresh_profile_dropdown(self):
        names = sorted(self._profiles.keys())
        self.profile_cb["values"] = names
        if self._profile_var.get() not in names:
            self._profile_var.set(names[0] if names else "")

    def _profile_snapshot(self) -> dict:
        """Capture the current setup as a profile bundle."""
        try:
            min_ex = float(self.min_exalt_var.get())
        except (tk.TclError, ValueError):
            min_ex = 0.0
        try:
            min_gear = float(self.min_exalt_gear_var.get())
        except (tk.TclError, ValueError):
            min_gear = 0.0
        try:
            min_unique = float(self.min_exalt_unique_var.get())
        except (tk.TclError, ValueError):
            min_unique = 0.0
        return {
            "item_states":      copy.deepcopy(self._item_states),
            "min_exalt":        min_ex,
            "min_exalt_gear":   min_gear,
            "min_exalt_unique": min_unique,
            "output_base":      self.output_var.get(),
        }

    def _profile_save_current(self):
        name = simpledialog.askstring(
            "Save Profile",
            "Profile name:\n(reusing an existing name overwrites it)",
            parent=self, initialvalue=self._profile_var.get())
        if not name:
            return
        name = name.strip()
        if not name:
            return
        self._profiles[name] = self._profile_snapshot()
        self._profile_var.set(name)
        self.cfg["profiles"]       = self._profiles
        self.cfg["active_profile"] = name
        save_config(self.cfg)
        self._refresh_profile_dropdown()
        messagebox.showinfo("Profile saved", f"Profile '{name}' saved.", parent=self)

    def _profile_switch(self):
        name = self._profile_var.get()
        prof = self._profiles.get(name)
        if not prof:
            return
        self._item_states = copy.deepcopy(prof.get("item_states", {}))
        self.min_exalt_var.set(prof.get("min_exalt", 0.0))
        self.min_exalt_gear_var.set(prof.get("min_exalt_gear", 0.0))
        self.min_exalt_unique_var.set(prof.get("min_exalt_unique", 0.0))
        self.output_var.set(prof.get("output_base", "poe2_pickit"))

        self.cfg["item_states"]    = self._item_states
        self.cfg["active_profile"] = name
        save_config(self.cfg)

        # Refresh the open category grid so the new selections show immediately
        key = self._active_cat
        if key and key != "_gear":
            payload = gen._cache_get(self._selected_league() or "Mercenaries", key)
            if payload and not isinstance(payload, Exception):
                self._populate_cat_grid(key, payload)
        for k in self._cat_sidebar_badges:
            self._update_sidebar_badge(k)

    def _profile_delete(self):
        name = self._profile_var.get()
        if not name or name not in self._profiles:
            return
        if not messagebox.askyesno("Delete profile",
                                   f"Delete profile '{name}'?", parent=self):
            return
        self._profiles.pop(name, None)
        self.cfg["profiles"] = self._profiles
        if self.cfg.get("active_profile") == name:
            self.cfg["active_profile"] = ""
        save_config(self.cfg)
        self._refresh_profile_dropdown()

    # ── Divine rate helper ────────────────────────────────────────────────────

    def _get_divine_rate(self, league):
        """Return the ex value of 1 Divine Orb (e.g. 248 ex)."""
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

    def _get_chaos_ex_value(self, league):
        """Return the ex value of 1 Chaos Orb (e.g. 24.4 ex).
        Used to convert item ex values → chaos: chaos = ex / chaos_ex_value.
        primaryValue in the POE2 exchange API is in Divine units, so we must
        convert through the exalted rate rather than treating pv as chaos."""
        payload = gen._cache_get(league, "currency")
        if not payload or isinstance(payload, Exception):
            return 0.0
        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        rate = gen.exalted_rate(payload)
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if item and item.get("name") == "Chaos Orb":
                pv = float(line.get("primaryValue") or 0.0)
                return pv * rate if rate else pv
        return 0.0

    def _prices_from_payload(self, payload, league):
        """Derive {name: {ex, chaos, div}} from a cached poe.ninja payload so
        global search can cover categories that haven't been rendered yet.
        Mirrors the price extraction in _populate_cat_grid."""
        if not payload or isinstance(payload, Exception):
            return {}
        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        rate     = gen.exalted_rate(payload)
        div_rate = self._get_divine_rate(league)
        chaos_ex = self._get_chaos_ex_value(league)
        out = {}
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if not item or not item.get("name"):
                continue
            raw = item["name"]
            if raw in gen.ITEM_NAME_SKIP:
                continue
            name = gen.ITEM_NAME_CORRECTIONS.get(raw, raw)
            pv   = float(line.get("primaryValue") or 0.0)
            ex   = pv * rate if rate else pv
            out[name] = {
                "ex":    ex,
                "chaos": ex / chaos_ex if chaos_ex else ex,
                "div":   ex / div_rate if div_rate else 0.0,
            }
        return out

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

    def report_callback_exception(self, exc, val, tb):
        """Tk calls this for any uncaught error in an event/after callback. Default
        prints to stderr (lost under pythonw/the EXE); log it so it leaves a trace.
        This is the net that would have caught the v2.6.0 icon crash immediately."""
        logger.error("Tk callback exception", exc_info=(exc, val, tb))

    @staticmethod
    def _guarded(fn, *args):
        """Run fn(*args) in a worker thread, logging any exception instead of
        letting it vanish (raw threads have no report_callback_exception)."""
        try:
            fn(*args)
        except Exception:
            log_exc(f"thread {getattr(fn, '__name__', fn)}")

    def _resolve_wiki_icons(self, cat_key, rows):
        """Background thread: batch-query poe2wiki.net for icon URLs, then fetch images.

        For currency: two-pass lookup for Greater/Perfect variants —
          pass 1: try the item's own wiki file (e.g. 'Greater Jeweller's Orb' → has its own icon)
          pass 2: if not found, try the base name (e.g. 'Greater Chaos Orb' → 'Chaos Orb')
        For gems: strip '(Level X)' so all levels share one wiki file.
        """
        names = [r[0] for r in rows]

        to_fetch = [n for n in names if n not in self._wiki_icon_cache]
        if to_fetch:
            # Pass 1: query each item by its own wiki file title (strip level suffix for gems)
            file_to_items: dict[str, list] = {}
            for n in to_fetch:
                base  = self._wiki_base_name(n)
                title = f"File:{base} inventory icon.png"
                file_to_items.setdefault(title, []).append(n)

            found = self._batch_wiki_query(file_to_items)
            with self._wiki_cache_lock:
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
                    with self._wiki_cache_lock:
                        for title, url in found2.items():
                            for item_name in fallback_map.get(title, []):
                                self._wiki_icon_cache[item_name] = url

            # poe.ninja's image CDN 404s, so it's no longer a usable fallback —
            # mark anything the wiki couldn't resolve as empty (skipped, no re-query).
            with self._wiki_cache_lock:
                for n in to_fetch:
                    if n not in self._wiki_icon_cache:
                        self._wiki_icon_cache[n] = ""
                try:
                    with open(WIKI_CACHE_FILE, "w", encoding="utf-8") as f:
                        json.dump(self._wiki_icon_cache, f, indent=2)
                except Exception:
                    pass

        # Fetch images from the resolved poe2wiki URLs (bounded pool).
        to_load = [
            (name, self._wiki_icon_cache.get(name, ""))
            for name in names
            if self._wiki_icon_cache.get(name)
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
            log_exc(f"fetch_icon {name}")

    def _apply_icon(self, key, name, path):
        """Main thread: set icon on matching card.

        Icons download on background threads, so by the time one arrives the card's
        label may already be destroyed (the user navigated away or the grid was
        rebuilt). That's an expected race — skip it quietly rather than letting
        ``.configure()`` raise a TclError and spam the debug log.
        """
        for card in self._cat_cards.get(key, []):
            if card._name != name:
                continue
            lbl = getattr(card, "_icon_lbl", None)
            if lbl is None or not lbl.winfo_exists():
                break   # card/grid was rebuilt before the icon finished downloading
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
                lbl.configure(image=photo, width=photo.width(), height=photo.height())
                lbl._ph = photo
            except Exception:
                log_exc(f"apply_icon {name}")
            break

    # ── State persistence ─────────────────────────────────────────────────────

    def _save_states_now(self):
        self.cfg["item_states"] = self._item_states
        save_config(self.cfg)

    # ── Gear & Bases panel (existing controls) ────────────────────────────────

    def _build_cat_gear_panel(self, parent):
        """The old-style panel for unique categories and base types."""
        inner, c = self._scrollable(parent)
        self._cat_gear_canvas = c

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
                checkbtn(row, lbl_text, self.cat_enabled[key]).pack(
                    side="left", padx=10, pady=6)
                tf = tk.Frame(row, bg=row_bg)
                tf.pack(side="right", padx=8)
                label(tf, "ex  (−1 = global)", fg=TEXT_DIM, font=FONT_SM, bg=row_bg).pack(side="right")
                entry(tf, self.cat_thresh[key], width=6).pack(side="right", padx=(0, 4))
                label(tf, "threshold:", fg=TEXT_DIM, font=FONT_SM, bg=row_bg).pack(
                    side="right", padx=(0, 4))

        cat_group("Unique Categories", gen.UNIQUE_CATEGORIES, unique=True,
                  desc="Unique items matched by exact name ([UniqueName]).  "
                       "Threshold and enable/disable apply at the whole-category level.")

        # Base Types
        lf_b = tk.Frame(inner, bg=BG)
        lf_b.pack(fill="x", pady=(16, 0))
        label(lf_b, "Exceptional Base Types  (Game Data)", fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(16, 8))
        sep(lf_b).pack(side="left", fill="x", expand=True, padx=(0, 16), pady=3)

        sec_b = tk.Frame(inner, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        sec_b.pack(fill="x", padx=16, pady=(2, 12))

        label(sec_b,
              "Adds exceptional base type rules (245 bases across 25 categories) sourced from game data — "
              "weapons, armour, off-hands, plus Runeforged/Runemastered variants.  Instant, no network call.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))

        checkbtn(sec_b, "Include exceptional base types in pickit",
                 self.include_bases_var).pack(anchor="w", padx=10, pady=(0, 4))

        qrow = tk.Frame(sec_b, bg=BG2)
        qrow.pack(anchor="w", padx=10, pady=(0, 10))
        label(qrow, "Min quality:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        entry(qrow, self.base_quality_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        label(qrow, "%", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        label(qrow, "   Min item level:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(
            side="left", padx=(16, 0))
        entry(qrow, self.base_min_level_var, width=5).pack(side="left", padx=(6, 4), ipady=4)
        label(qrow, "(82 = max ilvl)", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(
            side="left", padx=(6, 0))

    # Chance Bases + Craft Bases tabs now live in tab_chance_bases.py and
    # tab_craft_bases.py (mixed into PickitApp via ChanceBasesTab / CraftBasesTab).

    # ══════════════════════════════════════════════════════════════════════════
    #  PREVIEW PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_preview_page(self, page):
        self._tab_desc(page,
            "Browse the raw content of your last generated pickit file.  "
            "Active rules are shown in green, commented-out (below-threshold) rules in grey, "
            "and section headers in gold.  Use the Filter box to search by item name or any keyword.  "
            "Click 'Copy all' to copy the entire file to your clipboard.")
        # ── Validation results banner (#1) ────────────────────────────────────
        self._val_bar = tk.Frame(page, bg=BG2, highlightthickness=1,
                                 highlightbackground=BORDER)
        self._val_bar.pack(fill="x", padx=16, pady=(8, 0))
        self._val_hdr = tk.Label(self._val_bar, text="Generate to validate your pickit.",
                                 bg=BG2, fg=TEXT_DIM, font=FONT_BOLD, anchor="w",
                                 padx=10, pady=6)
        self._val_hdr.pack(fill="x")
        self._val_detail, self._val_text = scrolled_text(self._val_bar, height=5, state="disabled")
        # _val_detail packed only when there are issues to show
        self._val_text.tag_config("err",  foreground=TEXT_ERR)
        self._val_text.tag_config("warn", foreground=TEXT_WARN)

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
        btn(ctrl, "Re-validate", self._revalidate).pack(side="right", padx=(0, 6))

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
        t.configure(state="normal")
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
        t.configure(state="disabled")
        t.yview_moveto(ypos)
        self.preview_count_var.set(f"{active} active rules  ·  {commented} commented out")

    def _filter_preview(self, *_):
        q = self.filter_var.get().lower()
        if not q or not self._preview_lines:
            if self._preview_lines:
                self._render_preview(self._preview_lines)
            return
        self._render_preview([l for l in self._preview_lines if q in l.lower()])

    def _render_validation(self, validation):
        """Show validator results in the Preview-tab banner (#1)."""
        if not hasattr(self, "_val_hdr"):
            return
        errs  = validation.get("errors", [])   if validation else []
        warns = validation.get("warnings", []) if validation else []
        if not errs and not warns:
            self._val_hdr.configure(text="✓ Validation passed — no issues found", fg=TEXT_OK)
            self._val_detail.pack_forget()
            return
        parts = []
        if errs:
            parts.append(f"{len(errs)} error{'s' if len(errs) != 1 else ''}")
        if warns:
            parts.append(f"{len(warns)} warning{'s' if len(warns) != 1 else ''}")
        self._val_hdr.configure(text="⚠ Validation: " + "  ·  ".join(parts),
                             fg=TEXT_ERR if errs else TEXT_WARN)
        self._val_text.configure(state="normal")
        self._val_text.delete("1.0", "end")
        for ln, msg in errs:
            self._val_text.insert("end", f"Line {ln}: {msg}\n", "err")
        for ln, msg in warns:
            self._val_text.insert("end", f"Line {ln}: {msg}\n", "warn")
        self._val_text.configure(state="disabled")
        self._val_detail.pack(fill="x", padx=6, pady=(0, 6))

    def _revalidate(self):
        if self._preview_lines:
            self._render_validation(gen.validate_pickit(self._preview_lines))

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
        # Called from the generate worker thread — marshal the cfg mutation + save
        # onto the main thread so it can't race a concurrent save_config (which could
        # corrupt the JSON or raise "dictionary changed size during iteration").
        def _apply():
            h = self.cfg.get("history", [])
            h.append(entry_dict)
            if len(h) > 50:
                h = h[-50:]
            self.cfg["history"] = h
            save_config(self.cfg)
            self._refresh_history_ui()
        self.after(0, _apply)

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
            "Point the bot folder to your Exiled Bot pickit directory, set where the in-game loot "
            "filter goes, and tune auto-schedule, backups and overwrite protection.  "
            "Click 'Save settings' to apply.")
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

        # Loot filter (PoE2 game client)
        secf = self._section_frame(inner, "Loot Filter (PoE2 client)")
        label(secf, "A matching PoE2 in-game loot filter (.filter) is written next to the .ipd on every "
                    "generate. Optionally also copy it to your Path of Exile 2 folder so it appears in the "
                    "in-game filter list. It shows only what the bot picks up and hides everything else.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 4))
        ff = tk.Frame(secf, bg=BG2)
        ff.pack(fill="x", padx=10, pady=(0, 6))
        ff.columnconfigure(0, weight=1)
        entry(ff, self.poe2_filter_dir_var).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        btn(ff, "Browse…", self._browse_filter_folder).grid(row=0, column=1)
        checkbtn(secf, "Also copy loot filter to PoE2 folder after generate", self.copy_filter_var
                 ).pack(anchor="w", padx=10, pady=(0, 4))

        # Automation & safety — the behaviour toggles grouped together, each with a
        # short note directly beneath it (toggle first, explanation second).
        sec2 = self._section_frame(inner, "Automation & Safety")
        checkbtn(sec2, "Auto-generate every hour while the app is open", self.auto_schedule_var
                 ).pack(anchor="w", padx=10, pady=(8, 0))
        label(sec2, "Re-generates the pickit hourly in the background so prices stay fresh.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=34, pady=(0, 8))
        checkbtn(sec2, "Confirm before overwriting a recent pickit", self.confirm_ovw_var
                 ).pack(anchor="w", padx=10, pady=(0, 0))
        label(sec2, "Asks before overwriting a pickit you generated in the last couple of minutes.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=34, pady=(0, 8))
        bf2 = tk.Frame(sec2, bg=BG2)
        bf2.pack(fill="x", padx=10, pady=(0, 10))
        label(bf2, "Keep backups:", fg=TEXT_DIM, bg=BG2).pack(side="left")
        self._make_slider(bf2, self.backup_count_var, from_=0, to=20, resolution=1,
                          fmt="{:.0f} backups", width=200).pack(side="left", padx=(10, 4))
        label(bf2, "(0 = disabled)", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left", padx=(6, 0))

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
        self.cfg["copy_filter_to_game"]    = self.copy_filter_var.get()
        self.cfg["poe2_filter_dir"]        = self.poe2_filter_dir_var.get().strip()
        self.cfg["backup_count"]           = self.backup_count_var.get()
        self.cfg["confirm_overwrite_secs"] = 120 if self.confirm_ovw_var.get() else 0
        self.cfg["auto_schedule"]          = self.auto_schedule_var.get()
        self.cfg["include_bases"]          = self.include_bases_var.get()
        self.cfg["base_quality"]           = self.base_quality_var.get()
        self.cfg["base_min_level"]         = self.base_min_level_var.get()
        self.cfg["min_exalt"]      = 0.0
        self.cfg["min_exalt_gear"] = 0.0
        try:
            self.cfg["min_exalt_unique"] = float(self.min_exalt_unique_var.get())
        except (tk.TclError, ValueError):
            pass
        save_config(self.cfg)
        self._log("Settings saved.", "ok")

    def _reset_defaults(self):
        if messagebox.askyesno("Reset settings", "Reset all settings to defaults?"):
            self.cfg = dict(DEFAULT_CONFIG)
            save_config(self.cfg)
            # Re-sync all tk vars so the live UI reflects defaults immediately
            self.league_var.set(self.cfg.get("league", ""))
            self.min_exalt_var.set(self.cfg.get("min_exalt", 0.0))
            self.min_exalt_gear_var.set(self.cfg.get("min_exalt_gear", 0.0))
            self.min_exalt_unique_var.set(self.cfg.get("min_exalt_unique", 0.0))
            self.output_var.set(self.cfg.get("output_base", "poe2_pickit"))
            self.bot_folder_var.set(self.cfg.get("bot_folder", ""))
            self.auto_copy_var.set(self.cfg.get("auto_copy", False))
            self.copy_filter_var.set(self.cfg.get("copy_filter_to_game", True))
            self.poe2_filter_dir_var.set(self.cfg.get("poe2_filter_dir") or _default_poe2_filter_dir())
            self.backup_count_var.set(self.cfg.get("backup_count", 5))
            self.confirm_ovw_var.set(True)
            self.auto_schedule_var.set(True)
            self.include_bases_var.set(True)
            self.base_quality_var.set(self.cfg.get("base_quality", 28))
            self.base_min_level_var.set(self.cfg.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))
            for key in ALL_CATEGORY_KEYS:
                self.cat_enabled[key].set(True)
                self.cat_thresh[key].set(-1.0)
            self._log("Settings reset to defaults.", "warn")

    def _browse_bot_folder(self):
        folder = filedialog.askdirectory(title="Select Exiled Bot pickit folder")
        if folder:
            self.bot_folder_var.set(folder)

    def _browse_filter_folder(self):
        folder = filedialog.askdirectory(title="Select Path of Exile 2 folder")
        if folder:
            self.poe2_filter_dir_var.set(folder)

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
        btn(btn_f, "Open debug log", lambda: self._open_file_path(LOG_PATH)).pack(side="left", padx=(6, 0))
        btn(btn_f, "Prune cache", self._prune_cache_ui).pack(side="left", padx=(6, 0))
        btn(btn_f, "Clear", self._debug_clear).pack(side="left", padx=(6, 0))

        sep(page).pack(fill="x", padx=16)

        df, self.debug_text = scrolled_text(page, state="disabled")
        df.pack(fill="both", expand=True, padx=16, pady=(8, 16))
        for tag, col in [("header", GOLD), ("ok", TEXT_OK), ("err", TEXT_ERR),
                         ("warn", TEXT_WARN), ("info", TEXT_INFO), ("dim", TEXT_DIM)]:
            self.debug_text.tag_config(tag, foreground=col)

    def _dlog(self, msg, tag=""):
        def _do():
            self.debug_text.configure(state="normal")
            self.debug_text.insert("end", msg + "\n", tag)
            self.debug_text.see("end")
            self.debug_text.configure(state="disabled")
        self.after(0, _do)

    def _prune_cache_ui(self):
        """Delete disk-cache files older than 60 days and show result."""
        try:
            removed = gen.prune_disk_cache(max_age_days=60)
            msg = (f"Pruned {removed} stale cache file(s)."
                   if removed else "Nothing to prune — all cache files are recent.")
            self._dlog(f"[Prune] {msg}", "ok" if removed else "dim")
            log_info(f"Manual prune: {removed} file(s) removed")
        except Exception as e:
            self._dlog(f"[Prune] Error: {e}", "err")

    def _debug_clear(self):
        self.debug_text.configure(state="normal")
        self.debug_text.delete("1.0", "end")
        self.debug_text.configure(state="disabled")

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
            d("  ✓  Generator module healthy", "ok")
        except Exception as e:
            d(f"  ✗  {e}", "err")
        d("")
        d("── 4. External API connectivity", "header")
        # poe.ninja — the only hard dependency (generation falls back to the
        # offline cache if it's down).
        try:
            t0 = time.time()
            data = gen.fetch_json(gen.INDEX_STATE_URL, {})
            d(f"  ✓  poe.ninja      reachable ({(time.time()-t0)*1000:.0f} ms)", "ok")
            leagues = data.get("economyLeagues", [])
            d(f"     active leagues: {', '.join(lg.get('name', '?') for lg in leagues) or 'none'}", "dim")
        except Exception as e:
            d(f"  ✗  poe.ninja      FAILED — will use cached prices if available: {e}", "err")
        # poe2wiki — optional (item icons); icons fall back to poe.ninja if down.
        try:
            t0 = time.time()
            r = requests.get(self._WIKI_API,
                             params={"action": "query", "meta": "siteinfo", "format": "json"},
                             headers={"User-Agent": gen.USER_AGENT}, timeout=10)
            ok = r.status_code == 200
            d(f"  {'✓' if ok else '⚠'}  poe2wiki.net   {'reachable' if ok else 'HTTP '+str(r.status_code)} "
              f"({(time.time()-t0)*1000:.0f} ms)  [optional]", "ok" if ok else "warn")
        except Exception as e:
            d(f"  ⚠  poe2wiki.net   unreachable [optional — icons skipped]: {e}", "warn")
        d("")
        d("── 5. Offline cache (lets you generate when poe.ninja is down)", "header")
        try:
            import glob
            files = glob.glob(os.path.join(PRICE_CACHE_DIR, "*.json"))
            if files:
                age_m = (time.time() - max(os.path.getmtime(f) for f in files)) / 60
                d(f"  ✓  {len(files)} categories cached on disk (newest {age_m:.0f} min old)", "ok")
                d("     → generation can still run offline from these prices", "dim")
            else:
                d("  ⚠  no cached prices yet — generate once online to enable offline mode", "warn")
        except Exception as e:
            d(f"  ✗  {e}", "err")
        d("")
        d("── 6. Output paths", "header")
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
            league = "Mercenaries"
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
        self._update_lbl.configure(
            text=f"⬆  Update available: v{remote}  —  click here to download  (you have v{VERSION})"
        )
        try:
            self._update_bar.pack(fill="x", after=self.winfo_children()[1])
        except Exception:
            self._update_bar.pack(fill="x")
        # Also pop a small dialog so the update can't be missed (once per launch).
        if not getattr(self, "_update_prompted", False):
            self._update_prompted = True
            if messagebox.askyesno(
                    "Update available",
                    f"A new version of ExileBot 2 Pickit Generator is available!\n\n"
                    f"        You have:   v{VERSION}\n"
                    f"        Latest:       v{remote}\n\n"
                    f"Download and install it now?",
                    parent=self):
                self._install_update(remote)

    def _open_releases(self):
        import webbrowser
        webbrowser.open(RELEASES_URL)

    # ── One-click update (#2) ──────────────────────────────────────────────────

    def _install_update(self, remote: str):
        """Download the new EXE and swap it in via a helper script, then relaunch.
        Only works when running the built EXE; in dev just open the releases page."""
        if not getattr(sys, "frozen", False):
            self._open_releases()
            return

        url = (f"https://github.com/{GITHUB_REPO}/releases/download/"
               f"v{remote}/ExileBot2PickitGenerator.exe")
        log_info(f"update: starting download of v{remote} from {url}")

        self._update_cancelled = False

        dlg = tk.Toplevel(self)
        dlg.title("Updating…")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self)
        tk.Label(dlg, text=f"Downloading v{remote}…", bg=BG, fg=TEXT,
                 font=FONT, padx=28, pady=(18, 4)).pack()
        status = tk.Label(dlg, text="Connecting…", bg=BG, fg=TEXT_DIM, font=FONT_SM)
        status.pack(padx=28, pady=(0, 8))
        # A Cancel button + close-to-cancel guarantee the user is never trapped on
        # "Updating…" if the download stalls or the release asset isn't published.
        btn(dlg, "Cancel", lambda: self._cancel_update(dlg, status)).pack(pady=(0, 16))
        # Force the dialog to actually render + sit on top (it was showing blank).
        dlg.update_idletasks()
        try:
            x = self.winfo_rootx() + max((self.winfo_width() - dlg.winfo_width()) // 2, 0)
            y = self.winfo_rooty() + 140
            dlg.geometry(f"+{x}+{y}")
        except Exception:
            pass
        dlg.lift()
        try:
            dlg.attributes("-topmost", True)
        except Exception:
            pass
        dlg.protocol("WM_DELETE_WINDOW", lambda: self._cancel_update(dlg, status))
        dlg.update()

        def _worker():
            try:
                dest = os.path.join(tempfile.gettempdir(),
                                    f"ExileBot2PickitGenerator_v{remote}.exe")
                # (connect, read) timeouts: a stalled download aborts after 60s of
                # no bytes instead of hanging on "Updating…" forever.
                with requests.get(url, stream=True, timeout=(15, 60),
                                  headers={"User-Agent": f"poe2-pickit/{VERSION}"}) as r:
                    r.raise_for_status()
                    total = int(r.headers.get("Content-Length", 0))
                    done = 0
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(chunk_size=262144):
                            if self._update_cancelled:
                                raise RuntimeError("cancelled")
                            if not chunk:
                                continue
                            f.write(chunk)
                            done += len(chunk)
                            if total:
                                self.after(0, lambda d=done, t=total: status.configure(
                                    text=f"{d*100//t}%   ({d//1048576} / {t//1048576} MB)"))
                            else:
                                self.after(0, lambda d=done: status.configure(
                                    text=f"{d//1048576} MB"))
                if self._update_cancelled:
                    raise RuntimeError("cancelled")
                if os.path.getsize(dest) < 5_000_000:
                    raise RuntimeError(
                        f"download incomplete — the v{remote} release asset may not be "
                        "published on GitHub yet")
                log_info(f"update: download ok ({os.path.getsize(dest)} bytes)")
                self.after(0, lambda: self._apply_update_swap(dest, dlg))
            except Exception as exc:
                if self._update_cancelled:
                    log_info("update: cancelled by user")
                    self.after(0, dlg.destroy)
                    return
                log_exc("update download")
                self.after(0, lambda e=str(exc): self._update_failed(e, dlg))

        threading.Thread(target=_worker, daemon=True).start()

    def _cancel_update(self, dlg, status=None):
        """Abort an in-progress update download and close the dialog."""
        self._update_cancelled = True
        if status is not None:
            try:
                status.configure(text="Cancelling…")
            except Exception:
                pass

    def _apply_update_swap(self, new_exe: str, dlg):
        """Spawn a detached helper that waits for us to exit, overwrites the EXE,
        relaunches it, then deletes itself."""
        try:
            cur = sys.executable
            pid = os.getpid()
            bat = os.path.join(tempfile.gettempdir(), "poe2_pickit_update.bat")
            log = os.path.join(_cfg_dir, "update.log")
            # Sleep with `ping`, not `timeout`: `timeout` reads from the console and
            # fails immediately in a DETACHED_PROCESS (no console), turning the wait
            # loop into a busy-spin. The copy is retried because Windows Defender can
            # briefly lock a freshly downloaded EXE; if it never frees, fall back to
            # opening the releases page so the user isn't left on a stale version.
            script = (
                "@echo off\r\n"
                "setlocal\r\n"
                f'set "LOG={log}"\r\n'
                'echo [update] helper started >> "%LOG%"\r\n'
                ":waitloop\r\n"
                f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL\r\n'
                "if not errorlevel 1 (\r\n"
                "  ping -n 2 127.0.0.1 >NUL\r\n"
                "  goto waitloop\r\n"
                ")\r\n"
                "ping -n 2 127.0.0.1 >NUL\r\n"          # let the OS release the EXE lock
                "set /a tries=0\r\n"
                ":copyloop\r\n"
                f'copy /Y "{new_exe}" "{cur}" >NUL 2>&1\r\n'
                "if not errorlevel 1 goto copied\r\n"
                "set /a tries+=1\r\n"
                'echo [update] copy attempt %tries% failed >> "%LOG%"\r\n'
                "if %tries% GEQ 10 goto giveup\r\n"
                "ping -n 3 127.0.0.1 >NUL\r\n"
                "goto copyloop\r\n"
                ":copied\r\n"
                'echo [update] copy ok - relaunching >> "%LOG%"\r\n'
                f'start "" "{cur}"\r\n'
                "goto done\r\n"
                ":giveup\r\n"
                'echo [update] copy failed - opening releases page >> "%LOG%"\r\n'
                f'start "" "{RELEASES_URL}"\r\n'
                ":done\r\n"
                'del "%~f0"\r\n'
            )
            # Write as the OEM codepage (what cmd.exe reads .bat files in) so install
            # paths with non-ASCII characters survive instead of being mangled by
            # ascii+errors="ignore", which silently broke the copy/relaunch.
            with open(bat, "w", encoding="oem") as f:
                f.write(script)
            log_info(f"update: launching swap helper {bat}")
            DETACHED = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            subprocess.Popen(["cmd", "/c", bat], creationflags=DETACHED, close_fds=True)
            try:
                dlg.destroy()
            except Exception:
                pass
            # Persist settings, then HARD-exit so the helper can overwrite the EXE.
            # (self.destroy() alone sometimes left the process alive, so the helper
            # waited forever and the update never applied.)
            try:
                if self._schedule_after:
                    self.after_cancel(self._schedule_after)
                self.cfg["window_geometry"] = self.geometry()
                save_config(self.cfg)
            except Exception:
                pass
            os._exit(0)
        except Exception as exc:
            log_exc("update swap")
            self._update_failed(str(exc), dlg)

    def _update_failed(self, msg: str, dlg):
        try:
            dlg.destroy()
        except Exception:
            pass
        messagebox.showwarning(
            "Update failed",
            f"Couldn't auto-update:\n{msg}\n\nOpening the download page instead.",
            parent=self)
        self._open_releases()

    # ══════════════════════════════════════════════════════════════════════════
    #  League helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _fetch_leagues_async(self):
        self.league_var.set(self.league_var.get() or "Loading…")
        self.league_cb.configure(state="disabled")
        threading.Thread(target=self._fetch_leagues, daemon=True).start()

    def _fetch_leagues(self):
        try:
            leagues = gen.fetch_live_leagues()
            self._leagues = leagues
            names = [f"{d}  [{n}]" for n, _, d in leagues]
            self.after(0, lambda: self._populate_leagues(names))
        except Exception as e:
            self.after(0, lambda msg=str(e): self._log(f"Could not fetch leagues: {msg}", "err"))
            self.after(0, lambda: self.league_var.set(self.cfg.get("league") or ""))
            self.after(0, lambda: self.league_cb.configure(state="normal"))

    def _populate_leagues(self, names):
        self.league_cb["values"] = names
        self.league_cb.configure(state="normal")
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
        # Warm the cache for the selected league immediately
        self.after(200, lambda: self._preload_all_cats_async(self._selected_league() or ""))

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
        # The Generate-tab Log was removed; keep this a safe no-op so the many
        # existing self._log(...) progress calls still work.
        if getattr(self, "log_text", None) is None:
            return
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        def _do():
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"[{ts}] ", "ts")
            self.log_text.insert("end", msg + "\n", tag)
            self.log_text.see("end")
            self.log_text.configure(state="disabled")
        self.after(0, _do)

    def _log_clear(self):
        if getattr(self, "log_text", None) is None:
            return
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _log_copy(self):
        if getattr(self, "log_text", None) is None:
            return
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
                    def _set(d=divine):
                        self._divine_rate_var.set(f"1 Divine = {d:.1f} ex")
                        self._update_unique_conv()
                    self.after(0, _set)
                    break
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════════════════
    #  Schedule
    # ══════════════════════════════════════════════════════════════════════════

    def _schedule_tick(self):
        if not self.cfg.get("auto_schedule", True):
            self.schedule_lbl.configure(text="⏱ Auto: off")
        elif not self._running:
            now = time.time()
            if now - self._last_run_time >= 3600:
                self._start_generate(silent=True)
            remaining = int(3600 - (now - self._last_run_time))
            h, m = divmod(max(remaining, 0) // 60, 60)
            self.schedule_lbl.configure(text=f"⏱ Next: {h}h {m}m")
        self._schedule_after = self.after(30_000, self._schedule_tick)

    # ══════════════════════════════════════════════════════════════════════════
    #  Rule helpers
    # ══════════════════════════════════════════════════════════════════════════
    #  Rule identity/diff helpers live in pickit_assembly (asm.extract_rule_name /
    #  asm.active_rule_ids) so they can be unit-tested without the GUI.

    @staticmethod
    def _fmt_val_multi(ex, divine_rate, chaos_ex, sep="  ·  "):
        """Format an exalt value with its divine and chaos equivalents, e.g.
        '1,037,226 ex · 3,667 div · 41,234c'."""
        parts = [f"{ex:,.0f} ex"]
        if divine_rate and divine_rate > 0:
            parts.append(f"{ex / divine_rate:,.1f} div")
        if chaos_ex and chaos_ex > 0:
            parts.append(f"{ex / chaos_ex:,.0f}c")
        return sep.join(parts)

    # ══════════════════════════════════════════════════════════════════════════
    #  GENERATE
    # ══════════════════════════════════════════════════════════════════════════

    def _effective_craftbase_ilvls(self) -> dict:
        """The item level each *visible* Craft Bases card is currently showing.

        A craft spinbox inherits its starting value from the global 'Min item
        level' box but only persists a per-base override once the user edits it.
        Generation used to fall back to the global for any un-edited base, so the
        .ipd could emit a different ilvl than the Craft tab displayed (tab shows
        82, file says 79). Reading the live spinbox values here makes the tab
        authoritative: we generate exactly what the user sees. Returns {} when the
        tab has never been opened (no cards built yet), leaving the old global
        fallback in place.
        """
        out: dict = {}
        for card in getattr(self, "_craftbase_cards", []):
            try:
                out[card._name] = max(1, min(100, int(float(card._ilvl_var.get()))))
            except (AttributeError, ValueError, tk.TclError):
                continue
        return out

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
        self.gen_btn.configure(state="disabled")
        self.force_btn.configure(state="disabled")
        self.open_ipd_btn.configure(state="disabled")
        self.open_filter_btn.configure(state="disabled")
        self.status_lbl.configure(text="Generating…", fg=TEXT_WARN)
        self.progress_var.set("Starting…")

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
            # Stable base (no silent timestamp) — used for the in-game filter name
            # so hourly auto-runs overwrite one file instead of piling up copies.
            "output_stable":   os.path.basename(os.path.splitext(self.output_var.get())[0]),
            "auto_copy":       self.auto_copy_var.get(),
            "bot_folder":      self.bot_folder_var.get(),
            "copy_filter_to_game": self.copy_filter_var.get(),
            "poe2_filter_dir":     self.poe2_filter_dir_var.get().strip(),
            "backup_count":    self.backup_count_var.get(),
            "cat_enabled":     {k: v.get() for k, v in self.cat_enabled.items()},
            "cat_thresh":      {},
            "include_bases":   self.include_bases_var.get(),
            "base_quality":    self.base_quality_var.get(),
            "base_min_level":  self.base_min_level_var.get(),
            "item_states":     dict(self._item_states),
        }
        # Make the Craft Bases tab authoritative: bake the ilvl each craft card is
        # actually showing into the snapshot as a per-base override, so the .ipd
        # matches the tab even for bases the user never edited (see
        # _effective_craftbase_ilvls). Deep-copy the _craftbase sub-dict so we never
        # mutate the live item_states off the main thread.
        _eff_craft = self._effective_craftbase_ilvls()
        if _eff_craft:
            _cb = {n: dict(st) for n, st in snapshot["item_states"].get("_craftbase", {}).items()}
            for _name, _lvl in _eff_craft.items():
                _cb.setdefault(_name, {})["ilvl"] = _lvl
            snapshot["item_states"] = dict(snapshot["item_states"])
            snapshot["item_states"]["_craftbase"] = _cb
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
        try:
            snapshot["min_exalt_unique"] = self.min_exalt_unique_var.get()
        except tk.TclError:
            snapshot["min_exalt_unique"] = float(self.cfg.get("min_exalt_unique", 0.0))
            self.min_exalt_unique_var.set(snapshot["min_exalt_unique"])
            self._log("Unique threshold invalid — reset to saved value.", "warn")

        # Init segmented bar — one segment per category + maybe bases
        _n_main = sum(1 for c in gen.ALL_CATEGORIES
                      if snapshot["cat_enabled"].get(c[0], True))
        _n_segs = _n_main + (1 if snapshot.get("include_bases") else 0)
        self._seg_bar.init_segments(_n_segs)
        self._seg_bar.pack(fill="x", padx=10, pady=(4, 0))
        self._last_gen_stats = {}

        threading.Thread(target=self._generate, args=(snapshot,), daemon=True).start()

    def _generate(self, snapshot: dict):
        success = False
        try:
            league    = snapshot["league"]
            min_exalt = snapshot["min_exalt"]
            min_exalt_gear = snapshot.get("min_exalt_gear", 5.0)
            min_exalt_unique = snapshot.get("min_exalt_unique", 0.0)

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
            try:
                min_exalt_unique = float(min_exalt_unique)
            except (TypeError, ValueError):
                min_exalt_unique = float(self.cfg.get("min_exalt_unique", 0.0))
                self._log("Unique threshold invalid — reset to saved value.", "warn")

            base_path = os.path.join(OUTPUT_DIR,
                                     os.path.basename(os.path.splitext(snapshot["output_var"])[0]))
            ipd_path  = base_path + ".ipd"

            self._log(f"League    : {league}")
            self._log(f"Threshold : {min_exalt:.0f} ex  (currency/items)  |  {min_exalt_unique:.0f} ex  (unique gear)")
            self._log(f"Output    : {os.path.basename(base_path)}.ipd")
            self._log("─" * 55, "dim")

            categories = [cat for cat in gen.ALL_CATEGORIES
                          if snapshot["cat_enabled"].get(cat[0], True)]
            total_cats  = len(categories)

            _gen_ts  = datetime.datetime.now()
            _gen_id  = _gen_ts.strftime('%Y%m%d_%H%M%S')
            output_lines = asm.build_header_lines(league, _gen_ts, _gen_id, min_exalt, min_exalt_unique)
            self._log(f"Pickit ID : {_gen_id}", "info")

            self._log("Fetching currency rates…", "dim")
            stale_keys: set = set()      # categories served from the offline cache
            offline_mode    = False
            try:
                currency_payload = gen.fetch_category(league, "currency", "Currency", False)
                gen._cache_set(league, "currency", currency_payload)
            except Exception:
                disk, age = gen.load_payload_from_disk(league, "currency")
                if disk is not None:
                    currency_payload = disk
                    stale_keys.add("currency")
                    offline_mode = True
                    self._log(f"  ⚠ poe.ninja unreachable — using cached prices "
                              f"({self._fmt_age(age)} old)", "warn")
                else:
                    raise   # no network and no cache → nothing we can do
            divine_rate_exalts, _divine_found, rate = asm.compute_divine_rate(currency_payload)

            if not _divine_found:
                self._log("  ⚠ Divine Orb not found — divine conversion unavailable", "warn")
            if rate == 0:
                self._log("  ⚠ Exalted rate is 0 — item values may be inaccurate", "warn")

            self._log(f"1 Divine = {divine_rate_exalts:.1f} Exalted", "ok")
            output_lines += [f"// Conversion: 1 Divine = {divine_rate_exalts:.6f} Exalted", "",
                              gen.header_major("Economy Items"), ""]

            top_items: list[tuple[str, float]] = []   # (name, ex_val), sorted desc
            _cat_ok = 0
            _cat_fail = 0

            # Fetch all non-currency categories in parallel
            non_currency_cats = [(k, t, l, u) for k, t, l, u in categories if k != "currency"]
            self._log(f"Fetching {len(non_currency_cats)} categories in parallel…", "dim")
            self.after(0, lambda n=len(non_currency_cats):
                       self.progress_var.set(f"Fetching {n} categories in parallel…"))
            all_payloads = gen.fetch_all_payloads(league, non_currency_cats, stale_out=stale_keys)
            all_payloads["currency"] = currency_payload
            if stale_keys:
                offline_mode = True

            for cat_idx, (key, _ninja_type, label_text, is_unique) in enumerate(categories, 1):
                _seg_i = cat_idx - 1
                self.after(0, lambda s=f"Building {cat_idx}/{total_cats}: {label_text}":
                           self.progress_var.set(s))
                self.after(0, lambda i=_seg_i: self._seg_bar.set_segment(i, "active"))

                # Per-category threshold takes priority; fall back to the
                # appropriate global (gear vs currency) when not set (-1).
                effective_min = asm.effective_min(snapshot, key, is_unique,
                                                  min_exalt_gear, min_exalt_unique)

                payload = all_payloads.get(key)

                if isinstance(payload, Exception):
                    e = payload
                    output_lines += [gen.header_sub(label_text), f"// Failed: {e}", ""]
                    self._log(f"  ✗ {label_text}: {type(e).__name__}", "err")
                    self.after(0, lambda i=_seg_i: self._seg_bar.set_segment(i, "err"))
                    _cat_fail += 1
                    continue
                if payload is None:
                    output_lines += [gen.header_sub(label_text), "// No data returned", ""]
                    self._log(f"  ? {label_text}: no data", "warn")
                    self.after(0, lambda i=_seg_i: self._seg_bar.set_segment(i, "err"))
                    _cat_fail += 1
                    continue

                try:
                    # Items-tab on/off state → which names to keep (None = use threshold).
                    _cat_states = snapshot.get("item_states", {}).get(key, {})
                    enabled_names = asm.enabled_names_for(key, is_unique, payload, _cat_states)

                    lines = asm.build_category_lines(key, is_unique, payload,
                                                     divine_rate_exalts, effective_min,
                                                     min_exalt_gear, enabled_names)

                    output_lines += [gen.header_sub(label_text), ""]
                    output_lines += lines if lines else [f"// poe.ninja returned no rows for {label_text}"]
                    output_lines.append("")

                    active_in_cat = sum(1 for l in lines if l and not l.startswith("//"))
                    self._log(f"  ✓ {label_text}: {active_in_cat} active", "ok")
                    self.after(0, lambda i=_seg_i: self._seg_bar.set_segment(i, "ok"))
                    _cat_ok += 1

                    top_items.extend(asm.top_items_from_lines(lines))

                except Exception as e:
                    output_lines += [gen.header_sub(label_text), f"// Processing failed: {e}", ""]
                    self._log(f"  ✗ {label_text}: {e}", "err")
                    self.after(0, lambda i=_seg_i: self._seg_bar.set_segment(i, "err"))
                    _cat_fail += 1

            top_items.sort(key=lambda x: -x[1])
            top_items = top_items[:3]
            top_item  = top_items[0] if top_items else ("", 0.0)


            output_lines.extend(gen.STATIC_TABLET_RULES.splitlines())
            output_lines.extend(gen.STATIC_WOMBGIFT_RULES.splitlines())
            output_lines.extend(gen.STATIC_SPECIAL_WAYSTONE_RULES.splitlines())

            output_lines.extend(gen.build_chance_base_rules(asm.chance_base_disabled(snapshot)))

            # ── Craft bases (Normal blank bases; per-base item level) ─────────
            _craftbase_lines, _cb_count, _craft_ilvl = asm.craft_base_section(snapshot)
            if _craftbase_lines:
                output_lines.append("")
                output_lines.append("")
                output_lines.extend(_craftbase_lines)
                self._log(f"  ✓ Craft bases: {_cb_count} Normal ilvl-{_craft_ilvl}+ rules", "ok")

            # ── Base types (optional) ─────────────────────────────────────────
            if snapshot.get("include_bases"):
                min_q = int(snapshot.get("base_quality", 28))
                _base_seg = total_cats
                self.after(0, lambda i=_base_seg: self._seg_bar.set_segment(i, "active"))
                self._log("Building base type rules from game data…", "dim")
                def _base_prog(idx, total, title):
                    self.after(0, lambda s=f"Bases {idx}/{total}: {title}":
                               self.progress_var.set(s))
                    self._log(f"  [{idx}/{total}] {title}", "dim")
                try:
                    min_lvl   = int(snapshot.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))
                    base_lines = gen.build_base_rules(min_quality=min_q,
                                                      min_level=min_lvl,
                                                      progress_callback=_base_prog)
                    output_lines.append("")
                    output_lines.append("")
                    output_lines.append(gen.header_major("Gear Base Types (game data)"))
                    output_lines.append("//  Exceptional gear base types pulled from game data.")
                    output_lines.append("//  Separate from the Craft Bases section above.")
                    output_lines.append("")
                    output_lines.extend(base_lines)
                    output_lines.append("")
                    rule_count = sum(1 for l in base_lines if l and not l.startswith("//"))
                    if any("Runeforged" in l for l in base_lines):
                        self._log("  ✓ Runeforged/Runemastered supplement included", "dim")
                    self._log(f"  ✓ Base types: {rule_count} rules", "ok")
                    self.after(0, lambda i=_base_seg: self._seg_bar.set_segment(i, "ok"))
                except Exception as e:
                    self._log(f"  ✗ Base types failed: {e}", "err")
                    self.after(0, lambda i=_base_seg: self._seg_bar.set_segment(i, "err"))

            self._last_output = list(output_lines)

            # Static validation (#1) + diff vs the previous pickit (#5) — both
            # computed before the file is overwritten.
            validation = gen.validate_pickit(output_lines)
            self.after(0, lambda v=validation: self._render_validation(v))
            if os.path.isfile(ipd_path):
                try:
                    with open(ipd_path, encoding="utf-8") as _pf:
                        _old_ids = asm.active_rule_ids(_pf.read().splitlines())
                    _diff_prev = True
                except OSError:
                    _old_ids, _diff_prev = set(), False
            else:
                _old_ids, _diff_prev = set(), False
            _new_ids = asm.active_rule_ids(output_lines)
            _added   = sorted(_new_ids - _old_ids)
            _removed = sorted(_old_ids - _new_ids)

            # Write the single .ipd output file.
            self._backup_file(ipd_path, n=snapshot["backup_count"])
            with open(ipd_path, "w", encoding="utf-8") as f:
                f.write("\n".join(output_lines))
            self._log(f"Written: {os.path.basename(ipd_path)}", "dim")
            success = True

            # Auto-copy — stable name so hourly auto-runs overwrite one pickit in the
            # bot folder instead of leaving a trail of timestamped copies the bot
            # (which points at a single file) never reads.
            if snapshot["auto_copy"]:
                bot = snapshot["bot_folder"].strip()
                if bot and os.path.isdir(bot):
                    dest = os.path.join(bot, (snapshot.get("output_stable") or "poe2_pickit") + ".ipd")
                    shutil.copy2(ipd_path, dest)
                    self._log(f"Copied to bot folder: {dest}", "ok")
                else:
                    self._log("Auto-copy: bot folder not set or not found.", "warn")

            # ── PoE2 client loot filter (always written next to the .ipd) ─────
            try:
                filter_path = os.path.splitext(ipd_path)[0] + ".filter"
                filter_lines = gen.build_loot_filter(
                    output_lines, generated_iso=datetime.datetime.now().isoformat())
                with open(filter_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(filter_lines))
                shows = sum(1 for l in filter_lines if l == "Show")
                self._log(f"Loot filter: {os.path.basename(filter_path)} ({shows} Show blocks)", "dim")

                if snapshot.get("copy_filter_to_game"):
                    game_dir = (snapshot.get("poe2_filter_dir") or "").strip()
                    if game_dir and os.path.isdir(game_dir):
                        # Stable name so hourly auto-runs overwrite one in-game filter
                        # instead of leaving a trail of timestamped copies.
                        game_name = (snapshot.get("output_stable") or "poe2_pickit") + ".filter"
                        fdest = os.path.join(game_dir, game_name)
                        shutil.copy2(filter_path, fdest)
                        self._log(f"Loot filter copied to PoE2 folder: {fdest}", "ok")
                    else:
                        self._log("Loot filter: PoE2 folder not set or not found "
                                  "(set it in Settings).", "warn")
            except Exception as e:
                self._log(f"Loot filter failed: {e}", "err")

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
            _chaos_ex = self._get_chaos_ex_value(league)   # ex value of 1 chaos

            def _update_stats():
                self._stat_vars["active"].set(str(active))
                self._stat_vars["commented"].set(str(commented))
                self._stat_vars["divine"].set(f"{divine_rate_exalts:.1f} ex")
                if top_item[0]:
                    self._stat_vars["top"].set(
                        f"{top_item[0][:22]}\n"
                        + self._fmt_val_multi(top_item[1], divine_rate_exalts, _chaos_ex))
                else:
                    self._stat_vars["top"].set("—")
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

            if stale_keys:
                self._log(f"  ⚠ Offline: {len(stale_keys)} categor"
                          f"{'ies' if len(stale_keys) != 1 else 'y'} used cached prices "
                          f"(poe.ninja was unreachable)", "warn")
            self.after(0, lambda om=offline_mode: self._set_api_banner(om))

            # ── Price alerts ──────────────────────────────────────────────────
            prev_league  = self._last_gen_prices.get(league, {})
            chaos_ex_val = self._get_chaos_ex_value(league)
            new_gen_prices, alerts = asm.compute_price_alerts(
                categories, all_payloads, prev_league, chaos_ex_val, threshold=0.20)

            # Keep only the current league's baseline so the config file doesn't
            # accumulate a full price snapshot for every league ever generated.
            self._last_gen_prices = {league: new_gen_prices}
            alerts.sort(key=lambda t: t[0], reverse=True)
            # Shown in the post-generate summary box only (not re-logged below).
            self._price_alerts = [text for _, text in alerts[:10]]

            self._log("─" * 55, "dim")
            self._log(f"Done in {dur_str}  ·  {active} active rules", "ok")

            self._last_gen_stats = {
                "active":    active,
                "duration":  dur_str,
                "fsize_kb":  _fsize_kb,
                "top_items": top_items,
                "cat_ok":    _cat_ok,
                "cat_fail":  _cat_fail,
                "validation": validation,
                "diff_prev":  _diff_prev,
                "diff_added": _added,
                "diff_removed": _removed,
                "divine_rate": divine_rate_exalts,
                "chaos_ex":    _chaos_ex,
            }

            # Update config on the main thread to avoid racing with _save_settings.
            _lgp = self._last_gen_prices
            _cfg_updates = {
                "league":             league,
                "min_exalt":          min_exalt,
                "min_exalt_gear":     min_exalt_gear,
                "min_exalt_unique":   min_exalt_unique,
                "output_base":        snapshot["output_var"],
                "category_enabled":   dict(snapshot["cat_enabled"]),
                "category_threshold": dict(snapshot["cat_thresh"]),
                "last_gen_prices":    _lgp,
            }
            def _apply_cfg(updates=_cfg_updates):
                self.cfg.update(updates)
                save_config(self.cfg)
            self.after(0, _apply_cfg)

        except Exception as e:
            log_exc("generate")
            self._log(f"Error: {e}", "err")
            self._log(traceback.format_exc(), "dim")
        finally:
            self._last_run_time = time.time()  # advance regardless of success/failure
            self.after(0, lambda: self._generate_done(success))

    def _generate_done(self, success: bool = False):
        self._running = False
        self._seg_bar.pack_forget()
        self.progress_var.set("")
        self.gen_btn.configure(state="normal")
        self.force_btn.configure(state="normal")
        if success:
            self.open_ipd_btn.configure(state="normal")
            self.open_filter_btn.configure(state="normal")
            self._show_gen_summary()
        self.status_lbl.configure(
            text=f"Last run: {datetime.datetime.now().strftime('%H:%M:%S')}",
            fg=TEXT_OK if success else TEXT_ERR)

    def _show_gen_summary(self):
        s = self._last_gen_stats
        if not s:
            return
        top = s.get("top_items", [])
        active   = s.get("active", 0)
        dur      = s.get("duration", "")
        fsize    = s.get("fsize_kb", 0)
        cat_ok   = s.get("cat_ok", 0)
        cat_fail = s.get("cat_fail", 0)

        self._sum_vars["duration"].configure(text=f"Generated in {dur}")
        self._sum_vars["rules"].configure(text=f"{active:,} active rules")
        self._sum_vars["fsize"].configure(text=f"{fsize} KB")

        if top:
            dr = s.get("divine_rate", 0)
            cx = s.get("chaos_ex", 0)
            top_parts = []
            for name, ex_val in top[:3]:
                top_parts.append(f"{name}  {self._fmt_val_multi(ex_val, dr, cx, sep=' / ')}")
            self._sum_top_lbl.configure(text="      ·      ".join(top_parts))
        else:
            self._sum_top_lbl.configure(text="No items above threshold")

        cat_note = f"{cat_ok} categories"
        if cat_fail:
            cat_note += f"  ·  {cat_fail} failed"
        self._sum_cats_lbl.configure(text=cat_note)

        # row 3: validation status, what-changed, and price movers
        for w in self._sum_alerts_frame.winfo_children():
            w.destroy()
        rows = []   # (text, colour)

        # Validation (#1)
        val    = s.get("validation") or {}
        n_err  = len(val.get("errors", []))
        n_warn = len(val.get("warnings", []))
        if n_err:
            note = f"⚠ Validation: {n_err} error{'s' if n_err != 1 else ''}"
            if n_warn:
                note += f", {n_warn} warning{'s' if n_warn != 1 else ''}"
            rows.append((note + "  — see Preview tab", TEXT_ERR))
        elif n_warn:
            rows.append((f"⚠ Validation: {n_warn} warning{'s' if n_warn != 1 else ''}  — see Preview tab", TEXT_WARN))
        else:
            rows.append(("✓ Validation passed", TEXT_OK))

        # Changes since last pickit (#5)
        if s.get("diff_prev"):
            added, removed = s.get("diff_added", []), s.get("diff_removed", [])
            if added or removed:
                rows.append((f"Changes: +{len(added)} added  ·  -{len(removed)} removed", TEXT))
                for n in added[:3]:
                    rows.append((f"    + {n}", TEXT_OK))
                for n in removed[:3]:
                    rows.append((f"    - {n}", TEXT_ERR))
            else:
                rows.append(("Changes: none since last pickit", TEXT_DIM))

        alerts = getattr(self, "_price_alerts", [])
        if rows or alerts:
            self._sum_alerts_frame.pack(fill="x", padx=16, pady=(0, 12))
            for text, clr in rows:
                tk.Label(self._sum_alerts_frame, text=text, bg=BG2, fg=clr,
                         font=("Segoe UI", 12), anchor="w").pack(anchor="w", pady=1)
            if alerts:
                tk.Label(self._sum_alerts_frame, text="Price moves:", bg=BG2,
                         fg=TEXT_DIM, font=("Segoe UI", 12)).pack(anchor="w", pady=(4, 0))
                for a in alerts[:5]:
                    clr = TEXT_OK if a.startswith("▲") else TEXT_ERR
                    tk.Label(self._sum_alerts_frame, text=a, bg=BG2, fg=clr,
                             font=("Segoe UI", 12), anchor="w").pack(anchor="w", padx=(8, 0))
        else:
            self._sum_alerts_frame.pack_forget()

        self._gen_summary.pack(fill="x", padx=10, pady=(8, 0))

    # ══════════════════════════════════════════════════════════════════════════
    #  Close
    # ══════════════════════════════════════════════════════════════════════════

    def _on_close(self):
        self._quit_app()

    def _quit_app(self):
        if self._schedule_after:
            self.after_cancel(self._schedule_after)
        self.cfg["window_geometry"]  = self.geometry()
        self.cfg["cat_prev_prices"]  = self._cat_prev_prices
        try:
            self.cfg["min_exalt_unique"] = float(self.min_exalt_unique_var.get())
        except (tk.TclError, ValueError):
            pass
        save_config(self.cfg)
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

def _enable_dpi_awareness():
    """Tell Windows this process renders at native resolution, so the UI isn't
    bitmap-stretched (blurry) on displays scaled to 125%–250%. Must run before the
    Tk root is created. No-op / harmless on non-Windows or older Windows.

    SetProcessDpiAwarenessContext takes a pointer-sized DPI_AWARENESS_CONTEXT
    handle. Passing a bare Python int makes ctypes marshal it as a 32-bit C int,
    which fails *silently* (returns FALSE, no exception) on 64-bit Windows — the
    process then stays DPI-unaware and every window is blurry. Marshal it as
    c_void_p and check the BOOL result so we actually fall through to the older
    APIs when a step fails."""
    try:
        import ctypes
        from ctypes import wintypes
    except Exception:
        return

    # 1) Per-Monitor-v2 (Win 10 1703+) — crisp on every monitor, survives DPI changes.
    try:
        fn = ctypes.windll.user32.SetProcessDpiAwarenessContext
        fn.restype  = wintypes.BOOL
        fn.argtypes = [ctypes.c_void_p]
        if fn(ctypes.c_void_p(-4)):   # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
            return
    except Exception:
        pass

    # 2) Per-Monitor aware (Win 8.1+). Returns S_OK (0) on success.
    try:
        if ctypes.windll.shcore.SetProcessDpiAwareness(2) == 0:
            return
    except Exception:
        pass

    # 3) System DPI aware (Vista+) — last resort, still beats bitmap stretching.
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


if __name__ == "__main__":
    _enable_dpi_awareness()

    # Single-instance guard: if already running, focus existing window and exit
    import ctypes as _ct
    _MUTEX_NAME = "POE2PickitGeneratorSingleInstance"
    _mutex = _ct.windll.kernel32.CreateMutexW(None, False, _MUTEX_NAME)
    if _ct.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        _hwnd = _ct.windll.user32.FindWindowW(None, f"ExileBot 2 Pickit Generator  v{VERSION}")
        if _hwnd:
            _ct.windll.user32.ShowWindow(_hwnd, 9)
            _ct.windll.user32.SetForegroundWindow(_hwnd)
        raise SystemExit(0)

    app = PickitApp()
    app.mainloop()
