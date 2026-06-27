"""JSON-driven theme manager.

Themes are plain JSON token files (src/styles/themes/*.json). A single QSS
*template* (src/styles/app.qss.template) references those tokens as
``{{group.key}}`` placeholders. ``apply()`` loads the active theme, flattens its
tokens to dotted keys, substitutes them into the template, and sets the result
as the application-wide stylesheet.

Because Qt re-applies a stylesheet to the entire widget tree on
``setStyleSheet``, toggling the theme is instant and live — no individual widget
needs to know the colours.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

# In a PyInstaller build the styles are bundled under _MEIPASS/src/styles; in dev
# they sit next to this package.
if getattr(sys, "frozen", False):
    _STYLES_DIR = Path(getattr(sys, "_MEIPASS")) / "src" / "styles"
else:
    _STYLES_DIR = Path(__file__).resolve().parents[1] / "styles"
_THEMES_DIR = _STYLES_DIR / "themes"
_TEMPLATE = _STYLES_DIR / "app.qss.template"
_TOKEN_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def _flatten(data: dict, prefix: str = "") -> dict[str, str]:
    """Turn {'colors': {'bg': '#fff'}} into {'colors.bg': '#fff'}."""
    out: dict[str, str] = {}
    for key, value in data.items():
        dotted = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(_flatten(value, f"{dotted}."))
        else:
            out[dotted] = str(value)
    return out


class ThemeManager(QObject):
    """Loads JSON themes and applies them as dynamic QSS."""

    theme_changed = Signal(str)  # carries the new theme name

    def __init__(self, app: QApplication, default: str = "dark") -> None:
        super().__init__()
        self._app = app
        self._name = default
        self._template = _TEMPLATE.read_text(encoding="utf-8")
        self._tokens: dict[str, str] = {}

    @property
    def name(self) -> str:
        return self._name

    def available(self) -> list[str]:
        return sorted(p.stem for p in _THEMES_DIR.glob("*.json"))

    def load(self, name: str) -> dict[str, str]:
        path = _THEMES_DIR / f"{name}.json"
        return _flatten(json.loads(path.read_text(encoding="utf-8")))

    def _render(self) -> str:
        """Substitute every {{token}} in the template with its theme value."""
        return _TOKEN_RE.sub(
            lambda m: self._tokens.get(m.group(1), m.group(0)), self._template
        )

    def apply(self, name: str | None = None) -> None:
        if name:
            self._name = name
        self._tokens = self.load(self._name)
        self._app.setStyleSheet(self._render())
        self.theme_changed.emit(self._name)

    def toggle(self) -> None:
        order = self.available() or ["dark", "light"]
        idx = order.index(self._name) if self._name in order else 0
        self.apply(order[(idx + 1) % len(order)])

    def color(self, key: str, fallback: str = "#000000") -> str:
        """Raw token access for widgets that paint themselves (QPainter)."""
        return self._tokens.get(key, fallback)
