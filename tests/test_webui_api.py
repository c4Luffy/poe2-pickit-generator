"""Tests for the modern-UI bridge (webui/api.py) with mocked poe.ninja data."""

import os
import re
import threading

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


def test_every_example_round_trips_through_the_checker(api):
    """The 'Try an example' button is only useful if the item it hands back is one the
    checker can actually read. Build a pile of them and feed each straight back in."""
    api.cfg["min_exalt_unique"] = 1.0
    for _ in range(40):
        ex = api.example_item("L")
        assert ex.get("ok"), ex
        assert ex["kind"] in {"unique", "rare", "fractured"}
        back = api.check_item(ex["text"], "L")
        assert not back.get("error"), (ex, back)
        assert back["verdict"] in {"pick", "ignore", "depends"}
        assert back["item"]["base"], ex["text"]      # a base name was parsed out


def test_example_covers_uniques_rares_and_fractured_items(api):
    """One kind of example only ever teaches one kind of verdict."""
    kinds = {api.example_item("L")["kind"] for _ in range(60)}
    assert kinds == {"unique", "rare", "fractured"}, kinds


def test_a_fractured_example_is_actually_fractured(api):
    for _ in range(60):
        ex = api.example_item("L")
        if ex["kind"] != "fractured":
            continue
        assert "Fractured Item" in ex["text"] and "(fractured)" in ex["text"]
        r = api.check_item(ex["text"], "L")
        assert any(x["rule"] == "Fracture" for x in r["rows"]), r
        return
    raise AssertionError("never rolled a fractured example")


def test_example_mods_show_a_roll_not_a_range(api):
    """Our target text states the mod's range ('20-45%'); a real item shows one roll."""
    mods = webapi.AppApi._mods_for_class("Wands", 5)
    assert mods
    for m in mods:
        assert not re.search(r"\d-\d", m), m


def test_example_still_works_without_a_league(api):
    """Rare and fractured examples are built from bundled game data, so they work with
    no league and no network. Only a unique example needs live prices."""
    kinds = {api.example_item("")["kind"] for _ in range(40)}
    assert kinds == {"rare", "fractured"}, kinds


def test_prices_are_readable_at_both_ends_of_the_scale():
    """Prices run from 0.05 ex to millions. '2483040.00 ex' reads like a bug."""
    assert webapi.AppApi._ex(0.05) == "0.05"
    assert webapi.AppApi._ex(6.2) == "6.20"
    assert webapi.AppApi._ex(2483040.0) == "2,483,040"


def test_example_item_mod_text_is_game_shaped(api):
    """poe.ninja writes '[EnergyShield|Energy Shield]' over a range; the game shows the
    display name and a rolled number."""
    line = {"name": "N", "baseType": "B", "category": "Body Armour", "levelRequired": 64,
            "explicitModifiers": [{"text": "+(100-150) to maximum [EnergyShield|Energy Shield]"},
                                  {"text": "Skills have -(2-1.09) seconds to [Cooldown]"}]}
    t = webapi.AppApi._as_item_text(line)
    assert "+125 to maximum Energy Shield" in t
    assert "[" not in t and "]" not in t and "(100-150)" not in t


def test_price_shows_exalt_divine_and_chaos(api):
    """People price things in different units. Divine = 700 ex and Chaos = 85 ex in
    the fixture, so Big Sword (900 ex) is ~1.3 div / ~10.6 chaos."""
    api.cfg["min_exalt_unique"] = 6.0
    r = api.check_item(UNIQUE_TXT, "L")
    detail = next(x for x in r["rows"] if x["kind"] == "pick")["detail"]
    assert "900.00 ex" in detail and "div" in detail and "chaos" in detail


def test_price_hides_units_that_would_round_to_noise(api):
    """A 0.4 ex essence is 0.0006 div — printing '0.00 div' tells nobody anything."""
    api.cfg["min_exalt_gear"] = 0.0
    r = api.check_item(CHEAP_ESSENCE, "L")
    detail = r["rows"][0]["detail"]
    assert "0.40 ex" in detail and "div" not in detail


