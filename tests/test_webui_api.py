"""Tests for the modern-UI bridge (webui/api.py) with mocked poe.ninja data."""

import copy
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
    # save_config now REPORTS success (bool). A stub returning None reads as a
    # failed save, which is exactly what the bridge must now surface.
    monkeypatch.setattr(webapi, "save_config", lambda cfg: True)
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


def test_no_active_rule_is_typeless(tmp_path, monkeypatch):
    """Catastrophe guard. Exiled Bot treats a rule with no
    [Type]/[Category]/[WeaponCategory] condition as 'grab EVERYTHING on the
    ground' — the single worst thing this app can ship (CLAUDE.md calls it out
    as load-bearing). Feed *every* category real data so every rule builder
    runs, generate a full .ipd, and assert not one active (uncommented,
    [StashItem]) line is type-less."""
    def _cur(nv):
        return {"core": {"rates": {"exalted": 1.0}},
                "items": [{"id": n, "name": n, "image": "/i.png"} for n, _ in nv],
                "lines": [{"id": n, "primaryValue": v} for n, v in nv]}
    def _uni(nv):
        return {"core": {"rates": {"exalted": 1.0}},
                "lines": [{"name": n, "baseType": "Some Base", "primaryValue": v,
                           "icon": "https://x/i.png"} for n, v in nv]}

    def fake_fetch(league, categories, **kw):
        out = {}
        for tup in categories:
            key, is_unique = tup[0], (tup[3] if len(tup) > 3 else False)
            out[key] = (_uni([("Alpha Item", 900), ("Cheap Item", 2)]) if is_unique
                        else _cur([("Big Thing", 900), ("Small Thing", 3)]))
        return out

    monkeypatch.setattr(gen, "fetch_all_payloads", fake_fetch)
    monkeypatch.setattr(webapi.gen, "fetch_all_payloads", fake_fetch)
    monkeypatch.setattr(webapi, "OUTPUT_DIR", str(tmp_path))
    # save_config now REPORTS success (bool). A stub returning None reads as a
    # failed save, which is exactly what the bridge must now surface.
    monkeypatch.setattr(webapi, "save_config", lambda cfg: True)

    a = webapi.AppApi.__new__(webapi.AppApi)
    a._lock = threading.Lock()
    a._status = {"running": False, "log": [], "done": None}
    a._last_lines = []
    a.cfg = {"output_base": "t", "history": [], "item_states": {},
             "category_enabled": {}, "backup_count": 0}
    a._generate("L", 1, 1)                       # floors of 1 keep the most rules
    assert a._status["done"]["ok"], a._status["done"]

    lines = (tmp_path / "t.ipd").read_text(encoding="utf-8").splitlines()
    typed = ("[Type] ==", "[Category] ==", "[WeaponCategory] ==")
    offenders = [l for l in lines
                 if l.strip() and not l.lstrip().startswith("//")
                 and "[StashItem]" in l and not l.lstrip().startswith(typed)]
    assert not offenders, (
        f"{len(offenders)} type-less active rule(s) would vacuum up ALL ground "
        "loot:\n" + "\n".join(offenders[:10]))
    assert len(lines) > 100                      # sanity: a full pickit was written


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


# ── Floors ────────────────────────────────────────────────────────────────────

def test_floors_are_plain_exalt(api):
    """Floors are stored and shown in exalt only — the Chaos/Divine display dropdown was
    removed (it was a bug factory: the 58x preset bug, the "60.57176" display bug, the
    convert-vs-reinterpret confusion). The stored value is the exalt floor, full stop."""
    api.set_setting("min_exalt_unique", 6.0)
    api.set_setting("min_exalt_gear", 2.0)
    i = api.app_info()
    assert i["min_unique"] == 6.0 and i["min_gear"] == 2.0
    # the dead display-unit keys must not come back
    assert "floor_unit_unique" not in i and "floor_unit_gear" not in i
    assert "floor_unit_unique" not in webapi._SETTABLE


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


def test_whats_new_ignores_a_bare_auto_generated_changelog_link(api):
    """v4.38.1 was published before its notes were attached, so GitHub filled the
    body with a lone compare link — and the dialog dutifully showed a version
    heading and one URL, telling the reader nothing. A body with no prose in it
    loses to the highlights bundled in the exe."""
    from exilebot_pickit.version import HIGHLIGHTS, VERSION
    api.cfg["league"] = "L"
    api.cfg["pending_version"] = VERSION
    api.cfg["pending_notes"] = (
        "**Full Changelog**: https://github.com/c4Luffy/poe2-pickit-generator"
        "/compare/v4.38.0...v4.38.1")

    r = api.whats_new()
    assert r["show"] is True
    assert r["notes"] == HIGHLIGHTS


def test_whats_new_keeps_real_notes_that_also_link_the_changelog(api):
    """The guard must not throw away GENUINE notes just because they end with the
    same Full Changelog line — every real release body has one."""
    from exilebot_pickit.version import VERSION
    api.cfg["league"] = "L"
    api.cfg["pending_version"] = VERSION
    api.cfg["pending_notes"] = (
        "## Exceptional tab uses its full width\n\n"
        "- Shields and Foci no longer render into a third of the page.\n\n"
        "**Full Changelog**: https://github.com/c4Luffy/poe2-pickit-generator"
        "/compare/v4.38.0...v4.38.1")

    assert "Shields and Foci" in api.whats_new()["notes"]


def test_whats_new_survives_no_network(api, monkeypatch):
    """No cached notes and GitHub unreachable: the dialog still shows the REAL
    highlights — they ship inside the exe (version.HIGHLIGHTS) precisely so an
    offline or GitHub-less launch never degrades to an empty announcement."""
    api.cfg["league"] = "L"
    api.cfg["pending_version"] = ""
    import requests
    monkeypatch.setattr(requests, "get",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("offline")))
    r = api.whats_new()
    from exilebot_pickit.version import HIGHLIGHTS
    assert r["show"] is True and r["notes"] == HIGHLIGHTS
    assert r["url"].endswith(api.app_info()["version"])


# ── Clipboard (Item Check auto-paste) ─────────────────────────────────────────

def test_get_clipboard_round_trips_with_copy_text(api):
    """Item Check auto-pastes from the clipboard, so get_clipboard must read back
    exactly what copy_text wrote. On non-Windows (CI runs the suite on ubuntu) both
    sides degrade gracefully instead of raising — auto-paste is best-effort.

    The clipboard is process-wide OS state, so another app can hold it for an instant
    OR overwrite it between our write and our read — both are transient OS conditions,
    not bugs. So retry the whole round-trip: any attempt that reads back exactly proves
    the code works. A real bug fails *every* attempt, and still fails the assert below —
    the retry absorbs flakes without making the test vacuous."""
    import time
    item = "Item Class: Belts\nRarity: Unique\nHeadhunter\nLeather Belt"
    wrote = {}
    for _ in range(5):
        wrote = api.copy_text(item)
        if wrote.get("ok"):
            r = api.get_clipboard()
            assert isinstance(r, dict) and isinstance(r.get("text"), str)
            if r["text"] == item:
                return                         # round-tripped — the thing under test works
        time.sleep(0.1)                        # held/clobbered elsewhere — try again
    r = api.get_clipboard()
    assert isinstance(r, dict) and isinstance(r.get("text"), str)
    if wrote.get("ok"):                        # writes land but never read back → real bug
        assert r["text"] == item
    elif "busy" in str(wrote.get("error", "")):
        pytest.skip("clipboard held by another process — nothing to verify")
    else:                                      # no clipboard here (CI) — never an exception
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


# ── Economy sparklines ────────────────────────────────────────────────────────

