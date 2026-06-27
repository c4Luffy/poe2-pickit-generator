"""Persistent per-base exclusion state for the Chance / Craft tabs.

The twin of ``item_state.py``, but keyed by *kind* (``"chance"`` / ``"craft"``)
rather than poe.ninja category. Stores the set of base names the user has
excluded in each tab, persisted to a small JSON file so selections survive
restarts, and read by the GenerateWorker so excluded bases are dropped from the
generated chance/craft base rules.

The stored names are exactly what the engine's builders filter on:
``build_chance_base_rules(disabled_bases=...)`` matches base *types* and
``build_craft_base_rules(disabled=...)`` matches base *names* — both of which are
the card name shown in the grid.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.core.engine import APP_DIR

_PATH = APP_DIR / "base_states.json"


class BaseState:
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

    def is_enabled(self, kind: str, name: str) -> bool:
        return name not in self._disabled.get(kind, set())

    def set_enabled(self, kind: str, name: str, enabled: bool) -> None:
        bucket = self._disabled.setdefault(kind, set())
        if enabled:
            bucket.discard(name)
        else:
            bucket.add(name)
        self.save()

    def set_all(self, kind: str, names, enabled: bool) -> None:
        if enabled:
            self._disabled.pop(kind, None)
        else:
            self._disabled[kind] = set(names)
        self.save()

    def disabled_for(self, kind: str) -> set[str]:
        return set(self._disabled.get(kind, set()))


# Process-wide singleton.
base_state = BaseState()
