"""Collapsible navigation sidebar animated with QPropertyAnimation.

How the animation works
-----------------------
A QPropertyAnimation interpolates a Qt *property* from a start value to an end
value over a duration, sampling an easing curve each frame. Here we animate the
frame's width. To give the frame a single, hard width at every frame (not just a
max), we animate BOTH ``minimumWidth`` and ``maximumWidth`` together inside a
QParallelAnimationGroup — when they share the same animated value the widget is
pinned to exactly that width, producing the smooth slide in/out.
"""
from __future__ import annotations

from PySide6.QtCore import (QEasingCurve, QParallelAnimationGroup,
                            QPropertyAnimation, Qt, Signal)
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout)


class Sidebar(QFrame):
    navigated = Signal(str)   # emitted with a page key when a nav item is clicked
    toggled = Signal(bool)    # emitted with the new expanded state

    def __init__(
        self,
        parent=None,
        collapsed: int = 64,
        expanded: int = 220,
        duration_ms: int = 260,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._collapsed = collapsed
        self._expanded = expanded
        self._is_expanded = True
        self.setFixedWidth(expanded)

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 12, 8, 12)
        self._layout.setSpacing(6)

        # Brand + hamburger header.
        self._brand = QLabel("⚔  Pickit")
        self._brand.setObjectName("Brand")
        self._burger = QPushButton("☰")
        self._burger.setObjectName("NavToggle")
        self._burger.setCursor(Qt.CursorShape.PointingHandCursor)
        self._burger.clicked.connect(self.toggle)
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._brand)
        header.addStretch(1)
        header.addWidget(self._burger)
        self._layout.addLayout(header)
        self._layout.addSpacing(10)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: list[QPushButton] = []
        self._layout.addStretch(1)  # nav items get inserted above this stretch

        # One parallel animation over the two width properties.
        self._anim = QParallelAnimationGroup(self)
        for prop in (b"minimumWidth", b"maximumWidth"):
            a = QPropertyAnimation(self, prop, self)
            a.setDuration(duration_ms)
            a.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._anim.addAnimation(a)

    def add_item(self, key: str, label: str, icon: str = "•") -> QPushButton:
        full = f"  {icon}   {label}"
        btn = QPushButton(full)
        btn.setObjectName("NavButton")
        btn.setCheckable(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setProperty("full_text", full)
        btn.setProperty("icon_only", f"  {icon}")
        btn.clicked.connect(lambda: self.navigated.emit(key))
        self._group.addButton(btn)
        self._buttons.append(btn)
        self._layout.insertWidget(self._layout.count() - 1, btn)  # above the stretch
        if len(self._buttons) == 1:
            btn.setChecked(True)
        return btn

    def select(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def toggle(self) -> None:
        self._is_expanded = not self._is_expanded
        target = self._expanded if self._is_expanded else self._collapsed
        start = self.width()
        for i in range(self._anim.animationCount()):
            anim = self._anim.animationAt(i)
            anim.setStartValue(start)
            anim.setEndValue(target)
        # Show full captions + brand when expanded, icon-only when collapsed.
        self._brand.setText("⚔  Pickit" if self._is_expanded else "⚔")
        for btn in self._buttons:
            btn.setText(
                btn.property("full_text") if self._is_expanded
                else btn.property("icon_only")
            )
        self._anim.start()
        self.toggled.emit(self._is_expanded)
