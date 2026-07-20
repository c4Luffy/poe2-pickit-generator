"""Remote game-data v2: static always-pick sections come from data, not code."""

import json
import os
import time

import pytest

from exilebot_pickit import generator as gen
from exilebot_pickit.data import base_types as bt
from exilebot_pickit.data import corrections as corr
from exilebot_pickit.data import remote_data as rd

_ROOT = os.path.join(os.path.dirname(__file__), "..")


@pytest.fixture(autouse=True)
def _restore_game_data():
    """Applying remote data mutates the game-data modules IN PLACE.

    Without putting them back, every test that runs after this file sees the
    fake lists — e.g. the base types collapse to whatever a cache fixture
    wrote, and unrelated tests that look up a real base start failing purely
    because of test order.
    """
    import copy
    from exilebot_pickit import generator as _g
    from exilebot_pickit.data import base_types as _b
    bases = copy.deepcopy(_b._BASE_TYPES_BY_CATEGORY)
    valid = _g.VALID_EQUIPMENT_BASES
    try:
        yield
    finally:
        _b._BASE_TYPES_BY_CATEGORY.clear()
        _b._BASE_TYPES_BY_CATEGORY.update(bases)
        _g.VALID_EQUIPMENT_BASES = valid


def _load_bundled():
    with open(os.path.join(_ROOT, "game_data.json"), encoding="utf-8") as f:
        return json.load(f)


def test_bundled_game_data_validates():
    assert rd._validate(_load_bundled())


def test_bundled_game_data_matches_code_defaults():
    """The shipped JSON must mirror the built-in fallbacks, or offline users
    and online users would generate different pickits."""
    data = _load_bundled()
    assert data["always_pick"]["currency"] == corr.ALWAYS_PICK_CURRENCY
    assert data["always_pick"]["runes"] == corr.ALWAYS_PICK_RUNES
    assert data["tablets"]["types"] == corr.TABLET_TYPES
    assert [tuple(e) for e in data["tablets"]["uniques"]] == corr.TABLET_UNIQUES
    assert data["splinters"] == corr.SPLINTERS
    assert data["wombgifts"] == corr.WOMBGIFTS
    assert data["special_items"] == corr.SPECIAL_ITEMS
    assert data["name_fixes"]["corrections"] == corr.ITEM_NAME_CORRECTIONS
    assert set(data["name_fixes"]["skip"]) == corr.ITEM_NAME_SKIP
    assert [tuple(e) for e in data["chance_bases"]] == gen.CHANCE_BASES


def test_static_builders_emit_expected_rules():
    tab = gen.build_tablet_rules()
    # one rule per unique tablet + 3 rarities per tablet type + splinters
    assert sum('[Rarity] == "Unique"' in ln for ln in tab) == len(corr.TABLET_UNIQUES)
    for typ in corr.TABLET_TYPES:
        for rar in ("Normal", "Magic", "Rare"):
            assert f'[Type] == "{typ}" && [Rarity] == "{rar}" # [StashItem] == "true"' in tab
    for s in corr.SPLINTERS:
        assert f'[Type] == "{s}" # [StashItem] == "true"' in tab
    womb = gen.build_wombgift_rules()
    for w in corr.WOMBGIFTS:
        assert f'[Type] == "{w}" # [StashItem] == "true"' in womb
    spec = gen.build_special_item_rules()
    assert any("Expedition Logbook" in ln for ln in spec)


