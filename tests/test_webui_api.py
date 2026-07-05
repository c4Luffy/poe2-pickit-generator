"""Tests for the modern-UI bridge (webui/api.py) with mocked poe.ninja data."""

import os

import pytest

from exilebot_pickit import generator as gen
from exilebot_pickit.webui import api as webapi


def _payload(names_values, unique=False):
    """Minimal poe.ninja-shaped payload. exalted rate = 1 so values pass through."""
    if unique:
        return {"core": {"rates": {"exalted": 1.0}},
                "lines": [{"name": n, "baseType": "Some Base", "primaryValue": v,
                           "icon": "https://x/i.png"} for n, v in names_values]}
    return {"core": {"rates": {"exalted": 1.0}},
            "items": [{"id": n, "name": n, "image": "/img.png"} for n, _ in names_values],
            "lines": [{"id": n, "primaryValue": v} for n, v in names_values]}


FAKE = {
    "currency": _payload([("Divine Orb", 700), ("Exalted Orb", 1), ("Chaos Orb", 85)]),
    "essences": _payload([("Essence of Battle", 12), ("Essence of Haste", 0.4)]),
    "unique_weapons": _payload([("Big Sword", 900), ("Cheap Stick", 2)], unique=True),
}


@pytest.fixture
def api(tmp_path, monkeypatch):
    def fake_fetch(league, categories, **kw):
        return {k: FAKE.get(k, _payload([])) for k, *_ in [c for c in categories]}
    monkeypatch.setattr(gen, "fetch_all_payloads", fake_fetch)
    monkeypatch.setattr(webapi.gen, "fetch_all_payloads", fake_fetch)
    monkeypatch.setattr(webapi, "OUTPUT_DIR", str(tmp_path))
    a = webapi.AppApi.__new__(webapi.AppApi)   # skip __init__ network/prune work
    import threading
    a._lock = threading.Lock()
    a._status = {"running": False, "log": [], "done": None}
    a._last_lines = []
    a.cfg = {"output_base": "t", "history": [], "item_states": {},
             "category_enabled": {}, "backup_count": 0}
    monkeypatch.setattr(webapi, "save_config", lambda cfg: None)
    return a


def test_suggest_floors_counts(api):
    r = api.suggest_floors("L", 40)
    # currency is a pick-all category, so only the 2 essences count as "gear"
    assert r["total_unique"] == 2 and r["total_gear"] == 2
    assert r["kept_unique"] <= r["total_unique"]
    assert r["unique"] > 0 and r["gear"] > 0


def test_generate_writes_files_and_history(api, tmp_path):
    api._generate("L", 5, 20)
    d = api._status["done"]
    assert d and d["ok"], d
    assert os.path.isfile(os.path.join(str(tmp_path), "t.ipd"))
    assert os.path.isfile(os.path.join(str(tmp_path), "t.filter"))
    assert api.cfg["history"], "history entry missing"
    assert d["active"] > 0 and d["safety"] == ""


def test_safety_net_blocks_on_rule_collapse(api):
    # Previous run claims 10x the rules this data can produce.
    api.cfg["history"] = [{"active": 100000}]
    api.cfg["auto_copy"] = True
    api.cfg["bot_folder"] = "C:\\definitely\\missing"
    api._generate("L", 5, 20)
    d = api._status["done"]
    assert d["ok"] and "collapsed" in d["safety"]
    assert d["copied"] == ""    # auto-copy blocked


def test_economy_shape(api):
    r = api.economy("L")
    assert "cats" in r and r["divine_rate"] == 700
    cur = next(c for c in r["cats"] if c["key"] == "currency")
    assert cur["items"][0]["icon"].startswith("https://web.poecdn.com")


def test_league_start_preset(api):
    api.cfg["min_exalt_gear"] = 50
    r = api.league_start_preset()
    assert r["ok"] and api.cfg["min_exalt_gear"] == 0.0
    assert all(api.cfg["category_enabled"].values())


def test_league_start_restore_roundtrip(api):
    api.cfg["min_exalt_gear"] = 42.0
    api.cfg["min_exalt_unique"] = 7.0
    api.cfg["category_enabled"] = {"essences": False}
    api.league_start_preset()
    assert api.cfg["min_exalt_gear"] == 0.0
    assert api.league_start_active()["active"]
    r = api.league_start_restore()
    assert r["ok"] and api.cfg["min_exalt_gear"] == 42.0
    assert api.cfg["category_enabled"] == {"essences": False}
    assert not api.league_start_active()["active"]


def test_rare_item_rules_generation(api, tmp_path):
    api.cfg["include_rares"] = True
    api.cfg["rare_slots"] = {"Rings": True, "Amulets": False, "Belts": False}
    api.cfg["rare_min_ilvl"] = 78
    api._generate("L", 5, 20)
    d = api._status["done"]
    assert d and d["ok"], d
    content = open(os.path.join(str(tmp_path), "t.ipd"), encoding="utf-8").read()
    assert '[Type] == "Gold Ring" && [Rarity] == "Rare" # [ItemLevel] >= "78"' in content
    assert 'Amulet" && [Rarity] == "Rare"' not in content
    assert "RARE ITEMS" in content


def test_rare_slots_api(api):
    slots = api.rare_slots()
    assert {s["slot"] for s in slots} >= {"Rings", "Amulets", "Belts", "Gloves"}
    assert next(s for s in slots if s["slot"] == "Rings")["enabled"]
    assert not next(s for s in slots if s["slot"] == "Boots")["enabled"]
    assert api.set_rare_slot("Boots", True)["ok"]
    assert next(s for s in api.rare_slots() if s["slot"] == "Boots")["enabled"]
    assert "error" in api.set_rare_slot("Wings", True)