def test_economy_exposes_the_sparkline_curve_not_just_the_percent(api, monkeypatch):
    """poe.ninja sends a 7-day curve per unique; we only ever read totalChange and
    threw the shape away. The Economy rows now carry it so they can draw a trend."""
    payload = {"core": {"rates": {"exalted": 1.0}},
               "lines": [{"name": "Big Sword", "baseType": "B", "primaryValue": 900,
                          "sparkLine": {"totalChange": -8.28,
                                        "data": [0, -0.68, -4.27, -11.25, -8.28]}}]}

    def fake(league, categories, **kw):
        return {k: (payload if k == "unique_weapons" else
                    {"core": {"rates": {"exalted": 1.0}}, "items": [], "lines": []})
                for k, *_ in categories}
    monkeypatch.setattr(webapi.gen, "fetch_all_payloads", fake)

    cat = next(c for c in api.economy("L")["cats"] if c["key"] == "unique_weapons")
    it = cat["items"][0]
    assert it["chg"] == -8.3                      # the % stays rounded to 1dp
    assert it["spark"] == [0.0, -0.68, -4.27, -11.25, -8.28]


def test_sparkline_is_dropped_when_it_cannot_be_drawn(api, monkeypatch):
    """poe.ninja emits nulls, and one point is not a line. Both must come back None
    rather than a stub the renderer would have to guess at."""
    def mk(data):
        return {"core": {"rates": {"exalted": 1.0}},
                "lines": [{"name": "Big Sword", "baseType": "B", "primaryValue": 9,
                           "sparkLine": {"totalChange": 1, "data": data}}]}

    for data in ([5], [None, None], [], None):
        monkeypatch.setattr(webapi.gen, "fetch_all_payloads",
                            lambda lg, cats, _d=data, **kw: {
                                k: (mk(_d) if k == "unique_weapons" else
                                    {"core": {"rates": {"exalted": 1.0}},
                                     "items": [], "lines": []})
                                for k, *_ in cats})
        cat = next(c for c in api.economy("L")["cats"] if c["key"] == "unique_weapons")
        assert cat["items"][0]["spark"] is None, data

    # nulls mixed with real points: keep the real ones
    monkeypatch.setattr(webapi.gen, "fetch_all_payloads",
                        lambda lg, cats, **kw: {
                            k: (mk([0, None, 4, 6]) if k == "unique_weapons" else
                                {"core": {"rates": {"exalted": 1.0}},
                                 "items": [], "lines": []})
                            for k, *_ in cats})
    cat = next(c for c in api.economy("L")["cats"] if c["key"] == "unique_weapons")
    assert cat["items"][0]["spark"] == [0.0, 4.0, 6.0]


# ── First-run wizard ──────────────────────────────────────────────────────────

def test_wizard_signal_is_have_you_ever_generated(api):
    """A brand-new user is one who has never GENERATED. league is auto-saved the moment
    the list loads (v4.25.0) and bot_folder is auto-detected on first run, so neither
    proves the user has ever actually used the app."""
    api.cfg["league"] = "Runes of Aldur"       # set automatically at launch
    api.cfg["bot_folder"] = r"D:\ExiledBot2"   # found automatically
    api.cfg["history"] = []
    i = api.app_info()
    assert i["setup_done"] is False and i["has_history"] is False   # -> still a newcomer

    api.cfg["history"] = [{"active": 1200}]    # they generated once
    assert api.app_info()["has_history"] is True                    # -> no wizard


def test_wizard_never_shows_twice(api):
    """Finishing OR skipping sets the flag — nobody gets nagged on every launch."""
    assert api.app_info()["setup_done"] is False
    api.set_setting("setup_done", True)
    assert api.cfg["setup_done"] is True
    assert api.app_info()["setup_done"] is True


def test_setup_done_is_a_settable_key():
    """set_setting silently drops keys off the allowlist — the flag would never persist
    and the wizard would greet the user forever."""
    assert "setup_done" in webapi._SETTABLE


def test_bot_connection_distinguishes_found_from_actually_connected(api, tmp_path):
    """The wizard's step 2 used to say "connected" because a folder path existed. It
    doesn't mean the bot reads your pickit: if pickit.ini's active_profile names another
    file, the bot silently ignores everything you generate — the step the Setup Guide
    calls "the one everybody misses". Same folder, two very different verdicts."""
    pickit = tmp_path / "Configuration" / "default" / "Pickit"
    pickit.mkdir(parents=True)
    ini = pickit.parent / "pickit.ini"
    api.cfg["bot_folder"] = str(pickit)
    api.cfg["output_base"] = "poe2_pickit"
    api.cfg["auto_copy"] = True

    ini.write_text("active_profile=someone_elses_filter\n")
    bad = api.bot_connection()
    assert bad["state"] == "mismatch", bad          # found, but NOT connected
    assert bad["detail"]

    ini.write_text("active_profile=poe2_pickit\n")
    good = api.bot_connection()
    assert good["state"] == "ok", good              # only now is it true


def test_import_pickit_bot_resolves_the_file_the_bot_actually_runs(api, tmp_path):
    """Create-your-filter's 'Use the bot's pickit' button: it must load exactly
    bot_folder/<active_profile>.ipd — the file bot_connection verifies — and
    fail with a plain-language reason at every gap (no folder, unreadable ini,
    profile file missing) instead of guessing."""
    assert "error" in api.import_pickit_bot()       # no bot folder set

    pickit = tmp_path / "Configuration" / "default" / "Pickit"
    pickit.mkdir(parents=True)
    api.cfg["bot_folder"] = str(pickit)
    assert "error" in api.import_pickit_bot()       # no pickit.ini yet

    (pickit.parent / "pickit.ini").write_text("active_profile=my_tuned_rules\n")
    r = api.import_pickit_bot()
    assert "error" in r and "my_tuned_rules.ipd" in r["error"]   # ini names a missing file

    (pickit / "my_tuned_rules.ipd").write_text(
        '[Type] == "Divine Orb" # [StashItem] == "true"\n')
    r = api.import_pickit_bot()
    assert r["profile"] == "my_tuned_rules"
    assert r["path"] == str(pickit / "my_tuned_rules.ipd")


def test_fix_bot_profile_repairs_the_mismatch(api, tmp_path):
    """The wizard offers "Fix it for me" on a mismatch — it has to actually work."""
    pickit = tmp_path / "Configuration" / "default" / "Pickit"
    pickit.mkdir(parents=True)
    ini = pickit.parent / "pickit.ini"
    ini.write_text("active_profile=wrong_name\nother_setting=1\n")
    api.cfg["bot_folder"] = str(pickit)
    api.cfg["output_base"] = "poe2_pickit"
    api.cfg["auto_copy"] = True

    assert api.bot_connection()["state"] == "mismatch"
    r = api.fix_bot_profile()
    assert r.get("ok"), r
    assert api.bot_connection()["state"] == "ok"
    assert "other_setting=1" in ini.read_text()     # never trample the bot's other keys


def test_wizard_fallback_preset_exists_and_has_a_real_floor(api):
    """A fresh install has NO floor (0 ex), so the wizard lands a beginner on Balanced
    rather than letting Next-Next-Next-Generate hand them a vacuum pickit. If this preset
    were renamed or its floors dropped to 0, that protection would silently vanish."""
    from exilebot_pickit.ui.config import PRESETS
    p = next((x for x in PRESETS if x["key"] == "balanced"), None)
    assert p, "the wizard falls back to 'balanced' by key — it's gone"
    assert p["cfg"]["min_exalt_gear"] > 0, "balanced must set a real floor"
    assert p["cfg"]["min_exalt_unique"] > 0

    api.cfg["min_exalt_gear"] = 0.0        # the fresh-install state
    api.cfg["min_exalt_unique"] = 0.0
    api.apply_preset("balanced")
    assert api.cfg["min_exalt_gear"] > 0 and api.cfg["min_exalt_unique"] > 0


