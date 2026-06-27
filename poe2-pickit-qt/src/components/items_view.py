"""Items view — per-category card grid with click-to-exclude.

Left: the exchange categories. Right: a searchable grid of item cards for the
selected category (priced High → Low). Toggling a card persists to ItemState,
which the GenerateWorker reads so excluded items are dropped from the pickit.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from src.core.app_state import current_league
from src.core.engine import gen
from src.core.item_state import item_state
from src.core.logger import logger
from src.core.signals import bus
from src.core.workers import CategoryWorker, extract_rows
from src.ui.widgets.item_card import ItemCard

_NCOLS = 3


class ItemsView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._cards: list[ItemCard] = []
        self._current_cat: str | None = None
        self._thread: QThread | None = None
        self._worker: CategoryWorker | None = None
        self._build()
        bus.league_changed.connect(self._on_league_changed)
        if self.cat_list.count():
            self.cat_list.setCurrentRow(0)

    # ---- layout ----
    def _build(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self.cat_list = QListWidget()
        self.cat_list.setObjectName("CatList")
        self.cat_list.setFixedWidth(168)
        for key, _ninja, label, _is_unique in gen.EXCHANGE_CATEGORIES:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.cat_list.addItem(item)
        self.cat_list.currentItemChanged.connect(self._on_cat_changed)
        root.addWidget(self.cat_list)

        right = QVBoxLayout()
        right.setSpacing(10)

        header = QHBoxLayout()
        self.title = QLabel("Items")
        self.title.setObjectName("Title")
        self.count = QLabel("")
        self.count.setObjectName("Subtitle")
        header.addWidget(self.title)
        header.addStretch(1)
        header.addWidget(self.count)
        right.addLayout(header)

        toolbar = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search items…")
        self.search.textChanged.connect(self._filter)
        enable_btn = QPushButton("Enable all")
        enable_btn.clicked.connect(lambda: self._set_all(True))
        disable_btn = QPushButton("Disable all")
        disable_btn.clicked.connect(lambda: self._set_all(False))
        toolbar.addWidget(self.search, 1)
        toolbar.addWidget(enable_btn)
        toolbar.addWidget(disable_btn)
        right.addLayout(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._grid_host = QWidget()
        self.grid = QGridLayout(self._grid_host)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(8)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        for c in range(_NCOLS):
            self.grid.setColumnStretch(c, 1)
        self.scroll.setWidget(self._grid_host)
        right.addWidget(self.scroll, 1)

        self.status = QLabel("Select a category.")
        self.status.setObjectName("Subtitle")
        right.addWidget(self.status)
        root.addLayout(right, 1)

    # ---- category loading ----
    def _on_cat_changed(self, cur: QListWidgetItem, _prev) -> None:
        if cur is None:
            return
        self._current_cat = cur.data(Qt.ItemDataRole.UserRole)
        self.title.setText(cur.text())
        self._load_category(self._current_cat)

    def _on_league_changed(self, _league: str) -> None:
        if self._current_cat:
            self._load_category(self._current_cat)

    def _load_category(self, key: str) -> None:
        league = current_league()
        # Use the warm cache when available (instant); otherwise fetch off-thread.
        payload = gen._cache_get(league, key) if league else None
        if payload is not None and not isinstance(payload, Exception):
            self._populate(key, extract_rows(payload))
            return

        if self._thread is not None and self._thread.isRunning():
            return
        self._clear_grid()
        self.status.setText("Loading prices…")
        self.count.setText("")
        entry = next((e for e in gen.EXCHANGE_CATEGORIES if e[0] == key), None)
        if entry is None:
            return
        _key, ninja, _label, is_unique = entry
        self._thread = QThread(self)
        self._worker = CategoryWorker(league, key, ninja, is_unique)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.done.connect(self._on_loaded)
        self._worker.failed.connect(self._on_load_fail)
        self._worker.done.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.start()

    def _on_loaded(self, key: str, rows: list) -> None:
        if key == self._current_cat:
            self._populate(key, rows)

    def _on_load_fail(self, key: str, msg: str) -> None:
        if key == self._current_cat:
            self.status.setText(f"Failed to load {key}: {msg}")
            logger.error("Items load failed (%s): %s", key, msg)

    # ---- grid ----
    def _populate(self, key: str, rows: list) -> None:
        self._clear_grid()
        for i, (name, ex_value) in enumerate(rows):
            card = ItemCard(key, name, ex_value, item_state.is_enabled(key, name))
            card.toggled.connect(self._on_toggle)
            self.grid.addWidget(card, i // _NCOLS, i % _NCOLS)
            self._cards.append(card)
        self._apply_search()
        self._update_count()
        self.status.setText("" if rows else "No items in this category.")

    def _clear_grid(self) -> None:
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._cards = []

    def _on_toggle(self, cat: str, name: str, enabled: bool) -> None:
        item_state.set_enabled(cat, name, enabled)
        self._update_count()

    def _set_all(self, enabled: bool) -> None:
        if not self._current_cat:
            return
        item_state.set_all(self._current_cat, [c.name for c in self._cards], enabled)
        for card in self._cards:
            card.set_enabled(enabled)
        self._update_count()

    def _filter(self, _text: str) -> None:
        self._apply_search()

    def _apply_search(self) -> None:
        q = self.search.text().strip().lower()
        for card in self._cards:
            card.setVisible(q in card.name.lower())

    def _update_count(self) -> None:
        total = len(self._cards)
        enabled = sum(1 for c in self._cards if c.enabled)
        self.count.setText(f"{enabled} / {total} enabled")
