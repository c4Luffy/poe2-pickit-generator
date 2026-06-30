"""Rare Gear tab — pick up rares/magic worth keeping, scored by WeightedSum.

For each enabled equipment slot the generator emits one rule that picks up gear of
that slot and keeps only those whose WeightedSum mod score clears your threshold.
The per-slot mod weights are the bot's own (extracted from its default pickit), so
a base of any defence type — incl. the str/dex/int hybrids — scores on whatever
mods it rolled. Tune just the one number (the threshold) per slot.

Everything is OFF by default, so this adds nothing to the .ipd until you opt in.
Mixed into PickitApp; methods operate on the shared instance.
"""
import tkinter as tk

import poe2_pickit_generator as gen
from ui_common import *


def _fmt_threshold(v):
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else f"{f:g}"
    except (TypeError, ValueError):
        return ""


def _pretty_mod(stat_id):
    """Human-friendly mod name, e.g. base_maximum_life -> 'maximum life'."""
    s = stat_id
    for pre in ("base_", "local_", "additional_"):
        if s.startswith(pre):
            s = s[len(pre):]
    s = s.replace("_+%", " %").replace("_%", " %").replace("_+", " +").replace("_", " ")
    return s.strip()


def _slot_tip_text(display, mods, default_threshold):
    """Tooltip body: what this slot scores + what its number means."""
    top = ", ".join(_pretty_mod(m) for m, _w in mods[:8])
    more = f"  (+{len(mods) - 8} more)" if len(mods) > 8 else ""
    return (f"{display}: each item's mods are multiplied by their weight and summed; "
            f"kept if the total ≥ your number.\n\n"
            f"Scores: {top}{more}.\n\n"
            f"Bot's recommended bar: {default_threshold}. Lower it to keep more items, "
            f"raise it to keep only the best. Numbers are per-slot — don't compare across slots.")


class _Tip:
    """Minimal hover tooltip (no helper exists in this app)."""
    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

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