def test_apply_updates_static_sections_in_place():
    """A remote edit (e.g. a new tablet type after a patch) must flow into the
    generated rules without a restart, and generator's imported references
    must see it (in-place mutation)."""
    saved = {
        "types": list(corr.TABLET_TYPES),
        "uniques": list(corr.TABLET_UNIQUES),
        "womb": list(corr.WOMBGIFTS),
        "chance": list(gen.CHANCE_BASES),
        "skip": set(corr.ITEM_NAME_SKIP),
    }
    try:
        rd._apply({
            "tablets": {"types": ["Overseer Tablet", "Testline Tablet"],
                        "uniques": [["Testline Tablet", "Imaginary Unique"]]},
            "wombgifts": ["New Wombgift"],
            "chance_bases": [["Belts", "Heavy Belt", "Headhunter"]],
            "name_fixes": {"skip": ["Bogus Item"]},
        })
        tab = gen.build_tablet_rules()
        assert '[Type] == "Testline Tablet" && [Rarity] == "Rare" # [StashItem] == "true"' in tab
        assert any("Imaginary Unique" in ln for ln in tab)
        assert '[Type] == "New Wombgift" # [StashItem] == "true"' in gen.build_wombgift_rules()
        assert gen.CHANCE_BASES == [("Belts", "Heavy Belt", "Headhunter")]
        assert "Bogus Item" in gen.ITEM_NAME_SKIP  # same object as corr's
    finally:
        corr.TABLET_TYPES[:] = saved["types"]
        corr.TABLET_UNIQUES[:] = saved["uniques"]
        corr.WOMBGIFTS[:] = saved["womb"]
        gen.CHANCE_BASES[:] = saved["chance"]
        corr.ITEM_NAME_SKIP.clear()
        corr.ITEM_NAME_SKIP.update(saved["skip"])


def test_validate_rejects_malformed_sections():
    assert not rd._validate({"tablets": {"uniques": [["only-one-element"]]}})
    assert not rd._validate({"splinters": [1, 2]})
    assert not rd._validate({"chance_bases": [["cat", "base"]]})
    assert not rd._validate({"name_fixes": {"corrections": {"a": 1}}})
    assert rd._validate({})  # all sections optional


def test_builders_respect_disabled_names():
    dis = {"Overseer Tablet", "Visions of Paradise", "Breach Splinter"}
    lines = gen.build_tablet_rules(dis)
    tab = "\n".join(lines)
    # the TYPE toggle kills the all-rarity rules but not that type's uniques
    assert '[Type] == "Overseer Tablet" && [Rarity] == "Normal"' not in tab
    assert "Cruel Hegemony" in tab
    assert "Visions of Paradise" not in tab
    assert "Breach Splinter" not in tab
    assert "Simulacrum Splinter" in tab
    assert "Abyss Tablet" in tab
    assert gen.build_wombgift_rules(set(corr.WOMBGIFTS)) == []
    assert gen.build_special_item_rules(set(corr.SPECIAL_ITEMS)) == []
    # nothing disabled → all sections present
    full = "\n".join(gen.build_tablet_rules())
    for t in corr.TABLET_TYPES:
        assert t in full


def test_unique_exceptional_removed():
    # "pick ANY unique on an exceptional base" was removed by the owner
    # (uniques are picked purely by value now) — must stay gone.
    assert not hasattr(gen, "build_unique_exceptional_rules")


def test_exotic_base_rules():
    exo = gen.build_exotic_base_rules()
    assert '[Type] == "Breach Ring" # [StashItem] == "true"' in exo
    assert '[Type] == "Dusk Ring" # [StashItem] == "true"' in exo
    # unique-host bases pruned 2026-07-21 (owner trade-site check) must not
    # come back as dead rules — the plain base never drops
    assert not any('"Runic Fork"' in r or '"Glacial Fortress"' in r for r in exo)
    assert gen.build_exotic_base_rules(set(corr.EXOTIC_BASES)) == []
    assert gen.validate_pickit(exo)["errors"] == []
    # removed features must STAY removed (owner-confirmed 2026-07-05):
    # type-less catch-alls match everything; jewels flooded the stash
    assert not hasattr(gen, "build_exceptional_catchall_rules")
    assert not hasattr(gen, "build_jewel_rules")
    data = _load_bundled()
    assert data["exotic_bases"] == corr.EXOTIC_BASES
    assert data["special_items"] == corr.SPECIAL_ITEMS
    assert "jewels" not in data


