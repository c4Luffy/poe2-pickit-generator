"""Craft Bases tab — pick the best blank (Normal) bases at item level 82.

Mixed into PickitApp; all methods operate on the shared app instance (self).
"""
import tkinter as tk

from exilebot_pickit import generator as gen
from exilebot_pickit.ui.common import (
    BG, BG2, BG3, BORDER, BORDER_LT, FONT_SM, GOLD, TEXT_DIM,
    _CON, _COFF, _CTXON, _CTXOF, _CONB, _COFB,
    bind_card_hover, btn, entry, switch, Tip,
)


class CraftBasesTab:
    # ══════════════════════════════════════════════════════════════════════════
    #  CRAFT BASES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_craftbase_page(self, page):
        """Cards for each craft base — click to enable/disable picking it up as a
        Normal (white) base at item level 82, ideal for crafting."""
        tab_idx = self._building_tab_idx

        # Header card: title + count chip, divider, toolbar — same card language
        # as the Generate/Settings tabs instead of loose bars with rule lines.
        hdr_card = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        hdr_card.pack(fill="x", padx=14, pady=(10, 8))
        hrow = tk.Frame(hdr_card, bg=BG2)
        hrow.pack(fill="x", padx=14, pady=(9, 9))
        tk.Label(hrow, text="🧱", bg=BG2, fg=GOLD, font=("Segoe UI", 13)).pack(side="left", padx=(0, 9))
        tk.Label(hrow, text="Craft Bases", bg=BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(hrow, text="Normal blank bases worth crafting on — set the item level per base.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(10, 0))
        tk.Label(hrow, textvariable=self._craftbase_count_var,
                 bg=BG3, fg=GOLD, font=FONT_SM, padx=10, pady=3,
                 highlightthickness=1, highlightbackground=BORDER).pack(side="right")
        tk.Frame(hdr_card, bg=BORDER, height=1).pack(fill="x")

        tbar = tk.Frame(hdr_card, bg=BG2)
        tbar.pack(fill="x", padx=14, pady=8)
        _cb_ea = btn(tbar, "Enable All",  lambda: self._craftbase_set_all(True))
        _cb_ea.pack(side="left", padx=(0, 6))
        _cb_da = btn(tbar, "Disable All", lambda: self._craftbase_set_all(False))
        _cb_da.pack(side="left")
        tk.Label(tbar, text="Toggle off the ones you don't want — keep just your top picks per slot. "
                            "The ilvl box on each card is exactly what the bot requires.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=12)
        Tip(_cb_ea, "Pick up every craft base in the list.")
        Tip(_cb_da, "Pick up none of them.")

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
            w.bind("<MouseWheel>", lambda e, c=canvas: (c.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])
            w.bind("<Button-4>",   lambda e, c=canvas: (c.yview_scroll(-3, "units"), "break")[1])
            w.bind("<Button-5>",   lambda e, c=canvas: (c.yview_scroll( 3, "units"), "break")[1])

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
                       lambda e, c=self._craftbase_canvas: (c.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])

            grid_f = tk.Frame(self._craftbase_frame, bg=BG)
            grid_f.pack(fill="x", padx=12)
            for c_ in range(NCOLS):
                grid_f.columnconfigure(c_, weight=1, uniform="cb")
            grid_f.bind("<MouseWheel>",
                        lambda e, c=self._craftbase_canvas: (c.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])

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
        self._save_states_soon()

    def _make_craftbase_card(self, name, enabled, parent):
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB

        frame = tk.Frame(parent, bg=bg, highlightthickness=1, highlightbackground=bdr,
                         cursor="hand2")
        frame._name    = name
        frame._enabled = enabled
        frame._evar    = tk.BooleanVar(value=enabled)

        name_lbl = tk.Label(frame, text=name, bg=bg, fg=fg, cursor="hand2",
                            font=("Segoe UI", 10, "bold"), anchor="w", padx=12, pady=9)
        name_lbl.pack(side="left", fill="x", expand=True)
        frame._name_lbl = name_lbl

        # toggle switch (far right) — reflects & drives the enabled state
        sw = switch(frame, frame._evar, bg_color=bg, switch_width=36, switch_height=18,
                    command=lambda f=frame: self._set_craftbase_enabled(f, f._evar.get()))
        sw.pack(side="right", padx=(6, 10))
        frame._switch = sw

        # per-base item-level box — clean typeable field (no arrows). Type any
        # level 1–100; validated + saved on Enter or when focus leaves the box.
        ivar = tk.StringVar(value=str(self._craftbase_ilvl_for(name)))
        frame._ilvl_var = ivar
        ilvl_box = entry(frame, ivar, width=6, justify="center", height=26)
        ilvl_box.pack(side="right", padx=(0, 6), pady=4)
        ilvl_box.bind("<FocusOut>", lambda e, n=name, v=ivar: self._on_craftbase_ilvl(n, v))
        ilvl_box.bind("<Return>",   lambda e, n=name, v=ivar: self._on_craftbase_ilvl(n, v))
        frame._ilvl_spin = ilvl_box
        ilvl_lbl = tk.Label(frame, text="ilvl", bg=bg, fg=TEXT_DIM,
                            font=("Segoe UI", 9))
        ilvl_lbl.pack(side="right", padx=(8, 2))
        frame._ilvl_lbl = ilvl_lbl

        # defence-type chip (armour only; accessories/weapons blank)
        _dt = gen.craft_base_defence(name)
        dt_lbl = None
        if _dt:
            dt_lbl = tk.Label(frame, text=_dt, bg=BG3 if enabled else bg,
                              fg=GOLD if enabled else _CTXOF,
                              font=("Segoe UI", 8, "bold"), padx=7, pady=2)
            dt_lbl.pack(side="right", padx=(0, 8))
        frame._dt_lbl = dt_lbl

        def _click(e=None, f=frame):
            f._evar.set(not f._evar.get())
            self._set_craftbase_enabled(f, f._evar.get())
        def _scroll(e, c=self._craftbase_canvas):
            c.yview_scroll(-3 if e.delta > 0 else 3, "units")
            return "break"

        clickable = [frame, name_lbl, ilvl_lbl] + ([dt_lbl] if dt_lbl else [])
        for w in clickable:
            w.bind("<Button-1>", _click)
        for w in clickable + [ilvl_box, sw]:
            w.bind("<MouseWheel>", _scroll)
            w.bind("<Button-4>",   lambda e, c=self._craftbase_canvas: (c.yview_scroll(-3, "units"), "break")[1])
            w.bind("<Button-5>",   lambda e, c=self._craftbase_canvas: (c.yview_scroll( 3, "units"), "break")[1])

        bind_card_hover(frame, clickable, BORDER_LT,
                        lambda f=frame: _CONB if f._enabled else _COFB)
        return frame

    def _set_craftbase_enabled(self, frame, enabled):
        """Apply *enabled* to one craft-base card: persist state + restyle."""
        name   = frame._name
        states = self._item_states.setdefault("_craftbase", {})
        entry  = states.setdefault(name, {})
        if enabled:
            entry.pop("enabled", None)      # enabled is the default; keep any ilvl
            if not entry:
                states.pop(name, None)
        else:
            entry["enabled"] = False

        frame._enabled = enabled
        if frame._evar.get() != enabled:
            frame._evar.set(enabled)
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._ilvl_lbl.config(bg=bg)
        if frame._dt_lbl is not None:
            frame._dt_lbl.config(bg=BG3 if enabled else bg, fg=GOLD if enabled else _CTXOF)
        try:
            frame._switch.configure(bg_color=bg)
        except Exception:
            pass

        self._update_craftbase_count()
        self._save_states_soon()

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
        self._save_states_soon()

    def _update_craftbase_count(self):
        enabled = sum(1 for c in self._craftbase_cards if c._enabled)
        total   = len(self._craftbase_cards)
        self._craftbase_count_var.set(f"{enabled} / {total} enabled")
