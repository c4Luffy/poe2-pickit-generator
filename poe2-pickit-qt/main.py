"""Application entry point.

Run with:  python main.py   (from inside the poe2-pickit-qt/ folder)

Keeps logic out of the layout: this file only wires together the QApplication,
the ThemeManager, and the MainWindow, then starts the Qt event loop.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `src` importable regardless of the current working directory.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PySide6.QtWidgets import QApplication

from src.app import MainWindow
from src.core.logger import logger
from src.core.theme_manager import ThemeManager


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("ExileBot 2 Pickit — Qt")

    # JSON-driven theming: load + apply the dark theme as the app-wide stylesheet.
    theme = ThemeManager(app, default="dark")
    theme.apply()
    logger.info("Application started (theme=%s).", theme.name)

    window = MainWindow(theme)
    window.resize(1120, 720)
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
