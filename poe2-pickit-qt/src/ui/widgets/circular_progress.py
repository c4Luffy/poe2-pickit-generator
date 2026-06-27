"""Circular progress ring, custom-painted with QPainter — no native chrome.

Colours are exposed as Qt properties (``progressColor``/``trackColor``/
``textColor``) so they can be set from the stylesheet via ``qproperty-*`` rules —
that's how a QPainter widget participates in QSS theming. ``value`` is also a Qt
property, which lets ``animate_to()`` drive it with a QPropertyAnimation for a
smooth fill.
"""
from __future__ import annotations

from PySide6.QtCore import (Property, QEasingCurve, QPropertyAnimation, QRectF,
                            Qt)
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class CircularProgress(QWidget):
    def __init__(self, parent=None, thickness: int = 12) -> None:
        super().__init__(parent)
        self._value = 0.0
        self._thickness = thickness
        self._progress_color = QColor("#c8a96e")
        self._track_color = QColor("#2a2a38")
        self._text_color = QColor("#ece4d8")
        self._anim: QPropertyAnimation | None = None
        self.setMinimumSize(150, 150)

    # ---- value (0..100), animatable ----
    def get_value(self) -> float:
        return self._value

    def set_value(self, v: float) -> None:
        self._value = max(0.0, min(100.0, float(v)))
        self.update()

    value = Property(float, get_value, set_value)

    # ---- QSS-settable colours (qproperty-progressColor, etc.) ----
    def get_progress_color(self) -> QColor:
        return self._progress_color

    def set_progress_color(self, c: QColor) -> None:
        self._progress_color = c
        self.update()

    progressColor = Property(QColor, get_progress_color, set_progress_color)

    def get_track_color(self) -> QColor:
        return self._track_color

    def set_track_color(self, c: QColor) -> None:
        self._track_color = c
        self.update()

    trackColor = Property(QColor, get_track_color, set_track_color)

    def get_text_color(self) -> QColor:
        return self._text_color

    def set_text_color(self, c: QColor) -> None:
        self._text_color = c
        self.update()

    textColor = Property(QColor, get_text_color, set_text_color)

    # ---- animation helper ----
    def animate_to(self, target: float, duration_ms: int = 700) -> None:
        self._anim = QPropertyAnimation(self, b"value", self)
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(self._value)
        self._anim.setEndValue(max(0.0, min(100.0, float(target))))
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ---- painting ----
    def paintEvent(self, event) -> None:
        side = min(self.width(), self.height())
        margin = self._thickness / 2 + 2
        x = (self.width() - side) / 2 + margin
        y = (self.height() - side) / 2 + margin
        rect = QRectF(x, y, side - 2 * margin, side - 2 * margin)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._track_color, self._thickness)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)  # full track

        pen.setColor(self._progress_color)
        painter.setPen(pen)
        span = int(self._value / 100.0 * 360 * 16)
        painter.drawArc(rect, 90 * 16, -span)  # start at top, clockwise

        painter.setPen(self._text_color)
        font = QFont(self.font())
        font.setPointSize(max(12, int(side * 0.16)))
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, f"{int(round(self._value))}%")
        painter.end()
