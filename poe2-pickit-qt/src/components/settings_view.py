"""Settings view — app preferences and the profile manager.

Pure presentation over the ``settings`` store and the ``ThemeManager``:

* **Appearance** — choose the active theme (persisted; shared with the top-bar
  toggle, so the two stay in sync).
* **Startup** — whether to auto-fetch leagues when the app opens.
* **Profiles** — the canonical manager for the named Generate configs: activate,
  rename, or delete. The Generate tab has the quick dropdown + Save; this is where
  the full list lives. Both views listen on the same signals, so edits here show
  up there immediately.
* **Data** — open the folder that holds ``settings.json`` / ``item_states.json``.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QHBoxLayout,
                               QInputDialog, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QVBoxLayout,
                               QWidget)

from src.core.engine import APP_DIR
from src.core.logger import logger
from src.core.settings import settings
from src.core.signals import bus
from src.core.theme_manager import ThemeManager


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName("Card")
    inner = QVBoxLayout(frame)
    inner.setContentsMargins(16, 14, 16, 14)
    inner.setSpacing(10)
    head = QLabel(title)
    head.setObjectName("Metric")
    inner.addWidget(head)
    return frame, inner


class SettingsView(QWidget):
    def __init__(self, theme: ThemeManager, parent=None) -> None:
        super().__init__(parent)
        self._theme = theme
        self._syncing_theme = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("Title")
        sub = QLabel("Preferences and generation profiles — saved to settings.json")
        sub.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(sub)

        root.addWidget(self._appearance_card())
        root.addWidget(self._startup_card())
        root.addWidget(self._profiles_card(), 1)
        root.addWidget(self._data_card())

        bus.profiles_changed.connect(self._refresh_profiles)
        bus.active_profile_changed.connect(lambda _n: self._refresh_profiles())
        theme.theme_changed.connect(self._on_theme_changed_external)

    # ---- appearance ----
    def _appearance_card(self) -> QFrame:
        frame, inner = _card("Appearance")
        row = QHBoxLayout()
        row.addWidget(QLabel("Theme"))
        self.theme_cb = QComboBox()
        self.theme_cb.addItems(self._theme.available() or ["dark", "light"])
        idx = self.theme_cb.findText(self._theme.name)
        if idx >= 0:
            self.theme_cb.setCurrentIndex(idx)
        self.theme_cb.currentTextChanged.connect(self._on_theme_picked)
        row.addWidget(self.theme_cb)
        row.addStretch(1)
        inner.addLayout(row)
        return frame

    def _on_theme_picked(self, name: str) -> None:
        if self._syncing_theme or name == self._theme.name:
            return
        self._theme.apply(name)  # persists via main's theme_changed → settings

    def _on_theme_changed_external(self, name: str) -> None:
        """Keep the dropdown in sync when the top-bar toggle changes the theme."""
        idx = self.theme_cb.findText(name)
        if idx >= 0 and idx != self.theme_cb.currentIndex():
            self._syncing_theme = True
            self.theme_cb.setCurrentIndex(idx)
            self._syncing_theme = False

    # ---- startup ----
    def _startup_card(self) -> QFrame:
        frame, inner = _card("Startup")
        self.autofetch_chk = QCheckBox("Auto-fetch leagues from poe.ninja on launch")
        self.autofetch_chk.setChecked(bool(settings.get("auto_fetch_leagues", True)))
        self.autofetch_chk.toggled.connect(
            lambda on: settings.set("auto_fetch_leagues", bool(on)))
        inner.addWidget(self.autofetch_chk)
        return frame

    # ---- profiles ----
    def _profiles_card(self) -> QFrame:
        frame, inner = _card("Profiles")
        self.profile_list = QListWidget()
        self.profile_list.setObjectName("CatList")
        self.profile_list.itemDoubleClicked.connect(lambda _i: self._activate())
        inner.addWidget(self.profile_list, 1)

        btns = QHBoxLayout()
        btns.setSpacing(8)
        act_btn = QPushButton("Set Active")
        act_btn.clicked.connect(self._activate)
        ren_btn = QPushButton("Rename…")
        ren_btn.clicked.connect(self._rename)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete)
        btns.addWidget(act_btn)
        btns.addWidget(ren_btn)
        btns.addWidget(del_btn)
        btns.addStretch(1)
        self.profile_status = QLabel("")
        self.profile_status.setObjectName("Subtitle")
        btns.addWidget(self.profile_status)
        inner.addLayout(btns)

        self._refresh_profiles()
        return frame

    def _refresh_profiles(self) -> None:
        active = settings.active_profile_name()
        self.profile_list.clear()
        for name in settings.profile_names():
            prof = settings.get_profile(name) or {}
            league = prof.get("league") or "no league"
            summary = (f"{league} · gear {prof.get('gear_floor', 0)} ex · "
                       f"unique {prof.get('unique_floor', 0)} ex")
            mark = "●  " if name == active else "    "
            item = QListWidgetItem(f"{mark}{name}\n      {summary}")
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.profile_list.addItem(item)

    def _selected_name(self) -> str | None:
        item = self.profile_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _activate(self) -> None:
        name = self._selected_name()
        if name:
            settings.set_active(name)
            self.profile_status.setText(f"'{name}' is now active.")

    def _rename(self) -> None:
        name = self._selected_name()
        if not name:
            return
        new, ok = QInputDialog.getText(self, "Rename Profile", "New name:", text=name)
        new = new.strip()
        if not (ok and new) or new == name:
            return
        if settings.rename_profile(name, new):
            self.profile_status.setText(f"Renamed to '{new}'.")
        else:
            self.profile_status.setText(f"Can't rename — '{new}' already exists.")

    def _delete(self) -> None:
        name = self._selected_name()
        if not name:
            return
        if settings.delete_profile(name):
            self.profile_status.setText(f"Deleted '{name}'.")
        else:
            self.profile_status.setText("Can't delete the only profile.")

    # ---- data ----
    def _data_card(self) -> QFrame:
        frame, inner = _card("Data")
        path = QLabel(f"Settings & state live in:  {APP_DIR}")
        path.setObjectName("Subtitle")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        inner.addWidget(path)
        open_btn = QPushButton("Open data folder")
        open_btn.clicked.connect(self._open_data)
        row = QHBoxLayout()
        row.addWidget(open_btn)
        row.addStretch(1)
        inner.addLayout(row)
        return frame

    def _open_data(self) -> None:
        try:
            os.startfile(str(APP_DIR))  # type: ignore[attr-defined]  (Windows)
        except Exception:  # noqa: BLE001
            logger.warning("Could not open data folder: %s", APP_DIR)
