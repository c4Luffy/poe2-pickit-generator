"""Chance Bases tab — pick Normal bases to Orb-of-Chance into target uniques.

Mixed into PickitApp; all methods operate on the shared app instance (self).
"""
import tkinter as tk

import poe2_pickit_generator as gen
from ui_common import *


class ChanceBasesTab:
    # ══════════════════════════════════════════════════════════════════════════
    #  CHANCE BASES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_chance_page(self, page):
        """Cards for each chance-orb base — click to enable/disable picking it up."""
        tab_idx = self._building_tab_idx

        hdr_bar = tk.Frame(page, bg=BG2)
        hdr_bar.pack(fill="x")
        tk.Label(hdr_bar, text="Chance Bases",
                 bg=BG2, fg=GOLD, font=("Segoe UI", 12, "bold"),
                 padx=16, pady=8).pack(side="left")
        tk.Label(hdr_bar,
                 text="Pick up Normal-rarity bases to Orb of Chance into target uniques.",
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=4).pack(side="left")
        tk.Label(hdr_bar, textvariable=self._chance_count_var,
                 bg=BG2, fg=TEXT_DIM, font=FONT_SM, padx=8).pack(side="right", padx=8)
        sep(page).pack(fill="x")

        tbar = tk.Frame(page, bg=BG)
        tbar.pack(fill="x", padx=10, pady=(6, 4))
        btn(tbar, "Enable All",  lambda: self._chance_set_all(True)).pack(side="left", padx=(0, 4))
        btn(tbar, "Disable All", lambda: self._chance_set_all(False)).pack(side="left")
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
                       lambda e, c=self._chance_canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))

            grid_f = tk.Frame(self._chance_frame, bg=BG)
            grid_f.pack(fill="x", padx=12)
            for c_ in range(NCOLS):
                grid_f.columnconfigure(c_, weight=1, uniform="ch")
            grid_f.bind("<MouseWheel>",
                        lambda e, c=self._chance_canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))

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
        dot = ""    if enabled else "✗"

        frame = tk.Frame(parent, bg=bg, cursor="hand2",
                         highlightthickness=1, highlightbackground=bdr)
        frame._base_type = base_type
        frame._target    = target
        frame._enabled   = enabled

        name_lbl = tk.Label(frame, text=base_type, bg=bg, fg=fg,
                            font=("Segoe UI", 10, "bold"), anchor="w", padx=12, pady=7)
        name_lbl.pack(side="left", fill="x", expand=True)
        frame._name_lbl = name_lbl

        arrow_lbl = tk.Label(frame, text=f"→  {target}", bg=bg,
                             fg=TEXT_DIM if enabled else _CTXOF,
                             font=("Segoe UI", 9), padx=10)
        arrow_lbl.pack(side="right")
        frame._arrow_lbl = arrow_lbl

        dot_lbl = tk.Label(frame, text=dot, bg=bg,
                           fg=_CTXOF, font=("Segoe UI", 11), padx=4)
        dot_lbl.pack(side="right")
        frame._dot_lbl = dot_lbl

        def _click(e=None, f=frame):
            self._toggle_chance_card(f)
        def _scroll(e, c=self._chance_canvas):
            c.yview_scroll(-3 if e.delta > 0 else 3, "units")

        for w in (frame, name_lbl, arrow_lbl, dot_lbl):
            w.bind("<Button-1>",   _click)
            w.bind("<MouseWheel>", _scroll)
            w.bind("<Button-4>",   lambda e, c=self._chance_canvas: c.yview_scroll(-3, "units"))
            w.bind("<Button-5>",   lambda e, c=self._chance_canvas: c.yview_scroll( 3, "units"))

        return frame

    def _toggle_chance_card(self, frame):
        base_type = frame._base_type
        if "_chance" not in self._item_states:
            self._item_states["_chance"] = {}
        currently_disabled = not self._item_states["_chance"].get(base_type, {}).get("enabled", True)
        if currently_disabled:
            self._item_states["_chance"].pop(base_type, None)
            enabled = True
        else:
            self._item_states["_chance"][base_type] = {"enabled": False}
            enabled = False

        frame._enabled = enabled
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._arrow_lbl.config(bg=bg, fg=TEXT_DIM if enabled else _CTXOF)
        frame._dot_lbl.config(bg=bg, text="" if enabled else "✗")

        self._update_chance_count()
        self.after(0, self._save_states_now)

    def _chance_set_all(self, enabled_val):
        if "_chance" not in self._item_states:
            self._item_states["_chance"] = {}
        if enabled_val:
            self._item_states["_chance"].clear()
        else:
            for _, base_type, _ in gen.CHANCE_BASES:
                self._item_states["_chance"][base_type] = {"enabled": False}
        self._populate_chance_grid()
        self.after(0, self._save_states_now)

    def _update_chance_count(self):
        enabled = sum(1 for c in self._chance_cards if c._enabled)
        total   = len(self._chance_cards)
        self._chance_count_var.set(f"{enabled} / {total} enabled")
