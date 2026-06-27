"""Tiny shared app state — the currently selected league.

The Generate view owns the league dropdown; the Items view needs the same league
to fetch prices. Rather than couple them, the Generate view writes the league
here and anyone interested listens on ``bus.league_changed``.
"""
from __future__ import annotations

from src.core.signals import bus

_current_league = ""


def set_current_league(name: str) -> None:
    global _current_league
    if name and name != _current_league:
        _current_league = name
        bus.league_changed.emit(name)


def current_league() -> str:
    return _current_league
