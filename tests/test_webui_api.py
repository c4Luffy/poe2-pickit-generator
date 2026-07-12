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


def test_presets_are_well_formed():
    """Every preset must carry the copy the UI renders (name/tag/picks/floors/cost)
    and a strictness the meter can actually draw."""
    from exilebot_pickit.ui.config import PRESETS
    assert PRESETS, "no presets defined"
    for p in PRESETS:
        for k in ("key", "name", "icon", "strict", "tag", "picks", "floors", "cost", "cfg"):
            assert p.get(k) not in (None, ""), f"preset {p.get('key')!r} is missing {k}"
        assert 1 <= p["strict"] <= 4, f"{p['key']}: strictness must be 1-4"
        assert p["cfg"].get("min_exalt_gear") is not None


def test_apply_preset_sets_floors_and_marks_it_active(api):
    # read the expected floors from the preset itself, so tuning the numbers
    # doesn't break the test — this guards the mechanism, not the values
    from exilebot_pickit.ui.config import PRESETS
    p = next(x for x in PRESETS if x["key"] == "strict")
    r = api.apply_preset("strict")
    assert r["ok"]
    assert api.cfg["min_exalt_gear"] == p["cfg"]["min_exalt_gear"]
    assert api.cfg["min_exalt_unique"] == p["cfg"]["min_exalt_unique"]
    assert api.cfg["min_exalt"] == p["cfg"]["min_exalt_gear"]   # legacy mirror
    assert api.cfg["active_preset"] == "strict"


def test_preset_floors_rise_with_strictness():
    """A stricter preset must never have a LOWER floor than a looser one, or the
    strictness meter is lying to the user. Guards future floor tuning."""
    from exilebot_pickit.ui.config import PRESETS
    ladder = sorted((p for p in PRESETS
                     if p["key"] in ("vacuum", "balanced", "strict", "chase")),
                    key=lambda p: p["strict"])
    gears = [p["cfg"]["min_exalt_gear"] for p in ladder]
    uniqs = [p["cfg"]["min_exalt_unique"] for p in ladder]
    assert gears == sorted(gears), f"currency floors not ascending with strictness: {gears}"
    assert uniqs == sorted(uniqs), f"unique floors not ascending with strictness: {uniqs}"


def test_hand_editing_a_floor_clears_the_active_preset(api):
    """The UI must never claim a preset is active once its numbers were overridden."""
    api.apply_preset("balanced")
    assert api.cfg["active_preset"] == "balanced"
    api.set_setting("min_exalt_gear", 42)
    assert api.cfg["active_preset"] == ""


def test_currency_preset_switches_uniques_off_and_back(api):
    api.apply_preset("currency")
    ce = api.cfg["category_enabled"]
    uniq = [k for k in ce if k.startswith("unique_")]
    assert uniq, "no unique categories were touched"
    assert all(ce[k] is False for k in uniq)
    assert api.cfg["rare_gear_enabled"] is False
    # any other preset must put the unique categories back on
    api.apply_preset("balanced")
    ce = api.cfg["category_enabled"]
    assert all(ce[k] is True for k in ce if k.startswith("unique_"))
    assert api.cfg["rare_gear_enabled"] is True


def test_apply_unknown_preset_is_rejected(api):
    r = api.apply_preset("nope")
    assert not r["ok"] and "unknown" in r["error"]


def test_detect_bot_folder_finds_confirmed_install(api, tmp_path, monkeypatch):
    """A Pickit folder with pickit.ini beside it (a real bot install) under a
    scanned root is found."""
    home = tmp_path / "home"
    pickit = home / "Desktop" / "ExiledBot2" / "Configuration" / "default" / "Pickit"
    pickit.mkdir(parents=True)
    (pickit.parent / "pickit.ini").write_text("active_profile=poe2_pickit\n")
    monkeypatch.setattr(os.path, "expanduser",
                        lambda p: str(home) if p == "~" else p)
    r = api.detect_bot_folder()
    assert r["found"]
    assert os.path.normpath(str(pickit)) in r["all"]


def test_detect_bot_folder_ignores_pickit_without_ini(api, tmp_path, monkeypatch):
    """A bare Pickit folder with NO pickit.ini beside it is NOT a bot install and
    must never be offered — the guard against false positives."""
    home = tmp_path / "home2"
    pickit = home / "Desktop" / "NotABot" / "Configuration" / "default" / "Pickit"
    pickit.mkdir(parents=True)
    monkeypatch.setattr(os.path, "expanduser",
                        lambda p: str(home) if p == "~" else p)
    r = api.detect_bot_folder()
    assert os.path.normpath(str(pickit)) not in r["all"]



