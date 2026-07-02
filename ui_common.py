"""Shared UI toolkit for the ExileBot 2 Pickit Generator GUI.

Colours, fonts, small helper-widget factories, the ttk style setup, and the two
custom canvas widgets (_SegBar, sparkline). Both the main window and the per-tab
mixin modules import everything from here, so there is a single source of truth
for the look-and-feel and no circular import between tabs and the app shell.
"""
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk

import poe2_pickit_generator as gen

# Modern dark look for the CustomTkinter widgets (buttons, etc.).
ctk.set_appearance_mode("dark")


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
_COFF   = "#202028"   # item card disabled bg  (mid-gray, clearly different)
_CONB   = "#5a406a"   # item card enabled border
_COFB   = "#3a3a3a"   # item card disabled border (gray)
_CTXON  = "#ece4d8"   # item card enabled text
_CTXOF  = "#606060"   # item card disabled text (gray)
_CWARN  = "#221a06"   # disabled-but-valuable bg
_CWARNB = "#b87820"   # disabled-but-valuable border (amber)
_CTXWRN = "#7a6840"   # disabled-but-valuable text
_CVAL   = "#c8a050"   # value text

FONT      = ("Segoe UI", 11, "bold")
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas",  10)
FONT_SM   = ("Segoe UI",  10, "bold")

ALL_CATEGORY_KEYS = [c[0] for c in gen.ALL_CATEGORIES]

# Non-negative int from a config dict; canonical copy lives in the generator
# module (pickit_assembly must stay Tk-free, so it can't import this file).
cfg_int = gen.cfg_int


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
    """Modern rounded entry (CustomTkinter). width is in characters (converted to
    px); entries that stretch via grid/pack ignore it."""
    kwargs = dict(textvariable=var, fg_color=BG3, text_color=TEXT,
                  border_color=BORDER, corner_radius=6, font=FONT)
    if width:
        kwargs["width"] = max(int(width) * 8, 40)
    kwargs.update(kw)
    return ctk.CTkEntry(parent, **kwargs)

def checkbtn(parent, text, var, bg=None):
    """Modern checkbox (CustomTkinter). bg kept for call-site compatibility (unused)."""
    return ctk.CTkCheckBox(parent, text=text, variable=var,
        onvalue=True, offvalue=False,
        fg_color=GOLD, hover_color=GOLD_LT, text_color=TEXT, font=FONT,
        checkbox_width=18, checkbox_height=18, corner_radius=4)

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
                             fg_color=GOLD, hover_color=GOLD_LT, text_color="#111111", **kw)
    return ctk.CTkButton(parent, text=text, command=cmd, width=width, height=28,
                         corner_radius=8, font=FONT,
                         fg_color=BG3, hover_color=BORDER, text_color=TEXT, **kw)

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


def _draw_sparkline(canvas: tk.Canvas, data: list, w: int, h: int):
    """Draw a mini sparkline on *canvas*. Green = rising, red = falling."""
    vals = [float(v) for v in data if v is not None]
    if len(vals) < 2:
        return
    mn, mx = min(vals), max(vals)
    if mx == mn:
        y = h // 2
        canvas.create_line(0, y, w, y, fill="#5d5d7a", width=1)
        return
    def _y(v): return max(0, h - 1 - int((v - mn) / (mx - mn) * (h - 2)))
    def _x(i): return int(i / (len(vals) - 1) * (w - 1))
    coords = []
    for i, v in enumerate(vals):
        coords += [_x(i), _y(v)]
    color = "#4daa6f" if vals[-1] >= vals[0] else "#c04040"
    canvas.create_line(coords, fill=color, width=1, smooth=True)


# Export everything (incl. the underscore-prefixed colour names) so the app shell
# and tab modules can `from ui_common import *` and get the full toolkit.
__all__ = [n for n in dir() if n not in ("tk", "ttk", "ctk", "gen") and not n.startswith("__")]
