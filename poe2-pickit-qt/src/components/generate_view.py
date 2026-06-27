"""Generate view — league + value floors → live pickit generation.

Pure presentation + thread orchestration. The actual work runs in GenerateWorker
on a QThread; this view only collects inputs, starts the worker, and renders the
signals it emits. No engine logic lives here.
"""
from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt, QThread, QTimer
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFrame, QGridLayout,
                               QHBoxLayout, QInputDialog, QLabel, QLineEdit,
                               QMessageBox, QPushButton, QSlider, QTextEdit,
                               QVBoxLayout, QWidget)

from src.core.app_state import set_current_league
from src.core.deploy import deploy_outputs
from src.core.engine import OUTPUT_DIR
from src.core.history import history
from src.core.logger import logger
from src.core.settings import settings
from src.core.signals import bus
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
        self._desired_league = ""   # league to (re)select once leagues load
        self._gen_thread: QThread | None = None
        self._gen_worker: GenerateWorker | None = None
        self._lg_thread: QThread | None = None
        self._lg_worker: LeagueWorker | None = None
        self._auto_run = False   # set when a run is triggered by the hourly timer
        self._build()
        self._refresh_profiles()
        self._apply_profile(settings.active_profile())
        bus.profiles_changed.connect(self._refresh_profiles)
        bus.active_profile_changed.connect(self._on_active_profile_changed)
        bus.settings_changed.connect(self._on_settings_changed)

        # Hourly auto-generate (Automation & Safety setting).
        self._schedule_timer = QTimer(self)
        self._schedule_timer.setInterval(60 * 60 * 1000)  # 1 hour
        self._schedule_timer.timeout.connect(self._auto_generate)
        self._apply_schedule()

        if auto_fetch and settings.get("auto_fetch_leagues", True):
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

        # Profile bar: pick a saved config bundle, or save the current one.
        prof_row = QHBoxLayout()
        prof_row.setSpacing(8)
        prof_lbl = QLabel("Profile")
        prof_lbl.setObjectName("Metric")
        self.profile_cb = QComboBox()
        self.profile_cb.setMinimumWidth(180)
        self.profile_cb.currentIndexChanged.connect(self._on_profile_picked)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_profile)
        saveas_btn = QPushButton("Save As…")
        saveas_btn.clicked.connect(self._save_profile_as)
        del_btn = QPushButton("Delete")
        del_btn.clicked.connect(self._delete_profile)
        prof_row.addWidget(prof_lbl)
        prof_row.addWidget(self.profile_cb)
        prof_row.addWidget(save_btn)
        prof_row.addWidget(saveas_btn)
        prof_row.addWidget(del_btn)
        prof_row.addStretch(1)
        root.addLayout(prof_row)

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
        self.league_cb.blockSignals(True)
        self.league_cb.clear()
        for name, _slug, display in leagues:
            self.league_cb.addItem(display, name)
        self.league_cb.blockSignals(False)
        # Restore the active profile's league if it's still live, else fall back.
        desired = self._desired_league or (leagues[0][0] if leagues else "")
        self._select_league(desired)
        set_current_league(self._selected_league())
        self.refresh_btn.setEnabled(True)
        self.status.setText(f"Loaded {len(leagues)} leagues.")
        logger.info("Loaded %d leagues.", len(leagues))

    def _select_league(self, name: str) -> None:
        """Select ``name`` by matching the league list, else set it as free text."""
        if not name:
            return
        for i, (lname, _slug, _disp) in enumerate(self._leagues):
            if lname == name:
                self.league_cb.setCurrentIndex(i)
                return
        self.league_cb.setCurrentText(name)

    def _on_league_fail(self, msg: str) -> None:
        self.refresh_btn.setEnabled(True)
        self.status.setText(f"League fetch failed: {msg}")
        logger.error("League fetch failed: %s", msg)

    def _selected_league(self) -> str:
        idx = self.league_cb.currentIndex()
        if 0 <= idx < len(self._leagues):
            return self._leagues[idx][0]
        return self.league_cb.currentText().strip()

    # ---- profiles ----
    def _refresh_profiles(self) -> None:
        """Repopulate the dropdown from the store, selecting the active profile.

        Guarded with ``blockSignals`` so programmatic repopulation doesn't fire
        ``_on_profile_picked`` (which would re-activate / re-apply needlessly).
        """
        self.profile_cb.blockSignals(True)
        self.profile_cb.clear()
        self.profile_cb.addItems(settings.profile_names())
        idx = self.profile_cb.findText(settings.active_profile_name())
        if idx >= 0:
            self.profile_cb.setCurrentIndex(idx)
        self.profile_cb.blockSignals(False)

    def _apply_profile(self, prof: dict) -> None:
        """Push a profile's values onto the config controls."""
        self._desired_league = prof.get("league", "") or ""
        self._select_league(self._desired_league)
        self.unique_slider.setValue(int(prof.get("unique_floor", 0) or 0))
        self.gear_slider.setValue(int(prof.get("gear_floor", 0) or 0))
        self.output_edit.setText(prof.get("output_name") or "poe2_pickit")
        self.bases_chk.setChecked(bool(prof.get("include_bases", True)))

    def _collect_config(self) -> dict:
        """Read the current control values into a profile dict."""
        return {
            "league": self._selected_league(),
            "unique_floor": self.unique_slider.value(),
            "gear_floor": self.gear_slider.value(),
            "output_name": self.output_edit.text().strip() or "poe2_pickit",
            "include_bases": self.bases_chk.isChecked(),
        }

    def _on_profile_picked(self, _index: int) -> None:
        name = self.profile_cb.currentText()
        if name:
            settings.set_active(name)  # → active_profile_changed → _apply_profile

    def _on_active_profile_changed(self, name: str) -> None:
        """React to an activation from anywhere (this view or Settings)."""
        idx = self.profile_cb.findText(name)
        if idx >= 0 and idx != self.profile_cb.currentIndex():
            self.profile_cb.blockSignals(True)
            self.profile_cb.setCurrentIndex(idx)
            self.profile_cb.blockSignals(False)
        self._apply_profile(settings.active_profile())

    def _save_profile(self) -> None:
        name = settings.active_profile_name()
        settings.save_profile(name, self._collect_config())
        self.status.setText(f"Saved profile '{name}'.")

    def _save_profile_as(self) -> None:
        name, ok = QInputDialog.getText(self, "Save Profile As", "Profile name:")
        name = name.strip()
        if not (ok and name):
            return
        settings.save_profile(name, self._collect_config())
        settings.set_active(name)
        self.status.setText(f"Saved profile '{name}'.")

    def _delete_profile(self) -> None:
        name = settings.active_profile_name()
        if settings.delete_profile(name):
            self.status.setText(f"Deleted profile '{name}'.")
        else:
            self.status.setText("Can't delete the only profile.")

    # ---- automation ----
    def _on_settings_changed(self, key: str) -> None:
        if key == "auto_schedule":
            self._apply_schedule()

    def _apply_schedule(self) -> None:
        if settings.get("auto_schedule"):
            if not self._schedule_timer.isActive():
                self._schedule_timer.start()
            logger.info("Hourly auto-generate is ON.")
        else:
            self._schedule_timer.stop()

    def _auto_generate(self) -> None:
        """Hourly timer entry point — runs unattended (no overwrite prompt)."""
        self._auto_run = True
        self._start_generate()

    def _recent_pickit_exists(self, window: int = 120) -> bool:
        name = self.output_edit.text().strip() or "poe2_pickit"
        path = os.path.join(str(OUTPUT_DIR), name + ".ipd")
        try:
            return os.path.exists(path) and (time.time() - os.path.getmtime(path)) < window
        except OSError:
            return False

    # ---- generate ----
    def _start_generate(self) -> None:
        if self._gen_thread is not None and self._gen_thread.isRunning():
            return
        auto = self._auto_run
        self._auto_run = False
        league = self._selected_league()
        if not league:
            self.status.setText("Pick a league first.")
            return

        # Confirm before clobbering a pickit generated moments ago (skip for
        # unattended hourly runs, which intentionally refresh in place).
        if (not auto and settings.get("confirm_overwrite")
                and self._recent_pickit_exists()):
            ans = QMessageBox.question(
                self, "Overwrite recent pickit?",
                "You generated this pickit less than 2 minutes ago. Overwrite it?")
            if ans != QMessageBox.StandardButton.Yes:
                self.status.setText("Generation cancelled.")
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
            backup_count=int(settings.get("backup_count", 0) or 0),
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
        self._record_history(stats)
        self._deploy(stats)
        logger.info("Generation finished: %d active rules in %.1fs.",
                    stats["active"], stats["duration"])

    def _deploy(self, stats: dict) -> None:
        """Copy the outputs to the bot/game folders per Settings, and log results."""
        _LOG = {"ok": logger.info, "warn": logger.warning, "err": logger.error}
        for level, msg in deploy_outputs(stats.get("ipd", ""), stats.get("filter", "")):
            _LOG.get(level, logger.info)(msg)
            if level != "ok":
                self.status.setText(f"⚠ {msg}")

    def _record_history(self, stats: dict) -> None:
        """Persist a compact record of this run (everything but the line dump)."""
        record = {k: stats[k] for k in (
            "ts", "league", "unique_floor", "gear_floor", "include_bases",
            "active", "commented", "divine", "top_name", "duration",
            "errors", "warnings", "ipd", "filter") if k in stats}
        record["profile"] = settings.active_profile_name()
        history.add(record)

    def _on_failed(self, msg: str) -> None:
        self.generate_btn.setEnabled(True)
        self.status.setText(f"✗ Generation failed: {msg}")
        logger.error("Generation failed: %s", msg)

    def _open_output(self) -> None:
        try:
            os.startfile(str(OUTPUT_DIR))  # type: ignore[attr-defined]  (Windows)
        except Exception:  # noqa: BLE001
            logger.warning("Could not open output folder: %s", OUTPUT_DIR)