def test_cache_from_another_app_version_is_ignored(tmp_path):
    """A cache written by a DIFFERENT build must not be applied.

    Regression guard for 2026-07-12: the disk cache was keyed only on a 6-hour
    timer, so after shipping a game-data fix the stale cache was applied over the
    new bundled lists and silently won. A pickit generated right after the fix
    still carried 22 rules for Hallowed Sceptre and Dark Staff — two bases that
    had just been removed precisely because they don't drop. A new build always
    ships data at least as new as an older build's cache, so on a version change
    the cache is dropped and a refetch is forced.
    """
    from exilebot_pickit.version import VERSION

    cache_dir = str(tmp_path)
    # A FULL snapshot with one category altered — a remote copy that omits
    # categories is now rejected outright (it would delete them), and a
    # future-dated ts is treated as "not fresh", so neither can stand in for
    # "some cached data" here any more.
    stale = {cat: [[n, s] for n, s in entries]
             for cat, entries in bt._BASE_TYPES_BY_CATEGORY.items()}
    stale["Sceptres"] = [["Ghost Sceptre", 2]]

    def _write(app_version):
        with open(os.path.join(cache_dir, rd._CACHE_BASENAME), "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "app_version": app_version,
                       "data": {"base_types": stale}}, f)

    # Same version → the cache is applied and reported as fresh.
    _write(VERSION)
    status, ts = rd.load_cached_game_data(cache_dir)
    assert "cached remote data applied" in status
    assert ts > 0

    # Different version → ignored, and ts=0 forces refresh_game_data() to refetch.
    _write("0.0.1-old")
    status, ts = rd.load_cached_game_data(cache_dir)
    assert "another app version" in status
    assert ts == 0.0


def _full_base_types(**overrides):
    """A complete, valid base_types payload, optionally with categories replaced."""
    out = {cat: [[n, s] for n, s in entries]
           for cat, entries in bt._BASE_TYPES_BY_CATEGORY.items()}
    out.update(overrides)
    return out


def test_remote_copy_may_not_delete_a_base_category():
    """_apply prunes any category the remote copy omits, so a truncated or
    half-edited game_data.json used to pass validation and silently delete 16 of
    17 categories — stripping almost every base rule from every user's pickit,
    with no error anywhere. game_data.json is a full snapshot, not a patch."""
    before = len(bt._BASE_TYPES_BY_CATEGORY)
    assert before > 1

    partial = {"base_types": {"Belts": [["Fine Belt", 0]]}}
    assert not rd._validate(partial)

    # and the bundled data is untouched by the rejection
    assert len(bt._BASE_TYPES_BY_CATEGORY) == before

    # adding a category is still allowed
    grown = {"base_types": _full_base_types(Newthing=[["Some Base", 0]])}
    assert rd._validate(grown)


def test_remote_copy_may_not_empty_a_base_category():
    """A category present but emptied strips exactly the same rules as deleting
    it, so it must be rejected the same way."""
    assert not rd._validate({"base_types": _full_base_types(Belts=[])})


def test_base_name_that_would_break_a_rule_is_rejected():
    """A newline in a base name splits one rule into two, and the second half
    carries no [Type] — which Exiled Bot reads as matching EVERYTHING on the
    ground. An empty name yields [Type] == "" and matches nothing."""
    for bad in ('Fine Belt" # x\n[Rarity] == "Normal', "", "   ", "\n", 5, None):
        assert not rd._validate({"base_types": _full_base_types(Belts=[[bad, 0]])}), bad
    assert rd._validate({"base_types": _full_base_types(Belts=[["Fine Belt", 0]])})


def test_socket_threshold_must_be_a_real_int():
    """bool is a subclass of int, so True would have been accepted as 1."""
    for bad in (True, False, "2", 2.5, -1, 99, None):
        assert not rd._validate({"base_types": _full_base_types(Belts=[["Fine Belt", bad]])}), bad
    assert rd._validate({"base_types": _full_base_types(Belts=[["Fine Belt", 3]])})


