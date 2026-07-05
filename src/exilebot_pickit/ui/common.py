"""Shared UI toolkit for the ExileBot 2 Pickit Generator GUI.

Colours, fonts, small helper-widget factories, the ttk style setup, and the two
custom canvas widgets (_SegBar, sparkline). Both the main window and the per-tab
mixin modules import everything from here, so there is a single source of truth
for the look-and-feel and no circular import between tabs and the app shell.
"""
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

from exilebot_pickit import generator as gen

# Modern dark look for the CustomTkinter widgets (buttons, etc.).
# ── Theme palettes ────────────────────────────────────────────────────────────
# Every colour the UI uses lives in a palette dict. The active theme is chosen on
# startup from the saved config ("theme": "dark" | "light") and its values are
# assigned to the module-level names below, which the whole app imports by name.
# Because those names are imported *by value*, changing theme applies on the next
# launch (see _restart_app in the GUI) rather than live.

_DARK = {
    "BG": "#181820", "BG2": "#20202c", "BG3": "#2a2a3a", "BG4": "#323248",
    "BORDER": "#3a3a54", "BORDER_LT": "#4a4a68",
    "GOLD": "#c8a96e", "GOLD_LT": "#e8c98e", "GOLD_GLOW": "#c8a96e33",
    "TEXT": "#ece4d8", "TEXT_DIM": "#8888a0",
    "TEXT_OK": "#5dbb8a", "TEXT_ERR": "#e05555", "TEXT_WARN": "#d4a84b", "TEXT_INFO": "#6ab0e8",
    "SHADOW": "#0c0c1400", "SHADOW_HV": "#0c0c1444",
    "_CBAR": "#16141a", "_CBTN": "#1c1a22", "_CHOV": "#252230",
    "_CSEL": "#2d1f10", "_CSFG": "#e8c878",
    "_CON": "#25222e", "_COFF": "#202028", "_CONB": "#5a406a", "_COFB": "#3a3a3a",
    "_CTXON": "#ece4d8", "_CTXOF": "#606060",
    "_CWARN": "#221a06", "_CWARNB": "#b87820", "_CTXWRN": "#7a6840", "_CVAL": "#c8a050",
    # Semantic accents (themed so banners/flashes stay legible in light mode)
    "ACC_WARN_BG": "#3a2a1a", "ACC_WARN_FG": "#e8b84b",   # warning banners
    "ACC_OK_BG": "#1e3a2a",                               # copy-to-clipboard flash
    "ROW_ALT": "#1e1e2a",                                 # emphasised list-row bg
}

# Light theme — hand-tuned so the gold accent, borders and warning colours stay
# legible on a warm off-white background (not just an inverted dark theme).
_LIGHT = {
    "BG": "#ece9e2", "BG2": "#f8f6f1", "BG3": "#e2ded4", "BG4": "#d3cec1",
    "BORDER": "#d0ccbf", "BORDER_LT": "#b6ad98",
    "GOLD": "#97752f", "GOLD_LT": "#b6924a", "GOLD_GLOW": "#97752f33",
    "TEXT": "#2b2822", "TEXT_DIM": "#6f6a5c",
    "TEXT_OK": "#2c8a58", "TEXT_ERR": "#c0392b", "TEXT_WARN": "#9a7420", "TEXT_INFO": "#2f77bd",
    "SHADOW": "#6b665500", "SHADOW_HV": "#6b665533",
    "_CBAR": "#e3e0d6", "_CBTN": "#eae7dd", "_CHOV": "#e0dccf",
    "_CSEL": "#f3e7c6", "_CSFG": "#7a5f22",
    "_CON": "#ffffff", "_COFF": "#e6e3da", "_CONB": "#c8a75f", "_COFB": "#d8d3c6",
    "_CTXON": "#2b2822", "_CTXOF": "#a49f92",
    "_CWARN": "#fbf2d6", "_CWARNB": "#c69a34", "_CTXWRN": "#8a6d2c", "_CVAL": "#8a6c2c",
    # Semantic accents (themed so banners/flashes stay legible in light mode)
    "ACC_WARN_BG": "#f6e7c4", "ACC_WARN_FG": "#7a5c14",   # warning banners
    "ACC_OK_BG": "#d9efdf",                               # copy-to-clipboard flash
    "ROW_ALT": "#efece3",                                 # emphasised list-row bg
}

_PALETTES = {"dark": _DARK, "light": _LIGHT}


