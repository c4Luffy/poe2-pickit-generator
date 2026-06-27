"""Debug view — troubleshooting tools (ports the old app's Debug page).

Run diagnostics (Python env, modules, generator, poe.ninja connectivity), test
every category endpoint, dump the saved config, open the log file, or prune stale
disk-cache files. Network work runs in a DebugWorker on a QThread; results stream
back as coloured lines. Share this output when reporting a bug.
"""
from __future__ import annotations

import json
import os

from PySide6.QtCore import QThread
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget)

from src.core.app_state import current_league
from src.core.engine import APP_DIR, CACHE_DIR, OUTPUT_DIR, gen
from src.core.logger import LOG_PATH, logger
from src.core.settings import settings
from src.core.workers import DebugWorker

_COLORS = {
    "header": "#d4b072",
    "ok": "#5dbb8a",
    "err": "#e05555",
    "warn": "#d4a84b",
    "info": "#ece4d8",
    "dim": "#8a8a9c",
}


class DebugView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: DebugWorker | None = None
        self._build()

    # ---- layout ----
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("Debug")
        title.setObjectName("Title")
        sub = QLabel("Troubleshooting tools — share this output when reporting a bug.")
        sub.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(sub)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        self._buttons = {
            "diag": self._mk_btn("Run diagnostics", self._run_diagnostics, bar),
            "api": self._mk_btn("Test all endpoints", self._run_api_test, bar),
        }
        self._mk_btn("Show config", self._show_config, bar)
        self._mk_btn("Open log", self._open_log, bar)
        self._mk_btn("Prune cache", self._prune_cache, bar)
        self._mk_btn("Clear", self._clear, bar)
        bar.addStretch(1)
        root.addLayout(bar)

        self.console = QTextEdit()
        self.console.setObjectName("Console")
        self.console.setReadOnly(True)
        self.console.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        root.addWidget(self.console, 1)

    def _mk_btn(self, text: str, slot, bar: QHBoxLayout) -> QPushButton:
        b = QPushButton(text)
        b.clicked.connect(slot)
        bar.addWidget(b)
        return b

    # ---- console ----
    def _log(self, level: str, msg: str) -> None:
        self.console.setTextColor(QColor(_COLORS.get(level, _COLORS["info"])))
        self.console.append(msg)

    def _clear(self) -> None:
        self.console.clear()

    # ---- worker-backed actions ----
    def _run_diagnostics(self) -> None:
        self._start_worker("diag")

    def _run_api_test(self) -> None:
        self._start_worker("api")

    def _start_worker(self, mode: str) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        self._clear()
        for b in self._buttons.values():
            b.setEnabled(False)
        self._thread = QThread(self)
        self._worker = DebugWorker(mode, current_league())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.line.connect(self._log)
        self._worker.done.connect(self._on_done)
        self._worker.done.connect(self._thread.quit)
        self._thread.start()

    def _on_done(self) -> None:
        for b in self._buttons.values():
            b.setEnabled(True)

    # ---- synchronous actions ----
    def _show_config(self) -> None:
        self._clear()
        self._log("header", "── Paths")
        for name, path in (("App dir", APP_DIR), ("Output", OUTPUT_DIR),
                           ("Cache", CACHE_DIR), ("Log", LOG_PATH)):
            self._log("info", f"  {name:<8}: {path}")
        self._log("dim", "")
        self._log("header", "── settings.json")
        self._log("info", json.dumps(settings.snapshot(), indent=2))

    def _open_log(self) -> None:
        try:
            if os.path.exists(LOG_PATH):
                os.startfile(str(LOG_PATH))  # type: ignore[attr-defined]  (Windows)
            else:
                self._log("warn", f"No log file yet at {LOG_PATH}")
        except Exception:  # noqa: BLE001
            logger.warning("Could not open log: %s", LOG_PATH)

    def _prune_cache(self) -> None:
        try:
            removed = gen.prune_disk_cache(max_age_days=60)
            msg = (f"Pruned {removed} stale cache file(s)." if removed
                   else "Nothing to prune — all cache files are recent.")
            self._log("ok" if removed else "dim", f"[Prune] {msg}")
            logger.info("Manual cache prune: %d file(s) removed", removed)
        except Exception as exc:  # noqa: BLE001
            self._log("err", f"[Prune] Error: {exc}")
