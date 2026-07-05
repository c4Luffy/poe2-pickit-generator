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

import sys, os, re, json, time, shutil, threading, datetime, traceback, subprocess, importlib, hashlib, copy
from concurrent.futures import ThreadPoolExecutor as _TPE
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
from tkinter import font as tkfont

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
    from exilebot_pickit import generator as gen
    from exilebot_pickit.generators import assembly as asm
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing package",
        "exilebot_pickit package not found.\n"
        "Run:  pip install -e .")
    sys.exit(1)

try:
    import requests
except ImportError:
    _r = tk.Tk(); _r.withdraw()
    messagebox.showerror("Missing dependency",
        "Install requests:  pip install requests")
    sys.exit(1)

from exilebot_pickit.ui.config import (
    _cfg_dir, CONFIG_PATH, OUTPUT_DIR, ICON_DIR, PRICE_CACHE_DIR, WIKI_CACHE_FILE,
    DEFAULT_CONFIG, _default_poe2_filter_dir, load_config, save_config,
    log_info, log_exc, logger, LOG_PATH,
)

log_info(f"=== app start cfg_dir={_cfg_dir} ===")

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


from exilebot_pickit.ui.common import (
    ALL_CATEGORY_KEYS, BG, BG2, BG3, BORDER, FONT, FONT_BOLD, FONT_MONO, FONT_SM,
    GOLD, TEXT, TEXT_DIM, TEXT_ERR, TEXT_INFO, TEXT_OK, TEXT_WARN, _SegBar,
    _CBAR, _CBTN, _CHOV, _CSEL, _CSFG, _CON, _COFF, _CTXON, _CTXOF, _CONB, _COFB,
    _CWARN, _CTXWRN, _CWARNB, _CVAL,
    ACC_WARN_BG, ACC_WARN_FG, ACC_OK_BG, ROW_ALT,
    THEME, _PALETTES,
    _animate_border_glow, _card_hover_bind,
    btn, entry, label, scrolled_text, sep, switch,
    setup_styles, Tip,
)
from exilebot_pickit.ui.tabs.chance_bases import ChanceBasesTab
from exilebot_pickit.ui.tabs.craft_bases import CraftBasesTab


# ══════════════════════════════════════════════════════════════════════════════
#  Main Application
# ══════════════════════════════════════════════════════════════════════════════

TABS = ["Generate", "Economy", "Chance Bases", "Craft Bases", "Preview", "History", "Settings", "Debug"]

from exilebot_pickit.ui.updater import AutoUpdateMixin, VERSION

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


