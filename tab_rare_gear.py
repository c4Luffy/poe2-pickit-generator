"""Rare Gear tab — pick up rares/magic worth keeping, scored by WeightedSum.

Two modes, switched at the top of the tab:
- Simple (default): one [Category]/[WeaponCategory] rule per equipment slot.
- Per-base (Pro): one [Type] rule per base, split by slot × defence type ×
  Low/Mid/High base bracket (see rare_gear_catalog + rare_gear_templates), with
  auto-derived prefix/suffix rules and jewel archetypes.

For each enabled equipment slot the generator emits one rule that picks up gear of
that slot and keeps only those whose WeightedSum mod score clears your threshold.
The per-slot mod weights are the bot's own (extracted from its default pickit), so
a base of any defence type — incl. the str/dex/int hybrids — scores on whatever
mods it rolled. Tune just the one number (the threshold) per slot.

Anti-clutter controls (the bot's own thresholds keep far too much):
- Strictness presets bulk-set every threshold to default × factor (Strict = 1.5×).
- Min item level (default 65) keeps campaign junk out of the stash (post-#).
- Min base tier (0 = off) stops low-tier bases being picked up at all (pre-#).
- Magic items are opt-in (off by default).

Everything is OFF by default, so this adds nothing to the .ipd until you opt in.
Mixed into PickitApp; methods operate on the shared instance.
"""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import poe2_pickit_generator as gen
import rare_gear_catalog as rgc
import rare_gear_templates as rgt
from pickit_assembly import build_rare_gear_pro_rules, pro_section_key
from ui_common import *

# Combo display order + labels for the Per-base mode rows.
_PRO_COMBOS = [
    ("armour", "Armour"), ("evasion", "Evasion"), ("es", "Energy Shield"),
    ("armour_evasion", "Armour + Evasion"), ("armour_es", "Armour + ES"),
    ("evasion_es", "Evasion + ES"), ("tri", "Str/Dex/Int"), ("all", "All bases"),
]
_PRO_BRACKETS = [("low", "Low"), ("mid", "Mid"), ("high", "High")]


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
        # widget destroyed while hovered (e.g. a card rebuild) must not leak
        # the override-redirect Toplevel on screen
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


