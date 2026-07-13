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





# ── Item Check ────────────────────────────────────────────────────────────────

UNIQUE_TXT = """Item Class: Two Hand Swords
Rarity: Unique
Big Sword
Some Base
--------
Requirements:
Level: 65
--------
Item Level: 82
--------
+50 to maximum Life
"""

CHEAP_ESSENCE = """Item Class: Stackable Currency
Rarity: Currency
Essence of Haste
--------
Stack Size: 2/10
"""


def test_item_text_parser_reads_item_level_after_the_first_separator():
    """PoE2 puts 'Item Level:' in a block *after* the first '--------', so a parser
    that stops at that separator never sees it. Guards the original bug."""
    it = webapi.AppApi._parse_item_text(UNIQUE_TXT)
    assert it["name"] == "Big Sword"          # display name
    assert it["base"] == "Some Base"          # base is the second name line
    assert it["class"] == "Two Hand Swords"
    assert it["rarity"] == "Unique"
    assert it["ilvl"] == 82                   # <- the bug: this used to be None


def test_item_check_picks_a_unique_above_the_floor_and_shows_the_real_rule(api):
    api.cfg["min_exalt_unique"] = 6.0
    r = api.check_item(UNIQUE_TXT, "L")
    assert r["verdict"] == "pick", r
    # the verdict is the pickit itself: it hands back the actual .ipd line
    assert r["rule"] and "Big Sword" in r["rule"] and "[StashItem]" in r["rule"]


def test_item_check_explains_a_unique_that_misses_the_floor(api):
    api.cfg["min_exalt_unique"] = 5000.0      # Big Sword is 900
    r = api.check_item(UNIQUE_TXT, "L")
    assert r["verdict"] == "ignore"
    row = next(x for x in r["rows"] if x["kind"] == "ignore")
    assert "900" in row["detail"] and "5000" in row["detail"]
    assert row["fix"]                          # tells the user how to make it pick


def test_item_check_never_claims_the_floor_applied_when_it_did_not(api):
    """Currency is a PICK_ALL category — every item is taken whatever it is worth.
    Reporting 'it clears your floor' for a 1 ex orb under a 50 ex floor would be a
    lie even though the PICK verdict is right."""
    api.cfg["min_exalt_gear"] = 50.0
    r = api.check_item("Item Class: Stackable Currency\nRarity: Currency\nExalted Orb\n--------\n", "L")
    assert r["verdict"] == "pick"
    detail = r["rows"][0]["detail"]
    assert "at or above" not in detail
    assert "does not apply" in detail or "whatever the price" in detail


def test_item_check_below_floor_in_a_normal_category_is_ignored(api):
    api.cfg["min_exalt_gear"] = 5.0            # Essence of Haste is 0.4
    r = api.check_item(CHEAP_ESSENCE, "L")
    assert r["verdict"] == "ignore"
    assert any("0.4" in x["detail"] for x in r["rows"])


def test_item_check_without_a_league_does_not_claim_nothing_matches(api):
    """No league means the poe.ninja half never ran. Saying 'no rule matches' would
    report a conclusion we never actually checked."""
    r = api.check_item(UNIQUE_TXT, "")
    assert r["verdict"] != "none"
    assert any("league" in x["detail"].lower() for x in r["rows"])


def test_item_check_rare_on_an_uncovered_base_is_a_definitive_no(api):
    api.cfg["rare_gear_enabled"] = True
    r = api.check_item("Item Class: Boots\nRarity: Rare\nWidow Grasp\nNot A Real Base\n"
                       "--------\nItem Level: 81\n", "L")
    row = next(x for x in r["rows"] if x["rule"].startswith("Rare gear"))
    assert row["kind"] == "ignore" and "never picked up" in row["detail"]


def test_item_check_only_mentions_fracture_for_a_fractured_item(api):
    plain = api.check_item("Item Class: Wands\nRarity: Rare\nX\nAttuned Wand\n"
                           "--------\nItem Level: 80\n", "L")
    assert not any(x["rule"] == "Fracture" for x in plain["rows"])
    frac = api.check_item("Item Class: Wands\nRarity: Rare\nX\nAttuned Wand\n--------\n"
                          "Item Level: 80\n--------\nFractured Item\n+45 to Spirit (fractured)\n", "L")
    assert any(x["rule"] == "Fracture" for x in frac["rows"])


def test_item_check_rejects_text_that_is_not_an_item(api):
    assert api.check_item("hello world", "L").get("error")


def test_item_check_fracture_targets_are_renderable_strings(api):
    """fracture_targets_for_class returns rich dicts; handing them to the UI raw
    rendered as '[object Object]'. Each target must carry plain tier/text strings."""
    r = api.check_item("Item Class: Wands\nRarity: Rare\nX\nAttuned Wand\n--------\n"
                       "Item Level: 80\n--------\nFractured Item\n+45 to Spirit (fractured)\n", "L")
    row = next(x for x in r["rows"] if x["rule"] == "Fracture")
    assert row["targets"]
    for t in row["targets"]:
        assert isinstance(t["tier"], str) and isinstance(t["text"], str)
        assert t["text"] and "object" not in t["text"]
