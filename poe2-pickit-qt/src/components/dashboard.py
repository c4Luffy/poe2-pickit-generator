"""Dashboard view — composes the Phase 1 widgets and an in-app console.

Pure presentation: it wires the reusable widgets together and listens to the log
bridge. No business logic lives here.
"""
from __future__ import annotations

import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QTextEdit, QVBoxLayout, QWidget)

from src.core.logger import log_bridge, logger
from src.ui.widgets.circular_progress import CircularProgress
from src.ui.widgets.system_monitor import SystemMonitor

_LEVEL_COLORS = {
    "ERROR": "#e05555",
    "WARNING": "#d4a84b",
    "INFO": "#5dbb8a",
    "DEBUG": "#8a8a9a",
}


class Dashboard(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Dashboard")
        title.setObjectName("Title")
        subtitle = QLabel("PySide6 prototype shell — Phase 1")
        subtitle.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Top row: progress card + system monitor.
        row = QHBoxLayout()
        row.setSpacing(16)

        prog_card = QFrame()
        prog_card.setObjectName("Card")
        pc = QVBoxLayout(prog_card)
        pc.setContentsMargins(16, 16, 16, 16)
        pc.addWidget(QLabel("Task Progress"))
        self.circular = CircularProgress()
        pc.addWidget(self.circular, alignment=Qt.AlignmentFlag.AlignCenter)
        run = QPushButton("Run demo task")
        run.setObjectName("Primary")
        run.clicked.connect(self._run_demo)
        pc.addWidget(run)

        self.monitor = SystemMonitor()

        row.addWidget(prog_card, 1)
        row.addWidget(self.monitor, 1)
        root.addLayout(row)

        # Console card.
        console_card = QFrame()
        console_card.setObjectName("Card")
        cc = QVBoxLayout(console_card)
        cc.setContentsMargins(16, 16, 16, 16)
        cc.addWidget(QLabel("Console"))
        self.console = QTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        cc.addWidget(self.console)
        root.addWidget(console_card, 1)

        log_bridge.message.connect(self._on_log)
        logger.info("Dashboard ready — click 'Run demo task' to animate the ring.")

    def _on_log(self, level: str, msg: str) -> None:
        color = _LEVEL_COLORS.get(level, "#8a8a9a")
        self.console.append(f'<span style="color:{color}">{msg}</span>')

    def _run_demo(self) -> None:
        target = random.uniform(35, 100)
        logger.info("Demo task started → target %.0f%%", target)
        self.circular.animate_to(target)
