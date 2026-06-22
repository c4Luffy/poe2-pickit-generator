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
                 text="Pick Normal-rarity bases at item level 82 — blank bases worth crafting on.",
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

        for cat, names in gen.craft_base_categories():
            hdr_f = tk.Frame(self._craftbase_frame, bg=BG)
            hdr_f.pack(fill="x", padx=14, pady=(14 if self._craftbase_cards else 6, 2))
            tk.Label(hdr_f, text=cat.upper(), bg=BG, fg=GOLD,
                     font=("Segoe UI", 8, "bold")).pack(side="left")
            tk.Frame(hdr_f, bg=BORDER, height=1).pack(
                side="left", fill="x", expand=True, padx=(8, 0), pady=5)
            for w in [hdr_f] + list(hdr_f.winfo_children()):
                w.bind("<MouseWheel>",
                       lambda e, c=self._craftbase_canvas: c.yview_scroll(-3 if e.delta > 0 else 3, "units"))

            for name in names:
                enabled = states.get(name, {}).get("enabled", True) if name in states else True
                card = self._make_craftbase_card(name, enabled)
                card.pack(fill="x", padx=12, pady=2)
                self._craftbase_cards.append(card)

        self._update_craftbase_count()

    def _make_craftbase_card(self, name, enabled):
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        dot = ""    if enabled else "✗"

        frame = tk.Frame(self._craftbase_frame, bg=bg, cursor="hand2",
                         highlightthickness=1, highlightbackground=bdr)
        frame._name    = name
        frame._enabled = enabled

        name_lbl = tk.Label(frame, text=name, bg=bg, fg=fg,
                            font=("Segoe UI", 10, "bold"), anchor="w", padx=12, pady=7)
        name_lbl.pack(side="left", fill="x", expand=True)
        frame._name_lbl = name_lbl

        tag_lbl = tk.Label(frame, text='Normal · ilvl 82+', bg=bg,
                           fg=TEXT_DIM if enabled else _CTXOF,
                           font=("Segoe UI", 9), padx=10)
        tag_lbl.pack(side="right")
        frame._tag_lbl = tag_lbl

        dot_lbl = tk.Label(frame, text=dot, bg=bg,
                           fg=_CTXOF, font=("Segoe UI", 11), padx=4)
        dot_lbl.pack(side="right")
        frame._dot_lbl = dot_lbl

        def _click(e=None, f=frame):
            self._toggle_craftbase_card(f)
        def _scroll(e, c=self._craftbase_canvas):
            c.yview_scroll(-3 if e.delta > 0 else 3, "units")

        for w in (frame, name_lbl, tag_lbl, dot_lbl):
            w.bind("<Button-1>",   _click)
            w.bind("<MouseWheel>", _scroll)
            w.bind("<Button-4>",   lambda e, c=self._craftbase_canvas: c.yview_scroll(-3, "units"))
            w.bind("<Button-5>",   lambda e, c=self._craftbase_canvas: c.yview_scroll( 3, "units"))

        return frame

    def _toggle_craftbase_card(self, frame):
        name = frame._name
        if "_craftbase" not in self._item_states:
            self._item_states["_craftbase"] = {}
        currently_disabled = not self._item_states["_craftbase"].get(name, {}).get("enabled", True)
        if currently_disabled:
            self._item_states["_craftbase"].pop(name, None)
            enabled = True
        else:
            self._item_states["_craftbase"][name] = {"enabled": False}
            enabled = False

        frame._enabled = enabled
        bg  = _CON  if enabled else _COFF
        fg  = _CTXON if enabled else _CTXOF
        bdr = _CONB if enabled else _COFB
        frame.config(bg=bg, highlightbackground=bdr)
        frame._name_lbl.config(bg=bg, fg=fg)
        frame._tag_lbl.config(bg=bg, fg=TEXT_DIM if enabled else _CTXOF)
        frame._dot_lbl.config(bg=bg, text="" if enabled else "✗")

        self._update_craftbase_count()
        self.after(0, self._save_states_now)

    def _craftbase_set_all(self, enabled_val):
        if "_craftbase" not in self._item_states:
            self._item_states["_craftbase"] = {}
        if enabled_val:
            self._item_states["_craftbase"].clear()
        else:
            for _cat, names in gen.craft_base_categories():
                for name in names:
                    self._item_states["_craftbase"][name] = {"enabled": False}
        self._populate_craftbase_grid()
        self.after(0, self._save_states_now)

    def _update_craftbase_count(self):
        enabled = sum(1 for c in self._craftbase_cards if c._enabled)
        total   = len(self._craftbase_cards)
        self._craftbase_count_var.set(f"{enabled} / {total} enabled")
