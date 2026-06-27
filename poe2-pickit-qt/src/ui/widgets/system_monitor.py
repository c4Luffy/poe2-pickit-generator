"""System monitoring widget boilerplate.

Polls CPU/RAM on a QTimer and feeds two LinearProgress bars. Uses ``psutil`` for
real metrics when it's installed; otherwise it shows a smooth simulated signal so
the prototype still demonstrates live updates.
"""
from __future__ import annotations

import random

from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QVBoxLayout)
from PySide6.QtCore import QTimer

from src.ui.widgets.linear_progress import LinearProgress

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except Exception:
    _HAS_PSUTIL = False


class _MetricRow(QFrame):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        head = QHBoxLayout()
        name = QLabel(title)
        name.setObjectName("Subtitle")
        self._value_lbl = QLabel("0%")
        self._value_lbl.setObjectName("Metric")
        head.addWidget(name)
        head.addStretch(1)
        head.addWidget(self._value_lbl)

        self._bar = LinearProgress()
        lay.addLayout(head)
        lay.addWidget(self._bar)

    def set_value(self, pct: float) -> None:
        self._bar.setValue(int(round(pct)))
        self._value_lbl.setText(f"{pct:.0f}%")


class SystemMonitor(QFrame):
    def __init__(self, parent=None, interval_ms: int = 1000) -> None:
        super().__init__(parent)
        self.setObjectName("Card")

        lay = QVBoxLayout(self)
        title = QLabel("System Monitor")
        title.setObjectName("Title")
        source = QLabel("source: psutil" if _HAS_PSUTIL else "source: simulated")
        source.setObjectName("Subtitle")

        self._cpu = _MetricRow("CPU")
        self._ram = _MetricRow("Memory")

        lay.addWidget(title)
        lay.addWidget(source)
        lay.addSpacing(8)
        lay.addWidget(self._cpu)
        lay.addSpacing(6)
        lay.addWidget(self._ram)
        lay.addStretch(1)

        self._cpu_sim = 30.0
        self._ram_sim = 45.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(interval_ms)
        self._tick()

    def _tick(self) -> None:
        if _HAS_PSUTIL:
            cpu = float(psutil.cpu_percent())
            ram = float(psutil.virtual_memory().percent)
        else:
            self._cpu_sim = min(100.0, max(2.0, self._cpu_sim + random.uniform(-9, 9)))
            self._ram_sim = min(100.0, max(10.0, self._ram_sim + random.uniform(-4, 4)))
            cpu, ram = self._cpu_sim, self._ram_sim
        self._cpu.set_value(cpu)
        self._ram.set_value(ram)
