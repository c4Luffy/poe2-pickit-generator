"""Background workers (QObject + signals, run on a QThread).

The engine does blocking network I/O, so it must never run on the GUI thread.
Each worker is a plain QObject moved onto a QThread; it communicates results back
to the UI purely through signals (Qt marshals them to the GUI thread for us).
"""
from __future__ import annotations

import datetime
import os
import re
import time

from PySide6.QtCore import QObject, Signal

from src.core.base_state import base_state
from src.core.engine import OUTPUT_DIR, gen
from src.core.item_state import item_state

_NAME_RE = re.compile(r'\[UniqueName\]\s*==\s*"([^"]+)"')
_TYPE_RE = re.compile(r'"([^"]+)"')
_EXVAL_RE = re.compile(r"ExValue = ([\d.]+)")


def _rule_name(line: str) -> str:
    m = _NAME_RE.search(line) or _TYPE_RE.search(line)
    return m.group(1) if m else "?"


def _sparkline(line: dict) -> tuple[tuple, bool]:
    """Return (trend_points, is_up) for a payload line.

    poe.ninja spells the field two ways — ``sparkline`` on currency overviews and
    ``sparkLine`` on item/unique overviews — with a low-confidence fallback. Points
    are the 7-day relative price series; trend direction comes from totalChange.
    """
    spark = line.get("sparkline") or line.get("sparkLine") \
        or line.get("lowConfidenceSparkline") or {}
    points = tuple(x for x in (spark.get("data") or []) if x is not None)
    up = float(spark.get("totalChange") or 0.0) >= 0
    return points, up


def extract_rows(payload: dict) -> list[tuple[str, float, tuple, bool]]:
    """Return [(name, exalt_value, trend_points, is_up), ...] High → Low."""
    rate = gen.exalted_rate(payload)
    items_by_id = {i["id"]: i for i in payload.get("items", [])}
    rows: list[tuple[str, float, tuple, bool]] = []
    for line in payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if not item or not item.get("name"):
            continue
        raw = item["name"]
        if raw in gen.ITEM_NAME_SKIP:
            continue
        name = gen.ITEM_NAME_CORRECTIONS.get(raw, raw)
        if name is None:
            continue
        pv = float(line.get("primaryValue") or 0.0)
        points, up = _sparkline(line)
        rows.append((name, pv * rate if rate else pv, points, up))
    rows.sort(key=lambda r: -r[1])
    return rows


class CategoryWorker(QObject):
    """Fetches one category's priced items for the Items grid."""

    done = Signal(str, list)    # (cat_key, rows)
    failed = Signal(str, str)   # (cat_key, error)

    def __init__(self, league: str, cat_key: str, ninja_type: str, is_unique: bool) -> None:
        super().__init__()
        self.league = league
        self.cat_key = cat_key
        self.ninja_type = ninja_type
        self.is_unique = is_unique

    def run(self) -> None:
        try:
            league = self.league or gen.detect_current_league()
            payload = gen.fetch_category(league, self.cat_key, self.ninja_type, self.is_unique)
            gen._cache_set(league, self.cat_key, payload)
            self.done.emit(self.cat_key, extract_rows(payload))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(self.cat_key, str(exc))


