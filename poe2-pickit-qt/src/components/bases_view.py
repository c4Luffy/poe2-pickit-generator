"""Chance / Craft bases view — click-to-exclude grid over static engine data.

One reusable view, instantiated twice (``kind="chance"`` and ``kind="craft"``).
Unlike the Items grid this needs no network: the bases are curated constants in
the engine. Toggling a card persists to ``base_state``, which the GenerateWorker
reads so excluded bases are dropped from the generated chance/craft base rules.

* **chance** — ``gen.CHANCE_BASES`` → cards labelled by base type, meta = the
  target unique(s) an Orb of Chance aims at.
* **craft** — ``gen.craft_base_categories()`` → cards labelled by base name, meta
  = the defence type (STR / DEX / INT / hybrids; blank for weapons).
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPushButton, QScrollArea, QVBoxLayout,
                               QWidget)

from src.core.base_state import base_state
from src.core.engine import gen
from src.ui.widgets.base_card import BaseCard

_NCOLS = 2

_META = {
    "chance": ("Chance Bases",
               "Normal bases worth using an Orb of Chance on to target specific uniques."),
    "craft":  ("Craft Bases",
               "Normal bases at item level {ilvl}+ — blank bases worth crafting on."),
}


class BasesView(QWidget):
    def __init__(self, kind: str, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self._cards: list[BaseCard] = []
        self._groups_ui: list[tuple[QLabel, list[BaseCard]]] = []
        self._build()
        self._populate()

    # ---- data ----
    def _groups(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """Return ``[(category, [(name, meta), ...]), ...]`` for this kind."""
        if self.kind == "chance":
            groups: dict[str, list[tuple[str, str]]] = {}
            for cat, base_type, target in gen.CHANCE_BASES:
                groups.setdefault(cat, []).append((base_type, target))
            return list(groups.items())
        return [
            (cat, [(name, gen.craft_base_defence(name)) for name in names])
            for cat, names in gen.craft_base_categories()
        ]

    # ---- layout ----
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        head_title, head_sub = _META[self.kind]
        title = QLabel(head_title)
        title.setObjectName("Title")
        sub = QLabel(head_sub.format(ilvl=gen.CRAFT_BASE_MIN_ILVL))
        sub.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(sub)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search bases…")
        self.search.textChanged.connect(self._apply_search)
        enable_btn = QPushButton("Enable all")
        enable_btn.clicked.connect(lambda: self._set_all(True))
        disable_btn = QPushButton("Disable all")
        disable_btn.clicked.connect(lambda: self._set_all(False))
        self.count = QLabel("")
        self.count.setObjectName("Subtitle")
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(enable_btn)
        toolbar.addWidget(disable_btn)
        toolbar.addWidget(self.count)
        root.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._host = QWidget()
        self._vbox = QVBoxLayout(self._host)
        self._vbox.setContentsMargins(0, 0, 0, 0)
        self._vbox.setSpacing(10)
        self._vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll.setWidget(self._host)
        root.addWidget(self.scroll, 1)

    # ---- grid ----
    def _populate(self) -> None:
        for cat, entries in self._groups():
            header = QLabel(cat)
            header.setObjectName("Metric")
            self._vbox.addWidget(header)

            grid_host = QWidget()
            grid = QGridLayout(grid_host)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.setSpacing(8)
            for c in range(_NCOLS):
                grid.setColumnStretch(c, 1)

            cards: list[BaseCard] = []
            for i, (name, meta) in enumerate(entries):
                card = BaseCard(self.kind, name, meta,
                                base_state.is_enabled(self.kind, name))
                card.toggled.connect(self._on_toggle)
                grid.addWidget(card, i // _NCOLS, i % _NCOLS)
                cards.append(card)
                self._cards.append(card)
            self._vbox.addWidget(grid_host)
            self._groups_ui.append((header, cards))

        self._update_count()

    def _on_toggle(self, kind: str, name: str, enabled: bool) -> None:
        base_state.set_enabled(kind, name, enabled)
        self._update_count()

    def _set_all(self, enabled: bool) -> None:
        base_state.set_all(self.kind, [c.name for c in self._cards], enabled)
        for card in self._cards:
            card.set_enabled(enabled)
        self._update_count()

    def _apply_search(self, _text: str = "") -> None:
        q = self.search.text().strip().lower()
        for header, cards in self._groups_ui:
            any_visible = False
            for card in cards:
                shown = q in card.name.lower() or q in card.meta.lower()
                card.setVisible(shown)
                any_visible = any_visible or shown
            header.setVisible(any_visible)

    def _update_count(self) -> None:
        total = len(self._cards)
        enabled = sum(1 for c in self._cards if c.enabled)
        self.count.setText(f"{enabled} / {total} enabled")