def _active_theme_name() -> str:
    """Saved theme name from the config file (default 'dark'), read directly so the
    palette is resolved before any widget is built."""
    try:
        import json
        from exilebot_pickit.ui.config import CONFIG_PATH
        with open(CONFIG_PATH, encoding="utf-8") as f:
            name = json.load(f).get("theme", "dark")
        return name if name in _PALETTES else "dark"
    except Exception:
        return "dark"


THEME = _active_theme_name()
_P    = _PALETTES[THEME]

ctk.set_appearance_mode("light" if THEME == "light" else "dark")

# ── Colours (resolved from the active palette) ────────────────────────────────
BG        = _P["BG"]
BG2       = _P["BG2"]
BG3       = _P["BG3"]
BG4       = _P["BG4"]
BORDER    = _P["BORDER"]
BORDER_LT = _P["BORDER_LT"]
GOLD      = _P["GOLD"]
GOLD_LT   = _P["GOLD_LT"]
GOLD_GLOW = _P["GOLD_GLOW"]
TEXT      = _P["TEXT"]
TEXT_DIM  = _P["TEXT_DIM"]
TEXT_OK   = _P["TEXT_OK"]
TEXT_ERR  = _P["TEXT_ERR"]
TEXT_WARN = _P["TEXT_WARN"]
TEXT_INFO = _P["TEXT_INFO"]
SHADOW    = _P["SHADOW"]
SHADOW_HV = _P["SHADOW_HV"]

# ── Category card UI colours ──────────────────────────────────────────────────
_CBAR   = _P["_CBAR"]    # sidebar bg
_CBTN   = _P["_CBTN"]    # sidebar button normal bg
_CHOV   = _P["_CHOV"]    # sidebar button hover
_CSEL   = _P["_CSEL"]    # sidebar button selected bg
_CSFG   = _P["_CSFG"]    # selected button text
_CON    = _P["_CON"]     # item card enabled bg
_COFF   = _P["_COFF"]    # item card disabled bg
_CONB   = _P["_CONB"]    # item card enabled border
_COFB   = _P["_COFB"]    # item card disabled border
_CTXON  = _P["_CTXON"]   # item card enabled text
_CTXOF  = _P["_CTXOF"]   # item card disabled text
_CWARN  = _P["_CWARN"]   # disabled-but-valuable bg
_CWARNB = _P["_CWARNB"]  # disabled-but-valuable border (amber)
_CTXWRN = _P["_CTXWRN"]  # disabled-but-valuable text
_CVAL   = _P["_CVAL"]    # value text

# ── Semantic accents ──────────────────────────────────────────────────────────
ACC_WARN_BG = _P["ACC_WARN_BG"]   # warning banner background
ACC_WARN_FG = _P["ACC_WARN_FG"]   # warning banner text
ACC_OK_BG   = _P["ACC_OK_BG"]     # success flash background
ROW_ALT     = _P["ROW_ALT"]       # emphasised list-row background

FONT      = ("Segoe UI", 11, "bold")
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas",  10)
FONT_SM   = ("Segoe UI",  10, "bold")

ALL_CATEGORY_KEYS = [c[0] for c in gen.ALL_CATEGORIES]

# Non-negative int from a config dict; canonical copy lives in the generator
# module (pickit_assembly must stay Tk-free, so it can't import this file).
cfg_int = gen.cfg_int


# ── Helper widgets ────────────────────────────────────────────────────────────