class LeagueWorker(QObject):
    """Fetches the live league list from poe.ninja."""

    done = Signal(list)    # list[(name, slug, display)]
    failed = Signal(str)

    def run(self) -> None:
        try:
            self.done.emit(gen.fetch_live_leagues())
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class GenerateWorker(QObject):
    """Runs a full pickit generation and reports progress + results."""

    progress = Signal(str, int)   # (message, percent 0..100)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        league: str,
        unique_floor: float,
        gear_floor: float,
        output_base: str,
        include_bases: bool = True,
    ) -> None:
        super().__init__()
        self.league = league
        self.unique_floor = unique_floor
        self.gear_floor = gear_floor
        self.output_base = output_base
        self.include_bases = include_bases

    def run(self) -> None:  # noqa: C901  (linear pipeline, intentionally flat)
        try:
            t0 = time.time()
            league = self.league
            W = gen._W

            self.progress.emit("Fetching currency rates…", 5)
            currency = gen.fetch_category(league, "currency", "Currency", False)
            gen._cache_set(league, "currency", currency)

            rate = gen.exalted_rate(currency)
            divine = 1.0
            items_by_id = {i["id"]: i for i in currency.get("items", [])}
            for line in currency.get("lines", []):
                item = items_by_id.get(line.get("id"))
                if item and item.get("name") == "Divine Orb":
                    pv = float(line.get("primaryValue") or 0.0)
                    divine = pv * rate if rate else pv
                    break

            out: list[str] = [
                "/" * W,
                "//" + "  EXILEBOT 2  |  QT GENERATE".center(W - 4) + "//",
                "/" * W,
                f"// League    : {league}",
                f"// Generated : {datetime.datetime.now():%Y-%m-%d %H:%M:%S}",
                f"// Threshold : {self.gear_floor:.0f} ex (exchange/gear)  |  "
                f"{self.unique_floor:.0f} ex (unique)",
                "/" * W,
                "",
                f"// Conversion: 1 Divine = {divine:.6f} Exalted",
                "",
                gen.header_major("Economy Items"),
                "",
            ]

            non_currency = [c for c in gen.ALL_CATEGORIES if c[0] != "currency"]
            self.progress.emit(f"Fetching {len(non_currency)} categories…", 18)
            payloads = gen.fetch_all_payloads(league, non_currency)
            payloads["currency"] = currency

            top: list[tuple[str, float]] = []
            total = len(gen.ALL_CATEGORIES)
            for idx, (key, _ninja, label, is_unique) in enumerate(gen.ALL_CATEGORIES, 1):
                self.progress.emit(f"Building {label}…", 18 + int(idx / total * 62))
                payload = payloads.get(key)
                if payload is None or isinstance(payload, Exception):
                    out += [gen.header_sub(label), f"// (no data for {label})", ""]
                    continue

                # Drop user-excluded items (Items tab) for the price-driven
                # exchange categories. Uniques/waystones aren't per-item filtered.
                disabled = item_state.disabled_for(key)
                enabled_names = None
                if disabled and not is_unique:
                    in_payload = {
                        gen.ITEM_NAME_CORRECTIONS.get(i["name"], i["name"])
                        for i in payload.get("items", []) if i.get("name")
                    }
                    enabled_names = in_payload - disabled

                if is_unique:
                    lines = gen.build_unique_lines(payload, divine, min_exalt=self.unique_floor)
                elif key == "uncut_gems":
                    lines = gen.build_uncut_gem_lines(
                        payload, divine, min_exalt=self.gear_floor, enabled_names=enabled_names)
                elif key == "waystones":
                    lines = gen.build_waystone_lines()
                else:
                    pick_all = key in gen.PICK_ALL_CATEGORIES
                    always = (gen.ALWAYS_PICK_CURRENCY if key == "currency"
                              else gen.ALWAYS_PICK_RUNES if key == "runes" else None)
                    lines = gen.build_exchange_lines(
                        payload, divine, pick_all=pick_all, min_exalt=self.gear_floor,
                        tier_sort=(key == "essences"), enabled_names=enabled_names,
                        always_names=always,
                    )

                out += [gen.header_sub(label), ""] + lines + [""]
                for line in lines:
                    if line.startswith("//") or "[StashItem]" not in line:
                        continue
                    m = _EXVAL_RE.search(line)
                    if m:
                        top.append((_rule_name(line), float(m.group(1))))

            # Static blocks + curated bases.
            out += gen.STATIC_TABLET_RULES.splitlines()
            out += gen.STATIC_WOMBGIFT_RULES.splitlines()
            out += gen.STATIC_SPECIAL_WAYSTONE_RULES.splitlines()
            out += gen.build_chance_base_rules(
                disabled_bases=base_state.disabled_for("chance"))
            out += gen.build_craft_base_rules(
                disabled=base_state.disabled_for("craft"))

            if self.include_bases:
                self.progress.emit("Building gear base types…", 84)
                out += ["", gen.header_major("Gear Base Types (game data)"), ""]
                out += gen.build_base_rules()

            self.progress.emit("Validating & writing files…", 92)
            validation = gen.validate_pickit(out)

            base = os.path.join(str(OUTPUT_DIR),
                                os.path.basename(self.output_base) or "poe2_pickit")
            ipd_path = base + ".ipd"
            filter_path = base + ".filter"
            with open(ipd_path, "w", encoding="utf-8") as f:
                f.write("\n".join(out))
            with open(filter_path, "w", encoding="utf-8") as f:
                f.write("\n".join(gen.build_loot_filter(out)))

            active = sum(1 for l in out if l and not l.startswith("//") and "[StashItem]" in l)
            commented = sum(1 for l in out if l.startswith("//") and "[StashItem]" in l)
            top.sort(key=lambda r: -r[1])
            top_name, top_value = top[0] if top else ("", 0.0)

            self.progress.emit("Done", 100)
            self.finished.emit({
                "ts": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "league": league,
                "unique_floor": self.unique_floor,
                "gear_floor": self.gear_floor,
                "include_bases": self.include_bases,
                "active": active,
                "commented": commented,
                "divine": divine,
                "top_name": top_name,
                "top_value": top_value,
                "duration": time.time() - t0,
                "ipd": ipd_path,
                "filter": filter_path,
                "errors": len(validation["errors"]),
                "warnings": len(validation["warnings"]),
                "lines": out,
            })
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))
