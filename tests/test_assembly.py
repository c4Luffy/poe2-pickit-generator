"""Unit tests for pickit_assembly — the pure rule-assembly logic lifted out of the
GUI's ``_generate``. These run with no display, no network, no file I/O, so the
generation pipeline is finally testable on its own.

Run with:  python -m pytest test_assembly.py -v
"""
import datetime

from exilebot_pickit.generators import assembly as asm
from exilebot_pickit import generator as gen


# ── Helpers ──────────────────────────────────────────────────────────────────

def _exchange_payload(items, rate=1.0):
    """poe.ninja-shaped exchange payload. items: list of (id, name, primary_value)."""
    return {
        "core":  {"rates": {"exalted": rate}},
        "items": [{"id": i, "name": n} for i, n, _ in items],
        "lines": [{"id": i, "primaryValue": v} for i, _, v in items],
    }


def _unique_payload(rows, rate=1.0):
    """Unique payload. rows: list of (name, base_type, primary_value)."""
    return {
        "core":  {"rates": {"exalted": rate}},
        "lines": [{"name": n, "baseType": b, "primaryValue": v} for n, b, v in rows],
    }


# ── build_header_lines ───────────────────────────────────────────────────────

def test_header_banner_carries_league_and_id():
    ts = datetime.datetime(2026, 6, 28, 16, 37, 44)
    out = asm.build_header_lines("Fate of the Vaal", ts, "20260628_163744", 7.0, 50.0)
    text = "\n".join(out)
    assert "ID: 20260628_163744" in out[1]
    assert "Fate of the Vaal" in text
    assert out[0] == "/" * gen._W           # opening border
    assert "2026-06-28 16:37:44" in text    # generated timestamp


def test_header_documents_core_tokens():
    out = "\n".join(asm.build_header_lines("L", datetime.datetime.now(), "ID", 0, 0))
    for token in ("[TotalResistances]", "[ComputedArmour]", "[UniqueName]",
                  "[WaystoneTier]", "[IgnoreRitual]", "[StashUnid]", "WeaponCategory"):
        assert token in out, f"header missing {token}"
    # The all-important pre/post-identify split must be explained.
    assert "Before # = checked BEFORE identifying" in out


# ── compute_divine_rate ──────────────────────────────────────────────────────

def test_compute_divine_rate_found():
    payload = _exchange_payload([(1, "Divine Orb", 350.0), (2, "Chaos Orb", 1.0)], rate=1.0)
    divine, found, rate = asm.compute_divine_rate(payload)
    assert found is True
    assert divine == 350.0
    assert rate == 1.0


def test_compute_divine_rate_applies_exalted_rate():
    payload = _exchange_payload([(1, "Divine Orb", 2.0)], rate=180.0)
    divine, found, _ = asm.compute_divine_rate(payload)
    assert found is True
    assert divine == 360.0     # primaryValue * exalted rate


def test_compute_divine_rate_missing():
    payload = _exchange_payload([(1, "Chaos Orb", 1.0)], rate=1.0)
    divine, found, _ = asm.compute_divine_rate(payload)
    assert found is False
    assert divine == 1.0


# ── effective_min ────────────────────────────────────────────────────────────