class PickitApp(tk.Tk, ChanceBasesTab, CraftBasesTab, AutoUpdateMixin):
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
        # when run from source it lives in the package's resources/ folder.
        try:
            _icon_dir = getattr(sys, "_MEIPASS", None) or os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "resources")
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
        self._last_output     = []
        self._preview_lines   = []
        self._generate_start  = 0.0
        self._tab_canvases    = {}
        self._active_canvas   = None

        # Self-updating game data: apply the last remote copy from disk before
        # the UI builds (so new unique categories get toggles), then fetch a
        # fresh copy in the background for next time. Best-effort — any failure
        # leaves the bundled data untouched.
        try:
            from exilebot_pickit.data import remote_data as _rd
            _rd.load_cached_game_data(PRICE_CACHE_DIR)
        except Exception:
            log_exc("load_cached_game_data")

        self._init_vars()
        self._log_buffer = []
        self._build_ui()
        try:
            _rd.refresh_game_data_async(
                PRICE_CACHE_DIR,
                done=lambda st: log_info(f"game data refresh: {st}"))
        except Exception:
            log_exc("refresh_game_data_async")
        self._fetch_leagues_async()
        self._check_update_async()
        threading.Thread(target=self._fetch_divine_rate_async, daemon=True).start()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-g>", lambda e: self._start_generate())
        self.bind_all("<Control-r>", lambda e: self._fetch_leagues_async())
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>",   self._on_wheel_up)
        self.bind_all("<Button-5>",   self._on_wheel_down)

        # If the settings file was unreadable, say so once instead of silently
        # starting over with defaults (the corrupt file is kept as .corrupt.bak).
        from exilebot_pickit.ui import config as _cfgmod
        if _cfgmod.CONFIG_LOAD_ERROR:
            self.after(600, lambda: messagebox.showwarning(
                "Settings reset", _cfgmod.CONFIG_LOAD_ERROR, parent=self))


    # ── Variable init ─────────────────────────────────────────────────────────

    def _init_vars(self):
        self.league_var       = tk.StringVar(value=self.cfg.get("league") or "")
        self.min_exalt_var      = tk.DoubleVar(value=self.cfg.get("min_exalt", 0.0))
        self.min_exalt_gear_var = tk.DoubleVar(value=self.cfg.get("min_exalt_gear", 0.0))
        self.min_exalt_unique_var = tk.DoubleVar(value=self.cfg.get("min_exalt_unique", 0.0))
        self.output_var       = tk.StringVar(value=self.cfg.get("output_base", "poe2_pickit"))
        self.bot_folder_var   = tk.StringVar(value=self.cfg.get("bot_folder", ""))
        self.auto_copy_var    = tk.BooleanVar(value=self.cfg.get("auto_copy", False))
        self.copy_filter_var  = tk.BooleanVar(value=self.cfg.get("copy_filter_to_game", False))
        self.poe2_filter_dir_var = tk.StringVar(
            value=self.cfg.get("poe2_filter_dir") or _default_poe2_filter_dir())
        self.backup_count_var = tk.IntVar(value=self.cfg.get("backup_count", 5))
        self.confirm_ovw_var  = tk.BooleanVar(value=self.cfg.get("confirm_overwrite_secs", 120) > 0)
        self.theme_var        = tk.StringVar(
            value="Light" if (self.cfg.get("theme") or "dark").lower() == "light" else "Dark")

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
        # Currency-table column sort: col None = the category's natural default order.
        self._cat_sort_col    = None
        self._cat_sort_dir    = "desc"
        self._item_prices     = {}   # {cat_key: {name: {ex, chaos, div}}}
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
        self._cat_sidebar_inds: dict = {}

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
        # Track icon resolution coverage for diagnostics.
        self._unresolved_icon_count = 0
        self._total_icon_count = 0
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
        header_lbl = tk.Label(hdr,
              text=f"  ⚔  ExileBot 2 Pickit Generator  v{VERSION}",
              fg=GOLD, bg=BG3, font=("Segoe UI", 13, "bold"), padx=16, pady=10,
              anchor="w")
        header_lbl.pack(side="left")
        # Gold accent line under header
        accent = tk.Frame(hdr, bg=GOLD, height=2)
        accent.pack(fill="x", side="bottom")
        self.status_lbl = label(hdr, "Ready", fg=TEXT_DIM, font=FONT_SM, bg=BG3, padx=16)
        self.status_lbl.pack(side="right")

        # Update banner (hidden until a newer version is found). The label is a
        # clickable, underlined link → opens the GitHub releases page; that's
        # the whole update flow now (no in-app download/swap — see updater.py).
        self._update_bar = tk.Frame(self, bg=ACC_WARN_BG, pady=4)
        _upd_font = (FONT_BOLD[0], FONT_BOLD[1], "bold underline")
        self._update_lbl = tk.Label(self._update_bar, text="", bg=ACC_WARN_BG,
                                    fg=ACC_WARN_FG, font=_upd_font, cursor="hand2")
        self._update_lbl.pack(side="left", padx=12)
        self._update_lbl.bind("<Button-1>", lambda e: self._open_releases())
        _close_btn = tk.Label(self._update_bar, text="✕", bg=ACC_WARN_BG, fg=TEXT_DIM,
                              font=FONT_SM, cursor="hand2")
        _close_btn.pack(side="right", padx=8)
        _close_btn.bind("<Button-1>", lambda e: self._update_bar.pack_forget())

        sep(self).pack(fill="x")

        # Update bar lives here (hidden by default — shown by _check_update_async)

        # Tab bar
        tab_bar = tk.Frame(self, bg=BG2)
        tab_bar.pack(fill="x")
        self._tab_btns = []
        self._tab_indicators = []
        for i, name in enumerate(TABS):
            tab_f = tk.Frame(tab_bar, bg=BG2)
            tab_f.pack(side="left")
            b = tk.Label(tab_f, text=name, bg=BG2, fg=TEXT_DIM,
                         font=FONT, padx=14, pady=8, cursor="hand2")
            b.pack(side="top")
            # Active indicator line (hidden by default)
            ind = tk.Frame(tab_f, bg=GOLD, height=2)
            ind.pack(side="bottom", fill="x")
            ind.pack_forget()  # hidden until active
            b.bind("<Button-1>", lambda e, idx=i: self._show_tab(idx))
            b.bind("<Enter>",    lambda e, w=b, idx=i: w.configure(fg=TEXT) if self._cur_tab != idx else None)
            b.bind("<Leave>",    lambda e, w=b, idx=i: w.configure(fg=TEXT_DIM) if self._cur_tab != idx else None)
            self._tab_btns.append(b)
            self._tab_indicators.append(ind)

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
                # Subtle border glow on the container
                _animate_border_glow(self._container, BORDER, f"{GOLD}33", steps=4, interval=15, restore=True)
            else:
                page.pack_forget()
        for i, b in enumerate(self._tab_btns):
            if i == idx:
                b.configure(bg=BG3, fg=GOLD)
                self._tab_indicators[i].pack(side="bottom", fill="x")
            else:
                b.configure(bg=BG2, fg=TEXT_DIM)
                self._tab_indicators[i].pack_forget()
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

    def _section_frame(self, parent, title, pady=(12, 0), icon=""):
        """A titled section card in the same visual language as the Settings
        group cards (icon + gold title header, divider, body). An empty *title*
        yields a plain headerless card."""
        if title:
            return self._settings_group(parent, icon, title)
        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=16, pady=pady)
        return card

    def _tab_desc(self, parent, text):
        """Thin description banner shown at the top of each tab."""
        bar = tk.Frame(parent, bg=BG3, highlightthickness=1, highlightbackground=BORDER,
                       padx=1, pady=1)
        bar.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(bar, text=text, bg=BG3, fg=TEXT_DIM, font=FONT_SM,
                 anchor="w", padx=12, pady=8, wraplength=900, justify="left").pack(fill="x")

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

    def _make_value_picker(self, parent, var, max_ex=500):
        """Minimum-value picker: a number box + an 'Exalt / Divine' unit dropdown.

        *var* always stores the value in Exalt (what generation uses); picking
        'Divine' just converts the typed amount using the live Divine rate for
        the selected league. Replaces the old slider, which was fiddly for
        picking exact values.
        """
        frame = tk.Frame(parent, bg=BG2)
        unit_var = tk.StringVar(value="Exalt")
        _updating = [False]     # guard against feedback loops

        def _div_rate():
            r = self._get_divine_rate(self._selected_league() or "")
            return r if r and r > 1.0 else None

        amount_var = tk.StringVar()

        def _var_to_box(*_):
            if _updating[0]:
                return
            try:
                ex = float(var.get())
            except (tk.TclError, ValueError):
                return
            _updating[0] = True
            try:
                if unit_var.get() == "Divine" and _div_rate():
                    amount_var.set(f"{ex / _div_rate():g}")
                else:
                    amount_var.set(f"{ex:g}")
            finally:
                _updating[0] = False

        def _box_to_var(*_):
            if _updating[0]:
                return
            txt = amount_var.get().strip().replace(",", ".")
            try:
                v = float(txt) if txt else 0.0
            except ValueError:
                return                       # mid-typing junk — ignore
            if unit_var.get() == "Divine" and _div_rate():
                v *= _div_rate()
            v = max(0.0, min(float(max_ex), v))
            _updating[0] = True
            try:
                var.set(v)
            finally:
                _updating[0] = False

        spin = ttk.Spinbox(frame, textvariable=amount_var, from_=0, to=max_ex,
                           increment=1, width=8, font=FONT)
        spin.pack(side="left", ipady=3)
        unit_cb = ttk.Combobox(frame, textvariable=unit_var, state="readonly",
                               values=("Exalt", "Divine"), width=8, font=FONT)
        unit_cb.pack(side="left", padx=(6, 0), ipady=3)
        Tip(spin, "Type the minimum value. 0 = no minimum (pick up everything).")
        Tip(unit_cb, "Choose the currency you want to type the value in. "
                     "It's converted with the live Divine rate either way.")

        # Wheel over the spinbox nudges the amount by 1 (in the shown unit).
        def _wheel(e):
            try:
                cur = float((amount_var.get() or "0").replace(",", "."))
            except ValueError:
                return "break"
            amount_var.set(f"{max(0.0, cur + (1 if e.delta > 0 else -1)):g}")
            return "break"
        spin.bind("<MouseWheel>", _wheel)

        unit_cb.bind("<<ComboboxSelected>>", _var_to_box)
        amount_var.trace_add("write", _box_to_var)
        var.trace_add("write", _var_to_box)
        _var_to_box()
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
            "Use the Economy tab to exclude specific items you don't want the bot to pick up.")

        # ── Pinned action footer (packed BEFORE the scroll area so it stays
        #    visible without scrolling — same pattern as the Settings tab) ─────
        footer = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        footer.pack(side="bottom", fill="x")

        # API status banner (hidden unless poe.ninja was unreachable)
        self.api_banner = tk.Label(
            footer, text="", bg=ACC_WARN_BG, fg=ACC_WARN_FG, font=FONT_SM,
            anchor="w", padx=12, pady=6, justify="left")
        # not packed yet — shown only when offline_mode is set

        fbar = tk.Frame(footer, bg=BG2)
        fbar.pack(fill="x", padx=14, pady=9)

        self.gen_btn = btn(fbar, "⚡  Generate  (Ctrl+G)",
                           self._start_generate, style="Gold.TButton")
        self.gen_btn.pack(side="left")
        Tip(self.gen_btn, "Fetch live prices and build your pickit now. Shortcut: Ctrl+G.")

        self.force_btn = btn(fbar, "⟳  Force Refresh", self._force_refresh_generate)
        self.force_btn.pack(side="left", padx=(8, 0))
        Tip(self.force_btn, "Re-download all prices from poe.ninja (ignore the cache), then generate.")

        self.open_ipd_btn = btn(fbar, ".ipd", lambda: self._open_file(".ipd"))
        self.open_ipd_btn.pack(side="left", padx=(8, 0))
        self.open_ipd_btn.configure(state="disabled")
        Tip(self.open_ipd_btn, "Open the pickit file you just generated.")

        self.open_filter_btn = btn(fbar, ".filter", lambda: self._open_file(".filter"))
        self.open_filter_btn.pack(side="left", padx=(6, 0))
        self.open_filter_btn.configure(state="disabled")
        Tip(self.open_filter_btn, "Open the in-game loot filter you just generated.")

        _open_out = btn(fbar, "📂  Output", self._open_output_folder)
        _open_out.pack(side="left", padx=(6, 0))
        Tip(_open_out, "Open the folder where your generated files are saved.")

        # Progress readout, right-aligned in the footer
        pf = tk.Frame(fbar, bg=BG2)
        pf.pack(side="right")
        self.progress_var = tk.StringVar(value="")
        self.progress_lbl = tk.Label(pf, textvariable=self.progress_var,
                                     bg=BG2, fg=TEXT_INFO, font=FONT_SM)
        self.progress_lbl.pack(side="left")
        self._progress_bar = ttk.Progressbar(pf, mode="determinate", length=140)
        # not packed yet — shown while a generate runs

        # Per-category segment bar spans the footer's full width during a run
        self._seg_bar = _SegBar(footer, bar_height=10)
        self._seg_bar.configure(bg=BG2)   # match the footer, not the page bg
        # not packed yet — shown while a generate runs

        inner, _ = self._scrollable(page)

        # ── League ───────────────────────────────────────────────────────────
        sec = self._section_frame(inner, "League", icon="🌐")
        label(sec, "Your active PoE2 economy league. Prices are fetched from poe.ninja for this league only. "
                   "Auto-detected on startup — hit ↻ to refresh if the list is wrong or a new league launched.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", padx=10, pady=(8, 2))
        row = tk.Frame(sec, bg=BG2)
        row.pack(fill="x", padx=10, pady=(4, 10))
        row.columnconfigure(0, weight=1)
        # readonly (not "normal"): leagues always come from the fetched list, and
        # readonly means clicking ANYWHERE on the box opens the dropdown — with
        # an editable box only the little arrow opened it, which felt broken.
        self.league_cb = ttk.Combobox(row, textvariable=self.league_var,
                                       state="readonly", font=FONT)
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
        # Switching league is heavyweight (badge reset + full preload) — don't
        # let a stray mousewheel over the box change it while the page scrolls.
        for _seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.league_cb.bind(_seq, lambda e: "break")

        # ── Profiles ─────────────────────────────────────────────────────────
        secp = self._section_frame(inner, "Profile", icon="👤")
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
        _p_save = btn(prow, "Save",   self._profile_save_current)
        _p_save.grid(row=0, column=1, padx=(0, 4))
        _p_del = btn(prow, "Delete", self._profile_delete)
        _p_del.grid(row=0, column=2, padx=(0, 4))
        _p_cmp = btn(prow, "Compare", self._profile_compare)
        _p_cmp.grid(row=0, column=3)
        Tip(_p_save, "Save the current settings and item selections as a named profile.")
        Tip(_p_del, "Delete the selected profile (your current settings stay).")
        Tip(_p_cmp, "Show two saved profiles side by side to see exactly how they differ.")
        self._refresh_profile_dropdown()

        # ── Output ───────────────────────────────────────────────────────────
        sec3 = self._section_frame(inner, "Output File", icon="💾")
        or_ = tk.Frame(sec3, bg=BG2)
        or_.pack(fill="x", padx=10, pady=10)
        label(or_, f"Saved to:  {OUTPUT_DIR}{os.sep}  (.ipd extension added automatically)",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(anchor="w", pady=(0, 6))
        or2 = tk.Frame(or_, bg=BG2)
        or2.pack(fill="x")
        or2.columnconfigure(0, weight=1)
        entry(or2, self.output_var).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        btn(or2, "Browse…", self._browse_output).grid(row=0, column=1)

        # ── Unique items value floor ─────────────────────────────────────────
        secu = self._section_frame(inner, "Unique Items — Only Pick Up If Worth At Least…", icon="💎")
        label(secu, "The bot skips any unique item priced below this value.  Type the amount "
                    "and pick the currency — Exalt or Divine, it's the same thing, just "
                    "converted with the live rate.  Leave it at 0 to pick up every unique.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2, wraplength=820, justify="left").pack(
                  anchor="w", padx=10, pady=(8, 2))
        urow = tk.Frame(secu, bg=BG2)
        urow.pack(fill="x", padx=10, pady=(2, 2))
        self._make_value_picker(urow, self.min_exalt_unique_var, max_ex=1000).pack(side="left")
        self._unique_conv_lbl = label(secu, "", fg=GOLD, font=FONT_SM, bg=BG2)
        self._unique_conv_lbl.pack(anchor="w", padx=10, pady=(0, 10))
        self.min_exalt_unique_var.trace_add("write", self._on_unique_floor_change)
        self.after(300, self._update_unique_conv)

        # ── Currency & everything else value floor ───────────────────────────
        secg = self._section_frame(inner, "Everything Else — Only Pick Up If Worth At Least…", icon="⚖")
        label(secg, "Same idea, but for everything that is not a unique: currency, essences, "
                    "fragments, runes, catalysts and so on.  Anything priced below this value "
                    "is skipped.  Leave it at 0 to pick up everything.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2, wraplength=820, justify="left").pack(
                  anchor="w", padx=10, pady=(8, 2))
        grow = tk.Frame(secg, bg=BG2)
        grow.pack(fill="x", padx=10, pady=(2, 2))
        self._make_value_picker(grow, self.min_exalt_gear_var, max_ex=500).pack(side="left")
        self._gear_conv_lbl = label(secg, "", fg=GOLD, font=FONT_SM, bg=BG2)
        self._gear_conv_lbl.pack(anchor="w", padx=10, pady=(0, 10))
        self.min_exalt_gear_var.trace_add("write", self._clamp_threshold_gear)
        self.min_exalt_gear_var.trace_add("write", lambda *_: self._update_gear_conv())
        self.after(300, self._update_gear_conv)

        # ── Stats row ─────────────────────────────────────────────────────────
        stats_f = tk.Frame(inner, bg=BG)
        stats_f.pack(fill="x", padx=10, pady=(14, 10))

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

        # Generate progress is routed to the Debug tab's log widget.
        # bottom spacer so the last section isn't flush against the window edge
        tk.Frame(inner, bg=BG, height=8).pack(fill="x")

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

    def _update_gear_conv(self, *_):
        """Divine/Chaos readout under the non-unique value picker, mirroring the
        unique one so both floors get the same at-a-glance conversion."""
        lbl = getattr(self, "_gear_conv_lbl", None)
        if lbl is None:
            return
        try:
            ex = float(self.min_exalt_gear_var.get())
        except (tk.TclError, ValueError):
            return
        if ex <= 0:
            lbl.configure(text="Picking up everything (no value floor).")
            return
        league   = self._selected_league() or ""
        div_rate = self._get_divine_rate(league)
        chaos_ex = self._get_chaos_ex_value(league)
        parts = []
        if div_rate and div_rate > 1.0:
            parts.append(f"{ex / div_rate:.2f} divine")
        if chaos_ex and chaos_ex > 0:
            parts.append(f"~{ex / chaos_ex:.0f} chaos")
        lbl.configure(text=("≈  " + "    ·    ".join(parts)) if parts
                      else "(Divine / Chaos equivalents shown once prices load)")

    # ══════════════════════════════════════════════════════════════════════════
    #  CATEGORIES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_categories_page(self, page):
        """Card-based category browser. Sidebar = categories, right = item grid."""
        self._tab_desc(page,
            "Everything the bot will pick up, grouped by category — pick a category on the left.  "
            "Every item is kept by default: click a card to turn it gray and exclude it, or use "
            "Search to find one fast.  Cards are sorted most-valuable first.")
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
        # Debounced: rebuilding the grid per keystroke froze the UI on short
        # queries ("e" matches hundreds of items across every category).
        self._cat_search_var.trace_add("write", self._cat_filter_soon)

        # Header card: title + count, divider, then both toolbar rows — one card
        # in the same language as Generate/Settings instead of loose bars.
        hdr_card = tk.Frame(right, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        hdr_card.pack(fill="x", padx=10, pady=(8, 6))
        hrow = tk.Frame(hdr_card, bg=BG2)
        hrow.pack(fill="x", padx=14, pady=(8, 8))
        tk.Label(hrow, textvariable=self._cat_header_var,
                 bg=BG2, fg=GOLD, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(hrow, textvariable=self._cat_count_var,
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="right")
        tk.Frame(hdr_card, bg=BORDER, height=1).pack(fill="x")

        # Row 1 — item actions: search, enable/disable, reset
        tbar = tk.Frame(hdr_card, bg=BG2)
        tbar.pack(fill="x", padx=14, pady=(8, 2))

        tk.Label(tbar, text="Search:", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        _search_e = entry(tbar, self._cat_search_var, width=16)
        _search_e.pack(side="left", padx=(4, 10), ipady=3)
        Tip(_search_e, "Type to filter this category's cards by name.")

        _ea = btn(tbar, "Enable All",  lambda: self._cat_items_set_all(True))
        _ea.pack(side="left", padx=(0, 3))
        _da = btn(tbar, "Disable All", lambda: self._cat_items_set_all(False))
        _da.pack(side="left", padx=(0, 3))
        _rs = btn(tbar, "Reset",       self._cat_items_reset)
        _rs.pack(side="left", padx=(0, 8))
        Tip(_ea, "Keep (pick up) every item in this category.")
        Tip(_da, "Exclude every item in this category.")
        Tip(_rs, "Undo your changes for this category and restore the defaults.")

        # Row 2 — value unit + refresh (right)
        tbar2 = tk.Frame(hdr_card, bg=BG2)
        tbar2.pack(fill="x", padx=14, pady=(0, 8))

        # Refresh = rightmost; pack it first so side="right" anchors it to the edge
        self._refresh_btn = btn(tbar2, "↻ Refresh", self._refresh_cat_prices)
        self._refresh_btn.pack(side="right", padx=(0, 4))
        Tip(self._refresh_btn, "Fetch fresh poe.ninja prices for the items shown here.")

        # Price unit selector — right side of row 2, just left of Refresh
        val_f = tk.Frame(tbar2, bg=BG2)
        val_f.pack(side="right", padx=(0, 10))
        Tip(val_f, "Show prices in Exalt, Chaos, or Divine. Display only — it doesn't change what gets picked.")
        tk.Label(val_f, text="Value:", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(0, 4))
        for unit_key, unit_label in (("ex", "Exalt"), ("chaos", "Chaos"), ("div", "Divine")):
            ub = tk.Frame(val_f, bg=BG3, highlightthickness=1, highlightbackground=BORDER,
                          cursor="hand2", padx=7, pady=3)
            lbl = tk.Label(ub, text=unit_label, bg=BG3, fg=TEXT_DIM,
                           font=FONT_SM)
            lbl.pack()
            ub._lbl = lbl
            ub.pack(side="left", padx=1)
            def _mk_cmd(u=unit_key):
                return lambda e=None: self._set_price_unit(u)
            ub.bind("<Button-1>", _mk_cmd(unit_key))
            lbl.bind("<Button-1>", _mk_cmd(unit_key))
            self._price_unit_btns[unit_key] = ub
        self._update_price_unit_btns()

        # ── Right: content switcher ───────────────────────────────────────────
        self._cat_right = tk.Frame(right, bg=BG)
        self._cat_right.pack(fill="both", expand=True)

        # Panel A: item grid (exchange categories)
        self._cat_grid_outer = tk.Frame(self._cat_right, bg=BG)

        self._cat_loading_lbl = tk.Label(self._cat_grid_outer,
            text="Select a category", bg=BG, fg=TEXT_DIM,
            font=("Segoe UI", 11))
        self._cat_loading_lbl.place(relx=0.5, rely=0.4, anchor="center")

        # Sticky table header (Item | Price | 7d | Keep) — sortable columns.
        self._build_cat_table_header(self._cat_grid_outer)

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
                    lambda e: (self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])
            _w.bind("<Button-4>",  lambda e: (self._cat_canvas.yview_scroll(-3, "units"), "break")[1])
            _w.bind("<Button-5>",  lambda e: (self._cat_canvas.yview_scroll( 3, "units"), "break")[1])

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
        sep_line = tk.Frame(sidebar, bg=GOLD, height=1)
        sep_line.pack(fill="x", padx=8)

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

        sep_line2 = tk.Frame(inner, bg=GOLD, height=1)
        sep_line2.pack(fill="x", padx=8, pady=4)
        self._cat_sidebar_btns["_gear"] = self._make_cat_btn(inner, "GEAR & BASES", "_gear")

    def _make_cat_btn(self, parent, text, key):
        frame = tk.Frame(parent, bg=_CBTN, cursor="hand2")

        # Active indicator dot (hidden by default)
        ind = tk.Frame(frame, bg=GOLD, width=3)
        ind.pack(side="left", fill="y")
        ind.pack_forget()
        self._cat_sidebar_inds[key] = ind

        lbl = tk.Label(frame, text=text, bg=_CBTN, fg=TEXT_DIM,
                       font=("Segoe UI", 9), anchor="w", padx=10, pady=8)
        lbl.pack(side="left", fill="x", expand=True)

        badge = tk.Label(frame, text="", bg=_CBTN, fg=TEXT_DIM,
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
            # Hide active indicator
            prev_ind = self._cat_sidebar_inds.get(self._active_cat)
            if prev_ind:
                prev_ind.pack_forget()

        self._active_cat = key

        # Highlight selected button
        if key in self._cat_sidebar_btns:
            bf = self._cat_sidebar_btns[key]
            bf.configure(bg=_CSEL)
            for c in bf.winfo_children():
                c.configure(bg=_CSEL)
                if isinstance(c, tk.Label):
                    c.configure(fg=_CSFG)
            # Show active indicator
            cur_ind = self._cat_sidebar_inds.get(key)
            if cur_ind:
                cur_ind.pack(side="left", fill="y")

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
            # Each category opens in its natural default order (sort resets on switch).
            self._cat_sort_col = None
            self._cat_sort_dir = "desc"
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

        # 3 workers, not 6 — poe.ninja's shared budget is ~12 req/5 min, and the
        # preload fires ~21 category requests; a gentler fan-out avoids 429s.
        with ThreadPoolExecutor(max_workers=3) as ex:
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

        # ── Sort: a user-chosen column if one is active, else the category default ─
        col = self._cat_sort_col
        if col is None:
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
                rows.sort(key=lambda r: -r[2])   # price High -> Low
        else:
            rev = (self._cat_sort_dir == "desc")
            if col == "name":
                rows.sort(key=lambda r: r[0].lower(), reverse=rev)
            elif col == "trend":
                rows.sort(key=lambda r: (self._pct_from_spark(r[5]) if self._pct_from_spark(r[5]) is not None
                                         else -9e99), reverse=rev)
            else:  # price
                rows.sort(key=lambda r: r[2], reverse=rev)

        self._item_prices[key] = {
            name: {"ex": ex, "chaos": chaos, "div": (ex / div_rate if div_rate else 0.0)}
            for name, chaos, ex, div_rate, _, _sp in rows
        }

        if key not in self._item_states:
            self._item_states[key] = {}
        states = self._item_states[key]
        self._cat_cards[key] = []

        # ── Flat render plan: section headers only appear in the natural (unsorted)
        #    order; once the user sorts a column the list goes flat. Each entry is
        #    ("header", text) or ("item", row_tuple). Rendered lazily in chunks so a
        #    big category never freezes the UI.
        grouped = (col is None)
        plan = []
        if grouped and key == "uncut_gems":
            _GEM_LABELS = {"Support": "Uncut Support Gems",
                           "Spirit":  "Uncut Spirit Gems",
                           "Skill":   "Uncut Skill Gems"}
            cur = None
            for row in rows:
                nm = row[0]
                gt = next((t for t in ("Support", "Spirit", "Skill") if f"Uncut {t} Gem" in nm), None)
                if gt != cur:
                    plan.append(("header", _GEM_LABELS.get(gt, gt or "")))
                    cur = gt
                plan.append(("item", row))
        elif grouped and key == "expedition":
            shown = False
            for row in rows:
                if "Thaumaturgic Flux" in row[0] and not shown:
                    plan.append(("header", "Thaumaturgic Flux"))
                    shown = True
                plan.append(("item", row))
        else:
            plan = [("item", row) for row in rows]

        self._cat_last_fetched[key] = datetime.datetime.now().strftime("%H:%M")
        self._cat_canvas.yview_moveto(0)
        self._update_cat_sort_header()

        seq   = self._cat_render_seq
        CHUNK = 30

        def _render_chunk(start=0):
            if seq != self._cat_render_seq or self._active_cat != key:
                return  # superseded by a newer populate/search/clear — abort
            end = min(start + CHUNK, len(plan))
            for kind, data in plan[start:end]:
                if kind == "header":
                    self._make_cat_section_header(self._cat_grid_frame, data)
                else:
                    (name, chaos, ex, _div_r, icon_url, sparkline) = data
                    div_val = ex / _div_r if _div_r else 0.0
                    enabled = states.get(name, {}).get("enabled", True)
                    pct = self._pct_from_spark(sparkline)
                    card = self._make_item_card(key, name, chaos, ex, div_val,
                                                icon_url, enabled, pct)
                    card.pack(in_=self._cat_grid_frame, fill="x")
                    tk.Frame(self._cat_grid_frame, bg=BORDER, height=1).pack(
                        in_=self._cat_grid_frame, fill="x")
                    self._cat_cards[key].append(card)
            self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
            if end < len(plan):
                self._cat_render_after = self.after(1, lambda: _render_chunk(end))
            else:
                # All rows built — finalize counts and start icon loading now that
                # every row exists for _apply_icon to find by name.
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
        # Global floor = the gear/exchange floor — the same value generation
        # uses (assembly.effective_min), so card warnings match the output.
        try:
            return self.min_exalt_gear_var.get()
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

    def _make_item_card(self, cat_key, name, chaos, ex_val, div_val, icon_url, enabled, pct=None):
        """One full-width table row: [icon + name] | price | 7d | keep-switch.

        Columns are aligned via a shared grid config (_cfg_table_cols) so values
        line up down the whole list. State (kept / excluded / excluded-but-valuable)
        is carried by the row background + the toggle switch."""
        bg, fg, _bdr, _dt, _df = self._card_colors(cat_key, ex_val, enabled)

        row = tk.Frame(self._cat_grid_frame, bg=bg, cursor="hand2")
        row._cat_key = cat_key
        row._name    = name
        row._enabled = enabled
        row._chaos   = chaos
        row._ex      = ex_val
        row._div     = div_val
        row._evar    = tk.BooleanVar(value=enabled)
        self._cfg_table_cols(row)

        # col 0 — icon + name (name elides with … when the column is too narrow)
        cell = tk.Frame(row, bg=bg)
        cell.grid(row=0, column=0, sticky="ew", padx=(8, 6), pady=4)
        row._cell = cell
        ph = tk.PhotoImage(width=26, height=26)
        ph.put(BG3, to=(0, 0, 26, 26))
        icon_lbl = tk.Label(cell, image=ph, bg=bg, width=26, height=26, bd=0)
        icon_lbl.pack(side="left", padx=(0, 9))
        icon_lbl._ph = ph
        row._icon_lbl = icon_lbl
        name_lbl = tk.Label(cell, text=name, bg=bg, fg=fg,
                            font=("Segoe UI", 10), anchor="w")
        name_lbl.pack(side="left", fill="x", expand=True)
        row._name_lbl = name_lbl
        self._bind_name_elide(name_lbl, name)

        # col 1 — price (right-aligned, tabular)
        val_lbl = tk.Label(row, text=self._fmt_price(chaos, ex_val, div_val),
                           bg=bg, fg=_CVAL, font=("Segoe UI", 10), anchor="e")
        val_lbl.grid(row=0, column=1, sticky="e", padx=(4, 10))
        row._val_lbl = val_lbl

        # col 2 — 7-day move (from the sparkline endpoints), green up / red down
        if pct is None:
            t_txt, t_fg = "—", TEXT_DIM
        else:
            t_txt = f"{'+' if pct >= 0 else '−'}{abs(pct) * 100:.0f}%"
            t_fg  = TEXT_OK if pct >= 0 else TEXT_ERR
        trend_lbl = tk.Label(row, text=t_txt, bg=bg, fg=t_fg,
                             font=("Segoe UI", 9), anchor="e")
        trend_lbl.grid(row=0, column=2, sticky="e", padx=(0, 12))
        row._trend_lbl = trend_lbl

        # col 3 — keep switch
        sw = switch(row, row._evar, bg_color=bg, switch_width=34, switch_height=17,
                    command=lambda f=row: self._set_item_enabled(f, f._evar.get()))
        sw.grid(row=0, column=3, sticky="e", padx=(0, 12))
        row._switch = sw

        def _click(e=None, f=row):
            f._evar.set(not f._evar.get())
            self._set_item_enabled(f, f._evar.get())
        def _right_click(e, f=row):
            self._copy_card_rule(f)
        def _scroll(e):
            self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units")
            return "break"   # stop the global bind_all handler double-scrolling

        clickable = [row, cell, icon_lbl, name_lbl, val_lbl, trend_lbl]
        for w in clickable:
            w.bind("<Button-1>", _click)
            w.bind("<Button-3>", _right_click)
            w.bind("<Button-2>", _right_click)
        for w in clickable + [sw]:
            w.bind("<MouseWheel>", _scroll)
            w.bind("<Button-4>",   lambda e: (self._cat_canvas.yview_scroll(-3, "units"), "break")[1])
            w.bind("<Button-5>",   lambda e: (self._cat_canvas.yview_scroll( 3, "units"), "break")[1])

        return row

    # ── Table helpers (column config, sticky header, sorting, state) ──────────

    def _cfg_table_cols(self, parent):
        """Shared column widths so every row (and the header) line up."""
        s = self._ui_scale
        parent.columnconfigure(0, weight=1)              # item (icon + name)
        parent.columnconfigure(1, minsize=int(94 * s))   # price
        parent.columnconfigure(2, minsize=int(58 * s))   # 7d move
        parent.columnconfigure(3, minsize=int(58 * s))   # keep switch

    def _build_cat_table_header(self, parent):
        """Sticky, sortable column header above the scrolling item list."""
        h = tk.Frame(parent, bg=BG2)
        self._cfg_table_cols(h)
        h.columnconfigure(4, minsize=int(12 * self._ui_scale))  # scrollbar gutter
        self._cat_sort_lbls = {}

        def _mk(col, text, gcol, anchor):
            lbl = tk.Label(h, text=text, bg=BG2, fg=TEXT_DIM,
                           font=("Segoe UI", 9, "bold"), cursor="hand2",
                           anchor=anchor, padx=8, pady=7)
            lbl.grid(row=0, column=gcol, sticky=("w" if anchor == "w" else "e"))
            lbl.bind("<Button-1>", lambda e, c=col: self._on_cat_sort(c))
            Tip(lbl, "Click to sort by this column.")
            self._cat_sort_lbls[col] = (lbl, text)

        _mk("name",  "ITEM",  0, "w")
        _mk("price", "PRICE", 1, "e")
        _mk("trend", "7D",    2, "e")
        tk.Label(h, text="KEEP", bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 9, "bold"),
                 anchor="e", padx=8, pady=7).grid(row=0, column=3, sticky="e")

        h.pack(side="top", fill="x", padx=(8, 0))            # match the canvas' left inset
        tk.Frame(parent, bg=BORDER, height=1).pack(side="top", fill="x")
        self._cat_table_header = h

    def _make_cat_section_header(self, parent, text):
        """Full-width gold section divider for grouped categories (gems, expedition)."""
        hdr = tk.Frame(parent, bg=_CBAR)
        lbl = tk.Label(hdr, text=text.upper(), bg=_CBAR, fg=GOLD,
                       font=("Segoe UI", 9, "bold"), padx=10, pady=5, anchor="w")
        lbl.pack(fill="x")
        hdr.pack(in_=parent, fill="x", pady=(8, 0))
        for w in (hdr, lbl):
            w.bind("<MouseWheel>",
                   lambda e: (self._cat_canvas.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])
        return hdr

    def _on_cat_sort(self, col):
        """Header click: toggle direction on the same column, else switch column."""
        if self._cat_sort_col == col:
            self._cat_sort_dir = "asc" if self._cat_sort_dir == "desc" else "desc"
        else:
            self._cat_sort_col = col
            self._cat_sort_dir = "desc" if col in ("price", "trend") else "asc"
        key = self._active_cat
        if not key or key == "_gear":
            return
        # Sorting while a search is active used to silently drop the query and
        # show the full category — keep the search results instead.
        if self._cat_cards.get("_search") is not None:
            self._update_cat_sort_header()
            self._cat_filter()
            return
        league  = self._selected_league() or "Mercenaries"
        payload = gen._cache_get(league, key)
        if payload and not isinstance(payload, Exception):
            self._populate_cat_grid(key, payload)

    def _update_cat_sort_header(self):
        """Reflect the active sort column/direction in the header labels."""
        lbls = getattr(self, "_cat_sort_lbls", None)
        if not lbls:
            return
        arrow = " ↓" if self._cat_sort_dir == "desc" else " ↑"
        for col, (lbl, text) in lbls.items():
            if self._cat_sort_col == col:
                lbl.configure(text=text + arrow, fg=GOLD)
            else:
                lbl.configure(text=text, fg=TEXT_DIM)

    @staticmethod
    def _pct_from_spark(sparkline):
        """7-day % change from a sparkline's first→last point, or None if unusable."""
        if sparkline and len(sparkline) >= 2 and sparkline[0] > 0:
            return (sparkline[-1] - sparkline[0]) / sparkline[0]
        return None

    def _bind_name_elide(self, lbl, full):
        """Truncate a row's item name with … to fit its column width (updates live)."""
        if not hasattr(self, "_name_font"):
            try:
                self._name_font = tkfont.Font(family="Segoe UI", size=10)
            except Exception:
                self._name_font = None
        f = self._name_font
        if f is None:
            return
        def _do(_e=None):
            w = lbl.winfo_width()
            if w <= 1:
                return
            if f.measure(full) <= w:
                if lbl.cget("text") != full:
                    lbl.configure(text=full)
                return
            s = full
            while s and f.measure(s + "…") > w:
                s = s[:-1]
            lbl.configure(text=(s + "…") if s else "…")
        lbl.bind("<Configure>", _do, add="+")

    def _set_item_enabled(self, frame, enabled):
        """Apply kept/excluded state to one row: persist + restyle + refresh counts."""
        key  = frame._cat_key
        name = frame._name
        if key not in self._item_states:
            self._item_states[key] = {}
        if enabled:
            self._item_states[key].pop(name, None)   # back to default (threshold-driven)
        else:
            self._item_states[key][name] = {"enabled": False}
        frame._enabled = enabled
        if frame._evar.get() != enabled:
            frame._evar.set(enabled)
        self._restyle_item_row(frame)
        self._update_cat_count(key)
        self._save_states_soon()

    def _restyle_item_row(self, card):
        """Recolour a row from its current _enabled state (bg / text / switch)."""
        try:
            if not card.winfo_exists():
                return   # stale reference to a destroyed row (e.g. cleared search grid)
        except Exception:
            return
        bg, fg, _bdr, _dt, _df = self._card_colors(card._cat_key, card._ex, card._enabled)
        for w in (card, getattr(card, "_cell", None), card._icon_lbl,
                  card._name_lbl, card._val_lbl, card._trend_lbl):
            if w is not None:
                try:
                    w.configure(bg=bg)
                except Exception:
                    pass
        card._name_lbl.configure(fg=fg)
        try:
            card._switch.configure(bg_color=bg)
        except Exception:
            pass

    def _copy_card_rule(self, frame):
        name = frame._name
        rule = f'[Type] == "{name}" # [StashItem] == "true"'
        self.clipboard_clear()
        self.clipboard_append(rule)
        # Brief visual flash on the card
        orig_bg = frame.cget("bg")
        frame.configure(bg=ACC_OK_BG)
        for w in frame.winfo_children():
            try:
                w.configure(bg=ACC_OK_BG)
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
                badge.configure(text="", fg=TEXT_DIM)  # not fetched yet

    # ── Price unit switching ──────────────────────────────────────────────────

    def _set_api_banner(self, offline: bool):
        """Show or hide the 'poe.ninja unreachable' banner on the Generate tab."""
        banner = getattr(self, "api_banner", None)
        if banner is None:
            return
        if offline:
            banner.configure(text="⚠  poe.ninja was unreachable — this pickit used cached prices. "
                               "They may be out of date. Try Force Refresh when the site is back up.")
            # Banner lives in the Generate footer now — pin it above the button row.
            banner.pack(fill="x", before=self.gen_btn.master)
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
                b.configure(bg=GOLD, highlightbackground=GOLD)
                b._lbl.configure(bg=GOLD, fg="#111")
            else:
                b.configure(bg=BG3, highlightbackground=BORDER)
                b._lbl.configure(bg=BG3, fg=TEXT_DIM)

    # ── Search / enable-all / disable-all ────────────────────────────────────

    def _cat_filter_soon(self, *_, delay=250):
        """Debounce the search trace — rebuild the grid once typing pauses."""
        if getattr(self, "_search_after_id", None):
            try:
                self.after_cancel(self._search_after_id)
            except Exception:
                pass
        self._search_after_id = self.after(delay, self._cat_filter)

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
            self._make_cat_section_header(self._cat_grid_frame, cat_label)
            states = self._item_states.get(cat_key, {})
            for name, data in matches:
                enabled = states.get(name, {}).get("enabled", True)
                card = self._make_item_card(
                    cat_key, name,
                    data.get("chaos", 0), data.get("ex", 0), data.get("div", 0),
                    self._wiki_icon_cache.get(name, ""), enabled)
                card.pack(in_=self._cat_grid_frame, fill="x")
                tk.Frame(self._cat_grid_frame, bg=BORDER, height=1).pack(
                    in_=self._cat_grid_frame, fill="x")
                self._cat_cards["_search"].append(card)

        if not found_any:
            tk.Label(self._cat_grid_frame, text="No results",
                     bg=BG, fg=TEXT_DIM, font=("Segoe UI", 11)).pack(pady=30)

        self._cat_canvas.configure(scrollregion=self._cat_canvas.bbox("all"))
        self._cat_canvas.yview_moveto(0)

        # Show cached icons for search results — through a small shared pool,
        # not a thread per card (a broad query used to spawn dozens at once).
        _jobs = [(card._name, self._wiki_icon_cache.get(card._name, ""))
                 for card in self._cat_cards["_search"]]
        _jobs = [(n, u) for n, u in _jobs if u]
        if _jobs:
            def _fetch_batch(jobs=_jobs):
                with _TPE(max_workers=4) as pool:
                    for n, u in jobs:
                        pool.submit(self._fetch_icon, "_search", n, u)
            threading.Thread(target=_fetch_batch, daemon=True).start()

        count = len(self._cat_cards["_search"])
        self._cat_count_var.set(f"{count} result{'s' if count != 1 else ''} across all categories")

    def _cat_items_set_all(self, enabled: bool):
        key = self._active_cat
        if not key or key == "_gear":
            return

        # During a global search, apply to the visible results (across whatever
        # categories they belong to) — the per-category card list holds destroyed
        # widgets while searching, so acting on it silently did nothing.
        search_cards = self._cat_cards.get("_search")
        if search_cards is not None:
            for card in search_cards:
                ck = card._cat_key
                card._enabled = enabled
                card._evar.set(enabled)
                if enabled:
                    self._item_states.get(ck, {}).pop(card._name, None)
                else:
                    self._item_states.setdefault(ck, {})[card._name] = {"enabled": False}
                self._restyle_item_row(card)
            self._save_states_soon()
            return

        if enabled:
            self._item_states.pop(key, None)   # clear exclusions → items follow threshold
        else:
            self._item_states.setdefault(key, {})
        for card in self._cat_cards.get(key, []):
            card._enabled = enabled
            card._evar.set(enabled)
            if not enabled:
                self._item_states[key][card._name] = {"enabled": False}
            self._restyle_item_row(card)
        self._update_cat_count(key)
        self._save_states_soon()

    def _cat_items_reset(self):
        """Reset all item states for the current category to default (all kept)."""
        key = self._active_cat
        if not key or key == "_gear":
            return
        if self._cat_cards.get("_search") is not None:
            # Reset the visible search results back to kept
            self._cat_items_set_all(True)
            return
        self._item_states.pop(key, None)
        for card in self._cat_cards.get(key, []):
            card._enabled = True
            card._evar.set(True)
            self._restyle_item_row(card)
        self._update_cat_count(key)
        self._save_states_soon()

    # ── Min price filter ──────────────────────────────────────────────────────

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
            "item_states":         copy.deepcopy(self._item_states),
            "min_exalt":           min_ex,
            "min_exalt_gear":      min_gear,
            "min_exalt_unique":    min_unique,
            "output_base":         self.output_var.get(),
            "include_bases":       self.include_bases_var.get(),
            "base_quality":        self.base_quality_var.get(),
            "base_min_level":      self.base_min_level_var.get(),
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
        self.include_bases_var.set(prof.get("include_bases", True))
        self.base_quality_var.set(prof.get("base_quality", 28))
        self.base_min_level_var.set(prof.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))

        self.cfg["item_states"]       = self._item_states
        self.cfg["include_bases"]     = self.include_bases_var.get()
        self.cfg["base_quality"]      = self.base_quality_var.get()
        self.cfg["base_min_level"]    = self.base_min_level_var.get()
        self.cfg["active_profile"]    = name
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

    # ── Profile compare dialog ────────────────────────────────────────────────

    def _profile_compare(self):
        """Side-by-side diff of two saved profiles."""
        names = sorted(self._profiles.keys())
        if len(names) < 2:
            messagebox.showinfo("Compare Profiles",
                                "Save at least two profiles to compare them.",
                                parent=self)
            return

        win = tk.Toplevel(self)
        win.title("Compare Profiles")
        win.configure(bg=BG)
        win.geometry("900x640")
        win.minsize(700, 400)
        win.transient(self)
        win.grab_set()

        # ── Top: selection row ────────────────────────────────────────────────
        top = tk.Frame(win, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text="Profile A:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        cb_a = ttk.Combobox(top, values=names, state="readonly", font=FONT, width=20)
        cb_a.pack(side="left", padx=(4, 16))
        cb_a.set(names[0])
        tk.Label(top, text="Profile B:", bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        cb_b = ttk.Combobox(top, values=names, state="readonly", font=FONT, width=20)
        cb_b.pack(side="left", padx=(4, 10))
        cb_b.set(names[1] if len(names) > 1 else names[0])

        def _run_compare(*_):
            self._profile_compare_render(win, cb_a.get(), cb_b.get())
        btn(top, "Compare", _run_compare).pack(side="left", padx=(10, 0))
        btn(top, "Close", win.destroy).pack(side="right")

        # ── Results area ──────────────────────────────────────────────────────
        self._profile_compare_render(win, cb_a.get(), cb_b.get())

    def _profile_compare_render(self, win, name_a, name_b):
        """Populate the compare dialog with diff rows."""
        pa = self._profiles.get(name_a, {})
        pb = self._profiles.get(name_b, {})
        if not pa or not pb:
            return

        # Find or create results frame
        old = getattr(win, "_cmp_frame", None)
        if old:
            old.destroy()

        body = tk.Frame(win, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=(6, 16))
        win._cmp_frame = body

        # Scrollable area for long diffs
        cv = tk.Canvas(body, bg=BG, highlightthickness=0)
        sb = tk.Scrollbar(body, orient="vertical", command=cv.yview,
                          bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        cv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(cv, bg=BG)
        win_id = cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.bind("<Configure>", lambda e: cv.itemconfig(win_id, width=e.width))

        # ── Build diff rows ───────────────────────────────────────────────────
        rows = []

        def _add(label, val_a, val_b, changed=None):
            """changed: True=different, False=same, None=non-comparable"""
            if changed is None:
                changed = val_a != val_b
            rows.append((label, str(val_a), str(val_b), changed))

        _add("Min Exalt (exchange)", pa.get("min_exalt", 0), pb.get("min_exalt", 0))
        _add("Min Exalt (gear)", pa.get("min_exalt_gear", 0), pb.get("min_exalt_gear", 0))
        _add("Min Exalt (unique)", pa.get("min_exalt_unique", 0), pb.get("min_exalt_unique", 0))
        _add("Output file", pa.get("output_base", ""), pb.get("output_base", ""))
        _add("Include bases", pa.get("include_bases", True), pb.get("include_bases", True))
        _add("Base quality", pa.get("base_quality", 28), pb.get("base_quality", 28))
        _add("Base min ilvl", pa.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL), pb.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))

        # Item states diff
        sa = pa.get("item_states", {})
        sb_ = pb.get("item_states", {})
        cats_a = set(sa.keys())
        cats_b = set(sb_.keys())
        _add("Item-state categories (A)", len(sa), len(sb_))
        only_a = cats_a - cats_b
        only_b = cats_b - cats_a
        if only_a:
            _add("  Only in A", ", ".join(sorted(only_a)[:6]) + ("…" if len(only_a) > 6 else ""), "—", True)
        if only_b:
            _add("  Only in B", "—", ", ".join(sorted(only_b)[:6]) + ("…" if len(only_b) > 6 else ""), True)
        for cat in sorted(cats_a & cats_b):
            items_a = set(sa[cat].keys())
            items_b = set(sb_[cat].keys())
            if items_a != items_b:
                added = items_b - items_a
                removed = items_a - items_b
                parts = []
                if removed:
                    parts.append(f"-{len(removed)}")
                if added:
                    parts.append(f"+{len(added)}")
                _add(f"  {cat}", ", ".join(sorted(removed)[:3]) if removed else "—",
                      ", ".join(sorted(added)[:3]) if added else "—", True)

        # ── Render ────────────────────────────────────────────────────────────
        hdr = tk.Frame(inner, bg=BG3)
        hdr.pack(fill="x", pady=(0, 4))
        for _col, w, txt in (
            (0, 260, "Setting"), (1, 140, name_a), (2, 140, name_b)
        ):
            tk.Label(hdr, text=txt, bg=BG3, fg=GOLD, font=FONT_BOLD,
                     anchor="w", padx=10, pady=6, width=w//7).pack(side="left")
        sep_line = tk.Frame(inner, bg=BORDER, height=1)
        sep_line.pack(fill="x")

        for lbl, va, vb, changed in rows:
            row_f = tk.Frame(inner, bg=BG if changed else BG2)
            row_f.pack(fill="x")
            for _col, w, txt in ((0, 260, lbl), (1, 140, va), (2, 140, vb)):
                fg_col = TEXT if _col == 0 or not changed else (TEXT_ERR if _col == 1 else TEXT_OK)
                tk.Label(row_f, text=txt, bg=BG if changed else BG2, fg=fg_col,
                         font=FONT_SM, anchor="w", padx=10, pady=3, width=w//7).pack(side="left")
            if changed and lbl.strip():
                tk.Label(row_f, text="≠", bg=BG, fg=GOLD,
                         font=FONT_BOLD).pack(side="left", padx=(0, 6))

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
                log_exc("wiki batch query")
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
                    log_exc("wiki cache write")

        # Track resolution coverage for diagnostics.
        self._total_icon_count += len(names)
        self._unresolved_icon_count += sum(
            1 for n in names if not self._wiki_icon_cache.get(n)
        )

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

    # Only fetch icons from hosts we expect (wiki + official CDN). The URL comes
    # from wiki JSON (and is replayed from the on-disk cache), so gate it before
    # handing the bytes to Pillow — this also caps the image-parsing attack surface.
    _ICON_HOSTS = ("poe2wiki.net", "poecdn.com")
    _ICON_MAX_BYTES = 2 * 1024 * 1024   # 2 MB is generous for a 26px item icon

    @classmethod
    def _icon_url_ok(cls, url: str) -> bool:
        try:
            from urllib.parse import urlparse
            p = urlparse(url)
            host = (p.hostname or "").lower()
            return p.scheme == "https" and any(
                host == h or host.endswith("." + h) for h in cls._ICON_HOSTS)
        except Exception:
            return False

    def _fetch_icon(self, key, name, url):
        """Worker thread: download icon → apply to matching card."""
        if not url or not self._icon_url_ok(url):
            return
        try:
            slug = hashlib.md5(url.encode()).hexdigest()[:16]
            path = os.path.join(ICON_DIR, slug + ".png")
            if not os.path.exists(path):
                r = requests.get(url, timeout=10, headers=self._ICON_HEADERS, stream=True)
                if r.status_code == 200 and r.headers.get("Content-Type", "").startswith("image"):
                    buf, total = [], 0
                    for chunk in r.iter_content(65536):
                        total += len(chunk)
                        if total > self._ICON_MAX_BYTES:   # oversized — bail, don't cache
                            buf = None
                            break
                        buf.append(chunk)
                    if buf is not None:
                        # Atomic write so a crash can't cache a truncated PNG forever
                        tmp = path + ".tmp"
                        with open(tmp, "wb") as f:
                            f.write(b"".join(buf))
                        os.replace(tmp, path)
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
        self._save_after_id = None
        self.cfg["item_states"] = self._item_states
        save_config(self.cfg)

    def _save_states_soon(self, delay=300):
        """Debounced full-config save — bulk actions (Enable All etc.) fire one
        handler per row; this coalesces them into a single disk write. Closing
        the app saves synchronously anyway (_quit_app -> save_config)."""
        if getattr(self, "_save_after_id", None):
            try:
                self.after_cancel(self._save_after_id)
            except Exception:
                pass
        self._save_after_id = self.after(delay, self._save_states_now)

    # ── Gear & Bases panel (existing controls) ────────────────────────────────

    # Per-category floor chips ("Global floor") were removed 2026-07 per the
    # project owner: one value floor on the Generate tab is easier to reason
    # about. The −1 sentinel in cat_thresh is kept so old configs stay valid
    # (−1 = follow the Generate-tab floor, which is now always the case).
    def _build_cat_gear_panel(self, parent):
        """The old-style panel for unique categories and base types."""
        inner, c = self._scrollable(parent)
        self._cat_gear_canvas = c

        def cat_group(grp_label, cats, unique=False, desc="", icon="💎"):
            body = self._settings_group(inner, icon, grp_label)
            if desc:
                label(body, desc, fg=TEXT_DIM, font=FONT_SM, bg=BG2,
                      wraplength=820, justify="left").pack(
                    anchor="w", padx=10, pady=(8, 4))
            row_bg = ROW_ALT if unique else BG2
            for key, _, lbl_text, _ in cats:
                row = tk.Frame(body, bg=row_bg,
                               highlightthickness=1, highlightbackground=BORDER)
                row.pack(fill="x", padx=10, pady=(0, 4))
                _card_hover_bind(row, row_bg, row_bg)
                tk.Label(row, text=lbl_text, bg=row_bg, fg=TEXT, font=FONT).pack(
                    side="left", padx=10, pady=7)
                sw = switch(row, self.cat_enabled[key], bg_color=row_bg)
                sw.pack(side="right", padx=(6, 10))
                Tip(sw, "On = this whole category goes into the pickit. "
                        "The minimum value from the Generate tab decides which "
                        "items in it are worth picking up.")

        cat_group("Unique Item Categories", gen.UNIQUE_CATEGORIES, unique=True,
                  desc="Turn whole groups of unique items on or off.  Each unique is matched "
                       "by its exact name, priced live from poe.ninja, and kept only if it "
                       "meets the minimum value you set on the Generate tab — new uniques "
                       "added in game patches show up here automatically on the next run.")

        # Base Types
        sec_b = self._section_frame(inner, "High-End Gear Bases (non-unique)", icon="🧱")
        label(sec_b,
              "Also pick up ordinary (non-unique) endgame gear that is worth keeping because "
              "of high quality or extra sockets — good for selling, crafting or vendoring.  "
              "These have no market price, so the minimum value from the Generate tab does "
              "not apply here; the quality / item-level limits below decide what's kept.\n\n"
              "Example rule this adds:   pick up an \"Ornate Plate\" if its quality is 28%+ "
              "or it has 3+ sockets, at item level 82.",
              fg=TEXT_DIM, font=FONT_SM, bg=BG2, wraplength=820, justify="left").pack(
                  anchor="w", padx=10, pady=(8, 4))

        inc_row = tk.Frame(sec_b, bg=BG2)
        inc_row.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(inc_row, text="Pick up high-end gear bases",
                 bg=BG2, fg=TEXT, font=FONT).pack(side="left")
        switch(inc_row, self.include_bases_var).pack(side="right", padx=(12, 0))

        qrow = tk.Frame(sec_b, bg=BG2)
        qrow.pack(anchor="w", padx=10, pady=(0, 10))
        label(qrow, "Min quality:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        _bq_e = entry(qrow, self.base_quality_var, width=5)
        _bq_e.pack(side="left", padx=(6, 4), ipady=4)
        Tip(_bq_e, "Only keep these bases if they have at least this quality %.")
        label(qrow, "%", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left")
        label(qrow, "   Min item level:", fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(
            side="left", padx=(16, 0))
        _bml_e = entry(qrow, self.base_min_level_var, width=5)
        _bml_e.pack(side="left", padx=(6, 4), ipady=4)
        Tip(_bml_e, "Only keep these bases at this item level or higher (82 is the max).")
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

        # Pinned footer: filter + counts on the left, actions on the right —
        # the rule text above gets the rest of the page.
        footer = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        footer.pack(side="bottom", fill="x")
        ctrl = tk.Frame(footer, bg=BG2)
        ctrl.pack(fill="x", padx=14, pady=8)
        label(ctrl, "Filter:", fg=TEXT_DIM, font=FONT, bg=BG2).pack(side="left", padx=(0, 6))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", self._filter_preview)
        _pv_filter = entry(ctrl, self.filter_var, width=28)
        _pv_filter.pack(side="left", ipady=4)
        Tip(_pv_filter, "Show only lines containing this text — an item name or any keyword.")
        self.preview_count_var = tk.StringVar(value="Generate to see rules")
        label(ctrl, "", textvariable=self.preview_count_var,
              fg=TEXT_DIM, font=FONT_SM, bg=BG2).pack(side="left", padx=(12, 0))
        _pv_copy = btn(ctrl, "Copy all", self._preview_copy, style="Gold.TButton")
        _pv_copy.pack(side="right")
        _pv_val = btn(ctrl, "Re-validate", self._revalidate)
        _pv_val.pack(side="right", padx=(0, 6))
        Tip(_pv_copy, "Copy the whole pickit file to your clipboard.")
        Tip(_pv_val, "Re-check the pickit for syntax errors and show the results above.")

        pf, self.preview_text = scrolled_text(page, state="disabled")
        pf.pack(fill="both", expand=True, padx=16, pady=(10, 10))
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
        # Pinned footer: the destructive action lives here, out of the content flow.
        footer = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        footer.pack(side="bottom", fill="x")
        fbar = tk.Frame(footer, bg=BG2)
        fbar.pack(fill="x", padx=14, pady=8)
        _clr_hist = btn(fbar, "🗑  Clear history", self._clear_history)
        _clr_hist.pack(side="right")
        Tip(_clr_hist, "Delete all saved run history and the chart. This can't be undone.")

        # Run table, in a titled card
        tcard = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        tcard.pack(fill="both", expand=True, padx=16, pady=(12, 0))
        thdr = tk.Frame(tcard, bg=BG2)
        thdr.pack(fill="x", padx=14, pady=9)
        tk.Label(thdr, text="🕘", bg=BG2, fg=GOLD, font=("Segoe UI", 13)).pack(side="left", padx=(0, 9))
        tk.Label(thdr, text="Run history", bg=BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(thdr, text="last 50 runs", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="right")
        tk.Frame(tcard, bg=BORDER, height=1).pack(fill="x")
        cols = ("Date/time", "Active", "Commented", "Divine rate", "Top item", "Duration")
        self._hist_tree = ttk.Treeview(tcard, columns=cols, show="headings", height=10)
        for c in cols:
            self._hist_tree.heading(c, text=c)
            self._hist_tree.column(c, width=120, anchor="w")
        self._hist_tree.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        # Sparkline chart, same card language
        chart_frame = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        chart_frame.pack(fill="x", padx=16, pady=(12, 12))
        chdr = tk.Frame(chart_frame, bg=BG2)
        chdr.pack(fill="x", padx=14, pady=9)
        tk.Label(chdr, text="📈", bg=BG2, fg=GOLD, font=("Segoe UI", 13)).pack(side="left", padx=(0, 9))
        tk.Label(chdr, text="Active rules over time", bg=BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Frame(chart_frame, bg=BORDER, height=1).pack(fill="x")
        self._hist_canvas = tk.Canvas(chart_frame, bg=BG2, height=80,
                                      highlightthickness=0, bd=0)
        self._hist_canvas.pack(fill="x", padx=10, pady=(4, 8))

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
        c.create_polygon(poly, fill=ACC_OK_BG, outline="")

        # Line + dots
        for i in range(len(pts) - 1):
            c.create_line(_x(i), _y(pts[i]), _x(i+1), _y(pts[i+1]),
                          fill=TEXT_OK, width=2)
        for i, v in enumerate(pts):
            c.create_oval(_x(i)-3, _y(v)-3, _x(i)+3, _y(v)+3,
                          fill=TEXT_OK, outline="")

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

    # ── Settings-page building blocks (Windows 11 / Discord-style cards) ───────

    def _settings_group(self, parent, icon, title, collapsible=False, expanded=True):
        """A titled settings card. Returns the body frame to pack rows into.
        When *collapsible*, the header row toggles the body via a chevron."""
        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=16, pady=(14, 0))

        header = tk.Frame(card, bg=BG2, cursor="hand2" if collapsible else "arrow")
        header.pack(fill="x", padx=14, pady=11)
        tk.Label(header, text=icon, bg=BG2, fg=GOLD,
                 font=("Segoe UI", 13)).pack(side="left", padx=(0, 9))
        tk.Label(header, text=title, bg=BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(side="left")

        body    = tk.Frame(card, bg=BG2)
        divider = tk.Frame(card, bg=BORDER, height=1)

        if collapsible:
            chev = tk.Label(header, text="▾" if expanded else "▸",
                            bg=BG2, fg=TEXT_DIM, font=FONT_BOLD)
            chev.pack(side="right")
            state = {"open": expanded}
            def _toggle(_e=None):
                state["open"] = not state["open"]
                if state["open"]:
                    divider.pack(fill="x")
                    body.pack(fill="x")
                    chev.configure(text="▾")
                else:
                    body.pack_forget()
                    divider.pack_forget()
                    chev.configure(text="▸")
            for w in (header, *header.winfo_children()):
                w.bind("<Button-1>", _toggle)
            if expanded:
                divider.pack(fill="x")
                body.pack(fill="x")
        else:
            divider.pack(fill="x")
            body.pack(fill="x")
        return body

    def _settings_toggle_row(self, parent, title, subtitle, var, command=None):
        """A row: title + subtitle on the left, a toggle switch on the right."""
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill="x", padx=14, pady=8)
        switch(row, var, command=command).pack(side="right", padx=(12, 0))
        txt = tk.Frame(row, bg=BG2)
        txt.pack(side="left", fill="x", expand=True)
        tk.Label(txt, text=title, bg=BG2, fg=TEXT, font=FONT).pack(anchor="w")
        if subtitle:
            tk.Label(txt, text=subtitle, bg=BG2, fg=TEXT_DIM, font=FONT_SM,
                     anchor="w", justify="left", wraplength=680).pack(anchor="w", pady=(1, 0))
        return row

    def _settings_path_row(self, parent, title, var, browse_cmd, subtitle=""):
        """A titled folder row: label, optional subtitle, entry + Browse button."""
        block = tk.Frame(parent, bg=BG2)
        block.pack(fill="x", padx=14, pady=8)
        tk.Label(block, text=title, bg=BG2, fg=TEXT, font=FONT).pack(anchor="w")
        if subtitle:
            tk.Label(block, text=subtitle, bg=BG2, fg=TEXT_DIM, font=FONT_SM,
                     anchor="w", justify="left", wraplength=740).pack(anchor="w", pady=(1, 5))
        r = tk.Frame(block, bg=BG2)
        r.pack(fill="x", pady=(4, 0))
        r.columnconfigure(0, weight=1)
        entry(r, var).grid(row=0, column=0, sticky="ew", ipady=4, padx=(0, 6))
        btn(r, "Browse…", browse_cmd).grid(row=0, column=1)

    def _settings_divider(self, parent):
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", padx=14, pady=2)

    def _build_settings_page(self, page):
        self._tab_desc(page,
            "Connect the generator to your bot and tune how files are saved.  "
            "Changes apply when you click Save settings.")

        # Fixed action bar pinned to the bottom (packed BEFORE the scroll area so it
        # stays visible without scrolling — VS Code / Windows 11 style).
        footer = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        footer.pack(side="bottom", fill="x")
        fbar = tk.Frame(footer, bg=BG2)
        fbar.pack(fill="x", padx=16, pady=10)
        btn(fbar, "Save settings", self._save_settings, style="Gold.TButton").pack(side="left")
        btn(fbar, "Reset to defaults", self._reset_defaults).pack(side="left", padx=(8, 0))
        self._settings_saved_lbl = tk.Label(fbar, text="", bg=BG2, fg=TEXT_OK, font=FONT_SM)
        self._settings_saved_lbl.pack(side="left", padx=(12, 0))

        inner, _ = self._scrollable(page)

        # ── Appearance ───────────────────────────────────────────────────────
        g = self._settings_group(inner, "🎨", "Appearance")
        tk.Label(g, text="Choose the app's colour theme. Applied on restart — the colours are "
                         "fixed when the app launches.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, anchor="w", justify="left",
                 wraplength=760).pack(anchor="w", padx=14, pady=(2, 2))
        self._settings_theme_cards(g)
        self._theme_hint = tk.Label(g, text="", bg=BG2, fg=TEXT_WARN, font=FONT_SM,
                                    anchor="w", justify="left")
        self._theme_hint.pack(anchor="w", padx=14, pady=(2, 0))
        arow = tk.Frame(g, bg=BG2)
        arow.pack(fill="x", padx=14, pady=(6, 11))
        _rb = btn(arow, "↻ Restart now", self._restart_app)
        _rb.pack(side="left")
        Tip(_rb, "Save settings and relaunch so the new theme takes effect.")
        self._update_theme_hint()

        # ── Bot integration (most-used) ──────────────────────────────────────
        g = self._settings_group(inner, "🤖", "Bot Integration")
        self._settings_path_row(g, "Exiled Bot 2 pickit folder", self.bot_folder_var,
            self._browse_bot_folder,
            "Where the bot reads its pickit from. The generated .ipd is deployed here.")
        self._settings_divider(g)
        self._settings_toggle_row(g, "Auto-copy .ipd after generate",
            "Deploy the pickit to the bot folder automatically on every run.",
            self.auto_copy_var, command=self._update_autocopy_hint)
        # Inline warning: on but no (valid) folder → the copy would silently no-op.
        self._autocopy_hint = tk.Label(g, text="", bg=BG2, fg=TEXT_WARN, font=FONT_SM,
                                       anchor="w", justify="left", wraplength=760)
        self.bot_folder_var.trace_add("write", lambda *_: self._update_autocopy_hint())
        self._update_autocopy_hint()

        # ── In-game loot filter (manual play only) ───────────────────────────
        g = self._settings_group(inner, "🎮", "In-Game Loot Filter")
        tk.Label(g, text="A matching .filter is written next to the .ipd on every run. "
                         "Turning this on also copies it into your PoE2 folder so you can "
                         "select it in-game.  ⚠ Leave OFF while botting — a filter that "
                         "hides items can make the bot walk to drops it can't pick up.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, anchor="w", justify="left",
                 wraplength=760).pack(anchor="w", padx=14, pady=(8, 2))
        self._settings_toggle_row(g, "Copy .filter to the game folder after generate",
            "For watching your own screen during manual play — not for bot use.",
            self.copy_filter_var)
        self._settings_divider(g)
        self._settings_path_row(g, "Path of Exile 2 filter folder", self.poe2_filter_dir_var,
            self._browse_filter_folder,
            "Usually Documents \\ My Games \\ Path of Exile 2 (auto-detected when possible).")

        # ── Backups & safety ─────────────────────────────────────────────────
        g = self._settings_group(inner, "🛡", "Backups & Safety")
        self._settings_toggle_row(g, "Confirm before overwriting a recent pickit",
            "Asks first before overwriting a pickit you generated in the last couple of minutes.",
            self.confirm_ovw_var)
        self._settings_divider(g)
        brow = tk.Frame(g, bg=BG2)
        brow.pack(fill="x", padx=14, pady=8)
        tk.Label(brow, text="Keep backups", bg=BG2, fg=TEXT, font=FONT).pack(anchor="w")
        tk.Label(brow, text="How many previous pickits to keep (0 = disabled).",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(anchor="w", pady=(1, 4))
        self._make_slider(brow, self.backup_count_var, from_=0, to=20, resolution=1,
                          fmt="{:.0f} backups", width=int(220 * self._ui_scale)).pack(anchor="w")

        # ── Updates ──────────────────────────────────────────────────────────
        g = self._settings_group(inner, "⬆", "Updates")
        tk.Label(g, text=f"You're running v{VERSION}. The app checks GitHub on startup and shows a "
                         "banner at the top when a new build is available.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, anchor="w", justify="left",
                 wraplength=760).pack(anchor="w", padx=14, pady=(2, 8))
        ubtns = tk.Frame(g, bg=BG2)
        ubtns.pack(fill="x", padx=14, pady=(0, 10))
        _upd_chk = btn(ubtns, "Check for updates now",
                       lambda: self._check_update_async(manual=True))
        _upd_chk.pack(side="left")
        Tip(_upd_chk, "Ask GitHub right now whether a newer version is available.")
        _rel = btn(ubtns, "Open releases page", self._open_releases)
        _rel.pack(side="left", padx=(8, 0))
        Tip(_rel, "Open the latest GitHub release in your browser to download the .exe.")

        # ── Advanced (collapsed by default) ──────────────────────────────────
        g = self._settings_group(inner, "🗂", "Advanced", collapsible=True, expanded=False)
        crow = tk.Frame(g, bg=BG2)
        crow.pack(fill="x", padx=14, pady=8)
        tk.Label(crow, text="Config file", bg=BG2, fg=TEXT, font=FONT).pack(anchor="w")
        tk.Label(crow, text="Your settings, category toggles and history are stored here. "
                            "Delete it to reset everything to defaults.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, justify="left",
                 wraplength=740).pack(anchor="w", pady=(1, 4))
        crow2 = tk.Frame(crow, bg=BG2)
        crow2.pack(fill="x")
        crow2.columnconfigure(0, weight=1)
        tk.Label(crow2, text=CONFIG_PATH, bg=BG2, fg=TEXT_DIM, font=FONT_MONO,
                 anchor="w").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        btn(crow2, "Open", lambda: self._open_file_path(CONFIG_PATH)).grid(row=0, column=1)

        # bottom spacer so the last card isn't flush against the footer
        tk.Frame(inner, bg=BG, height=12).pack(fill="x")

    def _settings_theme_cards(self, parent):
        """Two visual theme swatch cards (Dark / Light). Each renders a mini app
        preview in that theme's *own* palette so the choice shows the real look.
        Clicking one sets ``theme_var`` and surfaces the restart hint — colours are
        imported by value, so the change lands on the next launch, not live."""
        row = tk.Frame(parent, bg=BG2)
        row.pack(fill="x", padx=14, pady=(6, 2))
        self._theme_cards = {}
        for name in ("Dark", "Light"):
            pal = _PALETTES[name.lower()]
            card = tk.Frame(row, bg=BG2, highlightthickness=2,
                            highlightbackground=BORDER, highlightcolor=BORDER, cursor="hand2")
            card.pack(side="left", padx=(0, 12))

            # mini app preview, drawn in this theme's colours
            mini = tk.Frame(card, bg=pal["BG"], width=138, height=64,
                            highlightthickness=1, highlightbackground=pal["BORDER"])
            mini.pack(padx=6, pady=(6, 0))
            mini.pack_propagate(False)
            top = tk.Frame(mini, bg=pal["BG2"], height=17)
            top.pack(fill="x")
            top.pack_propagate(False)
            tk.Label(top, text="◆ v2.6", bg=pal["BG2"], fg=pal["GOLD"],
                     font=("Segoe UI", 7, "bold")).pack(side="left", padx=5)
            bodyf = tk.Frame(mini, bg=pal["BG"])
            bodyf.pack(fill="both", expand=True)
            tk.Label(bodyf, text="1,204", bg=pal["BG"], fg=pal["GOLD"],
                     font=("Segoe UI", 15, "bold")).pack(side="left", padx=(8, 6))
            chips = tk.Frame(bodyf, bg=pal["BG"])
            chips.pack(side="left")
            tk.Frame(chips, bg=pal["TEXT_OK"], width=18, height=4).pack(pady=2)
            tk.Frame(chips, bg=pal["TEXT_WARN"], width=18, height=4).pack(pady=2)

            # label + selected check
            lblrow = tk.Frame(card, bg=BG2)
            lblrow.pack(fill="x", padx=6, pady=(5, 6))
            tk.Label(lblrow, text=name, bg=BG2, fg=TEXT,
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            chk = tk.Label(lblrow, text="✓", bg=BG2, fg=GOLD, font=("Segoe UI", 10, "bold"))
            self._theme_cards[name] = (card, chk)

            def _pick(_e=None, n=name):
                self.theme_var.set(n)
                self._restyle_theme_cards()
                self._update_theme_hint()
            # bind the whole card subtree so a click anywhere selects it
            def _bind(w):
                w.bind("<Button-1>", _pick)
                for c in w.winfo_children():
                    _bind(c)
            _bind(card)
        self._restyle_theme_cards()

    def _restyle_theme_cards(self):
        """Ring the selected theme card in gold and show its ✓."""
        cur = self.theme_var.get()
        for name, (card, chk) in getattr(self, "_theme_cards", {}).items():
            on = (name == cur)
            card.configure(highlightbackground=GOLD if on else BORDER,
                           highlightcolor=GOLD if on else BORDER)
            if on:
                chk.pack(side="left", padx=(6, 0))
            else:
                chk.pack_forget()

    def _update_theme_hint(self):
        """Nudge to restart when the picked theme differs from the one this process
        actually rendered with (``THEME``) — not from cfg, which Save mutates."""
        lbl = getattr(self, "_theme_hint", None)
        if lbl is None:
            return
        picked = self.theme_var.get().strip().lower()
        lbl.configure(text="⚠  Restart to apply the new theme." if picked != THEME else "")

    def _update_autocopy_hint(self, *_):
        """Show an amber note under the Auto-copy toggle when it's on but the bot
        folder is blank or missing — otherwise the copy silently no-ops at generate."""
        lbl = getattr(self, "_autocopy_hint", None)
        if lbl is None:
            return
        try:
            on = bool(self.auto_copy_var.get())
        except tk.TclError:
            on = False
        folder = (self.bot_folder_var.get() or "").strip()
        if on and not folder:
            msg = "⚠  Auto-copy is on but no bot folder is set — the .ipd won't be deployed until you pick one above."
        elif on and not os.path.isdir(folder):
            msg = "⚠  Auto-copy is on but that folder doesn't exist — the .ipd won't be deployed until the path is valid."
        else:
            msg = ""
        if msg:
            lbl.configure(text=msg)
            if not lbl.winfo_manager():
                lbl.pack(anchor="w", padx=14, pady=(0, 8))
        else:
            lbl.pack_forget()

    def _save_settings(self):
        self.cfg["theme"]                  = self.theme_var.get().strip().lower()
        self.cfg["bot_folder"]             = self.bot_folder_var.get()
        self.cfg["auto_copy"]              = self.auto_copy_var.get()
        self.cfg["copy_filter_to_game"]    = self.copy_filter_var.get()
        self.cfg["poe2_filter_dir"]        = self.poe2_filter_dir_var.get().strip()
        def _safe(var, default):
            try:
                return var.get()
            except (tk.TclError, ValueError):
                return default
        self.cfg["backup_count"]           = _safe(self.backup_count_var, 5)
        self.cfg["confirm_overwrite_secs"] = 120 if self.confirm_ovw_var.get() else 0
        self.cfg["include_bases"]          = self.include_bases_var.get()
        self.cfg["base_quality"]           = _safe(self.base_quality_var, 28)
        self.cfg["base_min_level"]         = _safe(self.base_min_level_var, gen.CRAFT_BASE_MIN_ILVL)
        # Persist the live floors (an old bug force-zeroed these on every save).
        # min_exalt mirrors the gear floor — generation's global floor for all
        # non-unique categories is min_exalt_gear; min_exalt only feeds the
        # header comment and per-card warnings, which must agree with it.
        self.cfg["min_exalt_gear"] = float(_safe(self.min_exalt_gear_var,
                                                 self.cfg.get("min_exalt_gear", 0.0)))
        self.cfg["min_exalt"]      = self.cfg["min_exalt_gear"]
        try:
            self.cfg["min_exalt_unique"] = float(self.min_exalt_unique_var.get())
        except (tk.TclError, ValueError):
            pass
        self.after(0, lambda: save_config(self.cfg))
        self._log("Settings saved.", "ok")
        _lbl = getattr(self, "_settings_saved_lbl", None)
        if _lbl is not None:
            _lbl.configure(text="✓ Saved")
            self.after(2500, lambda: _lbl.configure(text=""))

    def _restart_app(self):
        """Persist settings, then relaunch so a theme change takes effect.

        The single-instance mutex (see ``main``) is held for this process's
        lifetime. The relauncher waits ~1s via ``ping`` — long enough for this
        process to exit and release the mutex — then starts the fresh instance
        detached so it outlives us.

        We ``os._exit`` rather than shutting down cleanly: a clean exit runs
        concurrent.futures' atexit handler, which joins any in-flight fetch
        worker (icon/price preload) and can hold this process — and the mutex —
        well past the relauncher's ~1s wait. If that happened, the new instance
        would find the mutex still held, see no window (already destroyed), and
        quit without relaunching, leaving the user with no app. Config is saved
        synchronously below, so a hard exit loses nothing."""
        self._save_settings()
        self.cfg["window_geometry"] = self.geometry()
        save_config(self.cfg)   # synchronous — must be on disk before we exit
        try:
            args = [sys.executable] if getattr(sys, "frozen", False) \
                else [sys.executable, "-m", "exilebot_pickit"]
            quoted = " ".join(f'"{a}"' for a in args)
            # The relaunched exe must NOT inherit PyInstaller's private env vars
            # (_MEIPASS2 / _PYI_*): with them set, the new bootloader skips its
            # own extraction and loads python*.dll from THIS process's _MEIxxxx
            # temp dir — which is deleted the moment we exit, producing
            # "Failed to load Python DLL ... _MEIxxxx\pythonXYZ.dll".
            env = {k: v for k, v in os.environ.items()
                   if k not in ("_MEIPASS2", "_PYI_APPLICATION_HOME_DIR",
                                "_PYI_ARCHIVE_FILE", "_PYI_PARENT_PROCESS_LEVEL")}
            env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP so the relauncher (and
            # the new app) survive this process exiting.
            subprocess.Popen(f"ping 127.0.0.1 -n 2 >nul & {quoted}",
                             shell=True, env=env,
                             creationflags=0x00000008 | 0x00000200)
        except Exception:
            log_exc("restart_app")
            self._log("Couldn't relaunch automatically — please reopen the app.", "warn")
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def _reset_defaults(self):
        if messagebox.askyesno(
                "Reset settings",
                "Reset all settings to their defaults?\n\n"
                "Your run history, saved profiles and per-item selections are kept.",
                parent=self):
            # Reset settings keys only — wiping history/profiles/item_states from
            # a button labelled "settings" destroyed far more than it claimed to.
            _keep = {k: self.cfg.get(k, DEFAULT_CONFIG.get(k))
                     for k in ("history", "profiles", "active_profile",
                               "item_states", "last_gen_prices",
                               "window_geometry")}
            self.cfg = dict(DEFAULT_CONFIG)
            self.cfg.update(_keep)
            self._item_states = dict(self.cfg.get("item_states", {}))
            self.after(0, lambda: save_config(self.cfg))
            # Re-sync all tk vars so the live UI reflects defaults immediately
            self.theme_var.set("Light" if (self.cfg.get("theme") or "dark").lower() == "light" else "Dark")
            self._restyle_theme_cards()
            self._update_theme_hint()
            self.league_var.set(self.cfg.get("league", ""))
            self.min_exalt_var.set(self.cfg.get("min_exalt", 0.0))
            self.min_exalt_gear_var.set(self.cfg.get("min_exalt_gear", 0.0))
            self.min_exalt_unique_var.set(self.cfg.get("min_exalt_unique", 0.0))
            self.output_var.set(self.cfg.get("output_base", "poe2_pickit"))
            self.bot_folder_var.set(self.cfg.get("bot_folder", ""))
            self.auto_copy_var.set(self.cfg.get("auto_copy", False))
            self.copy_filter_var.set(self.cfg.get("copy_filter_to_game", False))
            self.poe2_filter_dir_var.set(self.cfg.get("poe2_filter_dir") or _default_poe2_filter_dir())
            self.backup_count_var.set(self.cfg.get("backup_count", 5))
            self.confirm_ovw_var.set(True)
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
        tools = self._settings_group(page, "🔧", "Tools")
        btn_f = tk.Frame(tools, bg=BG2)
        btn_f.pack(fill="x", padx=14, pady=(8, 10))
        _dbg1 = btn(btn_f, "Run diagnostics", self._run_diagnostics)
        _dbg1.pack(side="left")
        _dbg2 = btn(btn_f, "Test all API endpoints",
                    lambda: threading.Thread(target=self._api_test_worker, daemon=True).start())
        _dbg2.pack(side="left", padx=(6, 0))
        _dbg3 = btn(btn_f, "Show config", self._debug_show_config)
        _dbg3.pack(side="left", padx=(6, 0))
        _dbg4 = btn(btn_f, "Open debug log", lambda: self._open_file_path(LOG_PATH))
        _dbg4.pack(side="left", padx=(6, 0))
        _dbg5 = btn(btn_f, "Prune cache", self._prune_cache_ui)
        _dbg5.pack(side="left", padx=(6, 0))
        _dbg6 = btn(btn_f, "Clear", self._debug_clear)
        _dbg6.pack(side="left", padx=(6, 0))
        _dbg7 = btn(btn_f, "Copy output", self._log_copy)
        _dbg7.pack(side="left", padx=(6, 0))
        Tip(_dbg7, "Copy everything shown below to the clipboard — paste it into a bug report.")
        Tip(_dbg1, "Check your Python setup, required modules, and poe.ninja connection.")
        Tip(_dbg2, "Ping every price category and report row counts and response times.")
        Tip(_dbg3, "Print your current saved settings here — handy for bug reports.")
        Tip(_dbg4, "Open the app's log file.")
        Tip(_dbg5, "Delete cached price files older than 60 days.")
        Tip(_dbg6, "Clear the output shown below.")

        df, self.debug_text = scrolled_text(page, state="disabled")
        df.pack(fill="both", expand=True, padx=16, pady=(12, 16))
        for tag, col in [("header", GOLD), ("ok", TEXT_OK), ("err", TEXT_ERR),
                         ("warn", TEXT_WARN), ("info", TEXT_INFO), ("dim", TEXT_DIM)]:
            self.debug_text.tag_config(tag, foreground=col)

        for msg, tag in self._log_buffer:
            self._dlog(msg, tag)
        self._log_buffer.clear()

    def _dlog(self, msg, tag=""):
        def _do():
            if not hasattr(self, "debug_text"):
                self._log_buffer.append((msg, tag))
                return
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
                               ("exilebot_pickit", True)]:
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
        # poe2wiki — optional (item icons); when it is down icons are simply skipped.
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
        resolved = max(0, self._total_icon_count - self._unresolved_icon_count)
        if self._total_icon_count > 0:
            d(f"     icons: {resolved}/{self._total_icon_count} resolved"
              f" ({self._unresolved_icon_count} missing — items show no icon)", "dim")
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
            self.after(0, lambda: self.league_cb.configure(state="readonly"))

    def _populate_leagues(self, names):
        self.league_cb["values"] = names
        self.league_cb.configure(state="readonly")
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
        self._dlog(msg, tag)

    def _log_clear(self):
        if hasattr(self, "debug_text"):
            self._debug_clear()

    def _log_copy(self):
        if not hasattr(self, "debug_text"):
            return
        content = self.debug_text.get("1.0", "end").strip()
        if not content:
            self._dlog("Log is empty — nothing to copy.", "warn")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        self._dlog("Log copied to clipboard.", "ok")

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

    def _start_generate(self):
        if self._running:
            self.status_lbl.configure(text="Already running…", fg=TEXT_WARN)
            return

        league = self._selected_league()
        if not league or league.startswith("Loading"):
            self.status_lbl.configure(
                text="No league — wait for leagues to load or type a name", fg=TEXT_ERR)
            self._log("No league selected — wait for the league list to load or type a name manually.", "warn")
            return

        base_path = self._output_base_path()
        ipd_path  = base_path + ".ipd"
        if os.path.isfile(ipd_path):
            age   = time.time() - os.path.getmtime(ipd_path)
            limit = self.cfg.get("confirm_overwrite_secs", 120)
            # limit == 0 means the confirmation is disabled (see _save_settings)
            if limit > 0 and age < limit:
                if not messagebox.askyesno("Overwrite?",
                        f"The pickit was generated {int(age)}s ago.\nOverwrite it now?"):
                    return

        def _num(var, default, lo, hi):
            """Read a numeric Tk var defensively: junk/empty input falls back to
            *default* (clamped to [lo, hi]) instead of raising TclError — a raised
            error here used to leave the Generate buttons disabled for the session."""
            try:
                v = var.get()
            except (tk.TclError, ValueError):
                v = default
            try:
                v = int(v)
            except (TypeError, ValueError):
                v = default
            v = max(lo, min(hi, v))
            var.set(v)   # reflect the corrected value back into the UI
            return v

        # Snapshot all Tk variables here on the main thread so the worker never
        # touches Tcl/Tk state from a background thread (avoids intermittent
        # freezes on non-Windows platforms where Tk is not thread-safe).
        # Built BEFORE the buttons are disabled so a bad value can never strand
        # the UI in its "running" state.
        snapshot = {
            "league":          league,
            "output_var":      self.output_var.get(),
            "auto_copy":       self.auto_copy_var.get(),
            "bot_folder":      self.bot_folder_var.get(),
            "copy_filter_to_game": self.copy_filter_var.get(),
            "poe2_filter_dir":     self.poe2_filter_dir_var.get().strip(),
            "backup_count":    _num(self.backup_count_var, 5, 0, 20),
            "cat_enabled":     {k: v.get() for k, v in self.cat_enabled.items()},
            "cat_thresh":      {},
            "include_bases":   self.include_bases_var.get(),
            "base_quality":    _num(self.base_quality_var, 28, 0, 100),
            "base_min_level":  _num(self.base_min_level_var, gen.CRAFT_BASE_MIN_ILVL, 1, 82),
            "item_states":     copy.deepcopy(self._item_states),
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
        snapshot["_fallback_min_exalt"] = float(self.cfg.get("min_exalt", 1.0))
        try:
            snapshot["min_exalt_gear"] = self.min_exalt_gear_var.get()
        except tk.TclError:
            snapshot["min_exalt_gear"] = float(self.cfg.get("min_exalt_gear", 5.0))
            self.min_exalt_gear_var.set(snapshot["min_exalt_gear"])
            self._log("Gear threshold invalid — reset to saved value.", "warn")
        snapshot["_fallback_min_exalt_gear"] = float(self.cfg.get("min_exalt_gear", 5.0))
        try:
            snapshot["min_exalt_unique"] = self.min_exalt_unique_var.get()
        except tk.TclError:
            snapshot["min_exalt_unique"] = float(self.cfg.get("min_exalt_unique", 0.0))
            self.min_exalt_unique_var.set(snapshot["min_exalt_unique"])
            self._log("Unique threshold invalid — reset to saved value.", "warn")
        snapshot["_fallback_min_exalt_unique"] = float(self.cfg.get("min_exalt_unique", 0.0))

        # Snapshot is complete and valid — only now flip into the running state.
        self._running = True
        self._generate_start = time.time()
        self._log_clear()
        self.gen_btn.configure(state="disabled")
        self.force_btn.configure(state="disabled")
        self.open_ipd_btn.configure(state="disabled")
        self.open_filter_btn.configure(state="disabled")
        self.status_lbl.configure(text="Generating…", fg=TEXT_WARN)
        self.progress_var.set("Starting…")
        self._progress_bar["value"] = 0
        self._progress_bar.pack(side="left", padx=(8, 0))

        # Init segmented bar — one segment per category + maybe bases
        _n_main = sum(1 for c in gen.ALL_CATEGORIES
                      if snapshot["cat_enabled"].get(c[0], True))
        _n_segs = _n_main + (1 if snapshot.get("include_bases") else 0)
        self._seg_bar.init_segments(_n_segs)
        self._seg_bar.pack(fill="x", padx=10, pady=(0, 6))
        self._last_gen_stats = {}
        self._progress_bar["maximum"] = _n_segs + 2
        self._progress_bar["value"] = 0

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
                min_exalt = float(snapshot.get("_fallback_min_exalt", 1.0))
                self._log("Currency threshold invalid — reset to saved value.", "warn")
            try:
                min_exalt_gear = float(min_exalt_gear)
            except (TypeError, ValueError):
                min_exalt_gear = float(snapshot.get("_fallback_min_exalt_gear", 5.0))
                self._log("Gear threshold invalid — reset to saved value.", "warn")
            try:
                min_exalt_unique = float(min_exalt_unique)
            except (TypeError, ValueError):
                min_exalt_unique = float(snapshot.get("_fallback_min_exalt_unique", 0.0))
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

            self.after(0, lambda: self._progress_bar.step(1))

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

            self.after(0, lambda: self._progress_bar.step(1))

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
                    self._log(f"  ✓ Base types: {rule_count} rules", "ok")
                    self.after(0, lambda i=_base_seg: self._seg_bar.set_segment(i, "ok"))
                except Exception as e:
                    self._log(f"  ✗ Base types failed: {e}", "err")
                    self.after(0, lambda i=_base_seg: self._seg_bar.set_segment(i, "err"))

            self.after(0, lambda: self._progress_bar.step(1))
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
            gen.write_text_atomic(ipd_path, "\n".join(output_lines))
            self._log(f"Written: {os.path.basename(ipd_path)}", "dim")
            success = True

            # Auto-copy to the bot folder — a single, stable filename (the bot
            # points at one file, not a trail of copies).
            if snapshot["auto_copy"]:
                bot = snapshot["bot_folder"].strip()
                if bot and os.path.isdir(bot):
                    dest = os.path.join(bot, os.path.basename(base_path) + ".ipd")
                    shutil.copy2(ipd_path, dest)
                    self._log(f"Copied to bot folder: {dest}", "ok")
                else:
                    self._log("Auto-copy: bot folder not set or not found.", "warn")

            # ── PoE2 client loot filter (always written next to the .ipd) ─────
            try:
                filter_path = os.path.splitext(ipd_path)[0] + ".filter"
                filter_lines = gen.build_loot_filter(
                    output_lines, generated_iso=datetime.datetime.now().isoformat())
                gen.write_text_atomic(filter_path, "\n".join(filter_lines))
                shows = sum(1 for l in filter_lines if l == "Show")
                self._log(f"Loot filter: {os.path.basename(filter_path)} ({shows} Show blocks)", "dim")

                if snapshot.get("copy_filter_to_game"):
                    game_dir = (snapshot.get("poe2_filter_dir") or "").strip()
                    if game_dir and os.path.isdir(game_dir):
                        # A single, stable filename — same name every generate.
                        game_name = os.path.basename(base_path) + ".filter"
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
            _new_last_gen_prices = {league: new_gen_prices}
            alerts.sort(key=lambda t: t[0], reverse=True)
            # Shown in the post-generate summary box only (not re-logged below).
            _new_price_alerts = [text for _, text in alerts[:10]]

            # Mutate the shared attributes on the main thread only, like every
            # other piece of GUI-visible state in this method.
            def _apply_price_alerts(lgp=_new_last_gen_prices, pa=_new_price_alerts):
                self._last_gen_prices = lgp
                self._price_alerts = pa
            self.after(0, _apply_price_alerts)

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
            _lgp = _new_last_gen_prices
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
            self.after(0, lambda: self._generate_done(success))

    def _generate_done(self, success: bool = False):
        self._running = False
        self._seg_bar.pack_forget()
        self._progress_bar.pack_forget()
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
        self.cfg["window_geometry"]  = self.geometry()
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


def main():
    """Launch the application."""
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


if __name__ == "__main__":
    main()
