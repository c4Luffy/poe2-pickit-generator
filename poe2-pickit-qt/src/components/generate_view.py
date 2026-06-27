"""Generate view — league + value floors → live pickit generation.

Pure presentation + thread orchestration. The actual work runs in GenerateWorker
on a QThread; this view only collects inputs, starts the worker, and renders the
signals it emits. No engine logic lives here.
"""
from __future__ import annotations

import os

from PySide6.QtCore import Qt, QThread
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QSlider, QTextEdit, QVBoxLayout, QWidget)

from src.core.app_state import set_current_league
from src.core.engine import OUTPUT_DIR
from src.core.logger import logger
from src.core.workers import GenerateWorker, LeagueWorker
from src.ui.widgets.linear_progress import LinearProgress


class _StatCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("Card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)
        head = QLabel(title)
        head.setObjectName("Subtitle")
        self._value = QLabel("—")
        self._value.setObjectName("Title")
        lay.addWidget(head)
        lay.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(str(text))


class GenerateView(QWidget):
    def __init__(self, parent=None, auto_fetch: bool = True) -> None:
        super().__init__(parent)
        self._leagues: list = []
        self._gen_thread: QThread | None = None
        self._gen_worker: GenerateWorker | None = None
        self._lg_thread: QThread | None = None
        self._lg_worker: LeagueWorker | None = None
        self._build()
        if auto_fetch:
            self._fetch_leagues()

    # ---- layout ----
    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        title = QLabel("Generate")
        title.setObjectName("Title")
        sub = QLabel("Live poe.ninja prices → .ipd pickit + matching .filter")
        sub.setObjectName("Subtitle")
        root.addWidget(title)
        root.addWidget(sub)

        cfg = QFrame()
        cfg.setObjectName("Card")
        grid = QGridLayout(cfg)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(1, 1)

        grid.addWidget(QLabel("League"), 0, 0)
        self.league_cb = QComboBox()
        self.league_cb.setEditable(True)
        self.league_cb.currentIndexChanged.connect(
            lambda: set_current_league(self._selected_league()))
        grid.addWidget(self.league_cb, 0, 1)
        self.refresh_btn = QPushButton("↻")
        self.refresh_btn.setFixedWidth(40)
        self.refresh_btn.clicked.connect(self._fetch_leagues)
        grid.addWidget(self.refresh_btn, 0, 2)

        grid.addWidget(QLabel("Unique floor"), 1, 0)
        self.unique_slider, u_row = self._slider(0, 1000)
        grid.addLayout(u_row, 1, 1, 1, 2)

        grid.addWidget(QLabel("Exchange & gear floor"), 2, 0)
        self.gear_slider, g_row = self._slider(0, 500)
        grid.addLayout(g_row, 2, 1, 1, 2)

        grid.addWidget(QLabel("Output name"), 3, 0)
        self.output_edit = QLineEdit("poe2_pickit")
        grid.addWidget(self.output_edit, 3, 1, 1, 2)

        self.bases_chk = QCheckBox("Include endgame gear base types")
        self.bases_chk.setChecked(True)
        grid.addWidget(self.bases_chk, 4, 1, 1, 2)
        root.addWidget(cfg)

        actions = QHBoxLayout()
        self.generate_btn = QPushButton("⚡  Generate Pickit")
        self.generate_btn.setObjectName("Primary")
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._start_generate)
        open_btn = QPushButton("Open output folder")
        open_btn.clicked.connect(self._open_output)
        actions.addWidget(self.generate_btn)
        actions.addWidget(open_btn)
        actions.addStretch(1)
        root.addLayout(actions)

        self.status = QLabel("Idle.")
        self.status.setObjectName("Subtitle")
        self.progress = LinearProgress()
        root.addWidget(self.status)
        root.addWidget(self.progress)

        stats = QHBoxLayout()
        stats.setSpacing(10)
        self.stat_active = _StatCard("Active rules")
        self.stat_commented = _StatCard("Commented")
        self.stat_divine = _StatCard("Divine rate")
        self.stat_top = _StatCard("Top item")
        self.stat_time = _StatCard("Run time")
        for card in (self.stat_active, self.stat_commented, self.stat_divine,
                     self.stat_top, self.stat_time):
            stats.addWidget(card, 1)
        root.addLayout(stats)

        self.preview = QTextEdit()
        self.preview.setObjectName("Console")
        self.preview.setReadOnly(True)
        self.preview.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        root.addWidget(self.preview, 1)

    def _slider(self, lo: int, hi: int) -> tuple[QSlider, QHBoxLayout]:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(lo, hi)
        slider.setSingleStep(5)
        slider.setPageStep(25)
        label = QLabel("0 ex")
        label.setObjectName("Metric")
        label.setFixedWidth(72)
        slider.valueChanged.connect(lambda v: label.setText(f"{v} ex"))
        row = QHBoxLayout()
        row.addWidget(slider, 1)
        row.addWidget(label)
        return slider, row

    # ---- leagues ----
    def _fetch_leagues(self) -> None:
        if self._lg_thread is not None and self._lg_thread.isRunning():
            return
        self.refresh_btn.setEnabled(False)
        self.status.setText("Loading leagues…")
        self._lg_thread = QThread(self)
        self._lg_worker = LeagueWorker()
        self._lg_worker.moveToThread(self._lg_thread)
        self._lg_thread.started.connect(self._lg_worker.run)
        self._lg_worker.done.connect(self._on_leagues)
        self._lg_worker.failed.connect(self._on_league_fail)
        self._lg_worker.done.connect(self._lg_thread.quit)
        self._lg_worker.failed.connect(self._lg_thread.quit)
        self._lg_thread.start()

    def _on_leagues(self, leagues: list) -> None:
        self._leagues = leagues
        self.league_cb.clear()
        for name, _slug, display in leagues:
            self.league_cb.addItem(display, name)
        if leagues:
            set_current_league(leagues[0][0])
        self.refresh_btn.setEnabled(True)
        self.status.setText(f"Loaded {len(leagues)} leagues.")
        logger.info("Loaded %d leagues.", len(leagues))

    def _on_league_fail(self, msg: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.status.setText(f"League fetch failed: {msg}")
        logger.error("League fetch failed: %s", msg)

    def _selected_league(self) -> str:
        idx = self.league_cb.currentIndex()
        if 0 <= idx < len(self._leagues):
            return self._leagues[idx][0]
        return self.league_cb.currentText().strip()

    # ---- generate ----
    def _start_generate(self) -> None:
        if self._gen_thread is not None and self._gen_thread.isRunning():
            return
        league = self._selected_league()
        if not league:
            self.status.setText("Pick a league first.")
            return
        try:
            unique_floor = float(self.unique_slider.value())
            gear_floor = float(self.gear_slider.value())
        except (TypeError, ValueError):
            unique_floor = gear_floor = 0.0

        self.generate_btn.setEnabled(False)
        self.preview.clear()
        self.progress.setValue(0)

        self._gen_thread = QThread(self)
        self._gen_worker = GenerateWorker(
            league, unique_floor, gear_floor,
            self.output_edit.text().strip() or "poe2_pickit",
            self.bases_chk.isChecked(),
        )
        self._gen_worker.moveToThread(self._gen_thread)
        self._gen_thread.started.connect(self._gen_worker.run)
        self._gen_worker.progress.connect(self._on_progress)
        self._gen_worker.finished.connect(self._on_finished)
        self._gen_worker.failed.connect(self._on_failed)
        self._gen_worker.finished.connect(self._gen_thread.quit)
        self._gen_worker.failed.connect(self._gen_thread.quit)
        self._gen_thread.start()
        logger.info("Generation started for league '%s'.", league)

    def _on_progress(self, msg: str, pct: int) -> None:
        self.status.setText(msg)
        self.progress.setValue(pct)

    def _on_finished(self, stats: dict) -> None:
        self.generate_btn.setEnabled(True)
        self.stat_active.set_value(f"{stats['active']:,}")
        self.stat_commented.set_value(f"{stats['commented']:,}")
        self.stat_divine.set_value(f"{stats['divine']:.1f} ex")
        self.stat_top.set_value(stats["top_name"][:16] if stats["top_name"] else "—")
        self.stat_time.set_value(f"{stats['duration']:.1f}s")
        verdict = "✓" if not stats["errors"] else "⚠"
        self.status.setText(
            f"{verdict} {stats['active']:,} active rules · {stats['errors']} errors · "
            f"saved to {os.path.basename(stats['ipd'])}"
        )
        self.preview.setPlainText("\n".join(stats["lines"][:800]))
        logger.info("Generation finished: %d active rules in %.1fs.",
                    stats["active"], stats["duration"])

    def _on_failed(self, msg: str) -> None:
        self.generate_btn.setEnabled(True)
        self.status.setText(f"✗ Generation failed: {msg}")
        logger.error("Generation failed: %s", msg)

    def _open_output(self) -> None:
        try:
            os.startfile(str(OUTPUT_DIR))  # type: ignore[attr-defined]  (Windows)
        except Exception:  # noqa: BLE001
            logger.warning("Could not open output folder: %s", OUTPUT_DIR)