def test_effective_min_category_override_wins():
    snap = {"cat_thresh": {"currency": 12.0}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 12.0


def test_effective_min_falls_back_to_gear_global():
    snap = {"cat_thresh": {"currency": -1.0}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 5.0


def test_effective_min_uses_unique_global_for_uniques():
    snap = {"cat_thresh": {}}
    assert asm.effective_min(snap, "unique_weapons", True, 5.0, 50.0) == 50.0


def test_effective_min_tolerates_bad_value():
    snap = {"cat_thresh": {"currency": "oops"}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 5.0


# ── enabled_names_for ────────────────────────────────────────────────────────

def test_enabled_names_excludes_disabled():
    payload = _exchange_payload([(1, "Chaos Orb", 1), (2, "Divine Orb", 1), (3, "Mirror", 1)])
    states = {"Divine Orb": {"enabled": False}}
    names = asm.enabled_names_for("currency", False, payload, states)
    assert names == {"Chaos Orb", "Mirror"}


def test_enabled_names_none_for_uniques():
    payload = _unique_payload([("Headhunter", "Heavy Belt", 1)])
    assert asm.enabled_names_for("unique_weapons", True, payload, {"x": {}}) is None


def test_enabled_names_none_when_no_states():
    payload = _exchange_payload([(1, "Chaos Orb", 1)])
    assert asm.enabled_names_for("currency", False, payload, {}) is None


# ── build_category_lines ─────────────────────────────────────────────────────

def test_build_category_lines_unique():
    payload = _unique_payload([("Headhunter", "Heavy Belt", 100.0)])
    lines = asm.build_category_lines("unique_weapons", True, payload, 1.0, 10.0, 5.0, None)
    joined = "\n".join(lines)
    assert '[UniqueName] == "Headhunter"' in joined
    assert '[Type] == "Heavy Belt"' in joined


def test_build_category_lines_currency_pick_all():
    # currency is a PICK_ALL category — every item active regardless of threshold.
    payload = _exchange_payload([(1, "Chaos Orb", 0.001)], rate=1.0)
    lines = asm.build_category_lines("currency", False, payload, 1.0, 9999.0, 5.0, None)
    active = [l for l in lines if l.startswith("[Type]")]
    assert any('"Chaos Orb"' in l for l in active)   # not commented out despite tiny value


def test_build_category_lines_waystones_ignores_payload():
    lines = asm.build_category_lines("waystones", False, {}, 1.0, 0.0, 5.0, None)
    assert lines == gen.build_waystone_lines()


def test_price_alerts_record_uniques_not_just_items_table_categories():
    """Unique payloads ship items: [] and carry the name on the LINE — the same
    reason build_unique_lines reads the line directly. compute_price_alerts
    required an items-table entry, so all 7 unique categories recorded ZERO
    prices: Mageblood could double and Top movers stayed empty, permanently,
    because the persisted baseline was empty too."""
    cats = [("unique_armours", None, "Unique Armours", True)]
    payloads = {"unique_armours": {
        "core": {"rates": {"exalted": 100.0}},
        "items": [],                                  # uniques have no items table
        "lines": [{"name": "Some Unique", "baseType": "Silk Robe", "primaryValue": 2.0}],
    }}
    prices, _alerts = asm.compute_price_alerts(cats, payloads, {}, 1.0, 0.2)
    assert prices["unique_armours"] == {"Some Unique": 200.0}


def test_price_alerts_fire_for_a_unique_that_moved():
    """With a baseline recorded, a real move must now produce an alert."""
    cats = [("unique_armours", None, "Unique Armours", True)]
    payloads = {"unique_armours": {
        "core": {"rates": {"exalted": 100.0}},
        "items": [],
        "lines": [{"name": "Some Unique", "baseType": "Silk Robe", "primaryValue": 4.0}],
    }}
    prev = {"unique_armours": {"Some Unique": 200.0}}      # doubled to 400
    _prices, alerts = asm.compute_price_alerts(cats, payloads, prev, 1.0, 0.2)
    assert any("Some Unique" in text for _sort, text in alerts), alerts


def test_a_unique_priced_on_several_bases_keeps_its_highest_price():
    """poe.ninja prices a unique once per base it rolls on, so the same name
    repeats. Iteration order must not decide which price represents it."""
    cats = [("unique_armours", None, "Unique Armours", True)]
    payloads = {"unique_armours": {
        "core": {"rates": {"exalted": 1.0}},
        "items": [],
        "lines": [{"name": "Two Base Unique", "baseType": "A", "primaryValue": 5.0},
                  {"name": "Two Base Unique", "baseType": "B", "primaryValue": 50.0}],
    }}
    prices, _ = asm.compute_price_alerts(cats, payloads, {}, 1.0, 0.2)
    assert prices["unique_armours"]["Two Base Unique"] == 50.0
