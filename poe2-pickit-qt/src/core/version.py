"""Single source of truth for the Qt app version.

Bumped on each release; compared by the auto-updater against the value published
on GitHub. Kept tiny and dependency-free so anything can import it.
"""
from __future__ import annotations

VERSION = "0.1.0"
APP_NAME = "ExileBot 2 Pickit"