def test_a_bad_cache_does_not_block_the_next_fetch(tmp_path):
    """load_cached_game_data returns a timestamp that refresh_game_data reads as
    "recently updated, skip the fetch". Returning a FRESH ts for a cache that was
    missing or failed validation suppressed remote updates for 6 hours on a
    single bad write."""
    from exilebot_pickit.version import VERSION

    cache_dir = str(tmp_path)

    def _write(payload):
        with open(os.path.join(cache_dir, rd._CACHE_BASENAME), "w", encoding="utf-8") as f:
            json.dump(payload, f)

    # payload fails validation → ts must be 0 so a refetch happens
    _write({"ts": time.time(), "app_version": VERSION,
            "data": {"base_types": "not-a-dict"}})
    assert rd.load_cached_game_data(cache_dir)[1] == 0.0

    # no data key at all → same
    _write({"ts": time.time(), "app_version": VERSION})
    assert rd.load_cached_game_data(cache_dir)[1] == 0.0

    # a good cache still reports its timestamp
    _write({"ts": time.time(), "app_version": VERSION,
            "data": {"base_types": _full_base_types()}})
    status, ts = rd.load_cached_game_data(cache_dir)
    assert ts > 0 and "cached remote data applied" in status


def test_a_future_dated_cache_does_not_block_updates_forever(tmp_path):
    """Clock skew or a hand-edited file could put ts far in the future, and
    "now - ts < 6h" is then true forever — remote updates never resumed."""
    from exilebot_pickit.version import VERSION

    cache_dir = str(tmp_path)
    with open(os.path.join(cache_dir, rd._CACHE_BASENAME), "w", encoding="utf-8") as f:
        json.dump({"ts": time.time() + 86400 * 365, "app_version": VERSION,
                   "data": {"base_types": _full_base_types()}}, f)
    assert rd.load_cached_game_data(cache_dir)[1] == 0.0


def test_no_exceptional_base_is_a_unique_only_base():
    """A base whose metadata path ends in ...Unique<N> exists ONLY to host a
    unique — a white one never drops. Three had been curated into the
    Exceptional list (Shrine Sceptre, Permafrost Staff, Reflecting Staff), so
    their Quality/ItemLevel rules could never fire and their toggles in the
    Exceptional tab did nothing at all. poe.ninja confirms it: those base names
    only ever appear carrying a unique (Atziri's Rule, The Whispering Ice,
    Guiding Palm, Sacred Flame), never as a tradeable white base.

    Guarded here because the list is hand-curated and the mistake is invisible
    without the metadata: the names look like ordinary high-level bases.

    NOTE the grouping below. The first version of this check asked whether ANY
    of a name's metadata paths was Unique-suffixed, which wrongly condemned
    Shrine Sceptre — it has three ordinary variants as well as a unique host —
    and it was removed from the data on that false basis before being restored.
    """
    import glob
    import json as _json

    dumps = glob.glob(os.path.join(_ROOT, "dist", "**", "gamedata_cache",
                                   "base_items.min.json"), recursive=True)
    if not dumps:
        pytest.skip("GGPK base-item dump not present in this checkout")

    with open(dumps[0], encoding="utf-8") as f:
        items = _json.load(f)

    # A name is unique-only when ALL of its metadata paths are Unique-suffixed.
    # Testing "any path" is wrong and cost us a real base: Shrine Sceptre has
    # FourSceptre6a/6b/6c (ordinary drops, one per Purity skill) alongside
    # FourSceptreUnique1, and the any-check condemned it. Group by name FIRST,
    # then require every path to be a unique host.
    paths_by_name: dict = {}
    for k, v in items.items():
        if v.get("name"):
            paths_by_name.setdefault(v["name"], []).append(k)
    unique_only = {n for n, paths in paths_by_name.items()
                   if all("Unique" in p.rsplit("/", 1)[-1] for p in paths)}

    # the control: a name with both kinds of path must NOT be treated as dead
    assert "Shrine Sceptre" not in unique_only, (
        "the any-path bug is back — Shrine Sceptre drops normally")
    assert "Reflecting Staff" in unique_only, "expected a real unique-only base"

    offenders = [(cat, n) for cat, entries in bt._BASE_TYPES_BY_CATEGORY.items()
                 for n, _s in entries if n in unique_only]
    assert not offenders, (
        "unique-only bases in the Exceptional list — a white one never drops, so "
        f"these rules can never fire: {offenders}")