def scrolled_text(parent, font=FONT_MONO, **kw):
    """Return (frame, Text widget) with both scrollbars.

    ``font`` is an explicit parameter (defaulting to FONT_MONO) so callers can
    override it without colliding with the hardcoded value — passing it through
    ``**kw`` would raise "got multiple values for keyword argument 'font'"."""
    frame = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
    vsb = tk.Scrollbar(frame, orient="vertical",   bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=10)
    hsb = tk.Scrollbar(frame, orient="horizontal", bg=BG3, troughcolor=BG2, relief="flat", bd=0, width=10)
    t = tk.Text(frame, bg=BG2, fg=TEXT, font=font,
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
    """Modern rounded entry (CustomTkinter). width is in characters (converted to
    px); entries that stretch via grid/pack ignore it."""
    kwargs = dict(textvariable=var, fg_color=BG3, text_color=TEXT,
                  border_color=BORDER, corner_radius=6, font=FONT)
    if width:
        kwargs["width"] = max(int(width) * 8, 40)
    kwargs.update(kw)
    return ctk.CTkEntry(parent, **kwargs)

def switch(parent, var, command=None, **kw):
    """Modern on/off toggle switch (CustomTkinter).

    Use where a boolean reads better as a switch than a checkbox (Windows 11 /
    Discord settings style). ``text`` is empty by default — the caller lays out
    its own title/subtitle label beside it. Supports .configure() like any widget.
    """
    extra = {"command": command} if command is not None else {}
    kwargs = dict(text="", variable=var, onvalue=True, offvalue=False,
                  progress_color=GOLD, fg_color=BG4,
                  button_color=TEXT, button_hover_color=GOLD_LT,
                  switch_width=42, switch_height=22)
    kwargs.update(kw)
    return ctk.CTkSwitch(parent, **kwargs, **extra)

def btn(parent, text, cmd, style=None, **kw):
    """Modern rounded button (CustomTkinter).

    style='Gold.TButton' renders the gold accent button. Width auto-sizes to the
    label (CTkButton's 140px default would blow out the compact toolbars).
    Supports the same .configure(state=...) used throughout for enable/disable.
    """
    width = kw.pop("width", max(64, len(str(text)) * 9 + 22))
    if style == "Gold.TButton":
        return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=30,
                             corner_radius=8, font=FONT_BOLD,
                             fg_color=GOLD, hover_color=GOLD_LT, text_color="#111111",
                             border_width=1, border_color=GOLD,
                             **kw)
    return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=28,
                         corner_radius=8, font=FONT,
                         fg_color=BG3, hover_color=BORDER_LT, text_color=TEXT,
                         border_width=1, border_color=BORDER,
                         **kw)

# ── ttk style setup (called once on app init) ─────────────────────────────────