def test_preset_floors_are_unit_agnostic_in_the_engine(api):
    """Guards the data half of the applyInfo/unit bug: whatever unit the UI shows, the
    engine stores and uses EXALT. applyInfo() used to drop the raw exalt number into the
    box while the unit select still said Chaos/Divine, so uEx() multiplied it back up —
    applying Balanced on a divine floor asked the bot for 2551 ex instead of 6. The JS
    fix rounds-trips through showFloor(); this pins the invariant it relies on."""
    from exilebot_pickit.ui.config import PRESETS
    for p in PRESETS:
        api.apply_preset(p["key"])
        assert api.cfg["min_exalt_gear"] == p["cfg"]["min_exalt_gear"]
        assert api.cfg["min_exalt_unique"] == p["cfg"]["min_exalt_unique"]
        # the unit is display-only and must never leak into the stored floor
        assert api.app_info()["min_gear"] == p["cfg"]["min_exalt_gear"]
        assert api.app_info()["min_unique"] == p["cfg"]["min_exalt_unique"]


def test_chaos_ex_also_returns_the_divine_rate(api):
    """The Generate tab needs both from one fetch: chaos for the reference line, divine
    for the floor slider's top. The divine rate used to arrive only after Economy or a
    generate, so the slider was stuck on its 100 ex fallback."""
    r = api.chaos_ex("L")
    assert r["ex"] == 85.0      # Chaos Orb, from the fixture currency payload
    assert r["div"] == 700.0    # Divine Orb — now returned too


def test_debug_digest_counts_js_errors_not_just_python(api, tmp_path, monkeypatch):
    """The Debug tab's error digest matched only 'EXC' (Python) lines, so a wave of
    'JSERR' (front-end) crashes — the kind this app actually hits — showed up as
    'errors: clean'. Both must be counted now."""
    from exilebot_pickit.ui import config as cfgmod
    log = tmp_path / "debug.log"
    log.write_text(
        "2026-07-15 10:00:00,000 ERROR EXC load_config\n"
        "json.decoder.JSONDecodeError: bad\n"
        "2026-07-15 10:01:00,000 ERROR JSERR JS error: Cannot read properties of null @2100\n"
        "2026-07-15 10:02:00,000 ERROR JSERR JS error: something else @42\n"
        "2026-07-15 10:03:00,000 INFO config saved\n",
        encoding="utf-8")
    monkeypatch.setattr(cfgmod, "LOG_PATH", str(log))

    e = api.debug_info()["errors"]
    kinds = {t["kind"]: t["count"] for t in e["by_type"]}
    assert kinds.get("JS error (UI)") == 2, kinds     # both JSERR lines counted
    assert kinds.get("load_config") == 1
    assert e["total"] == 3                            # not 1


def test_debug_digest_headline_counts_only_the_last_24h(api, tmp_path, monkeypatch):
    """The log rotates by size, not age, so a long-fixed incident lingers for
    weeks. Counting it forever made a healthy app open Debug on '53 errors'
    (the July save-race scar). The headline is now recent_total (24 hours —
    'is the app healthy NOW'); the all-time total stays available as the
    footnote number, and live errors still bump the nav badge instantly."""
    import time as _time
    from exilebot_pickit.ui import config as cfgmod
    old = _time.strftime("%Y-%m-%d %H:%M:%S",
                         _time.localtime(_time.time() - 3 * 86400))
    now = _time.strftime("%Y-%m-%d %H:%M:%S", _time.localtime())
    log = tmp_path / "debug.log"
    log.write_text(
        f"{old},000 ERROR EXC load_config\n"
        f"{old},000 ERROR EXC load_config\n"
        f"{now},000 ERROR JSERR JS error: fresh crash @7\n",
        encoding="utf-8")
    monkeypatch.setattr(cfgmod, "LOG_PATH", str(log))

    e = api.debug_info()["errors"]
    assert e["total"] == 3                 # all-time, for the footnote
    assert e["recent_total"] == 1          # only the fresh crash makes noise
    per = {t["kind"]: t for t in e["by_type"]}
    assert per["load_config"]["recent"] == 0
    assert per["JS error (UI)"]["recent"] == 1


# ── Full-scan regression tests (2026-07-15): the highest-damage untested paths ──

def test_auto_copy_success_lands_full_file_in_bot_folder(api, tmp_path):
    """The SUCCESS path of bot-folder auto-copy — the app's whole purpose. Only the
    blocked/missing-folder cases were tested; a regression here means generate
    reports success while the bot silently reads a stale pickit forever."""
    bot = tmp_path / "bot_pickit"
    bot.mkdir()
    api.cfg["auto_copy"] = True
    api.cfg["bot_folder"] = str(bot)
    api._generate("L", 5, 20)
    d = api._status["done"]
    assert d and d["ok"], d
    assert d["copied"] == str(bot)
    src = (tmp_path / "t.ipd").read_text(encoding="utf-8")
    dst = (bot / "t.ipd").read_text(encoding="utf-8")
    assert dst == src and len(dst) > 1000        # complete, byte-identical copy
    assert not (bot / "t.ipd.tmp").exists()      # atomic temp cleaned up


def test_profile_round_trip_restores_every_snapshot_key(api):
    """profile_load rebuilds settings key by key with .get defaults — any key drift
    between snapshot and load silently restores a 0-ex floor, and the next generate
    is a vacuum pickit. Round-trip every key exactly."""
    api.cfg.update({"min_exalt_gear": 7.5, "min_exalt": 7.5, "min_exalt_unique": 22.0,
                    "output_base": "farmset", "include_bases": False,
                    "auto_floor": True, "auto_floor_pct": 30,
                    "base_quality": 20, "base_min_level": 80})
    api.cfg["item_states"] = {"currency": {"Chaos Orb": {"enabled": False}}}
    api.cfg["category_enabled"] = {"essences": False}
    saved = api._profile_snapshot()
    assert api.profile_save("test-prof")["ok"]

    # trash every saved setting, then load the profile back
    api.cfg.update({"min_exalt_gear": 0.0, "min_exalt": 0.0, "min_exalt_unique": 0.0,
                    "output_base": "other", "include_bases": True,
                    "auto_floor": False, "auto_floor_pct": 40,
                    "base_quality": 25, "base_min_level": 82,
                    "item_states": {}, "category_enabled": {}})
    assert api.profile_load("test-prof")["ok"]
    assert api._profile_snapshot() == saved      # every key, exact
    assert api.cfg["min_exalt_gear"] == 7.5      # floors non-zero (no vacuum)
    assert api.cfg["min_exalt"] == 7.5           # legacy mirror kept in sync


def test_output_base_is_sanitized_against_paths_and_reserved_chars(api):
    """output_base becomes a filename and a backup prefix — absolute paths escaped
    OUTPUT_DIR entirely and reserved chars crashed the write after backup rotation."""
    api.set_setting("output_base", r"C:\Windows\evil")
    assert "\\" not in api.cfg["output_base"] and ":" not in api.cfg["output_base"]
    api.set_setting("output_base", "a?b*c")
    assert api.cfg["output_base"] == "a_b_c"
    api.set_setting("output_base", "...")
    assert api.cfg["output_base"] == "poe2_pickit"    # nothing left -> default


