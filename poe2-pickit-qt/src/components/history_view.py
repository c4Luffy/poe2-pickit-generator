"""History view — browse past generations and preview their output.

Left: a most-recent-first list of recorded runs. Right: a stat line for the
selected run, buttons to open its files/folder, and a read-only preview of the
saved ``.ipd`` (read from disk on demand — files live in ``output/``). Listens on
``bus.history_changed`` so a fresh generation shows up immediately.
"""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QPushButton, QTextEdit,
                               QVBoxLayout, QWidget)

from src.core.history import history
from src.core.logger import logger
from src.core.signals import bus

_PREVIEW_LINES = 800


class HistoryView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current: dict | None = None
        self._build()
        self._refresh()
        bus.history_changed.connect(self._refresh)

    # ---- layout ----
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("History")
        title.setObjectName("Title")
        header.addWidget(title)
        header.addStretch(1)
        self.count = QLabel("")
        self.count.setObjectName("Subtitle")
        self.clear_btn = QPushButton("Clear history")
        self.clear_btn.clicked.connect(self._clear)
        header.addWidget(self.count)
        header.addWidget(self.clear_btn)
        root.addLayout(header)

        sub = QLabel("Past generations — open the files or preview the pickit.")
        sub.setObjectName("Subtitle")
        root.addWidget(sub)

        body = QHBoxLayout()
        body.setSpacing(12)

        self.run_list = QListWidget()
        self.run_list.setObjectName("CatList")
        self.run_list.setFixedWidth(260)
        self.run_list.currentItemChanged.connect(self._on_select)
        body.addWidget(self.run_list)

        right = QVBoxLayout()
        right.setSpacing(10)

        self.detail = QLabel("Select a run.")
        self.detail.setObjectName("Subtitle")
        self.detail.setWordWrap(True)
        right.addWidget(self.detail)

        actions = QHBoxLayout()
        self.open_ipd_btn = QPushButton("Open .ipd")
        self.open_ipd_btn.clicked.connect(lambda: self._open("ipd"))
        self.open_filter_btn = QPushButton("Open .filter")
        self.open_filter_btn.clicked.connect(lambda: self._open("filter"))
        self.open_dir_btn = QPushButton("Open folder")
        self.open_dir_btn.clicked.connect(self._open_dir)
        for b in (self.open_ipd_btn, self.open_filter_btn, self.open_dir_btn):
            b.setEnabled(False)
            actions.addWidget(b)
        actions.addStretch(1)
        right.addLayout(actions)

        self.preview = QTextEdit()
        self.preview.setObjectName("Console")
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        right.addWidget(self.preview, 1)

        body.addLayout(right, 1)
        root.addLayout(body, 1)

    # ---- data ----
    def _refresh(self) -> None:
        runs = history.all()
        self.run_list.blockSignals(True)
        self.run_list.clear()
        for i, r in enumerate(runs):
            top = r.get("top_name") or "—"
            label = (f"{r.get('ts', '?')}\n      {r.get('league', '?')} · "
                     f"{r.get('active', 0):,} rules · {top[:18]}")
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.run_list.addItem(item)
        self.run_list.blockSignals(False)
        self.count.setText(f"{len(runs)} run{'s' if len(runs) != 1 else ''}")
        self.clear_btn.setEnabled(bool(runs))
        if runs:
            self.run_list.setCurrentRow(0)
        else:
            self._current = None
            self.detail.setText("No generations yet — run one from the Generate tab.")
            self.preview.clear()
            self._set_actions(False)

    def _on_select(self, cur: QListWidgetItem, _prev) -> None:
        if cur is None:
            return
        runs = history.all()
        idx = cur.data(Qt.ItemDataRole.UserRole)
        if not (isinstance(idx, int) and 0 <= idx < len(runs)):
            return
        self._current = runs[idx]
        self._show(self._current)

    def _show(self, r: dict) -> None:
        verdict = "✓" if not r.get("errors") else "⚠"
        self.detail.setText(
            f"{verdict} {r.get('ts', '?')}  ·  league {r.get('league', '?')}  ·  "
            f"profile {r.get('profile', '—')}\n"
            f"{r.get('active', 0):,} active · {r.get('commented', 0):,} commented · "
            f"{r.get('errors', 0)} errors · floors {r.get('gear_floor', 0)}/"
            f"{r.get('unique_floor', 0)} ex · {r.get('duration', 0):.1f}s · "
            f"top {r.get('top_name') or '—'}"
        )
        self._set_actions(True)
        self.preview.setPlainText(self._read_preview(r.get("ipd", "")))

    def _read_preview(self, path: str) -> str:
        if not path:
            return "(no output file recorded)"
        try:
            lines = Path(path).read_text(encoding="utf-8").splitlines()
            text = "\n".join(lines[:_PREVIEW_LINES])
            if len(lines) > _PREVIEW_LINES:
                text += f"\n… ({len(lines) - _PREVIEW_LINES:,} more lines)"
            return text
        except Exception:
            return f"(file no longer available)\n{path}"

    def _set_actions(self, on: bool) -> None:
        for b in (self.open_ipd_btn, self.open_filter_btn, self.open_dir_btn):
            b.setEnabled(on)

    # ---- actions ----
    def _open(self, key: str) -> None:
        if self._current:
            self._startfile(self._current.get(key, ""))

    def _open_dir(self) -> None:
        if self._current:
            ipd = self._current.get("ipd", "")
            self._startfile(str(Path(ipd).parent) if ipd else "")

    def _startfile(self, path: str) -> None:
        if path and Path(path).exists():
            try:
                os.startfile(path)  # type: ignore[attr-defined]  (Windows)
                return
            except Exception:  # noqa: BLE001
                pass
        logger.warning("Could not open: %s", path or "(empty)")

    def _clear(self) -> None:
        history.clear()
