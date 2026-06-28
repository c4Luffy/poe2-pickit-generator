"""Craft Bases tab — pick the best blank (Normal) bases at item level 82.

Mixed into PickitApp; all methods operate on the shared app instance (self).
"""
import tkinter as tk

import poe2_pickit_generator as gen
from ui_common import *


class CraftBasesTab:
    # ══════════════════════════════════════════════════════════════════════════
    #  CRAFT BASES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_craftbase_page(self, page):
        """Cards for each craft base — click to enable/disable picking it up as a
        Normal (white) base at item level 82, ideal for crafting."""
        tab_idx = self._building_tab_idx

        hdr_bar = tk.Frame(page, bg=BG2)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, text="Craft Bases",
                 bg=BG2, fg=GOLD, font=("Segoe UI", 12, "bold"),
                 padx=16, pady=8).pack(side="left")
        tk.Label(hdr_bar,
                 text="Normal blank bases worth crafting on — set the item level per base.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=4).pack(side="left")
        tk.Label(hdr_bar, textvariable=self._craftbase_count_var,
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="right", padx=8)
        sep(page).pack(fill="x")

        tbar = tk.Frame(page, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 4))
        btn(tbar, "Enable All",  lambda: self._craftbase_set_all(True)).pack(side="left", padx=(0, 4))
        btn(tbar, "Disable All", lambda: self._craftbase_set_all(False)).pack(side="left")
        tk.Label(tbar, text="Toggle off the ones you don't want — keep just your top picks per slot.",
                 bg=BG, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=10)
        sep(page).pack(fill="x")

        canvas = tk.Canvas(page, bg=BG, highlightthickness=0)
        vsb    = tk.Scrollbar(page, orient="vertical", command=canvas.yview,
                              bg=BG3, troughcolor=BG, relief="flat", bd=0, width=10)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(fill="both", expand=True, padx=0, pady=0)

        inner = tk.Frame(canvas, bg=BG)
        win   = canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        for w in (canvas, inner):
            w.bind("<MouseWheel>", lambda e, c=canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))
            w.bind("<Button-4>",   lambda e, c=canvas: c.yview_scroll(-3, "units"))
            w.bind("<Button-5>",   lambda e, c=canvas: c.yview_scroll( 3, "units"))

        self._craftbase_canvas = canvas
        self._craftbase_frame  = inner
        self._tab_canvases[tab_idx] = canvas

        self._populate_craftbase_grid()

    def _populate_craftbase_grid(self):
        if self._craftbase_frame is None:
            return
        for w in self._craftbase_frame.winfo_children():
            w.destroy()
        self._craftbase_cards = []
        states = self._item_states.get("_craftbase", {})
        NCOLS  = 2

        first = True
        for cat, names in gen.craft_base_categories():
            hdr_f = tk.Frame(self._craftbase_frame, bg=BG)
            hdr_f.pack(fill="x", padx=14, pady=(4 if first else 14, 4))
            first = False
            tk.Label(hdr_f, text=cat.upper(), bg=BG, fg=GOLD,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Frame(hdr_f, bg=BORDER, height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=5)
            for w in [hdr_f] + list(hdr_f.winfo_children()):
                w.bind("<MouseWheel>",
                       lambda e, c=self._craftbase_canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))

            grid_f = tk.Frame(self._craftbase_frame, bg=BG)
            grid_f.pack(fill="x", padx=12)
            for c_ in range(NCOLS):
                grid_f.columnconfigure(c_, weight=1, uniform="cb")
            grid_f.bind("<MouseWheel>",
                        lambda e, c=self._craftbase_canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))

            for i, name in enumerate(names):
                enabled = states.get(name, {}).get("enabled", True) if name in states else True
                card = self._make_craftbase_card(name, enabled, grid_f)
                card.grid(row=i // NCOLS, column=i % NCOLS, sticky="ew", padx=3, pady=3)
                self._craftbase_cards.append(card)

        self._update_craftbase_count()

    def _craftbase_ilvl_for(self, name):
        """Item level to show for a base: the user's saved override, else the
        built-in default (75 for accessories, otherwise the global min level)."""
        st = self._item_states.get("_craftbase", {}).get(name, {})
        if "ilvl" in st:
            return st["ilvl"]
        try:
            gmin = int(self.base_min_level_var.get())
        except (tk.TclError, ValueError):
            gmin = gen.CRAFT_BASE_MIN_ILVL
        return gen.craft_base_default_ilvl(name, gmin)

    def _on_craftbase_ilvl(self, name, var):
        """Validate + persist a per-base item level typed into a card's box."""
        try:
            val = max(1, min(100, int(float(var.get()))))
        except (ValueError, tk.TclError):
            val = self._craftbase_ilvl_for(name)
        var.set(str(val))
        states = self._item_states.setdefault("_craftbase", {})
        states.setdefault(name, {})["ilvl"] = val
        self.after(0, self._save_states_now)

    def _make_craftbase_card(self, name, enabled, parent):
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        dot = ""    if enabled else "✗"

        frame = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=bdr)
        frame._name    = name
        frame._enabled = enabled

        name_lbl = tk.Label(frame, text=name, bg=bg, fg=fg, cursor="hand2",
                            font=("Segoe UI", 10, "bold"), anchor="w", padx=12, pady=7)
        name_lbl.pack(side="left", fill="x", expand=True)
        frame._name_lbl = name_lbl

        # exclusion mark (far right)
        dot_lbl = tk.Label(frame, text=dot, bg=bg, fg=_CTXOF,
                           font=("Segoe UI", 11), padx=4, cursor="hand2")
        dot_lbl.pack(side="right")
        frame._dot_lbl = dot_lbl

        # per-base item-level box — type any level 1–100, saved per base
        ivar = tk.StringVar(value=str(self._craftbase_ilvl_for(name)))
        frame._ilvl_var = ivar
        spin = tk.Spinbox(frame, from_=1, to=100, width=4, textvariable=ivar,
                          justify="center", font=("Segoe UI", 10),
                          bg=BG3, fg=TEXT, buttonbackground=BG3, insertbackground=TEXT,
                          relief="flat", highlightthickness=1, highlightbackground=BORDER,
                          command=lambda n=name, v=ivar: self._on_craftbase_ilvl(n, v))
        spin.pack(side="right", padx=(0, 6), pady=4)
        spin.bind("<FocusOut>", lambda e, n=name, v=ivar: self._on_craftbase_ilvl(n, v))
        spin.bind("<Return>",   lambda e, n=name, v=ivar: self._on_craftbase_ilvl(n, v))
        frame._ilvl_spin = spin
        ilvl_lbl = tk.Label(frame, text="ilvl", bg=bg, fg=TEXT_DIM,
                            font=("Segoe UI", 9))
        ilvl_lbl.pack(side="right", padx=(8, 2))
        frame._ilvl_lbl = ilvl_lbl

        # defence-type tag (armour only; accessories/weapons blank)
        _dt = gen.craft_base_defence(name)
        dt_lbl = None
        if _dt:
            dt_lbl = tk.Label(frame, text=_dt, bg=bg,
                              fg=TEXT_DIM if enabled else _CTXOF,
                              font=("Segoe UI", 9), padx=6)
            dt_lbl.pack(side="right")
        frame._dt_lbl = dt_lbl

        def _click(e=None, f=frame):
            self._toggle_craftbase_card(f)
        def _scroll(e, c=self._craftbase_canvas):
            c.yview_scroll(-3 if e.delta > 0 else 3, "units")

        clickable = [frame, name_lbl, dot_lbl, ilvl_lbl] + ([dt_lbl] if dt_lbl else [])
        for w in clickable:
            w.bind("<Button-1>", _click)
        for w in clickable + [spin]:
            w.bind("<MouseWheel>", _scroll)
            w.bind("<Button-4>",   lambda e, c=self._craftbase_canvas: c.yview_scroll(-3, "units"))
            w.bind("<Button-5>",   lambda e, c=self._craftbase_canvas: c.yview_scroll( 3, "units"))

        return frame

    def _toggle_craftbase_card(self, frame):
        name   = frame._name
        states = self._item_states.setdefault("_craftbase", {})
        entry  = states.setdefault(name, {})
        enabled = not entry.get("enabled", True)
        if enabled:
            entry.pop("enabled", None)      # enabled is the default; keep any ilvl
            if not entry:
                states.pop(name, None)
        else:
            entry["enabled"] = False

        frame._enabled = enabled
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._ilvl_lbl.config(bg=bg)
        if frame._dt_lbl is not None:
            frame._dt_lbl.config(bg=bg, fg=TEXT_DIM if enabled else _CTXOF)
        frame._dot_lbl.config(bg=bg, text="" if enabled else "✗")

        self._update_craftbase_count()
        self.after(0, self._save_states_now)

    def _craftbase_set_all(self, enabled_val):
        states = self._item_states.setdefault("_craftbase", {})
        if enabled_val:
            # clear disabled flags but keep any per-base ilvl overrides
            for nm in list(states):
                states[nm].pop("enabled", None)
                if not states[nm]:
                    states.pop(nm, None)
        else:
            for _cat, names in gen.craft_base_categories():
                for name in names:
                    states.setdefault(name, {})["enabled"] = False
        self._populate_craftbase_grid()
        self.after(0, self._save_states_now)

    def _update_craftbase_count(self):
        enabled = sum(1 for c in self._craftbase_cards if c._enabled)
        total   = len(self._craftbase_cards)
        self._craftbase_count_var.set(f"{enabled} / {total} enabled")