def test_import_pickit_status_stale_detection(api, tmp_path):
    """Create-your-filter: the tab warns when the source pickit changed after
    the filter was saved from it (and stays quiet in every other state)."""
    src = tmp_path / "mine.ipd"
    src.write_text('[Type] == "Divine Orb" # [StashItem] == "true"', encoding="utf-8")

    # nothing remembered -> never stale
    assert api.import_pickit_status() == {"stale": False}

    # saved AFTER the pickit's mtime -> fresh
    api.cfg["filter_from_pickit"] = {"src": str(src), "out": "mine.filter",
                                     "at": os.path.getmtime(src) + 60}
    assert api.import_pickit_status()["stale"] is False

    # pickit edited AFTER the save -> stale, with names for the banner
    api.cfg["filter_from_pickit"]["at"] = os.path.getmtime(src) - 60
    st = api.import_pickit_status()
    assert st["stale"] is True
    assert st["src"] == "mine.ipd" and st["out"] == "mine.filter"
    assert st["path"] == str(src)

    # source pickit deleted -> quiet, not a crash
    src.unlink()
    assert api.import_pickit_status() == {"stale": False}


def test_enable_all_rules_flips_every_switch_but_keeps_numbers(api):
    """The one-click "All ON + Generate" helper: every category/item/slot
    toggle turns on, numeric tuning (floors, craft ilvl) is untouched."""
    api.cfg["category_enabled"] = {"currency": False, "uniques": True}
    api.cfg["item_states"] = {
        "_chance": {"Ornate Belt": {"enabled": False}},
        "_raregear": {"Helmet": {"enabled": False}},
        "craft": {"Sacred Focus": {"enabled": False, "ilvl": 81}},
    }
    api.cfg["rare_gear_enabled"] = False
    api.cfg["include_bases"] = False
    api.cfg["magic_rare_flasks"] = False
    api.cfg["active_preset"] = "balanced"
    api.cfg["min_exalt_gear"] = 7.5

    api.cfg["auto_floor"] = True
    r = api.enable_all_rules()
    assert r["ok"] and r["flipped"] == 3
    # auto-floor recomputes both floors on every generate, so leaving it on
    # would silently re-filter everything we just switched on
    assert api.cfg["auto_floor"] is False
    assert api.cfg["category_enabled"] == {}          # empty = all on
    assert api.cfg["item_states"]["_chance"]["Ornate Belt"]["enabled"] is True
    assert api.cfg["item_states"]["_raregear"]["Helmet"]["enabled"] is True
    craft = api.cfg["item_states"]["craft"]["Sacred Focus"]
    assert craft["enabled"] is True and craft["ilvl"] == 81   # number kept
    assert api.cfg["rare_gear_enabled"] and api.cfg["include_bases"]
    assert api.cfg["magic_rare_flasks"]
    assert api.cfg["active_preset"] == ""
    # "everything on" means everything: a 7.5 ex floor would still filter most
    # of what we just enabled, so both floors drop to 0
    assert api.cfg["min_exalt_gear"] == 0.0
    assert api.cfg["min_exalt_unique"] == 0.0
    # exceptional-base gates open to the loosest legal values too
    assert api.cfg["base_quality"] == 21 and api.cfg["base_min_level"] == 79


def test_undo_all_on_restores_the_exact_previous_switch_state(api):
    """All ON is one click; it must not be able to destroy an hour of switch
    curation. undo_all_on puts back exactly what enable_all_rules changed —
    including an item whose 'enabled' key did not exist before — and is
    one-shot: a second undo reports there is nothing left to undo."""
    api.cfg["category_enabled"] = {"currency": False}
    api.cfg["item_states"] = {
        "_chance": {"Ornate Belt": {"enabled": False}},
        "craft": {"Sacred Focus": {"ilvl": 81}},      # no 'enabled' key at all
    }
    api.cfg["rare_gear_enabled"] = False
    api.cfg["active_preset"] = "balanced"

    api.enable_all_rules()
    assert api.cfg["item_states"]["craft"]["Sacred Focus"]["enabled"] is True

    r = api.undo_all_on()
    assert r["ok"] and r["restored"] == 2
    assert api.cfg["category_enabled"] == {"currency": False}
    assert api.cfg["item_states"]["_chance"]["Ornate Belt"]["enabled"] is False
    sacred = api.cfg["item_states"]["craft"]["Sacred Focus"]
    assert "enabled" not in sacred and sacred["ilvl"] == 81   # key absence restored
    assert api.cfg["rare_gear_enabled"] is False
    assert api.cfg["active_preset"] == "balanced"

    assert "error" in api.undo_all_on()               # one-shot: nothing left


def test_backup_diff_reports_rule_changes_and_ignores_price_churn(api, tmp_path):
    """Preview's 'Compare backup': prices move EVERY run, so a diff that showed
    price churn would bury the real answer — which rules appeared/disappeared.
    ExValue comments are stripped before comparing; disabled rules don't count."""
    bdir = tmp_path / "backups"
    bdir.mkdir()
    (bdir / "t-20260718-120000.ipd").write_text("\n".join([
        '[Type] == "Chaos Orb" # [StashItem] == "true" // ExValue = 2.10',
        '[Type] == "Old Orb" # [StashItem] == "true" // ExValue = 9.00',
        '// [Type] == "Disabled Orb" # [StashItem] == "true"',
    ]), encoding="utf-8")
    (tmp_path / "t.ipd").write_text("\n".join([
        '[Type] == "Chaos Orb" # [StashItem] == "true" // ExValue = 3.40',   # price moved only
        '[Type] == "New Orb" # [StashItem] == "true" // ExValue = 12.00',
    ]), encoding="utf-8")

    r = api.backup_diff("t-20260718-120000.ipd")
    assert r["added_total"] == 1 and "New Orb" in r["added"][0]
    assert r["removed_total"] == 1 and "Old Orb" in r["removed"][0]
    assert not any("Chaos Orb" in l for l in r["added"] + r["removed"])   # price-only: silent
    assert not any("Disabled Orb" in l for l in r["removed"])             # commented: not a rule
    assert r["cur_total"] == 2 and r["old_total"] == 2

    assert "error" in api.backup_diff("../../evil.ipd")     # traversal-safe
    assert "error" in api.backup_diff("t-nope.ipd")


def test_chance_bases_prices_the_target_unique(api, monkeypatch):
    """Each Chance card shows the live price of the unique you're chancing FOR
    (Mageblood, Headhunter, …) — all accessories, priced from one fetch. The
    BEST price among multi-target entries wins (the jackpot you're hoping for).
    No league = no fetch = cards still render, just without a price."""
    def fake_fetch(league, key, ninja_type, is_unique):
        if key == "currency":
            return {"core": {"rates": {"exalted": 1.0}},
                    "items": [{"id": "d", "name": "Divine Orb"}],
                    "lines": [{"id": "d", "primaryValue": 400.0}]}
        return {"core": {"rates": {"exalted": 1.0}},
                "lines": [{"name": "Mageblood", "primaryValue": 1200.0},
                          {"name": "Andvarius", "primaryValue": 5.0},
                          {"name": "Perandus Seal", "primaryValue": 90.0}]}
    monkeypatch.setattr(webapi.gen, "fetch_category", fake_fetch)

    rows = {r["base"]: r for r in api.chance_bases("L")}
    mb = rows["Utility Belt"]                       # → Mageblood
    assert mb["target_ex"] == 1200.0 and mb["target_div"] == 3.0   # 1200 / 400
    ring = rows["Gold Ring"]                        # Ventor's / Andvarius / Perandus Seal
    assert ring["target_ex"] == 90.0               # best of the three present (Perandus)
    hh = rows["Heavy Belt"]                         # → Headhunter, not in the feed
    assert hh["target_ex"] is None                 # unpriced target: no price, still a card

    no_league = api.chance_bases(None)              # never fetches
    assert all(r["target_ex"] is None for r in no_league)