def test_bundled_json_base_types_match_the_code():
    """game_data.json must mirror _BASE_TYPES_BY_CATEGORY exactly.

    test_bundled_game_data_matches_code_defaults checks every OTHER section but
    not this one — the largest, 119 entries. The gap is not theoretical: while
    adding Sanctified/Paralysing Staff on 2026-07-19 the code was edited and the
    JSON write silently no-opped on a bad anchor, and the whole suite still
    passed with the two files disagreeing. An offline user (bundled code) and an
    online user (remote JSON) would then generate different pickits.
    """
    data = _load_bundled()
    json_bt = {c: [tuple(e) for e in ents] for c, ents in data["base_types"].items()}
    code_bt = {c: [tuple(e) for e in ents]
               for c, ents in bt._BASE_TYPES_BY_CATEGORY.items()}
    assert json_bt == code_bt, (
        "game_data.json and data/base_types.py disagree — re-sync them "
        f"(JSON-only: {set(json_bt) - set(code_bt)}, code-only: {set(code_bt) - set(json_bt)})")


def test_the_ritual_pinnacle_fragment_can_be_bought_from_a_ritual():
    """An Audience with the King is the Ritual pinnacle fragment, so a Ritual
    reward window is exactly where you would want it. Carrying [IgnoreRitual]
    was one-sided: if the item appears in the window the bot walks past ~50 ex,
    and if it only ever drops on the ground the flag does nothing — it could
    only cost, never help.

    The other two keep the flag: Expedition Logbook is a real ground drop
    (drop_level 78) so declining to re-buy it with tribute is a genuine saving,
    and Kulemak's Invitation is Abyss content where the flag never applies.
    """
    rules = {ln.split('"')[1]: ln for ln in gen.build_special_item_rules(set())
             if ln.startswith("[Type]")}

    assert "IgnoreRitual" not in rules["An Audience with the King"]
    assert 'IgnoreRitual] == "true"' in rules["Expedition Logbook"]
    assert 'IgnoreRitual] == "true"' in rules["Kulemak's Invitation"]
    # every one is still an actual pickup rule
    for name, ln in rules.items():
        assert '[StashItem] == "true"' in ln, name


def test_both_special_item_writers_agree_on_the_action():
    """Two builders emit these rules — the static one, and the economy
    force-branch when poe.ninja happens to price the item. They disagreed once
    already (v4.38.4), so the same item got contradictory rules depending on
    whether it was priced that day. One helper decides for both now.
    """
    for name in corr.SPECIAL_ITEMS:
        payload = {"core": {"rates": {"exalted": 1.0}},
                   "items": [{"id": "x", "name": name}],
                   "lines": [{"id": "x", "primaryValue": 50.0}]}
        forced = next(ln for ln in gen.build_exchange_lines(
            payload, 1.0, min_exalt=10.0,
            force_names=set(gen.always_pick_force_names())) if name in ln)
        static = next(ln for ln in gen.build_special_item_rules(set()) if name in ln)
        assert forced.split("//")[0].strip() == static.strip(), name


