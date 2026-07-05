"""Chance Bases tab — pick Normal bases to Orb-of-Chance into target uniques.

Mixed into PickitApp; all methods operate on the shared app instance (self).
"""
import tkinter as tk

from exilebot_pickit import generator as gen
from exilebot_pickit.ui.common import (
    BG, BG2, BG3, BORDER, BORDER_LT, FONT_SM, GOLD, TEXT_DIM,
    _CON, _COFF, _CTXON, _CTXOF, _CONB, _COFB,
    bind_card_hover, btn, switch, Tip,
)


class ChanceBasesTab:
    # ══════════════════════════════════════════════════════════════════════════
    #  CHANCE BASES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_chance_page(self, page):
        """Cards for each chance-orb base — click to enable/disable picking it up."""
        tab_idx = self._building_tab_idx

        # Header card: title + count chip, divider, toolbar — same card language
        # as the Generate/Settings tabs instead of loose bars with rule lines.
        hdr_card = tk.Frame(page, bg=BG2, highlightthickness=1, highlightbackground=BORDER)
        hdr_card.pack(fill="x", padx=14, pady=(10, 8))
        hrow = tk.Frame(hdr_card, bg=BG2)
        hrow.pack(fill="x", padx=14, pady=(9, 9))
        tk.Label(hrow, text="🎲", bg=BG2, fg=GOLD, font=("Segoe UI", 13)).pack(side="left", padx=(0, 9))
        tk.Label(hrow, text="Chance Bases", bg=BG2, fg=GOLD,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(hrow, text="Pick up Normal-rarity bases to Orb of Chance into target uniques.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=(10, 0))
        tk.Label(hrow, textvariable=self._chance_count_var,
                 bg=BG3, fg=GOLD, font=FONT_SM, padx=10, pady=3,
                 highlightthickness=1, highlightbackground=BORDER).pack(side="right")
        tk.Frame(hdr_card, bg=BORDER, height=1).pack(fill="x")

        tbar = tk.Frame(hdr_card, bg=BG2)
        tbar.pack(fill="x", padx=14, pady=8)
        _c_ea = btn(tbar, "Enable All",  lambda: self._chance_set_all(True))
        _c_ea.pack(side="left", padx=(0, 6))
        _c_da = btn(tbar, "Disable All", lambda: self._chance_set_all(False))
        _c_da.pack(side="left")
        tk.Label(tbar, text="Toggle a card to pick that base up (or leave it) — each shows the unique it chances into.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM).pack(side="left", padx=12)
        Tip(_c_ea, "Pick up every chance base in the list.")
        Tip(_c_da, "Pick up none of them.")

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

        self._chance_canvas = canvas
        self._chance_frame  = inner
        self._tab_canvases[tab_idx] = canvas

        self._populate_chance_grid()

    def _populate_chance_grid(self):
        if self._chance_frame is None:
            return
        for w in self._chance_frame.winfo_children():
            w.destroy()
        self._chance_cards = []
        states = self._item_states.get("_chance", {})
        NCOLS  = 2

        # Group the flat CHANCE_BASES list by category, preserving order.
        groups = []
        for cat, base_type, target in gen.CHANCE_BASES:
            if not groups or groups[-1][0] != cat:
                groups.append((cat, []))
            groups[-1][1].append((base_type, target))

        first = True
        for cat, items in groups:
            hdr_f = tk.Frame(self._chance_frame, bg=BG)
            hdr_f.pack(fill="x", padx=14, pady=(4 if first else 14, 4))
            first = False
            tk.Label(hdr_f, text=cat.upper(), bg=BG, fg=GOLD,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Frame(hdr_f, bg=BORDER, height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=5)
            for w in [hdr_f] + list(hdr_f.winfo_children()):
                w.bind("<MouseWheel>",
                       lambda e, c=self._chance_canvas: (c.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])

            grid_f = tk.Frame(self._chance_frame, bg=BG)
            grid_f.pack(fill="x", padx=12)
            for c_ in range(NCOLS):
                grid_f.columnconfigure(c_, weight=1, uniform="ch")
            grid_f.bind("<MouseWheel>",
                        lambda e, c=self._chance_canvas: (c.yview_scroll(-3 if e.delta > 0 else 3, "units"), "break")[1])

            for i, (base_type, target) in enumerate(items):
                enabled = states.get(base_type, {}).get("enabled", True) if base_type in states else True
                card = self._make_chance_card(base_type, target, enabled, grid_f)
                card.grid(row=i // NCOLS, column=i % NCOLS, sticky="ew", padx=3, pady=3)
                self._chance_cards.append(card)

        self._update_chance_count()

    def _make_chance_card(self, base_type, target, enabled, parent):
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB

        frame = tk.Frame(parent, bg=bg, cursor="hand2",
                         highlightthickness=1, highlightbackground=bdr)
        frame._base_type = base_type
        frame._target    = target
        frame._enabled   = enabled
        frame._evar      = tk.BooleanVar(value=enabled)

        name_lbl = tk.Label(frame, text=base_type, bg=bg, fg=fg,
                            font=("Segoe UI", 10, "bold"), anchor="w", padx=12, pady=9)
        name_lbl.pack(side="left", fill="x", expand=True)
        frame._name_lbl = name_lbl

        # toggle switch (far right) — reflects & drives the enabled state
        sw = switch(frame, frame._evar, bg_color=bg, switch_width=36, switch_height=18,
                    command=lambda f=frame: self._set_chance_enabled(f, f._evar.get()))
        sw.pack(side="right", padx=(6, 10))
        frame._switch = sw

        arrow_lbl = tk.Label(frame, text=f"→  {target}", bg=bg,
                             fg=TEXT_DIM if enabled else _CTXOF,
                             font=("Segoe UI", 9), padx=10)
        arrow_lbl.pack(side="right")
        frame._arrow_lbl = arrow_lbl

        def _click(e=None, f=frame):
            f._evar.set(not f._evar.get())
            self._set_chance_enabled(f, f._evar.get())
        def _scroll(e, c=self._chance_canvas):
            c.yview_scroll(-3 if e.delta > 0 else 3, "units")
            return "break"

        clickable = (frame, name_lbl, arrow_lbl)
        for w in clickable:
            w.bind("<Button-1>", _click)
        for w in clickable + (sw,):
            w.bind("<MouseWheel>", _scroll)
            w.bind("<Button-4>",   lambda e, c=self._chance_canvas: (c.yview_scroll(-3, "units"), "break")[1])
            w.bind("<Button-5>",   lambda e, c=self._chance_canvas: (c.yview_scroll( 3, "units"), "break")[1])

        bind_card_hover(frame, clickable, BORDER_LT,
                        lambda f=frame: _CONB if f._enabled else _COFB)
        return frame

    def _set_chance_enabled(self, frame, enabled):
        """Apply *enabled* to one chance-base card: persist state + restyle."""
        base_type = frame._base_type
        if "_chance" not in self._item_states:
            self._item_states["_chance"] = {}
        if enabled:
            self._item_states["_chance"].pop(base_type, None)
        else:
            self._item_states["_chance"][base_type] = {"enabled": False}

        frame._enabled = enabled
        if frame._evar.get() != enabled:
            frame._evar.set(enabled)
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._arrow_lbl.config(bg=bg, fg=TEXT_DIM if enabled else _CTXOF)
        try:
            frame._switch.configure(bg_color=bg)
        except Exception:
            pass

        self._update_chance_count()
        self._save_states_soon()

    def _chance_set_all(self, enabled_val):
        if "_chance" not in self._item_states:
            self._item_states["_chance"] = {}
        if enabled_val:
            self._item_states["_chance"].clear()
        else:
            for _, base_type, _ in gen.CHANCE_BASES:
                self._item_states["_chance"][base_type] = {"enabled": False}
        self._populate_chance_grid()
        self._save_states_soon()

    def _update_chance_count(self):
        enabled = sum(1 for c in self._chance_cards if c._enabled)
        total   = len(self._chance_cards)
        self._chance_count_var.set(f"{enabled} / {total} enabled")