def test_profile_summary_describes_what_the_profile_changes(api):
    """The profile panel answers "what does this profile actually do?".
    A profile stores absolute state, so the summary lists the floors it pins
    and everything it switches OFF — named sections by name, economy by count."""
    api.cfg["profiles"] = {"farm": {
        "min_exalt_gear": 5.0, "min_exalt_unique": 25.0, "auto_floor": False,
        "output_base": "farm_pickit", "include_bases": True,
        "base_quality": 25, "base_min_level": 82,
        "category_enabled": {"unique_jewels": False},
        "item_states": {
            "_chance": {"Gold Ring": {"enabled": False},
                        "Heavy Belt": {"enabled": True}},
            "_raregear": {"Helmet": {"enabled": False}},
            "currency": {"Orb of Alchemy": {"enabled": False},
                         "Chaos Orb": {"enabled": False}},
        }}}
    rows = {r["k"]: r["v"] for r in api.profile_summary("farm")["rows"]}
    assert "5 ex" in rows["Floors"] and "25 ex" in rows["Floors"]
    assert rows["Output file"] == "farm_pickit.ipd"
    assert "Gold Ring" in rows["Chance bases off"] and "Heavy Belt" not in rows["Chance bases off"]
    assert rows["Rare gear slots off"].startswith("1 — Helmet")
    # economy items are NAMED, not just counted — a shared profile that quietly
    # disables Divine Orb has to be visible to whoever imports it
    assert "Chaos Orb" in rows["Economy · currency off"]
    assert rows["Items disabled in total"] == "2"
    assert rows["Whole categories OFF"] == "unique_jewels"
    assert "error" in api.profile_summary("nope")


def test_profile_summary_reports_auto_floor_instead_of_numbers(api):
    """With auto-floor on, the pinned numbers are meaningless — say so."""
    api.cfg["profiles"] = {"a": {"auto_floor": True, "auto_floor_pct": 30,
                                 "min_exalt_gear": 1, "min_exalt_unique": 2}}
    rows = {r["k"]: r["v"] for r in api.profile_summary("a")["rows"]}
    assert "Auto-floor ON" in rows["Floors"] and "30%" in rows["Floors"]


def test_profile_import_commit_requires_a_preview_and_never_auto_switches(api):
    """Import adds a profile but must NOT silently replace the settings you're
    using — no active_profile change, and commit without a preview is refused."""
    assert "error" in api.profile_import_commit("x")        # nothing previewed
    api.cfg["active_profile"] = "current"
    api._pending_profile = ("shared", {"min_exalt_gear": 9.0})
    r = api.profile_import_commit("shared")
    assert r["ok"] and api.cfg["profiles"]["shared"]["min_exalt_gear"] == 9.0
    assert api.cfg["active_profile"] == "current"           # not switched
    assert "error" in api.profile_import_commit("shared")   # one-shot


def test_profile_summary_flags_disabled_loot_and_reassures_when_clean(api):
    """Sharing profiles is the risk: one that quietly disables Divine Orb (or a
    whole category) must say so, flagged, by name. And a profile that disables
    nothing must say THAT too — silence is not the same as "nothing is off"."""
    api.cfg["profiles"] = {
        "sneaky": {"item_states": {"currency": {"Divine Orb": {"enabled": False}}},
                   "category_enabled": {"unique_armours": False},
                   "include_bases": False},
        "clean": {"item_states": {}, "category_enabled": {}},
    }
    rows = api.profile_summary("sneaky")["rows"]
    by = {r["k"]: r for r in rows}
    assert "Divine Orb" in by["Economy · currency off"]["v"]
    assert by["Economy · currency off"]["warn"] is True
    assert by["Whole categories OFF"]["warn"] is True
    assert by["Base rules"]["warn"] is True
    assert "Loot rules" not in by                      # something IS off

    clean = {r["k"]: r for r in api.profile_summary("clean")["rows"]}
    assert "Nothing disabled" in clean["Loot rules"]["v"]
    assert clean["Loot rules"]["warn"] is False


def test_undo_all_on_restores_auto_floor_too(api):
    """All ON switches Adaptive floors off; undo has to put that back or the
    user silently loses the setting they had."""
    api.cfg["auto_floor"] = True
    api.cfg["min_exalt_gear"] = 200.0
    api.cfg["min_exalt_unique"] = 90.0
    api.cfg["base_quality"] = 28
    api.cfg["base_min_level"] = 82
    api.cfg["item_states"] = {"_chance": {"Gold Ring": {"enabled": False}}}
    api.enable_all_rules()
    assert api.cfg["auto_floor"] is False
    assert api.cfg["min_exalt_gear"] == 0.0 and api.cfg["min_exalt_unique"] == 0.0
    api.undo_all_on()
    assert api.cfg["auto_floor"] is True
    assert api.cfg["min_exalt_gear"] == 200.0 and api.cfg["min_exalt_unique"] == 90.0
    assert api.cfg["base_quality"] == 28 and api.cfg["base_min_level"] == 82
    assert api.cfg["item_states"]["_chance"]["Gold Ring"]["enabled"] is False


def test_all_on_offers_undo_even_when_no_switch_flipped(api):
    """Everything was already on, but All ON still zeroes the floors and kills
    auto-floor — so the undo button has to appear. It only stays hidden when
    the call genuinely changed nothing."""
    api.cfg.update({"item_states": {}, "category_enabled": {},
                    "auto_floor": True, "min_exalt_gear": 200.0,
                    "min_exalt_unique": 90.0, "rare_gear_enabled": True,
                    "include_bases": True, "magic_rare_flasks": True})
    r = api.enable_all_rules()
    assert r["flipped"] == 0 and r["changed"] is True

    api.undo_all_on()
    api.cfg.update({"auto_floor": False, "min_exalt_gear": 0.0,
                    "min_exalt_unique": 0.0})
    r2 = api.enable_all_rules()
    assert r2["flipped"] == 0 and r2["changed"] is False   # nothing to undo


def test_chance_bases_returns_art_and_price_for_every_target(api, monkeypatch):
    """A base can chance into several uniques (Gold Ring → Ventor's / Andvarius
    / Perandus Seal). Every one gets its own art and price — and when we ship no
    local icon for a target, poe.ninja's own art is used so none render blank."""
    def fake_fetch(league, key, ninja_type, is_unique):
        if key == "currency":
            return {"core": {"rates": {"exalted": 1.0}},
                    "items": [{"id": "d", "name": "Divine Orb"}],
                    "lines": [{"id": "d", "primaryValue": 400.0}]}
        return {"core": {"rates": {"exalted": 1.0}},
                "lines": [{"name": "Ventor's Gamble", "primaryValue": 20.0,
                           "icon": "https://web.poecdn.com/ventor.png"},
                          {"name": "Andvarius", "primaryValue": 5.0,
                           "icon": "https://web.poecdn.com/andvarius.png"},
                          {"name": "Perandus Seal", "primaryValue": 800.0,
                           "icon": "https://web.poecdn.com/perandus.png"}]}
    monkeypatch.setattr(webapi.gen, "fetch_category", fake_fetch)

    ring = next(r for r in api.chance_bases("L") if r["base"] == "Gold Ring")
    names = [t["name"] for t in ring["targets"]]
    assert names == ["Ventor's Gamble", "Andvarius", "Perandus Seal"]
    assert all(t["icon"] for t in ring["targets"])       # none blank
    # the two without bundled art fall back to poe.ninja's
    assert ring["targets"][1]["icon"] == "https://web.poecdn.com/andvarius.png"
    # headline price is still the BEST outcome (the jackpot you're chancing for)
    assert ring["target_ex"] == 800.0 and ring["target_div"] == 2.0


