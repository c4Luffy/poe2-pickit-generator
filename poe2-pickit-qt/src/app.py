"""Main application window.

Layout only: a left Sidebar + a content area (top bar with a theme toggle, then a
QStackedWidget of pages). Navigation and theming are wired through signals so this
shell stays free of business logic.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt
from PySide6.QtWidgets import (QGraphicsOpacityEffect, QHBoxLayout, QLabel,
                               QMainWindow, QPushButton, QStackedWidget,
                               QVBoxLayout, QWidget)

from src.components.bases_view import BasesView
from src.components.dashboard import Dashboard
from src.components.debug_view import DebugView
from src.components.generate_view import GenerateView
from src.components.history_view import HistoryView
from src.components.items_view import ItemsView
from src.components.settings_view import SettingsView
from src.core.logger import logger
from src.core.theme_manager import ThemeManager
from src.core.version import APP_NAME, VERSION
from src.ui.widgets.sidebar import Sidebar

# Page registry: (key, label, icon, factory). Placeholders are filled in later phases.
_NAV = [
    ("dashboard", "Dashboard", "▣", Dashboard),
    ("generate", "Generate", "⚡", GenerateView),
    ("items", "Items", "▤", ItemsView),
    ("chance", "Chance", "◈", BasesView),
    ("craft", "Craft", "⚒", BasesView),
    ("history", "History", "≣", HistoryView),
    ("settings", "Settings", "⚙", SettingsView),
    ("debug", "Debug", "❖", DebugView),
]


class _Placeholder(QWidget):
    def __init__(self, name: str) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        lay.addStretch(1)
        title = QLabel(name)
        title.setObjectName("Title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note = QLabel("Coming in a later phase.")
        note.setObjectName("Subtitle")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)
        lay.addWidget(note)
        lay.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self, theme: ThemeManager) -> None:
        super().__init__()
        self._theme = theme
        self.setWindowTitle(f"{APP_NAME}  v{VERSION}")

        central = QWidget()
        central.setObjectName("Root")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar + page stack.
        self.sidebar = Sidebar()
        self.stack = QStackedWidget()
        self._pages: dict[str, int] = {}
        for key, label, icon, factory in _NAV:
            if factory is SettingsView:
                widget = SettingsView(theme)        # needs the theme manager
            elif factory is BasesView:
                widget = BasesView(key)             # kind = nav key ("chance"/"craft")
            elif factory is not None:
                widget = factory()
            else:
                widget = _Placeholder(label)
            self._pages[key] = self.stack.addWidget(widget)
            self.sidebar.add_item(key, label, icon)
        self.sidebar.navigated.connect(self._navigate)

        # Content area: top bar + stack.
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)

        topbar = QWidget()
        topbar.setObjectName("TopBar")
        tl = QHBoxLayout(topbar)
        tl.setContentsMargins(20, 10, 20, 10)
        self._page_title = QLabel("Dashboard")
        self._page_title.setObjectName("Title")
        theme_btn = QPushButton("🌓  Theme")
        theme_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        theme_btn.clicked.connect(self._toggle_theme)
        tl.addWidget(self._page_title)
        tl.addStretch(1)
        tl.addWidget(theme_btn)

        cl.addWidget(topbar)
        cl.addWidget(self.stack, 1)

        root.addWidget(self.sidebar)
        root.addWidget(content, 1)
        self.setCentralWidget(central)

    def _navigate(self, key: str) -> None:
        if key in self._pages:
            self.stack.setCurrentIndex(self._pages[key])
            self._page_title.setText(key.capitalize())
            self._fade_in(self.stack.currentWidget())
            logger.info("Navigated to '%s'.", key)

    def _fade_in(self, widget: QWidget) -> None:
        """Quick opacity fade on the newly shown page.

        A QPropertyAnimation drives the ``opacity`` of a QGraphicsOpacityEffect
        from 0 → 1; the effect is removed when the fade finishes so the page
        renders normally (and without effect overhead) at rest.
        """
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(lambda: widget.setGraphicsEffect(None))
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
        self._fade_anim = anim  # keep a reference so it isn't GC'd mid-flight

    def _toggle_theme(self) -> None:
        self._theme.toggle()
        logger.info("Theme switched to '%s'.", self._theme.name)