def setup_styles(root, scale=1.0):
    style = ttk.Style(root)
    style.theme_use("clam")

    # ttk fonts are point-based and auto-scale with the monitor DPI, but ttk
    # padding and Treeview row height are in raw pixels — scale them so they stay
    # proportional to the (larger) text on high-DPI displays.
    def _s(px):
        return max(1, int(round(px * scale)))

    style.configure("TButton",
        background=BG3, foreground=TEXT,
        font=FONT, relief="flat",
        borderwidth=1, focusthickness=0,
        padding=(_s(10), _s(5)))
    style.map("TButton",
        background=[("active", BORDER), ("pressed", BG)],
        foreground=[("active", TEXT)])

    style.configure("Gold.TButton",
        background=GOLD, foreground="#111",
        font=FONT_BOLD, relief="flat",
        borderwidth=0, padding=(_s(14), _s(6)))
    style.map("Gold.TButton",
        background=[("active", GOLD_LT), ("pressed", GOLD)])

    style.configure("TCombobox",
        fieldbackground=BG3, background=BG3,
        foreground=TEXT, selectbackground=BG3,
        selectforeground=TEXT, arrowcolor=GOLD,
        bordercolor=BORDER, padding=_s(4))
    style.map("TCombobox", fieldbackground=[("readonly", BG3)],
                            foreground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.background",       BG3)
    root.option_add("*TCombobox*Listbox.foreground",       TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", GOLD)
    root.option_add("*TCombobox*Listbox.selectForeground", "#111")

    style.configure("Treeview",
        background=BG2, foreground=TEXT,
        fieldbackground=BG2, rowheight=_s(22), font=FONT)
    style.configure("Treeview.Heading",
        background=BG3, foreground=GOLD, font=FONT_BOLD, relief="flat")
    style.map("Treeview", background=[("selected", BORDER)])


# ══════════════════════════════════════════════════════════════════════════════
#  Segmented progress bar widget
# ══════════════════════════════════════════════════════════════════════════════

class _SegBar(tk.Canvas):
    """One coloured rectangle per category — fills left-to-right as each one completes."""
    _CLR = {
        "pending": "#1e1c28",
        "active":  "#c8a84b",   # gold — currently processing
        "ok":      "#4daa6f",   # green — success
        "err":     "#c04040",   # red — failed
    }
    GAP = 2

    def __init__(self, parent, bar_height=10, **kw):
        super().__init__(parent, bg=BG, bd=0, highlightthickness=0,
                         height=bar_height, **kw)
        self._n      = 0
        self._states: list[str] = []
        self._rects:  list[int] = []
        self.bind("<Configure>", self._redraw)

    def init_segments(self, n: int):
        self._n      = n
        self._states = ["pending"] * n
        self._rects  = []
        self.after(0, self._redraw)

    def set_segment(self, idx: int, state: str):
        if 0 <= idx < self._n:
            self._states[idx] = state
            if idx < len(self._rects):
                self.itemconfig(self._rects[idx],
                                fill=self._CLR.get(state, self._CLR["pending"]))

    def _redraw(self, _e=None):
        self.delete("all")
        self._rects = []
        if self._n == 0:
            return
        w  = max(self.winfo_width(), 1)
        h  = max(self.winfo_height(), 1)
        seg_w = max(4.0, (w - self.GAP * (self._n - 1)) / self._n)
        for i in range(self._n):
            x0 = round(i * (seg_w + self.GAP))
            x1 = round(x0 + seg_w)
            clr = self._CLR.get(self._states[i] if i < len(self._states) else "pending",
                                 self._CLR["pending"])
            rect = self.create_rectangle(x0, 0, x1, h, fill=clr, outline="",
                                          width=0)
            self._rects.append(rect)


# ── Micro-animation helpers ──────────────────────────────────────────────────

def _animate_border_glow(widget, color_from="#3a3a54", color_to="#c8a96e44",
                         steps=6, interval=20, restore=True):
    """Brief border glow animation on a widget with highlightthickness support."""
    orig = widget.cget("highlightbackground") if hasattr(widget, "cget") else color_from

    def _step(i):
        if i > steps:
            if restore:
                try:
                    widget.configure(highlightbackground=orig)
                except Exception:
                    pass
            return
        t = i / steps
        r = int(int(color_to[1:3], 16) * t + int(color_from[1:3], 16) * (1 - t))
        g = int(int(color_to[3:5], 16) * t + int(color_from[3:5], 16) * (1 - t))
        b = int(int(color_to[5:7], 16) * t + int(color_from[5:7], 16) * (1 - t))
        try:
            widget.configure(highlightbackground=f"#{r:02x}{g:02x}{b:02x}")
        except Exception:
            pass
        widget.after(interval, lambda: _step(i + 1))

    _step(0)


def _card_hover_bind(card_frame, bg_light="#2a2a3e", bg_dim="#20202c"):
    """Bind hover elevation effect on a card frame — subtle border light + bg shift."""
    def _enter(_e):
        try:
            card_frame.configure(bg=bg_light, highlightbackground=BORDER_LT)
        except Exception:
            pass
    def _leave(_e):
        try:
            card_frame.configure(bg=bg_dim, highlightbackground=BORDER)
        except Exception:
            pass
    card_frame.bind("<Enter>", _enter)
    card_frame.bind("<Leave>", _leave)


def bind_card_hover(frame, widgets, lit_color, resting_color_fn):
    """Border-elevation hover for a card: brighten the frame's border while the
    pointer is anywhere inside it, restore ``resting_color_fn()`` when it truly
    leaves.  ``resting_color_fn`` is a callable so the resting colour can reflect
    live state (e.g. the card's enabled/disabled border). Uses winfo_containing so
    moving between the card's own child widgets doesn't flicker the border."""
    def _enter(_e=None):
        try:
            frame.configure(highlightbackground=lit_color)
        except Exception:
            pass

    def _leave(_e=None):
        try:
            w = frame.winfo_containing(*frame.winfo_pointerxy())
        except Exception:
            w = None
        p = w
        while p is not None:
            if p is frame:
                return           # still inside this card — keep it lit
            p = getattr(p, "master", None)
        try:
            frame.configure(highlightbackground=resting_color_fn())
        except Exception:
            pass

    for w in widgets:
        w.bind("<Enter>", _enter, add="+")
        w.bind("<Leave>", _leave, add="+")


# ── Hover tooltip ─────────────────────────────────────────────────────────────

class Tip:
    """Attach a small hover tooltip to any widget: ``Tip(widget, "helpful text")``.

    Uses additive ``<Enter>``/``<Leave>`` binds so it never clobbers a widget's
    existing hover effects, and cleans itself up if the widget is destroyed while
    hovered (no leaked pop-up)."""
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _show(self, _e=None):
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 24
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 2
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, bg=_CBTN, fg=TEXT, font=FONT_SM,
                 justify="left", relief="solid", bd=1, padx=8, pady=6, wraplength=440).pack()

    def _hide(self, _e=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None