def test_example_unique_is_not_always_the_same_one(api):
    """It used to hand back the single priciest unique every time."""
    names = {api.example_item("L")["name"] for _ in range(80)}
    assert {"Big Sword", "Cheap Stick"} <= names, names


# ── Self-update (the exe swap) ────────────────────────────────────────────────

def test_update_helper_does_not_leak_pyinstaller_env_to_the_new_exe(api, tmp_path, monkeypatch):
    r"""A one-file exe unpacks to %TEMP%\_MEIxxxxxx and exports that path. If the update
    helper inherits it, the NEW exe assumes it is a child of the old one, skips
    unpacking, and reads from a folder the dying old process already deleted:
        FileNotFoundError: ...\_MEI599002\base_library.zip
    A real user hit exactly that. Both the spawned env and the .bat must clear it."""
    import subprocess
    import sys as _sys

    new_exe = tmp_path / "new.exe"
    new_exe.write_bytes(b"MZ")
    api._dl = {"result": {"ok": True, "path": str(new_exe)}}
    monkeypatch.setattr(_sys, "frozen", True, raising=False)
    monkeypatch.setattr(_sys, "executable", str(tmp_path / "cur.exe"), raising=False)
    monkeypatch.setenv("_MEIPASS2", r"C:\Temp\_MEI599002")
    monkeypatch.setenv("_PYI_APPLICATION_HOME_DIR", r"C:\Temp\_MEI599002")

    seen = {}

    def fake_popen(cmd, **kw):
        seen["env"] = kw.get("env")
        seen["bat"] = cmd[-1]
        return object()

    monkeypatch.setattr(subprocess, "Popen", fake_popen)
    monkeypatch.setattr(threading, "Thread", lambda *a, **k: type(
        "T", (), {"start": lambda self: None})())

    assert api.install_update().get("ok"), "installer refused to start"

    env = seen["env"]
    assert env is not None, "Popen inherited the whole environment"
    leaked = [k for k in env if k.startswith(("_MEIPASS", "_PYI"))]
    assert not leaked, f"PyInstaller vars leaked to the update helper: {leaked}"

    script = open(seen["bat"], encoding="ascii").read()
    for var in ("_MEIPASS2", "_PYI_ARCHIVE_FILE",
                "_PYI_APPLICATION_HOME_DIR", "_PYI_PARENT_PROCESS_LEVEL"):
        assert f'set "{var}="' in script, f"{var} not cleared inside the .bat"


def test_clean_env_keeps_everything_else(monkeypatch):
    monkeypatch.setenv("_MEIPASS2", "x")
    monkeypatch.setenv("PATH", "keepme")
    env = webapi.AppApi._clean_env()
    assert "_MEIPASS2" not in env
    assert env.get("PATH") == "keepme"


# ── Floor display units ───────────────────────────────────────────────────────

def test_floor_display_unit_is_remembered(api):
    """The floor is stored in EXALT, which is right. But the chosen display UNIT was
    never saved — so a user who set "Chaos 1" reopened the app to "60.57176 Exalt".
    Same floor, but it reads exactly like the setting was thrown away."""
    api.set_setting("min_exalt_unique", 60.57176)     # == 1 chaos at the time
    api.set_setting("floor_unit_unique", "Chaos")
    assert api.cfg["floor_unit_unique"] == "Chaos"

    i = api.app_info()
    assert i["min_unique"] == 60.57176                # the floor itself is untouched
    assert i["floor_unit_unique"] == "Chaos"          # and the UI knows to show chaos


def test_floor_unit_defaults_to_exalt(api):
    i = api.app_info()
    assert i["floor_unit_unique"] == "Exalt"
    assert i["floor_unit_gear"] == "Exalt"


