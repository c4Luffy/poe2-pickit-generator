"""Application-wide signal bus.

A single QObject whose signals decouple UI components from each other and from
business logic. Widgets emit/connect to these instead of calling into each other
directly, so the layout never reaches into logic and vice-versa.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    nav_changed = Signal(str)            # a sidebar item was selected (page key)
    theme_toggle_requested = Signal()    # someone asked to switch dark/light
    task_progress = Signal(str, float)   # (task key, percent 0..100)
    league_changed = Signal(str)         # the active league changed
    profiles_changed = Signal()          # the set/contents of saved profiles changed
    active_profile_changed = Signal(str) # a different profile became active (name)


# Process-wide singleton — `from src.core.signals import bus`.
bus = SignalBus()
