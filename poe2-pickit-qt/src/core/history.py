"""Persistent generation history.

A capped, most-recent-first list of past generations, persisted to ``history.json``
(gitignored). The GenerateView appends a record (on the GUI thread, so there's no
save race) when a run finishes; the History view reads it and listens on
``bus.history_changed`` to refresh. Records hold metadata + the output paths — the
preview reads the ``.ipd`` from disk on demand rather than snapshotting its text.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.core.engine import APP_DIR
from src.core.signals import bus

_PATH = APP_DIR / "history.json"
_MAX = 50


class History:
    def __init__(self) -> None:
        self._runs: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            self._runs = [r for r in data if isinstance(r, dict)] if isinstance(data, list) else []
        except Exception:
            self._runs = []

    def save(self) -> None:
        try:
            _PATH.write_text(json.dumps(self._runs[:_MAX], indent=2), encoding="utf-8")
        except Exception:
            pass

    def add(self, record: dict) -> None:
        self._runs.insert(0, dict(record))
        del self._runs[_MAX:]
        self.save()
        bus.history_changed.emit()

    def all(self) -> list[dict]:
        return list(self._runs)

    def clear(self) -> None:
        self._runs = []
        self.save()
        bus.history_changed.emit()


# Process-wide singleton.
history = History()