def test_item_check_resolves_superior_and_magic_names_to_the_real_base(api):
    """The pasted line often isn't the base the pickit keys on:
      * a Normal/Magic item WITH QUALITY copies as "Superior <Base>"
      * a Magic item wraps the base in affixes
    Both used to make Item Check answer "nothing matches" for items the bot
    really takes — worst on the quality white bases the Exceptional tab exists
    to collect, since those always carry the Superior prefix."""
    p = api._parse_item_text

    plain = p("Item Class: Body Armours\nRarity: Normal\nSoldier Cuirass\n"
              "--------\nItem Level: 82")
    superior = p("Item Class: Body Armours\nRarity: Normal\nSuperior Soldier Cuirass\n"
                 "--------\nQuality: +20% (augmented)\n--------\nItem Level: 82")
    assert superior["base"] == plain["base"] == "Soldier Cuirass"
    assert superior["quality"] == 20

    magic = p("Item Class: Body Armours\nRarity: Magic\n"
              "Sturdy Soldier Cuirass of the Bear\n--------\nItem Level: 82")
    assert magic["base"] == "Soldier Cuirass"

    # rare/unique already carry a separate base line — must be untouched
    rare = p("Item Class: Body Armours\nRarity: Rare\nDoom Shell\nSoldier Cuirass\n"
             "--------\nItem Level: 82")
    assert rare["name"] == "Doom Shell" and rare["base"] == "Soldier Cuirass"
    uniq = p("Item Class: Belts\nRarity: Unique\nHeadhunter\nHeavy Belt\n--------")
    assert uniq["name"] == "Headhunter" and uniq["base"] == "Heavy Belt"
    # an unknown/currency name passes through rather than being mangled
    cur = p("Item Class: Stackable Currency\nRarity: Currency\nDivine Orb\n--------")
    assert cur["base"] == "Divine Orb"


def test_item_check_quality_white_base_is_picked_like_the_plain_one(api):
    """End-to-end: the verdict for a quality white base must match the plain
    one. It said 'nothing matches' before, which is the opposite of the truth."""
    api.cfg.update({"base_quality": 21, "base_min_level": 79,
                    "include_bases": True, "min_exalt_gear": 0.0,
                    "min_exalt_unique": 0.0})
    body = ("Item Class: Body Armours\nRarity: Normal\nSuperior Soldier Cuirass\n"
            "--------\nQuality: +20% (augmented)\n--------\nItem Level: 82")
    r = api.check_item(body, "")          # no league -> no network
    assert r["item"]["base"] == "Soldier Cuirass"
    assert any(row["kind"] == "pick" for row in r["rows"]), r["rows"]


def test_clear_backups_only_removes_this_pickits_rotated_copies(api, tmp_path):
    """The Clear-all button must never touch the live pickit, another profile's
    backups, or unrelated files that happen to live in the backups folder."""
    bdir = tmp_path / "backups"
    bdir.mkdir()
    (bdir / "t-20260719-010000.ipd").write_text("a", encoding="utf-8")
    (bdir / "t-20260719-020000.ipd").write_text("b", encoding="utf-8")
    (bdir / "other-20260719-030000.ipd").write_text("c", encoding="utf-8")  # different output name
    (bdir / "notes.txt").write_text("keep me", encoding="utf-8")
    (tmp_path / "t.ipd").write_text("live pickit", encoding="utf-8")

    r = api.clear_backups()
    assert r["removed"] == 2
    left = sorted(p.name for p in bdir.iterdir())
    assert left == ["notes.txt", "other-20260719-030000.ipd"]
    assert (tmp_path / "t.ipd").read_text(encoding="utf-8") == "live pickit"

    assert api.clear_backups()["removed"] == 0      # idempotent


def test_all_on_twice_still_restores_the_original_switches(api):
    """A second "Turn everything on" used to overwrite the undo snapshot with the
    already-all-on state, so "Put my switches back" restored all-on — destroying
    exactly the curation the undo exists to protect."""
    api.cfg.update({"min_exalt_gear": 12.0, "min_exalt_unique": 90.0,
                    "auto_floor": True, "base_quality": 24, "base_min_level": 82,
                    "item_states": {"currency": {"Chaos Orb": False}}})
    before = {k: api.cfg[k] for k in
              ("min_exalt_gear", "min_exalt_unique", "auto_floor",
               "base_quality", "base_min_level")}

    api.enable_all_rules()
    api.enable_all_rules()                      # the second click
    assert api.cfg["min_exalt_gear"] == 0.0     # all-on really applied

    api.undo_all_on()
    after = {k: api.cfg[k] for k in before}
    assert after == before, f"undo lost the original settings: {after} != {before}"
    assert api.cfg["item_states"]["currency"]["Chaos Orb"] is False


def test_all_on_snapshot_is_recaptured_after_an_undo(api):
    """Holding the first snapshot must not freeze it forever — once undone, the
    next All ON has to capture the CURRENT state."""
    api.cfg.update({"min_exalt_gear": 5.0, "item_states": {}, "category_enabled": {}})
    api.enable_all_rules()
    api.undo_all_on()
    assert api.cfg["min_exalt_gear"] == 5.0

    api.cfg["min_exalt_gear"] = 33.0            # user picks a new floor
    api.enable_all_rules()
    api.undo_all_on()
    assert api.cfg["min_exalt_gear"] == 33.0, "second All ON reused a stale snapshot"


def test_a_non_utf8_pickit_does_not_break_generating(api, tmp_path):
    """A hand-edited/ANSI .ipd in the output folder raised UnicodeDecodeError in
    the added/removed diff. That is a ValueError, not an OSError, so it escaped
    the guard and aborted the run BEFORE the write — leaving the bad file in
    place so every later run failed the same way."""
    (tmp_path / "t.ipd").write_bytes(
        '[Type] == "Caf\xe8 Orb" # [StashItem] == "true"\r\n'.encode("cp1252"))

    api._generate("L", 5, 20)

    d = api._status["done"]
    assert d and d["ok"], f"generate aborted on a non-UTF-8 pickit: {d}"
    written = (tmp_path / "t.ipd").read_text(encoding="utf-8")
    assert "[StashItem]" in written                     # really replaced
    assert api.preview()                                # preview survives it too


def test_backups_never_match_another_profiles_files(api, tmp_path):
    """A hyphen is a legal output_base character, so the old
    ``f.startswith(base + "-")`` test made output_base "pickit" own every
    "pickit-strict-*.ipd" backup too. That is not cosmetic: rotation deleted
    the OTHER profile's backups (and counted files it didn't own, so its own
    keep-count drifted), "Delete all backups" wiped a profile the user never
    touched, and Restore handed back a different profile's pickit — which
    auto_copy then shipped straight to the bot. The stamp shape is now
    anchored, so the two sets are disjoint."""
    api.cfg["output_base"] = "pickit"
    bdir = tmp_path / "backups"
    bdir.mkdir()
    mine = ["pickit-20260719-010101.ipd", "pickit-20260719-020202.ipd"]
    theirs = ["pickit-strict-20260719-030303.ipd", "pickit-strict-20260719-040404.ipd"]
    for f in mine:
        (bdir / f).write_text('[Type] == "Mine" # [StashItem] == "true"', encoding="utf-8")
    for f in theirs:
        (bdir / f).write_text('[Type] == "Theirs" # [StashItem] == "true"', encoding="utf-8")
    # not a backup at all: no timestamp, or a malformed one
    (bdir / "pickit-notes.ipd").write_text("x", encoding="utf-8")
    (bdir / "pickit-2026719-010101.ipd").write_text("x", encoding="utf-8")

    assert sorted(b["name"] for b in api.list_backups()) == sorted(mine)

    # restore must refuse the neighbouring profile's file outright
    assert "error" in api.restore_backup("pickit-strict-20260719-030303.ipd")
    assert not (tmp_path / "pickit.ipd").exists()
    assert "error" in api.backup_diff("pickit-strict-20260719-030303.ipd")

    assert api.clear_backups()["removed"] == 2
    survivors = sorted(os.listdir(str(bdir)))
    assert survivors == sorted(theirs + ["pickit-2026719-010101.ipd", "pickit-notes.ipd"])