def test_every_shipped_base_with_an_implicit_shows_one():
    """The Exceptional tab exists partly to tell you what an implicit is worth.
    Half the table was blank: 64 shipped bases have an implicit in the game's
    own data and only 37 displayed one, so Corona Amulet (grants a HELMET
    socket) and Grasping Ring (a GLOVE socket) — facts that change how you use
    the item — showed nothing at all.

    Guarded against the GGPK dump so a future base can't quietly ship blank.
    """
    import glob
    import json as _json

    dumps = glob.glob(os.path.join(_ROOT, "dist", "**", "gamedata_cache",
                                   "base_items.min.json"), recursive=True)
    if not dumps:
        pytest.skip("GGPK base-item dump not present in this checkout")

    from exilebot_pickit.data.implicits.implicits import BASE_IMPLICITS

    with open(dumps[0], encoding="utf-8") as f:
        items = _json.load(f)
    has_implicit = {v["name"] for v in items.values()
                    if v.get("name") and v.get("implicits")}

    # accessories live in their own frozenset, not in _BASE_TYPES_BY_CATEGORY —
    # leaving them out made every ring and amulet look like an orphan entry.
    shipped = ({n for ents in bt._BASE_TYPES_BY_CATEGORY.values() for n, _s in ents}
               | set(corr.EXOTIC_BASES) | set(gen._ACCESSORY_BASES))
    blank = sorted(n for n in shipped if n in has_implicit and n not in BASE_IMPLICITS)
    assert not blank, f"shipped bases whose implicit we'd render blank: {blank}"

    # and nothing in the table may point at a base we don't ship
    orphans = sorted(n for n in BASE_IMPLICITS if n not in shipped)
    assert not orphans, f"implicits for bases we don't ship: {orphans}"


def test_percent_implicits_actually_say_percent():
    """The stat id carries the unit, and three entries dropped it — Grand Spear
    read "+25 Weapon range" for local_+%_weapon_range, i.e. a flat 25 rather
    than +25%. Anything whose game stat id contains "+%" or "_-%" must show a
    % sign, or the number means something entirely different to the reader."""
    import glob
    import json as _json

    cache = glob.glob(os.path.join(_ROOT, "dist", "**", "gamedata_cache"),
                      recursive=True)
    if not cache:
        pytest.skip("GGPK dump not present in this checkout")
    with open(os.path.join(cache[0], "base_items.min.json"), encoding="utf-8") as f:
        items = _json.load(f)
    with open(os.path.join(cache[0], "mods.min.json"), encoding="utf-8") as f:
        mods = _json.load(f)

    from exilebot_pickit.data.implicits.implicits import BASE_IMPLICITS

    offenders = []
    for v in items.values():
        name = v.get("name")
        if name not in BASE_IMPLICITS or not v.get("implicits"):
            continue
        ids = [s.get("id", "") for mid in v["implicits"]
               for s in ((mods.get(mid) or {}).get("stats") or [])]
        pct = [i for i in ids if "+%" in i or "_-%" in i or "%_" in i]
        if pct and "%" not in BASE_IMPLICITS[name]:
            offenders.append((name, BASE_IMPLICITS[name], pct[0]))
    assert not offenders, f"percentage implicits shown without a % sign: {offenders}"


def test_special_items_cover_the_unpriced_pinnacle_keys():
    """SPECIAL_ITEMS is the ONLY route to a rule for something poe.ninja doesn't
    price — almost every other rule this app writes comes from a price.

    Raven's Reflection (the Delirium pinnacle key, dropped from Simulacrum) had
    no rule at all for exactly that reason: unpriced in every category, and not
    named here. The owner noticed it missing from his pickit in-game. An unpriced
    valuable is invisible to the whole pipeline unless it is in this list.
    """
    assert "Raven's Reflection" in corr.SPECIAL_ITEMS

    rules = "\n".join(gen.build_special_item_rules(set()))
    for name in corr.SPECIAL_ITEMS:
        assert f'[Type] == "{name}"' in rules, f"{name} emits no rule"
    assert gen.validate_pickit(gen.build_special_item_rules(set()))["errors"] == []
