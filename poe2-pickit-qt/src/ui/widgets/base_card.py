"""A clickable base-type card for the Chance / Craft tabs.

Sibling of ``ItemCard``: same click-to-exclude mechanics and the same QSS object
names (``#ItemCard`` / ``#ItemName`` / ``#ItemPrice`` / ``#Dot``), so it inherits
the existing styling. The difference is the payload — a base shows a *meta* line
(the target unique for chance, the defence type for craft) instead of a price.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout


class BaseCard(QFrame):
    toggled = Signal(str, str, bool)  # (kind, name, enabled)

    def __init__(self, kind: str, name: str, meta: str, enabled: bool,
                 parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.name = name
        self.meta = meta
        self._enabled = enabled
        self.setObjectName("ItemCard")
        self.setProperty("enabled", enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(8)
        self._name = QLabel(name)
        self._name.setObjectName("ItemName")
        self._dot = QLabel("" if enabled else "✗")
        self._dot.setObjectName("Dot")
        self._dot.setFixedWidth(14)
        top.addWidget(self._name, 1)
        top.addWidget(self._dot)
        lay.addLayout(top)

        if meta:
            meta_lbl = QLabel(meta)
            meta_lbl.setObjectName("ItemPrice")
            meta_lbl.setWordWrap(True)
            lay.addWidget(meta_lbl)

    def mousePressEvent(self, event) -> None:
        self.set_enabled(not self._enabled)
        self.toggled.emit(self.kind, self.name, self._enabled)

    def set_enabled(self, enabled: bool) -> None:
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._dot.setText("" if enabled else "✗")
        self.setProperty("enabled", enabled)
        # Re-evaluate the [enabled="..."] QSS rule.
        self.style().unpolish(self)
        self.style().polish(self)

    @property
    def enabled(self) -> bool:
        return self._enabled