def test_a_malformed_profile_is_rejected_before_anything_is_saved(api):
    """A profile file is user-supplied (exported, hand-edited, shared). Fields
    used to be copied into cfg and saved, and only THEN could a type error
    raise — so a profile carrying a non-numeric floor, a string where
    item_states must be a dict, and an ABSOLUTE output_base was already on
    disk by then: app_info() raised
    for the rest of the session, _snapshot() broke Generate, and output_base
    (a str, so _coerce_types never healed it) permanently wrote the .ipd
    outside the output folder."""
    api.cfg["profiles"] = {"bad": {"min_exalt_gear": "abc", "item_states": "nope",
                                   "output_base": "C:\\Windows\\x"}}
    before = copy.deepcopy(api.cfg)

    r = api.profile_load("bad")
    assert "error" in r and "not applied" in r["error"].lower()
    assert api.cfg == before, "a rejected profile still changed the config"
    assert api.app_info()["output_base"] == before["output_base"]

    # the preview must not raise either — the UI awaits it bare, so a rejected
    # promise made the Import button do nothing at all, silently
    rows = api._describe_profile(api.cfg["profiles"]["bad"])
    assert any("unreadable" in str(r["v"]) for r in rows)
    api._pending_profile = ("shared", api.cfg["profiles"]["bad"])
    assert "error" in api.profile_import_commit("shared")
    assert "shared" not in api.cfg["profiles"], "a rejected import was stored anyway"

    # a usable profile still loads — and its output_base is sanitized to a
    # plain filename, never a path
    api.cfg["profiles"]["good"] = {"min_exalt_gear": 5, "min_exalt_unique": 7,
                                   "output_base": "..\\..\\evil",
                                   "item_states": {}, "category_enabled": {}}
    assert api.profile_load("good")["ok"]
    ob = api.cfg["output_base"]
    assert os.sep not in ob and ".." != ob and os.path.basename(ob) == ob


def test_always_pick_groups_are_split_by_kind(api):
    """"Fragments & Keys" bundled splinters, wombgifts and pinnacle keys into one
    category, so Raven's Reflection — a Delirium boss key — was filed under
    "Fragments" and read as misplaced. Each kind is its own category now."""
    labels = {label for _k, label, _rows in api._ap_groups()}
    assert {"Splinters", "Wombgifts", "Pinnacle Keys"} <= labels
    assert "Fragments & Keys" not in labels

    keys = dict((k, rows) for k, _l, rows in api._ap_groups())
    assert [n for n, _b, _s in keys["_ap_keys"]] == list(gen.SPECIAL_ITEMS)


def test_splitting_the_group_does_not_re_enable_old_disables(api):
    """Item states are keyed by CATEGORY, so renaming one orphans every switch
    saved under the old key — and a silently re-enabled item puts junk straight
    back in the stash. The retired "_ap_frag" key is still read."""
    api.cfg["item_states"] = {"_ap_frag": {
        "Breach Splinter": {"enabled": False},
        "Kulemak's Invitation": {"enabled": False},
    }}
    dis = api._ap_disabled(api._snapshot())
    assert "Breach Splinter" in dis
    assert "Kulemak's Invitation" in dis
    assert "Simulacrum Splinter" not in dis      # untouched stays on


def test_disabling_the_whole_old_category_survives_the_split(api):
    """Turning off all of "Fragments & Keys" saved one switch under "_ap_frag".
    All three successor categories must still read as off."""
    api.cfg["category_enabled"] = {"_ap_frag": False}
    snap = api._snapshot()
    for key in ("_ap_splinters", "_ap_wombgifts", "_ap_keys"):
        assert snap["cat_enabled"][key] is False, key
    # groups that were never part of that bucket are untouched
    assert snap["cat_enabled"]["_ap_tablets"] is True
    dis = api._ap_disabled(snap)
    assert "Raven's Reflection" in dis
    assert not any(t in dis for t in gen.TABLET_TYPES)


def test_a_current_switch_beats_the_retired_one(api):
    """Re-enabling an item after the split must win over the old "off"."""
    api.cfg["item_states"] = {
        "_ap_frag": {"Raven's Reflection": {"enabled": False}},
        "_ap_keys": {"Raven's Reflection": {"enabled": True}},
    }
    assert "Raven's Reflection" not in api._ap_disabled(api._snapshot())


def test_tablets_are_one_category_split_into_sections(api):
    """16 tablets read as one undifferentiated list: the 7 you juice maps with,
    then 9 uniques. They stay ONE category (4.41.5 briefly made them two) and are
    separated by a sub-heading instead."""
    groups = dict((k, rows) for k, _l, rows in api._ap_groups())
    assert "_ap_tablet_uniques" not in groups
    secs = [(n, s) for n, _b, s in groups["_ap_tablets"]]
    assert [n for n, s in secs if s == "Tablets"] == list(gen.TABLET_TYPES)
    assert ([n for n, s in secs if s == "Unique Tablets"]
            == [u for _t, u in gen.TABLET_UNIQUES])
    # base tablets must all come before the uniques, or the heading splits nothing
    kinds = [s for _n, s in secs]
    assert kinds == sorted(kinds, key=lambda s: s == "Unique Tablets")


def test_a_switch_saved_during_the_split_release_still_counts(api):
    """4.41.5 shipped uniques as their own category. Switches saved against that
    key must survive folding them back in, or a disabled unique comes back on."""
    api.cfg["item_states"] = {"_ap_tablet_uniques": {"Clear Skies": {"enabled": False}}}
    assert "Clear Skies" in api._ap_disabled(api._snapshot())


def test_exotic_bases_are_grouped_by_gear_slot(api):
    """48 bases in one alphabetical run buries the rings and amulets. Every base
    carries a slot, ordered jewellery-first."""
    rows = dict((k, r) for k, _l, r in api._ap_groups())["_ap_exotic"]
    assert len(rows) == len(gen.EXOTIC_BASES)
    order = [s for _n, _b, s in rows]
    assert order[0] == "Amulets" and "Rings" in order
    # each slot appears as ONE contiguous block, else the heading repeats
    seen = []
    for s in order:
        if not seen or seen[-1] != s:
            assert s not in seen, f"{s} is split into two blocks"
            seen.append(s)
    assert seen == [s for s in gen.EXOTIC_SLOT_ORDER if s in seen]
    # the map must not fall behind the list it describes, in EITHER direction:
    # a base removed from EXOTIC_BASES (e.g. the 17 unique-host bases pruned
    # 2026-07-21) must also be removed from EXOTIC_BASE_SLOTS, or the slot map
    # accumulates dead entries for names the app no longer ships at all
    assert [b for b in gen.EXOTIC_BASES if b not in gen.EXOTIC_BASE_SLOTS] == []
    assert [b for b in gen.EXOTIC_BASE_SLOTS if b not in gen.EXOTIC_BASES] == []