class RareGearTab:
    # ══════════════════════════════════════════════════════════════════════════
    #  RARE GEAR PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_raregear_page(self, page):
        tab_idx = self._building_tab_idx
        self._raregear_tab_idx = tab_idx

        hdr_bar = tk.Frame(page, bg=BG2)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, text="Rare Gear",
                 bg=BG2, fg=GOLD, font=("Segoe UI", 12, "bold"),
                 padx=16, pady=8).pack(side="left")
        self._raregear_mode_btns = {}
        for mode, label_txt in (("simple", "Simple"), ("pro", "Per-base")):
            b = btn(hdr_bar, label_txt, lambda m=mode: self._raregear_set_mode(m))
            b.pack(side="left", padx=(0, 4))
            self._raregear_mode_btns[mode] = b
        tk.Label(hdr_bar,
                 text="Score mods (WeightedSum), keep what clears your threshold. All off by default.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="left")
        tk.Label(hdr_bar, textvariable=self._rare_gear_count_var,
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="right", padx=8)
        sep(page).pack(fill="x")

        self._raregear_body = tk.Frame(page, bg=BG)
        self._raregear_body.pack(fill="both", expand=True)
        self._raregear_simple_frame = tk.Frame(self._raregear_body, bg=BG)
        self._raregear_pro_frame = None          # built on first switch to Per-base
        self._build_raregear_simple(self._raregear_simple_frame, tab_idx)
        self._raregear_show_mode()

    def _build_raregear_simple(self, page, tab_idx):
        tbar = tk.Frame(page, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 2))
        btn(tbar, "Enable All",  lambda: self._raregear_set_all(True)).pack(side="left", padx=(0, 4))
        btn(tbar, "Disable All", lambda: self._raregear_set_all(False)).pack(side="left")
        self._rare_gear_magic_var = tk.BooleanVar(value=self._rare_gear_magic)
        mcb = checkbtn(tbar, "Also keep Magic items (not just Rare)", self._rare_gear_magic_var)
        mcb.configure(command=self._on_raregear_magic)
        mcb.pack(side="right", padx=(0, 8))

        # Anti-clutter row: one-click strictness + the two junk gates.
        tbar2 = tk.Frame(page, bg=BG)
        tbar2.pack(fill="x", padx=10, pady=(2, 4))
        tk.Label(tbar2, text="Strictness:", bg=BG, fg=TEXT_DIM,
                 font=FONT_SM).pack(side="left", padx=(0, 6))
        for name, factor in gen.RARE_GEAR_STRICTNESS:
            b = btn(tbar2, name, lambda f=factor: self._raregear_apply_strictness(f))
            b.pack(side="left", padx=(0, 4))
            if factor == 1.5:
                _Tip(b, "Recommended if the bot stashes too much junk.")

        self._rare_gear_mintier_var = tk.StringVar(value=str(self._rare_gear_min_tier))
        tw = entry(tbar2, self._rare_gear_mintier_var, width=4)
        tw.pack(side="right", padx=(4, 8), ipady=1)
        tw.bind("<FocusOut>", lambda e: self._on_raregear_gates())
        tw.bind("<Return>",   lambda e: self._on_raregear_gates())
        tl = tk.Label(tbar2, text="min base tier ⓘ", bg=BG, fg=TEXT_DIM, font=FONT_SM,
                      cursor="question_arrow")
        tl.pack(side="right", padx=(12, 4))
        _Tip(tl, "Only pick up bases of at least this tier (higher = better base). "
                 "Cuts pickups at the source — low-tier bases aren't even grabbed. "
                 "The bot's own rules use 3. 0 = off. (Not applied to Jewels — no base tiers.)")

        self._rare_gear_minilvl_var = tk.StringVar(value=str(self._rare_gear_min_ilvl))
        iw = entry(tbar2, self._rare_gear_minilvl_var, width=4)
        iw.pack(side="right", padx=(4, 0), ipady=1)
        iw.bind("<FocusOut>", lambda e: self._on_raregear_gates())
        iw.bind("<Return>",   lambda e: self._on_raregear_gates())
        il = tk.Label(tbar2, text="min item level ⓘ", bg=BG, fg=TEXT_DIM, font=FONT_SM,
                      cursor="question_arrow")
        il.pack(side="right", padx=(12, 4))
        _Tip(il, "Only stash items of at least this item level — keeps campaign junk "
                 "out of your stash (maps drop ilvl 65+; top mod tiers need ~79+). "
                 "Checked after identifying, so items are still picked up and ID'd. 0 = off.")

        tk.Label(page,
                 text="How it works: each item's mods are multiplied by the slot's weights and added up; "
                      "the item is kept if that total ≥ your number. The defaults are the BOT's own bars — "
                      "they keep a lot. Stash filling with junk? Click Strict (sets every slot to 1.5× the "
                      "bot default; Very strict = 2×) — the numbers below update so you can still fine-tune. "
                      "Numbers are NOT comparable across slots (a Wand's 800 isn't 'stricter' than a Ring's "
                      "320). Hover the ⓘ on any slot to see exactly what it scores.",
                 bg=BG, fg=TEXT_DIM, font=FONT_SM, justify="left", wraplength=1180).pack(
                     anchor="w", padx=12, pady=(2, 4))
        sep(page).pack(fill="x")

        # Shared scrollable helper — scrolling is handled by the app's global
        # wheel router (per-widget binds here used to double the scroll speed).
        inner, canvas = self._scrollable(page)
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

    def _raregear_apply_strictness(self, factor):
        """Bulk-set every slot's threshold to its preset default × factor."""
        for token, v in self._rare_gear_vars.items():
            v["threshold"].set(_fmt_threshold(round(v["def"] * factor)))
            self._on_raregear_change(token)

    def _on_raregear_gates(self):
        """Parse + persist the min item level / min base tier entries."""
        for var, attr in ((self._rare_gear_minilvl_var, "_rare_gear_min_ilvl"),
                          (self._rare_gear_mintier_var, "_rare_gear_min_tier")):
            try:
                val = max(0, int(float(var.get())))
            except (ValueError, tk.TclError):
                val = getattr(self, attr)          # garbage → keep current
            var.set(str(val))
            setattr(self, attr, val)
        self._save_rare_gear()

    def _on_raregear_magic(self):
        self._rare_gear_magic = bool(self._rare_gear_magic_var.get())
        self._save_rare_gear()

    def _save_rare_gear(self):
        self.cfg["rare_gear"]          = dict(self._rare_gear)
        self.cfg["rare_gear_magic"]    = self._rare_gear_magic
        self.cfg["rare_gear_min_ilvl"] = self._rare_gear_min_ilvl
        self.cfg["rare_gear_min_tier"] = self._rare_gear_min_tier
        self.cfg["rare_gear_mode"]     = self._rare_gear_mode
        self.cfg["rare_gear_pro"]      = dict(self._rare_gear_pro)
        self._update_raregear_count()
        self._save_states_soon()              # persists the whole cfg (debounced)

    def _update_raregear_count(self):
        if self._rare_gear_mode == "pro":
            n = sum(1 for grp in ("sections", "jewels", "amulets")
                    for s in self._rare_gear_pro.get(grp, {}).values()
                    if isinstance(s, dict) and s.get("on"))
            n += sum(1 for k in ("belts", "rings")
                     if isinstance(self._rare_gear_pro.get(k), dict)
                     and self._rare_gear_pro[k].get("on"))
            exp = self._rare_gear_pro.get("expert")
            if (isinstance(exp, dict) and exp.get("on")
                    and str(exp.get("text", "")).strip()):
                n += 1
            try:      # exact projection: run the real emitter, count rule lines
                rules = sum(1 for l in build_rare_gear_pro_rules(
                    {"rare_gear_pro": self._rare_gear_pro}) if l.startswith("["))
            except Exception:
                rules = 0
            self._rare_gear_count_var.set(f"{n} section(s) enabled  →  {rules} rules")
        else:
            total   = len(gen.RARE_GEAR_SLOTS)
            enabled = sum(1 for s in self._rare_gear.values()
                          if isinstance(s, dict) and s.get("enabled"))
            self._rare_gear_count_var.set(f"{enabled} / {total} enabled")

    # ══════════════════════════════════════════════════════════════════════════
    #  PER-BASE (PRO) MODE
    # ══════════════════════════════════════════════════════════════════════════

    def _raregear_set_mode(self, mode):
        if mode == self._rare_gear_mode:
            return
        self._rare_gear_mode = mode
        self._raregear_show_mode()
        self._save_rare_gear()

    def _raregear_show_mode(self):
        for m, b in self._raregear_mode_btns.items():
            active = (m == self._rare_gear_mode)
            try:
                b.configure(fg_color=GOLD if active else BG3,
                            text_color="#111111" if active else TEXT)
            except Exception:
                pass
        self._raregear_simple_frame.pack_forget()
        if self._raregear_pro_frame is not None:
            self._raregear_pro_frame.pack_forget()
        if self._rare_gear_mode == "pro":
            if self._raregear_pro_frame is None:
                self._raregear_pro_frame = tk.Frame(self._raregear_body, bg=BG)
                self._build_raregear_pro(self._raregear_pro_frame)
            self._raregear_pro_frame.pack(fill="both", expand=True)
            self._tab_canvases[self._raregear_tab_idx] = self._raregear_pro_canvas
        else:
            self._raregear_simple_frame.pack(fill="both", expand=True)
            self._tab_canvases[self._raregear_tab_idx] = self._raregear_canvas
        self._update_raregear_count()

    def _build_raregear_pro(self, page):
        tk.Label(page,
                 text="One rule per base type — like a hand-written pickit. Each slot splits by "
                      "defence type; each row has Low (campaign) / Mid (cruel) / High (endgame) "
                      "base brackets: tick a bracket, tune its score threshold. P/S also emits "
                      "prefix-only and suffix-only rules at 60% / 55% of your number. The Simple "
                      "tab's min item level does NOT apply here (brackets + base tiers do that job).",
                 bg=BG, fg=TEXT_DIM, font=FONT_SM, justify="left", wraplength=1180).pack(
                     anchor="w", padx=12, pady=(6, 4))
        tbar = tk.Frame(page, bg=BG)
        tbar.pack(fill="x", padx=12, pady=(0, 4))
        eb = btn(tbar, "Enable all High (endgame)", self._raregear_pro_enable_high)
        eb.pack(side="left")
        _Tip(eb, "Tick the High (endgame) bracket of every slot and defence type — "
                 "the usual map-farming setup — without ~40 clicks. Thresholds and "
                 "P/S / Magic flags you already set are kept.")
        btn(tbar, "Disable all", self._raregear_pro_disable_all).pack(side="left", padx=(6, 0))
        sep(page).pack(fill="x")

        # Shared scrollable helper (global wheel router handles scrolling). The
        # pro frame is built lazily, so point the helper's tab registration at
        # this tab instead of whatever tab happened to be built last.
        prev_idx = getattr(self, "_building_tab_idx", None)
        self._building_tab_idx = self._raregear_tab_idx
        inner, canvas = self._scrollable(page)
        self._building_tab_idx = prev_idx
        self._raregear_pro_canvas = canvas

        for family, groups in rgc.CATALOG.items():
            self._make_raregear_family_card(inner, family, groups)
        self._make_raregear_amulet_card(inner)
        self._make_raregear_beltring_card(inner)
        self._make_raregear_jewel_card(inner)
        self._make_raregear_expert_card(inner)

    def _make_raregear_family_card(self, parent, family, groups):
        rows = [(c, lbl) for c, lbl in _PRO_COMBOS
                if c in groups and rgt.get_template(family, c)
                and any(groups[c].get(b) for b, _ in _PRO_BRACKETS)]
        if not rows:
            return
        n_bases = sum(len(groups[c].get(b) or []) for c, _ in rows for b, _ in _PRO_BRACKETS)

        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=14, pady=3)
        hdr = tk.Frame(card, bg=BG2, cursor="hand2")
        hdr.pack(fill="x")
        arrow = tk.Label(hdr, text="▸", bg=BG2, fg=TEXT_DIM, font=FONT, padx=8, pady=6)
        arrow.pack(side="left")
        tk.Label(hdr, text=rgc.FAMILY_LABELS.get(family, family),
                 bg=BG2, fg=TEXT, font=FONT).pack(side="left")
        tk.Label(hdr, text=f"{len(rows)} type(s) · {n_bases} bases",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=10).pack(side="left")
        body = tk.Frame(card, bg=BG2)

        def _toggle(_e=None, fam=family, grp=groups):
            if body.winfo_manager():
                body.pack_forget()
                arrow.configure(text="▸")
            else:
                if not body.winfo_children():
                    self._build_raregear_family_rows(body, fam, grp)
                body.pack(fill="x")
                arrow.configure(text="▾")
        for w in (hdr, arrow):
            w.bind("<Button-1>", _toggle)

    def _build_raregear_family_rows(self, body, family, groups):
        head = tk.Frame(body, bg=BG2)
        head.pack(fill="x", padx=8)
        tk.Label(head, text="", bg=BG2, font=FONT_SM, width=22, anchor="w").pack(side="left")
        for _b, blabel in _PRO_BRACKETS:
            tk.Label(head, text=blabel, bg=BG2, fg=TEXT_DIM, font=FONT_SM,
                     width=14, anchor="w").pack(side="left")
        tk.Label(head, text="Extras", bg=BG2, fg=TEXT_DIM,
                 font=FONT_SM, anchor="w").pack(side="left")

        for combo, clabel in _PRO_COMBOS:
            if combo not in groups:
                continue
            tmpl = rgt.get_template(family, combo)
            if not tmpl or not any(groups[combo].get(b) for b, _ in _PRO_BRACKETS):
                continue
            row = tk.Frame(body, bg=BG2)
            row.pack(fill="x", padx=8, pady=2)
            lab = tk.Label(row, text=clabel, bg=BG2, fg=TEXT, font=FONT_SM,
                           width=22, anchor="w")
            lab.pack(side="left")
            hint = groups[combo].get("high") or groups[combo].get("mid") or groups[combo].get("low")
            _Tip(lab, f"{rgc.FAMILY_LABELS.get(family, family)} — {clabel}. "
                      f"e.g. {', '.join(hint[:4])}.\n"
                      f"Default threshold {tmpl['thr']}; base-tier gates "
                      f"L≥{tmpl['tier']['low']} / M≥{tmpl['tier']['mid']} / H≥{tmpl['tier']['high']}.")
            for bracket, _blabel in _PRO_BRACKETS:
                cell = tk.Frame(row, bg=BG2, width=118)
                cell.pack(side="left")
                cell.pack_propagate(False)
                cell.configure(height=30)
                bases = groups[combo].get(bracket) or []
                if not bases:
                    tk.Label(cell, text="—", bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=20)
                    continue
                key = pro_section_key(family, combo, bracket)
                saved = self._rare_gear_pro["sections"].get(key)
                saved = saved if isinstance(saved, dict) else {}
                on_var  = tk.BooleanVar(value=bool(saved.get("on", False)))
                thr_var = tk.StringVar(value=_fmt_threshold(saved.get("thr", tmpl["thr"])))
                cb = checkbtn(cell, "", on_var)
                cb.configure(command=lambda k=key: self._on_raregear_pro_change(k),
                             width=22, checkbox_width=16, checkbox_height=16)
                cb.pack(side="left")
                ent = entry(cell, thr_var, width=5)
                ent.configure(height=24)
                ent.pack(side="left", padx=(0, 6))
                ent.bind("<FocusOut>", lambda e, k=key: self._on_raregear_pro_change(k))
                ent.bind("<Return>",   lambda e, k=key: self._on_raregear_pro_change(k))
                self._raregear_pro_vars[key] = {
                    "on": on_var, "thr": thr_var, "def": tmpl["thr"],
                    "entry": ent, "ps": None, "magic": None,
                }
                ent.configure(state=("normal" if on_var.get() else "disabled"))

            extras = tk.Frame(row, bg=BG2)
            extras.pack(side="left", padx=(6, 0))
            # P/S + Magic apply to the whole combo row (all its brackets).
            row_keys = [pro_section_key(family, combo, b) for b, _ in _PRO_BRACKETS
                        if groups[combo].get(b)]
            if tmpl.get("prefix") and tmpl.get("suffix"):
                first = self._rare_gear_pro["sections"].get(row_keys[0], {})
                ps_var = tk.BooleanVar(value=bool(first.get("ps", True))
                                       if isinstance(first, dict) else True)
                pcb = checkbtn(extras, "P/S", ps_var)
                pcb.configure(command=lambda ks=tuple(row_keys): self._on_raregear_pro_row_flags(ks),
                              width=54, checkbox_width=16, checkbox_height=16)
                pcb.pack(side="left")
                _Tip(pcb, "Also emit prefix-only and suffix-only rules at 60% / 55% "
                          "of the threshold (catches items with one great half).")
                for k in row_keys:
                    self._raregear_pro_vars[k]["ps"] = ps_var
            if tmpl.get("magic"):
                first = self._rare_gear_pro["sections"].get(row_keys[0], {})
                mg_var = tk.BooleanVar(value=bool(first.get("magic", False))
                                       if isinstance(first, dict) else False)
                mcb = checkbtn(extras, "Magic", mg_var)
                mcb.configure(command=lambda ks=tuple(row_keys): self._on_raregear_pro_row_flags(ks),
                              width=70, checkbox_width=16, checkbox_height=16)
                mcb.pack(side="left")
                _Tip(mcb, f"Also keep Magic items with a big {_pretty_mod(tmpl['magic'][0])} roll.")
                for k in row_keys:
                    self._raregear_pro_vars[k]["magic"] = mg_var

    def _raregear_pro_enable_high(self):
        """Bulk-tick the High (endgame) bracket of every supported section."""
        for family, groups in rgc.CATALOG.items():
            for combo, brackets in groups.items():
                if not rgt.get_template(family, combo) or not brackets.get("high"):
                    continue
                key = pro_section_key(family, combo, "high")
                sec = self._rare_gear_pro["sections"].get(key)
                sec = dict(sec) if isinstance(sec, dict) else {}
                sec["on"] = True
                self._rare_gear_pro["sections"][key] = sec
        self._raregear_pro_refresh_vars()
        self._save_rare_gear()

    def _raregear_pro_disable_all(self):
        if not messagebox.askyesno(
                "Disable all",
                "Untick every Per-base section (families, jewels, amulets, belts, "
                "rings) and switch Expert rules off?\n\nCustom thresholds are reset "
                "to defaults; your Expert rules text is kept.", parent=self):
            return
        self._rare_gear_pro["sections"] = {}
        self._rare_gear_pro["jewels"] = {}
        self._rare_gear_pro["amulets"] = {}
        self._rare_gear_pro["belts"] = {}
        self._rare_gear_pro["rings"] = {}
        exp = self._rare_gear_pro.get("expert")
        if isinstance(exp, dict):
            exp["on"] = False                      # keep the text, just turn it off
        self._raregear_pro_refresh_vars()
        self._save_rare_gear()

    def _raregear_pro_refresh_vars(self):
        """Push self._rare_gear_pro back into every built widget (bulk actions).

        Family rows are built lazily, so unexpanded cards need nothing — they
        read the state dict when first expanded."""
        secs = self._rare_gear_pro.get("sections", {})
        for key, v in self._raregear_pro_vars.items():
            s = secs.get(key)
            s = s if isinstance(s, dict) else {}
            v["on"].set(bool(s.get("on", False)))
            v["thr"].set(_fmt_threshold(s.get("thr", v["def"])))
            if v["ps"] is not None:
                v["ps"].set(bool(s.get("ps", True)))
            if v["magic"] is not None:
                v["magic"].set(bool(s.get("magic", False)))
            try:
                v["entry"].configure(state=("normal" if v["on"].get() else "disabled"))
            except Exception:
                pass
        jw = self._rare_gear_pro.get("jewels", {})
        for key, v in self._raregear_jewel_vars.items():
            j = jw.get(key)
            j = j if isinstance(j, dict) else {}
            v["on"].set(bool(j.get("on", False)))
            if v["thr"] is not None:
                v["thr"].set(_fmt_threshold(j.get("thr", v["def"])))
                try:
                    v["entry"].configure(state=("normal" if v["on"].get() else "disabled"))
                except Exception:
                    pass
        am = self._rare_gear_pro.get("amulets", {})
        for key, v in getattr(self, "_raregear_amulet_vars", {}).items():
            a = am.get(key)
            a = a if isinstance(a, dict) else {}
            v["on"].set(bool(a.get("on", False)))
            if v["thr"] is not None:
                v["thr"].set(_fmt_threshold(a.get("thr", v["def"])))
                try:
                    v["entry"].configure(state=("normal" if v["on"].get() else "disabled"))
                except Exception:
                    pass
        belts = self._rare_gear_pro.get("belts")
        belts = belts if isinstance(belts, dict) else {}
        for v in getattr(self, "_raregear_beltring_vars", {}).values():
            v["on"].set(bool(belts.get("on", False)))
            v["magic"].set(bool(belts.get("magic", False)))
            v["thr"].set(_fmt_threshold(belts.get("thr", v["def"])))
            if v["entry"] is not None:
                try:
                    v["entry"].configure(state=("normal" if v["on"].get() else "disabled"))
                except Exception:
                    pass
        rings = self._rare_gear_pro.get("rings")
        rings = rings if isinstance(rings, dict) else {}
        archs = rings.get("archetypes")
        archs = archs if isinstance(archs, dict) else {}
        for key, v in getattr(self, "_raregear_ring_vars", {}).items():
            s = archs.get(key)
            s = s if isinstance(s, dict) else {}
            v["on"].set(bool(s.get("on", False)))
            v["thr"].set(_fmt_threshold(s.get("thr", v["def"])))
            try:
                v["entry"].configure(state=("normal" if v["on"].get() else "disabled"))
            except Exception:
                pass
        if hasattr(self, "_raregear_ring_magic"):
            self._raregear_ring_magic.set(bool(rings.get("magic", False)))
        if hasattr(self, "_raregear_expert_on"):
            exp = self._rare_gear_pro.get("expert")
            self._raregear_expert_on.set(bool(exp.get("on")) if isinstance(exp, dict) else False)

    def _on_raregear_pro_change(self, key):
        v = self._raregear_pro_vars.get(key)
        if not v:
            return
        try:
            thr = float(v["thr"].get())
        except (ValueError, tk.TclError):
            thr = v["def"]
            v["thr"].set(_fmt_threshold(thr))
        sec = {"on": bool(v["on"].get()), "thr": thr}
        if v["ps"] is not None:
            sec["ps"] = bool(v["ps"].get())
        if v["magic"] is not None:
            sec["magic"] = bool(v["magic"].get())
        self._rare_gear_pro["sections"][key] = sec
        try:
            v["entry"].configure(state=("normal" if sec["on"] else "disabled"))
        except Exception:
            pass
        self._save_rare_gear()

    def _on_raregear_pro_row_flags(self, keys):
        for k in keys:
            self._on_raregear_pro_change(k)

    def _make_raregear_amulet_card(self, parent):
        amulets = self._rare_gear_pro.setdefault("amulets", {})
        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=14, pady=3)
        hdr = tk.Frame(card, bg=BG2)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Amulets", bg=BG2, fg=TEXT, font=FONT, padx=8, pady=6).pack(side="left")
        tk.Label(hdr, text=f"build archetypes over all {len(rgc.AMULET_BASES)} bases",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        body = tk.Frame(card, bg=BG2)
        body.pack(fill="x", padx=8, pady=(0, 6))
        self._raregear_amulet_vars = {}
        for arch in rgt.AMULET_ARCHETYPES:
            saved = amulets.get(arch["key"])
            saved = saved if isinstance(saved, dict) else {}
            on_var  = tk.BooleanVar(value=bool(saved.get("on", False)))
            thr_var = tk.StringVar(value=_fmt_threshold(saved.get("thr", arch["thr"])))
            row = tk.Frame(body, bg=BG2)
            row.pack(fill="x", pady=1)
            cb = checkbtn(row, arch["label"], on_var)
            cb.configure(command=lambda k=arch["key"]: self._on_raregear_amulet_change(k))
            cb.pack(side="left")
            ent = entry(row, thr_var, width=5)
            ent.configure(height=24)
            ent.pack(side="left", padx=(8, 0))
            ent.bind("<FocusOut>", lambda e, k=arch["key"]: self._on_raregear_amulet_change(k))
            ent.bind("<Return>",   lambda e, k=arch["key"]: self._on_raregear_amulet_change(k))
            self._raregear_amulet_vars[arch["key"]] = {"on": on_var, "thr": thr_var,
                                                       "def": arch["thr"], "entry": ent}
            ent.configure(state=("normal" if on_var.get() else "disabled"))
        saved = amulets.get("magic")
        on_var = tk.BooleanVar(value=bool(saved.get("on", False)) if isinstance(saved, dict) else False)
        row = tk.Frame(body, bg=BG2)
        row.pack(fill="x", pady=1)
        cb = checkbtn(row, "Magic amulets — +3 gem levels or 50%+ rarity", on_var)
        cb.configure(command=lambda: self._on_raregear_amulet_change("magic"))
        cb.pack(side="left")
        self._raregear_amulet_vars["magic"] = {"on": on_var, "thr": None, "def": None, "entry": None}

    def _on_raregear_amulet_change(self, key):
        v = self._raregear_amulet_vars.get(key)
        if not v:
            return
        sec = {"on": bool(v["on"].get())}
        if v["thr"] is not None:
            try:
                sec["thr"] = int(float(v["thr"].get()))
            except (ValueError, tk.TclError):
                sec["thr"] = v["def"]
                v["thr"].set(_fmt_threshold(v["def"]))
            try:
                v["entry"].configure(state=("normal" if sec["on"] else "disabled"))
            except Exception:
                pass
        self._rare_gear_pro.setdefault("amulets", {})[key] = sec
        self._save_rare_gear()

    def _make_raregear_beltring_card(self, parent):
        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=14, pady=3)
        hdr = tk.Frame(card, bg=BG2)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Belts & Rings", bg=BG2, fg=TEXT, font=FONT, padx=8, pady=6).pack(side="left")
        tk.Label(hdr, text=f"{len(rgc.BELT_BASES)} belt / {len(rgc.RING_BASES)} ring bases",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        body = tk.Frame(card, bg=BG2)
        body.pack(fill="x", padx=8, pady=(0, 6))

        # Belts: one row (prefix/suffix rules per base, optional Magic).
        self._raregear_beltring_vars = {}
        key, def_thr = "belts", rgt.BELT_TEMPLATE["thr"]
        saved = self._rare_gear_pro.get(key)
        saved = saved if isinstance(saved, dict) else {}
        on_var  = tk.BooleanVar(value=bool(saved.get("on", False)))
        thr_var = tk.StringVar(value=_fmt_threshold(saved.get("thr", def_thr)))
        mg_var  = tk.BooleanVar(value=bool(saved.get("magic", False)))
        row = tk.Frame(body, bg=BG2)
        row.pack(fill="x", pady=1)
        cb = checkbtn(row, "Belts — life + res prefixes/suffixes", on_var)
        cb.configure(command=lambda k=key: self._on_raregear_beltring_change(k))
        cb.pack(side="left")
        ent = entry(row, thr_var, width=5)
        ent.configure(height=24)
        ent.pack(side="left", padx=(8, 8))
        ent.bind("<FocusOut>", lambda e, k=key: self._on_raregear_beltring_change(k))
        ent.bind("<Return>",   lambda e, k=key: self._on_raregear_beltring_change(k))
        mcb = checkbtn(row, "Magic too", mg_var)
        mcb.configure(command=lambda k=key: self._on_raregear_beltring_change(k),
                      width=90, checkbox_width=16, checkbox_height=16)
        mcb.pack(side="left")
        self._raregear_beltring_vars[key] = {"on": on_var, "thr": thr_var,
                                             "def": def_thr, "magic": mg_var, "entry": ent}
        ent.configure(state=("normal" if on_var.get() else "disabled"))

        # Rings: one row per build archetype, each with its own threshold.
        rings_saved = self._rare_gear_pro.get("rings")
        rings_saved = rings_saved if isinstance(rings_saved, dict) else {}
        arch_saved = rings_saved.get("archetypes")
        legacy_all = not isinstance(arch_saved, dict) and bool(rings_saved.get("on"))
        arch_saved = arch_saved if isinstance(arch_saved, dict) else {}
        tk.Label(body, text=f"Rings — {len(rgt.RING_ARCHETYPES)} build archetypes over "
                            f"all {len(rgc.RING_BASES)} bases:",
                 bg=BG2, fg=TEXT, font=FONT_SM).pack(anchor="w", pady=(8, 1))
        self._raregear_ring_vars = {}
        grid = tk.Frame(body, bg=BG2)
        grid.pack(fill="x")
        for i, arch in enumerate(rgt.RING_ARCHETYPES):
            s = arch_saved.get(arch["key"])
            s = s if isinstance(s, dict) else {}
            on_var  = tk.BooleanVar(value=bool(s.get("on", legacy_all)))
            thr_var = tk.StringVar(value=_fmt_threshold(s.get("thr", arch["thr"])))
            cell = tk.Frame(grid, bg=BG2)
            cell.grid(row=i // 3, column=i % 3, sticky="w", padx=(12, 10), pady=1)
            cb = checkbtn(cell, arch["label"], on_var)
            cb.configure(command=self._on_raregear_rings_change,
                         width=150, checkbox_width=16, checkbox_height=16)
            cb.pack(side="left")
            ent = entry(cell, thr_var, width=5)
            ent.configure(height=24)
            ent.pack(side="left", padx=(4, 0))
            ent.bind("<FocusOut>", lambda e: self._on_raregear_rings_change())
            ent.bind("<Return>",   lambda e: self._on_raregear_rings_change())
            self._raregear_ring_vars[arch["key"]] = {"on": on_var, "thr": thr_var,
                                                     "def": arch["thr"], "entry": ent}
            ent.configure(state=("normal" if on_var.get() else "disabled"))
        self._raregear_ring_magic = tk.BooleanVar(
            value=bool(rings_saved.get("magic", False)))
        rmcb = checkbtn(body, "Magic rings too (added-damage pool + 50%+ rarity catch-alls)",
                        self._raregear_ring_magic)
        rmcb.configure(command=self._on_raregear_rings_change)
        rmcb.pack(anchor="w", pady=(2, 0))
        if legacy_all:                      # migrate old single-switch configs once
            self._on_raregear_rings_change(save=False)

    def _on_raregear_beltring_change(self, key):
        v = self._raregear_beltring_vars.get(key)
        if not v:
            return
        sec = {"on": bool(v["on"].get()), "magic": bool(v["magic"].get())}
        if v["entry"] is not None:
            try:
                sec["thr"] = int(float(v["thr"].get()))
            except (ValueError, tk.TclError):
                sec["thr"] = v["def"]
                v["thr"].set(_fmt_threshold(sec["thr"]))
            try:
                v["entry"].configure(state=("normal" if sec["on"] else "disabled"))
            except Exception:
                pass
        self._rare_gear_pro[key] = sec
        self._save_rare_gear()

    def _on_raregear_rings_change(self, save=True):
        archs, any_on = {}, False
        for key, v in self._raregear_ring_vars.items():
            try:
                thr = int(float(v["thr"].get()))
            except (ValueError, tk.TclError):
                thr = v["def"]
                v["thr"].set(_fmt_threshold(thr))
            on = bool(v["on"].get())
            any_on = any_on or on
            archs[key] = {"on": on, "thr": thr}
            try:
                v["entry"].configure(state=("normal" if on else "disabled"))
            except Exception:
                pass
        magic = bool(self._raregear_ring_magic.get())
        self._rare_gear_pro["rings"] = {"on": any_on or magic, "magic": magic,
                                        "archetypes": archs}
        if save:
            self._save_rare_gear()

    def _make_raregear_jewel_card(self, parent):
        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=14, pady=3)
        hdr = tk.Frame(card, bg=BG2)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Jewels", bg=BG2, fg=TEXT, font=FONT, padx=8, pady=6).pack(side="left")
        tk.Label(hdr, text="build archetypes + always-keep mods",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left")
        body = tk.Frame(card, bg=BG2)
        body.pack(fill="x", padx=8, pady=(0, 6))

        jewels = self._rare_gear_pro["jewels"]
        for arch in rgt.JEWEL_ARCHETYPES:
            key, label_txt, def_thr = arch[0], arch[1], arch[2]
            saved = jewels.get(key)
            saved = saved if isinstance(saved, dict) else {}
            on_var  = tk.BooleanVar(value=bool(saved.get("on", False)))
            thr_var = tk.StringVar(value=_fmt_threshold(saved.get("thr", def_thr)))
            row = tk.Frame(body, bg=BG2)
            row.pack(fill="x", pady=1)
            cb = checkbtn(row, f"{label_txt} (both-halves score)", on_var)
            cb.configure(command=lambda k=key: self._on_raregear_jewel_change(k))
            cb.pack(side="left")
            ent = entry(row, thr_var, width=5)
            ent.configure(height=24)
            ent.pack(side="left", padx=(8, 0))
            ent.bind("<FocusOut>", lambda e, k=key: self._on_raregear_jewel_change(k))
            ent.bind("<Return>",   lambda e, k=key: self._on_raregear_jewel_change(k))
            self._raregear_jewel_vars[key] = {"on": on_var, "thr": thr_var, "def": def_thr,
                                              "entry": ent}
            ent.configure(state=("normal" if on_var.get() else "disabled"))
        for key, label_txt, _stat in rgt.JEWEL_SINGLES:
            saved = jewels.get(key)
            saved = saved if isinstance(saved, dict) else {}
            on_var = tk.BooleanVar(value=bool(saved.get("on", False)))
            row = tk.Frame(body, bg=BG2)
            row.pack(fill="x", pady=1)
            cb = checkbtn(row, f"{label_txt} — keep any Magic/Rare jewel with it", on_var)
            cb.configure(command=lambda k=key: self._on_raregear_jewel_change(k))
            cb.pack(side="left")
            self._raregear_jewel_vars[key] = {"on": on_var, "thr": None, "def": None,
                                              "entry": None}

    def _on_raregear_jewel_change(self, key):
        v = self._raregear_jewel_vars.get(key)
        if not v:
            return
        sec = {"on": bool(v["on"].get())}
        if v["thr"] is not None:
            try:
                sec["thr"] = int(float(v["thr"].get()))
            except (ValueError, tk.TclError):
                sec["thr"] = v["def"]
                v["thr"].set(_fmt_threshold(v["def"]))
            try:
                v["entry"].configure(state=("normal" if sec["on"] else "disabled"))
            except Exception:
                pass
        self._rare_gear_pro["jewels"][key] = sec
        self._save_rare_gear()

    # ── Expert rules: hand-written .ipd lines appended verbatim ───────────────

    def _make_raregear_expert_card(self, parent):
        card = tk.Frame(parent, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        card.pack(fill="x", padx=14, pady=(3, 12))
        saved = self._rare_gear_pro.get("expert")
        saved = saved if isinstance(saved, dict) else {}
        hdr = tk.Frame(card, bg=BG2)
        hdr.pack(fill="x", padx=8, pady=(6, 0))
        self._raregear_expert_on = tk.BooleanVar(value=bool(saved.get("on", False)))
        cb = checkbtn(hdr, "Expert rules — include my own rules, exactly as written",
                      self._raregear_expert_on)
        cb.configure(command=self._on_raregear_expert_change)
        cb.pack(side="left")
        btn(hdr, "Import .ipd file…", self._raregear_expert_import).pack(side="right")
        tk.Label(card,
                 text="For hand-tuned rules the generator can't express — graduated threshold "
                      "ladders, ComputedArmour / ComputedEvasion / ComputedEnergyShield rules, "
                      "PhysicalDPS / ElementalDPS weapon rules, per-base Magic jewellery… "
                      "Everything below is appended to the pickit verbatim: no rewriting, no "
                      "thresholds applied. One rule per line, // for comments.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, justify="left", wraplength=1140).pack(
                     anchor="w", padx=10, pady=(2, 4))
        frame, txt = scrolled_text(card, height=10)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        txt.insert("1.0", str(saved.get("text", "")))
        txt.bind("<FocusOut>", lambda e: self._on_raregear_expert_change())
        self._raregear_expert_text = txt

    def _on_raregear_expert_change(self):
        txt = getattr(self, "_raregear_expert_text", None)
        text = txt.get("1.0", "end-1c") if txt is not None else ""
        self._rare_gear_pro["expert"] = {"on": bool(self._raregear_expert_on.get()),
                                         "text": text}
        self._save_rare_gear()

    def _raregear_expert_import(self):
        path = filedialog.askopenfilename(
            title="Import pickit rules",
            filetypes=[("Pickit rules", "*.ipd *.txt"), ("All files", "*.*")])
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        except OSError as e:
            messagebox.showerror("Import failed", str(e))
            return
        txt = self._raregear_expert_text
        existing = txt.get("1.0", "end-1c")
        if existing.strip():
            content = existing.rstrip("\n") + "\n\n" + content
        txt.delete("1.0", "end")
        txt.insert("1.0", content)
        self._raregear_expert_on.set(True)
        self._on_raregear_expert_change()
