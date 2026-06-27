"""Centralised logging with a Qt bridge.

The standard `logging` module does the formatting and timestamps; a small QObject
re-emits each record as a Qt signal so any widget (e.g. the in-app console) can
display it on the GUI thread without knowing where the log originated.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal

from src.core.engine import APP_DIR

# Persisted log file (next to the app / .exe). Opened from the Debug page.
LOG_PATH = APP_DIR / "pickit_qt.log"


class LogBridge(QObject):
    message = Signal(str, str)  # (level_name, formatted_message)


class _QtHandler(logging.Handler):
    """A logging handler that forwards each record onto a Qt signal."""

    def __init__(self, bridge: LogBridge) -> None:
        super().__init__()
        self._bridge = bridge

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self._bridge.message.emit(record.levelname, self.format(record))
        except Exception:
            self.handleError(record)


# Shared bridge + a configured module logger.
log_bridge = LogBridge()

logger = logging.getLogger("pickit_qt")
if not logger.handlers:
    logger.setLevel(logging.DEBUG)
    _fmt = logging.Formatter("%(asctime)s  %(levelname)-7s  %(message)s", "%H:%M:%S")

    _stream = logging.StreamHandler()
    _stream.setFormatter(_fmt)
    logger.addHandler(_stream)

    _qt = _QtHandler(log_bridge)
    _qt.setFormatter(_fmt)
    logger.addHandler(_qt)

    try:
        _file = logging.FileHandler(LOG_PATH, encoding="utf-8")
        _file.setFormatter(logging.Formatter(
            "%(asctime)s  %(levelname)-7s  %(message)s", "%Y-%m-%d %H:%M:%S"))
        logger.addHandler(_file)
    except Exception:  # noqa: BLE001  (never let logging setup crash startup)
        pass
