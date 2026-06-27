"""A clickable item card: name + price + enabled/excluded state.

Clicking toggles inclusion. Visual state is driven by a dynamic Qt property
(``enabled``) so the styling lives in QSS (``#ItemCard[enabled="false"]``); after
flipping it we re-polish the widget so the new rule applies.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel


def _fmt_ex(ex: float) -> str:
    if ex >= 1000:
        return f"{ex / 1000:.1f}k ex"
    if ex >= 10:
        return f"{ex:.0f} ex"
    return f"{ex:.1f} ex"


class ItemCard(QFrame):
    toggled = Signal(str, str, bool)  # (cat, name, enabled)

    def __init__(self, cat: str, name: str, ex_value: float, enabled: bool,
                 parent=None) -> None:
        super().__init__(parent)
        self.cat = cat
        self.name = name
        self._enabled = enabled
        self.setObjectName("ItemCard")
        self.setProperty("enabled", enabled)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)

        self._name = QLabel(name)
        self._name.setObjectName("ItemName")
        self._price = QLabel(_fmt_ex(ex_value))
        self._price.setObjectName("ItemPrice")
        self._dot = QLabel("" if enabled else "✗")
        self._dot.setObjectName("Dot")
        self._dot.setFixedWidth(14)

        lay.addWidget(self._name, 1)
        lay.addWidget(self._price)
        lay.addWidget(self._dot)

    def mousePressEvent(self, event) -> None:
        self.set_enabled(not self._enabled)
        self.toggled.emit(self.cat, self.name, self._enabled)

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
