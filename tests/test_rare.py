"""Rare stat-menu integrity: every id must be a real bot stat id, no dupes."""

import glob
import json
import os
import re

import pytest

from exilebot_pickit.data.bot_stat_ids import BOT_STAT_IDS
from exilebot_pickit.data import rare
from exilebot_pickit.data.rare import rules as rare_rules
from exilebot_pickit import generator as gen

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The game's own item_class for each rare-gear slot. The slot name is OUR label,
# so a few legitimately differ: Quarterstaff items are class "Warstaff", and the
# Mace slot deliberately covers both mace classes (owner call 2026-07-12).
_SLOT_ITEM_CLASSES = {
    "Body Armour": {"Body Armour"},
    "Helmet": {"Helmet"},
    "Gloves": {"Gloves"},
    "Boots": {"Boots"},
    "Amulet": {"Amulet"},
    "Ring": {"Ring"},
    "Belt": {"Belt"},
    "Focus": {"Focus"},
    "Quiver": {"Quiver"},
    "Bow": {"Bow"},
    "Crossbow": {"Crossbow"},
    "Quarterstaff": {"Warstaff"},
    "Spear": {"Spear"},
    "Mace": {"One Hand Mace", "Two Hand Mace"},
    "Sceptre": {"Sceptre"},
    "Wand": {"Wand"},
    "Staff": {"Staff"},
}

_UNIQUE_PATH = re.compile(r"Unique\d*$")


def _load_base_item_dump():
    """The GGPK base-item table, keyed by metadata path. None if not vendored."""
    dumps = glob.glob(os.path.join(_ROOT, "dist", "**", "gamedata_cache",
                                   "base_items.min.json"), recursive=True)
    if not dumps:
        return None
    with open(dumps[0], encoding="utf-8") as f:
        return json.load(f)


def test_every_stat_id_is_valid_in_bot_modslist():
    bad = {name: sid
           for section in rare.STAT_MENU.values()
           for name, sid in section.items()
           if sid not in BOT_STAT_IDS}
    assert not bad, f"stat ids not in bot ModsList: {bad}"


def test_every_base_we_name_is_in_the_validator_whitelist():
    """Every base a rare-gear recipe or a Fracture base override names must be
    accepted by VALID_EQUIPMENT_BASES.

    These rules carry no quality/sockets gate, so validate_pickit skips the
    base-name check for them — meaning a typo or a newly-added base passes
    silently today and only breaks the day someone adds a gate. Five ring bases
    (Biostatic + the four modifier-count rings) slipped through exactly this way
    in v4.11.4; this test is the guard.
    """
    from exilebot_pickit.data.fracture_bases import fracture_bases as fb
    used = {b for spec in rare_rules.RARE_GEAR.values() for b in spec["bases"]}
    used |= {b for bases in fb._FRACTURE_BASE_OVERRIDES.values() for b in bases}
    missing = sorted(b for b in used if b not in gen.VALID_EQUIPMENT_BASES)
    assert not missing, f"bases missing from VALID_EQUIPMENT_BASES: {missing}"


