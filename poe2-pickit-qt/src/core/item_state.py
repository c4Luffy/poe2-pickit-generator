"""Persistent per-item exclusion state.

Stores, per category, the set of item names the user has excluded. Persisted to a
small JSON file so selections survive restarts, and read by the GenerateWorker so
excluded items are dropped from the pickit.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.core.engine import APP_DIR

_PATH = APP_DIR / "item_states.json"


class ItemState:
    def __init__(self) -> None:
        self._disabled: dict[str, set[str]] = {}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(_PATH.read_text(encoding="utf-8"))
            self._disabled = {k: set(v) for k, v in data.items()}
        except Exception:
            self._disabled = {}

    def save(self) -> None:
        try:
            payload = {k: sorted(v) for k, v in self._disabled.items() if v}
            _PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_enabled(self, cat: str, name: str) -> bool:
        return name not in self._disabled.get(cat, set())

    def set_enabled(self, cat: str, name: str, enabled: bool) -> None:
        bucket = self._disabled.setdefault(cat, set())
        if enabled:
            bucket.discard(name)
        else:
            bucket.add(name)
        self.save()

    def set_all(self, cat: str, names, enabled: bool) -> None:
        if enabled:
            self._disabled.pop(cat, None)
        else:
            self._disabled[cat] = set(names)
        self.save()

    def disabled_for(self, cat: str) -> set[str]:
        return set(self._disabled.get(cat, set()))


# Process-wide singleton.
item_state = ItemState()