def test_a_remotely_added_exotic_base_is_shown_not_dropped(api):
    """EXOTIC_BASES self-updates from game_data.json, so a base can arrive with no
    slot mapped. It must still be pickable, under "Other"."""
    gen.EXOTIC_BASES.append("Mystery Trinket")
    try:
        rows = dict((k, r) for k, _l, r in api._ap_groups())["_ap_exotic"]
        assert ("Mystery Trinket", "", "Other") in rows
        assert rows[-1][0] == "Mystery Trinket"      # unmapped sorts last
    finally:
        gen.EXOTIC_BASES.remove("Mystery Trinket")


def test_key_sections_only_list_items_poe_ninja_prices(monkeypatch, api):
    """The Keys lens must not resurrect removed content. Calamity Fragments are in
    the game files but poe.ninja does not price them, so they are left out
    entirely — the same removed-item test used everywhere else."""
    from exilebot_pickit.data import corrections as corr
    listed = set(corr.KEY_ITEM_SECTIONS)
    assert "Raven’s Reflection".replace("’", "'") in listed
    assert not any("Calamity Fragment" in n for n in listed)
    assert set(corr.KEY_ITEM_SECTIONS.values()) == set(corr.KEY_SECTION_ORDER)

def test_keys_group_is_hidden_from_the_sidebar(api):
    """The one-item always-pick keys category would sit beside the Keys lens
    showing the same lone key. It is marked hidden so only the lens shows it,
    but it still exists so generation keeps writing its rules."""
    eco = api.economy("L")
    cats = {c["key"]: c for c in eco["cats"]}
    assert cats["_ap_keys"]["hidden"] is True
    assert eco["key_order"] == list(gen.KEY_SECTION_ORDER)
    # nothing else is hidden
    assert [k for k, c in cats.items() if c.get("hidden")] == ["_ap_keys"]


def test_reset_defaults_keeps_theme_but_clears_settings(api):
    """Reset turns every toggle back on and clears tuned floors, but must NOT
    repaint the app — the chosen theme is user data, kept like history/profiles."""
    api.cfg["theme"] = "twilight"
    api.cfg["min_exalt"] = 99
    api.cfg.setdefault("item_states", {}).setdefault("currency", {})["Chaos Orb"] = {"enabled": False}
    api.reset_defaults()
    assert api.cfg["theme"] == "twilight"          # kept
    assert api.cfg["min_exalt"] != 99              # floor cleared
    assert api.cfg["item_states"].get("currency", {}).get("Chaos Orb") is None  # toggle back on


def test_rare_strictness_scales_the_cutoff(api):
    """The strictness dial scales every slot WeightedSum cutoff; the recipe
    (stats/weights) is untouched, and what the tab shows must equal what is
    written into the pickit."""
    from exilebot_pickit.data.rare import rules as rr
    slot, spec = next(iter(rr.RARE_GEAR.items()))
    base = int(spec["threshold"])
    api.set_rare_strictness("very_strict")
    rec = api.rare_recipes()
    assert rec["strictness"] == "very_strict"
    shown = rec["slots"][slot]["threshold"]
    assert shown == int(round(base * 1.5)) > base            # cutoff raised
    assert f'>= "{shown}"' in rec["slots"][slot]["lines"][0]  # tab == output

    api.set_rare_strictness("looser")
    assert api.rare_recipes()["slots"][slot]["threshold"] == int(round(base * 0.8)) < base

    api.set_rare_strictness("nonsense")   # unknown -> balanced
    assert api.cfg["rare_strictness"] == "balanced"
    assert api.rare_recipes()["slots"][slot]["threshold"] == base


def test_per_slot_strictness_overrides_the_global_dial(api):
    """Each slot can override the global dial: Body Armour very strict while the
    rest stay looser. Clearing an override falls back to the global level, and
    the generate-time multiplier map reflects both."""
    from exilebot_pickit.data.rare import rules as rr
    ba = int(rr.RARE_GEAR["Body Armour"]["threshold"])
    api.set_rare_strictness("looser")
    api.set_rare_slot_strictness("Body Armour", "very_strict")
    rec = api.rare_recipes()
    assert rec["slots"]["Body Armour"]["threshold"] == int(round(ba * 1.5))   # override
    assert rec["slots"]["Body Armour"]["strictness_override"] == "very_strict"
    hb = int(rr.RARE_GEAR["Helmet"]["threshold"])
    assert rec["slots"]["Helmet"]["threshold"] == int(round(hb * 0.8))        # inherits looser
    assert rec["slots"]["Helmet"]["strictness_override"] == ""

    mults = api._rare_slot_mults(api._snapshot())
    assert mults["Body Armour"] == 1.5 and mults["Helmet"] == 0.8

    api.set_rare_slot_strictness("Body Armour", "inherit")   # clear -> global
    assert api.rare_recipes()["slots"]["Body Armour"]["threshold"] == int(round(ba * 0.8))
    assert api.set_rare_slot_strictness("Nope", "strict")["ok"] is False   # unknown slot


def _headless_env(tmp_path, monkeypatch, cfg):
    def fake_fetch(league, categories, **kw):
        return {k: FAKE.get(k, _payload([])) for k, *_ in categories}
    monkeypatch.setattr(webapi.gen, "fetch_all_payloads", fake_fetch)
    monkeypatch.setattr(webapi.gen, "set_disk_cache_dir", lambda *a, **k: None)
    monkeypatch.setattr(webapi.gen, "prune_disk_cache", lambda *a, **k: None)
    monkeypatch.setattr(webapi, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(webapi, "save_config", lambda cfg: True)
    monkeypatch.setattr(webapi, "load_config", lambda: dict(cfg))


def test_headless_regenerate_uses_saved_config(tmp_path, monkeypatch):
    """--regenerate rebuilds from the SAVED settings with no window: it takes the
    saved league and floors and writes the pickit, returning exit code 0."""
    _headless_env(tmp_path, monkeypatch, {
        "output_base": "t", "league": "L", "min_exalt_gear": 5,
        "min_exalt_unique": 20, "history": [], "item_states": {},
        "category_enabled": {}, "backup_count": 0})
    assert webapi.headless_regenerate() == 0          # saved league used
    assert os.path.isfile(os.path.join(str(tmp_path), "t.ipd"))


def test_headless_regenerate_league_override_and_no_league(tmp_path, monkeypatch):
    _headless_env(tmp_path, monkeypatch, {
        "output_base": "t", "history": [], "item_states": {},
        "category_enabled": {}, "backup_count": 0})               # no saved league
    monkeypatch.setattr(webapi.gen, "fetch_live_leagues", lambda: [])
    assert webapi.headless_regenerate() == 2                       # nothing to run
    assert webapi.headless_regenerate("L") == 0                    # explicit override works
    assert os.path.isfile(os.path.join(str(tmp_path), "t.ipd"))


def test_generated_ipd_carries_the_syntax_guide(api, tmp_path):
    """assembly.syntax_guide_lines() existed but neither writer called it, so no
    generated .ipd ever carried the bots own syntax reference ([WeightedSum],
    [IgnoreRitual], WeaponCategory vocabulary). Wired in 2026-07-21; this pins
    it so it cannot silently go unwired again."""
    api._generate("L", 5, 20)
    d = api._status["done"]
    assert d and d["ok"], d
    text = open(d["path"], encoding="utf-8").read()
    assert "Configuration Guide for Path of Exile 2" in text
    assert "[WeightedSum(stat:weight" in text
    assert "[IgnoreRitual]" in text