def test_every_rare_gear_base_can_actually_drop_as_a_rare():
    """Cross-check every RARE_GEAR base against the game's own item table.

    A rare recipe naming a base that cannot drop as a rare is a dead rule: it
    emits a [Type] line the bot will never match. Three dead-name classes exist,
    and all three are invisible by eye — the names look like ordinary bases:

    * unique-only — every metadata path for the name ends in ``...Unique<N>``.
      The base exists solely to host one unique (e.g. FourStaffUnique3 =
      "Reflecting Staff", which is only ever Atziri's Rule). No white/magic/rare
      one ever drops. Three of these reached the white-base, rare and craft
      lists on 2026-07-19.
    * anvil-only — "Runeforged "/"Runemastered " items are crafted at an anvil
      and never drop.
    * absent — the name is not in the game data at all (typo, or removed by a
      patch).

    IMPORTANT — "unique-only" means ALL of a name's paths are Unique-suffixed.
    Several names have both a unique-hosting path AND ordinary droppable ones:
    "Shrine Sceptre" is FourSceptreUnique1 *and* FourSceptre6a/6b/6c (three
    normal variants granting different Purity skills). Testing "any path
    contains Unique" would condemn it wrongly, so this test groups by name
    first. The item_class check catches the fourth failure mode: a base filed
    under the wrong slot, which would emit a rule whose stat weights can never
    roll on it.
    """
    items = _load_base_item_dump()
    if items is None:
        pytest.skip("GGPK base-item dump not present in this checkout")

    paths_by_name = {}
    class_by_name = {}
    for path, v in items.items():
        name = v.get("name")
        if not name:
            continue
        paths_by_name.setdefault(name, []).append(path)
        class_by_name.setdefault(name, set()).add(v.get("item_class"))

    dead, wrong_class = [], []
    for slot, spec in rare_rules.RARE_GEAR.items():
        assert spec["bases"], f"{slot} has no bases — every slot must emit at least one rule"
        for base in spec["bases"]:
            paths = paths_by_name.get(base)
            if not paths:
                dead.append(f"{slot}/{base}: absent from the game's item table")
                continue
            if all(_UNIQUE_PATH.search(p) for p in paths):
                dead.append(f"{slot}/{base}: unique-only, no rare ever drops ({paths[0]})")
                continue
            if base.startswith(("Runeforged ", "Runemastered ")):
                dead.append(f"{slot}/{base}: anvil-crafted, never drops ({paths[0]})")
                continue
            allowed = _SLOT_ITEM_CLASSES.get(slot)
            if allowed and not (class_by_name[base] & allowed):
                wrong_class.append(
                    f"{slot}/{base}: item_class {sorted(class_by_name[base])} not in {sorted(allowed)}")

    assert not dead, "rare-gear recipes name bases that can never drop as rares: " + "; ".join(dead)
    assert not wrong_class, "rare-gear bases filed under the wrong slot: " + "; ".join(wrong_class)


def test_slot_item_class_map_covers_every_wired_slot():
    """If a new slot is wired without an entry here, the class check above would
    silently skip it. Fail loudly instead."""
    missing = sorted(set(rare_rules.RARE_GEAR) - set(_SLOT_ITEM_CLASSES))
    assert not missing, f"slots with no expected item_class: {missing}"


def test_menu_has_all_sections():
    assert set(rare.STAT_MENU) == {
        "Defensive: Life / Mana / ES",
        "Defensive: Armour / Evasion / Block",
        "Resistances",
        "Utility",
        "Caster",
        "Attack / Weapon",
        "Skill Gem Levels",
    }


def test_no_duplicate_ids_within_a_section():
    for title, section in rare.STAT_MENU.items():
        ids = list(section.values())
        assert len(ids) == len(set(ids)), f"duplicate id in section {title!r}"


def test_all_skill_gem_level_is_excluded():
    # desecration/unique-only mod — must never be offered as a normal rare roll
    assert "all_skill_gem_level_+" not in rare.all_stat_ids()


def test_not_available_documents_the_unmapped_mods():
    assert rare.NOT_AVAILABLE and all(v for v in rare.NOT_AVAILABLE.values())


def test_rare_gear_rules_are_valid_and_use_real_stat_ids():
    # Every wired rare-gear slot must emit rules that pass the bot validator,
    # and every weighted/gated stat id must be a real bot stat id.
    for slot in rare_rules.rare_gear_slots():
        lines = rare_rules.rare_gear_example_lines(slot)
        assert lines, f"{slot} produced no rules"
        result = gen.validate_pickit(lines)
        assert not result["errors"], f"{slot} rules invalid: {result['errors']}"
        spec = rare_rules.RARE_GEAR[slot]
        for sid in list(spec["weights"]) + list(spec.get("gates", {})):
            assert sid in BOT_STAT_IDS, f"{slot} uses unknown stat id {sid}"