class RareGearTab:
    # ══════════════════════════════════════════════════════════════════════════
    #  RARE GEAR PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_raregear_page(self, page):
        tab_idx = self._building_tab_idx

        hdr_bar = tk.Frame(page, bg=BG2)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, text="Rare Gear",
                 bg=BG2, fg=GOLD, font=("Segoe UI", 12, "bold"),
                 padx=16, pady=8).pack(side="left")
        tk.Label(hdr_bar,
                 text="Score each slot's mods (WeightedSum) and keep what clears your threshold. "
                      "All off by default.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=4).pack(side="left")
        tk.Label(hdr_bar, textvariable=self._rare_gear_count_var,
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="right", padx=8)
        sep(page).pack(fill="x")

        tbar = tk.Frame(page, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 4))
        btn(tbar, "Enable All",  lambda: self._raregear_set_all(True)).pack(side="left", padx=(0, 4))
        btn(tbar, "Disable All", lambda: self._raregear_set_all(False)).pack(side="left")
        self._rare_gear_magic_var = tk.BooleanVar(value=self._rare_gear_magic)
        mcb = checkbtn(tbar, "Also keep Magic items (not just Rare)", self._rare_gear_magic_var)
        mcb.configure(command=self._on_raregear_magic)
        mcb.pack(side="right", padx=(0, 8))

        tk.Label(page,
                 text="How it works: each item's mods are multiplied by the slot's weights and added up; "
                      "the item is kept if that total ≥ your number. The numbers are the bot's own "
                      "recommended bar per slot — they are NOT comparable across slots (a Wand's 800 isn't "
                      "'stricter' than a Ring's 320). Lower a number to keep more items; raise it to keep "
                      "only the best. Hover the ⓘ on any slot to see exactly what it scores.",
                 bg=BG, fg=TEXT_DIM, font=FONT_SM, justify="left", wraplength=1180).pack(
                     anchor="w", padx=12, pady=(2, 4))
        sep(page).pack(fill="x")

        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        vsb    = tk.Scrollbar(page, orient="vertical", command=canvas.yview,
                              bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        for w in (canvas, inner):
            w.bind("<MouseWheel>", lambda e, c=canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))
            w.bind("<Button-4>",   lambda e, c=canvas: c.yview_scroll(-3, "units"))
            w.bind("<Button-5>",   lambda e, c=canvas: c.yview_scroll( 3, "units"))

        self._raregear_canvas = canvas
        self._tab_canvases[tab_idx] = canvas

        self._rare_gear_vars = {}
        for token, display, _kind in gen.RARE_GEAR_SLOTS:
            card = self._make_raregear_card(token, display, inner)
            card.pack(fill="x", padx=14, pady=3)
        self._update_raregear_count()

    def _make_raregear_card(self, token, display, parent):
        preset = gen.WEIGHTED_SUM_PRESETS.get(token, (100, []))
        def_threshold, mods = preset
        saved   = self._rare_gear.get(token, {}) if isinstance(self._rare_gear.get(token), dict) else {}
        enabled = bool(saved.get("enabled", False))
        thr_val = saved.get("threshold", def_threshold)

        frame = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        frame._token = token

        en_var  = tk.BooleanVar(value=enabled)
        thr_var = tk.StringVar(value=_fmt_threshold(thr_val))

        cb = checkbtn(frame, display, en_var)
        cb.configure(command=lambda t=token: self._on_raregear_change(t))
        cb.pack(side="left", padx=(10, 8), pady=6)

        info = tk.Label(frame, text=f"({len(mods)} mods · bot default {_fmt_threshold(def_threshold)})  ⓘ",
                        bg=BG2, fg=TEXT_DIM, font=("Segoe UI", 8), cursor="question_arrow")
        info.pack(side="left", padx=(0, 4))
        _Tip(info, _slot_tip_text(display, mods, _fmt_threshold(def_threshold)))

        thrw = entry(frame, thr_var, width=6)
        thrw.pack(side="right", padx=(4, 12), ipady=2)
        thrw.bind("<FocusOut>", lambda e, t=token: self._on_raregear_change(t))
        thrw.bind("<Return>",   lambda e, t=token: self._on_raregear_change(t))
        tk.Label(frame, text="keep if score ≥", bg=BG2, fg=TEXT_DIM,
                 font=FONT_SM).pack(side="right", padx=(8, 4))

        self._rare_gear_vars[token] = {
            "enabled": en_var, "threshold": thr_var, "def": def_threshold,
            "minw": thrw,
        }
        self._raregear_set_row_state(token, enabled)
        return frame

    def _raregear_set_row_state(self, token, enabled):
        v = self._rare_gear_vars.get(token)
        if not v:
            return
        try:
            v["minw"].configure(state=("normal" if enabled else "disabled"))
        except Exception:
            pass

    def _on_raregear_change(self, token):
        v = self._rare_gear_vars.get(token)
        if not v:
            return
        enabled = bool(v["enabled"].get())
        try:
            threshold = float(v["threshold"].get())
        except (ValueError, tk.TclError):
            threshold = v["def"]                       # blank/garbage → preset default
            v["threshold"].set(_fmt_threshold(threshold))
        self._rare_gear[token] = {"enabled": enabled, "threshold": threshold}
        self._raregear_set_row_state(token, enabled)
        self._save_rare_gear()

    def _raregear_set_all(self, enabled_val):
        for token, v in self._rare_gear_vars.items():
            v["enabled"].set(enabled_val)
            self._on_raregear_change(token)

    def _on_raregear_magic(self):
        self._rare_gear_magic = bool(self._rare_gear_magic_var.get())
        self._save_rare_gear()

    def _save_rare_gear(self):
        self.cfg["rare_gear"]       = dict(self._rare_gear)
        self.cfg["rare_gear_magic"] = self._rare_gear_magic
        self._update_raregear_count()
        self.after(0, self._save_states_now)   # persists the whole cfg

    def _update_raregear_count(self):
        total   = len(gen.RARE_GEAR_SLOTS)
        enabled = sum(1 for s in self._rare_gear.values()
                      if isinstance(s, dict) and s.get("enabled"))
        self._rare_gear_count_var.set(f"{enabled} / {total} enabled")
