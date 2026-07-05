"""Remote game-data v2: static always-pick sections come from data, not code."""

import json
import os

from exilebot_pickit import generator as gen
from exilebot_pickit.data import corrections as corr
from exilebot_pickit.data import remote_data as rd

_ROOT = os.path.join(os.path.dirname(__file__), "..")


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
