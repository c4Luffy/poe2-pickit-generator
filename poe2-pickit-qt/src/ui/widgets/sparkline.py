"""A tiny price-trend sparkline, custom-painted with QPainter.

Draws the poe.ninja 7-day price points as a normalised polyline — green when the
overall trend is up, red when it's down. Like ``CircularProgress``, the two colours
are exposed as Qt properties (``upColor`` / ``downColor``) so the theme can set them
from QSS via ``qproperty-*``; each instance then paints with whichever matches its
own trend direction.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QWidget


class Sparkline(QWidget):
    def __init__(self, data=(), up: bool = True, parent=None) -> None:
        super().__init__(parent)
        self._data = [float(x) for x in data if x is not None]
        self._up = bool(up)
        self._up_color = QColor("#5dbb8a")
        self._down_color = QColor("#e05555")
        self.setFixedSize(64, 22)

    def set_data(self, data, up: bool) -> None:
        self._data = [float(x) for x in data if x is not None]
        self._up = bool(up)
        self.update()

    # ---- QSS-settable colours (qproperty-upColor / qproperty-downColor) ----
    def get_up_color(self) -> QColor:
        return self._up_color

    def set_up_color(self, c: QColor) -> None:
        self._up_color = c
        self.update()

    upColor = Property(QColor, get_up_color, set_up_color)

    def get_down_color(self) -> QColor:
        return self._down_color

    def set_down_color(self, c: QColor) -> None:
        self._down_color = c
        self.update()

    downColor = Property(QColor, get_down_color, set_down_color)

    # ---- painting ----
    def paintEvent(self, event) -> None:
        pts = self._data
        if len(pts) < 2:
            return
        pad = 3.0
        w = self.width() - 2 * pad
        h = self.height() - 2 * pad
        lo, hi = min(pts), max(pts)
        rng = (hi - lo) or 1.0
        n = len(pts)

        poly = QPolygonF()
        for i, v in enumerate(pts):
            x = pad + w * (i / (n - 1))
            y = pad + h * (1.0 - (v - lo) / rng)  # high value → top
            poly.append(QPointF(x, y))

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._up_color if self._up else self._down_color, 1.6)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPolyline(poly)
        painter.end()
