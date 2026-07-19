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
    assert '[Type] == "Runic Fork" # [StashItem] == "true"' in exo
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
    """
    import glob
    import json as _json

    dumps = glob.glob(os.path.join(_ROOT, "dist", "**", "gamedata_cache",
                                   "base_items.min.json"), recursive=True)
    if not dumps:
        pytest.skip("GGPK base-item dump not present in this checkout")

    with open(dumps[0], encoding="utf-8") as f:
        items = _json.load(f)
    unique_only = {v["name"] for k, v in items.items()
                   if v.get("name") and "Unique" in k.rsplit("/", 1)[-1]}

    offenders = [(cat, n) for cat, entries in bt._BASE_TYPES_BY_CATEGORY.items()
                 for n, _s in entries if n in unique_only]
    assert not offenders, (
        "unique-only bases in the Exceptional list — a white one never drops, so "
        f"these rules can never fire: {offenders}")
