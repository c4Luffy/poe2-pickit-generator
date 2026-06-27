"""Persistent application settings + named generation profiles.

Mirrors ``item_state.py``: a small JSON file (``settings.json``, gitignored) holds
process-wide preferences that should survive restarts, loaded once into a
singleton. Two kinds of state live here:

* **App preferences** — the active theme and startup behaviour. These previously
  reset on every launch (the app always opened dark and refetched leagues).
* **Profiles** — named bundles of Generate-view config (league + value floors +
  output name + bases toggle). One profile is "active"; the Generate view loads it
  on startup and writes back to it. There is always at least one profile.

Components stay decoupled by listening on ``bus.profiles_changed`` /
``bus.active_profile_changed`` rather than reaching into each other.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from src.core.engine import APP_DIR
from src.core.signals import bus

_PATH = APP_DIR / "settings.json"


def default_game_filter_dir() -> str:
    """Best-guess location of the PoE2 client loot-filter folder (mirrors the
    old app's heuristic)."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Documents", "My Games", "Path of Exile 2"),
        os.path.join(home, "OneDrive", "Documents", "My Games", "Path of Exile 2"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]

# A profile = these fields. Anything missing is filled from here on load.
PROFILE_DEFAULTS: dict = {
    "league": "",
    "unique_floor": 0,
    "gear_floor": 0,
    "output_name": "poe2_pickit",
    "include_bases": True,
}

_DEFAULT_PROFILE_NAME = "Default"

# Top-level app preferences (everything except `profiles`/`active_profile`).
_APP_DEFAULTS: dict = {
    "theme": "dark",
    "auto_fetch_leagues": True,
    # Bot integration — where generated files get deployed after a run.
    "bot_folder": "",                 # Exiled Bot 2 pickit folder
    "auto_copy_ipd": False,           # copy <name>.ipd there after generate
    "poe2_filter_dir": default_game_filter_dir(),  # PoE2 client folder
    "copy_filter_to_game": False,     # copy <name>.filter there after generate
}


class Settings:
    def __init__(self) -> None:
        self._data: dict = {}
        self._load()

    # ---- persistence ----
    def _load(self) -> None:
        try:
            raw = json.loads(_PATH.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

        data = copy.deepcopy(_APP_DEFAULTS)
        data.update({k: v for k, v in raw.items()
                     if k in _APP_DEFAULTS})

        # Normalise profiles: ensure a dict of {name: full-profile}, never empty.
        profiles = raw.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            profiles = {_DEFAULT_PROFILE_NAME: copy.deepcopy(PROFILE_DEFAULTS)}
        data["profiles"] = {
            str(name): {**PROFILE_DEFAULTS, **(p if isinstance(p, dict) else {})}
            for name, p in profiles.items()
        }

        active = raw.get("active_profile")
        if active not in data["profiles"]:
            active = next(iter(data["profiles"]))
        data["active_profile"] = active

        self._data = data

    def save(self) -> None:
        try:
            _PATH.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def snapshot(self) -> dict:
        """A deep copy of all settings — for the Debug 'Show config' dump."""
        return copy.deepcopy(self._data)

    # ---- app preferences ----
    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        if self._data.get(key) == value:
            return
        self._data[key] = value
        self.save()

    # ---- profiles ----
    def profile_names(self) -> list[str]:
        return list(self._data["profiles"].keys())

    def active_profile_name(self) -> str:
        return self._data["active_profile"]

    def get_profile(self, name: str) -> dict | None:
        p = self._data["profiles"].get(name)
        return dict(p) if p is not None else None

    def active_profile(self) -> dict:
        return dict(self._data["profiles"][self._data["active_profile"]])

    def save_profile(self, name: str, data: dict) -> None:
        """Create or overwrite a profile, then persist. Unknown keys are dropped."""
        name = name.strip()
        if not name:
            return
        clean = {**PROFILE_DEFAULTS, **{k: data[k] for k in PROFILE_DEFAULTS if k in data}}
        self._data["profiles"][name] = clean
        self.save()
        bus.profiles_changed.emit()

    def set_active(self, name: str) -> None:
        if name in self._data["profiles"] and name != self._data["active_profile"]:
            self._data["active_profile"] = name
            self.save()
            bus.active_profile_changed.emit(name)

    def rename_profile(self, old: str, new: str) -> bool:
        new = new.strip()
        profiles = self._data["profiles"]
        if old not in profiles or not new or new in profiles:
            return False
        # Preserve insertion order by rebuilding the dict with the key swapped.
        self._data["profiles"] = {
            (new if k == old else k): v for k, v in profiles.items()
        }
        if self._data["active_profile"] == old:
            self._data["active_profile"] = new
            bus.active_profile_changed.emit(new)
        self.save()
        bus.profiles_changed.emit()
        return True

    def delete_profile(self, name: str) -> bool:
        """Remove a profile. Refuses to delete the last remaining one."""
        profiles = self._data["profiles"]
        if name not in profiles or len(profiles) <= 1:
            return False
        del profiles[name]
        if self._data["active_profile"] == name:
            new_active = next(iter(profiles))
            self._data["active_profile"] = new_active
            bus.active_profile_changed.emit(new_active)
        self.save()
        bus.profiles_changed.emit()
        return True


# Process-wide singleton.
settings = Settings()