def test_floor_units_are_in_the_settings_allowlist():
    """set_setting silently drops keys that aren't allowed — the unit would never persist."""
    assert "floor_unit_unique" in webapi._SETTABLE
    assert "floor_unit_gear" in webapi._SETTABLE


def test_base_min_level_can_be_set_to_79(api):
    """The UI used to hard-clamp the exceptional-base item level to 80-82, so 79 was
    unreachable. An ilvl-79 base can still roll the extra rune socket, and those sell —
    a 79 Sacred Focus with two sockets goes for real money."""
    api.set_setting("base_min_level", 79)
    assert api.cfg["base_min_level"] == 79
    assert api.app_info()["base_min_level"] == 79
    assert api._snapshot()["base_min_level"] == 79      # and it reaches the generator


# ── What's new (post-update) ──────────────────────────────────────────────────

def test_whats_new_shows_once_after_an_update(api):
    """The app told you what an update contained BEFORE you installed it, then never
    mentioned it again — so people landed on a new version with no idea what changed."""
    from exilebot_pickit.version import VERSION
    api.cfg["league"] = "L"                       # an existing user, not a fresh install
    api.cfg["pending_version"] = VERSION          # notes cached at download time
    api.cfg["pending_notes"] = "## Fixed\nthe thing"

    r = api.whats_new()
    assert r["show"] is True
    assert r["version"] == VERSION
    assert "the thing" in r["notes"]              # served from cache: works offline

    api.mark_whats_new_seen()
    assert api.whats_new()["show"] is False       # and never again for this version


def test_whats_new_does_not_greet_a_brand_new_user(api):
    """A first-time user has nothing to catch up on. Opening the app with a changelog
    in their face is noise, not a welcome."""
    api.cfg.pop("league", None)
    api.cfg["history"] = []
    assert api.whats_new()["show"] is False
    from exilebot_pickit.version import VERSION
    assert api.cfg["last_seen_version"] == VERSION   # silently marked, so no nag later


def test_whats_new_survives_no_network(api, monkeypatch):
    """No cached notes and GitHub unreachable: still announce the version rather than
    blowing up or showing nothing."""
    api.cfg["league"] = "L"
    api.cfg["pending_version"] = ""
    import requests
    monkeypatch.setattr(requests, "get",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    r = api.whats_new()
    assert r["show"] is True and r["notes"] == "" and r["url"].endswith(
        api.app_info()["version"])


# ── Clipboard (Item Check auto-paste) ─────────────────────────────────────────

def test_get_clipboard_round_trips_with_copy_text(api):
    """Item Check auto-pastes from the clipboard, so get_clipboard must read back
    exactly what copy_text wrote. On non-Windows (CI runs the suite on ubuntu) both
    sides degrade gracefully instead of raising — auto-paste is best-effort."""
    item = "Item Class: Belts\nRarity: Unique\nHeadhunter\nLeather Belt"
    wrote = api.copy_text(item)
    r = api.get_clipboard()
    assert isinstance(r, dict) and isinstance(r.get("text"), str)
    if wrote.get("ok"):                        # real Windows clipboard available
        assert r["text"] == item
    else:                                      # no clipboard here — never an exception
        assert r["text"] == ""


def test_whats_new_force_reopens_seen_notes_without_marking(api):
    """Clicking the version number re-opens the notes even after they were dismissed —
    and reading them on demand must not touch the seen-state."""
    from exilebot_pickit.version import VERSION
    api.cfg["league"] = "L"
    api.cfg["last_seen_version"] = VERSION          # already seen -> normal path hides
    api.cfg["pending_version"] = VERSION
    api.cfg["pending_notes"] = "## the notes"
    assert api.whats_new()["show"] is False
    r = api.whats_new(True)
    assert r["show"] is True and r["version"] == VERSION and "the notes" in r["notes"]
    assert api.cfg["last_seen_version"] == VERSION  # untouched
