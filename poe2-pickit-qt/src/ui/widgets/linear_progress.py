"""A borderless, QSS-styled linear progress bar.

The visual styling lives entirely in app.qss.template under the ``#Linear``
selector (background, rounded corners, and the coloured ``::chunk``) — this class
just sets the object name and sane defaults so the QSS applies.
"""
from __future__ import annotations

from PySide6.QtWidgets import QProgressBar


class LinearProgress(QProgressBar):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Linear")
        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(False)
        self.setFixedHeight(10)
