"""Rare-tab skeleton: the roadmap is well-formed and emits nothing until a
class design is approved (gen.RARE_DESIGNED)."""
from exilebot_pickit import generator as gen
from exilebot_pickit.generators import assembly as asm


def test_rare_groups_are_well_formed():
    names = [n for _g, ns in gen.RARE_CLASS_GROUPS for n in ns]
    assert len(names) == 22, names
    assert len(set(names)) == len(names)          # no duplicates
    # owner-banned + unreleased classes must never appear
    for banned in ("Talismans", "Bucklers", "Claws", "Daggers", "Flails",
                   "One Hand Swords", "Two Hand Swords", "One Hand Axes",
                   "Two Hand Axes", "Traps"):
        assert banned not in names


def test_rare_section_emits_nothing_until_designed():
    assert gen.RARE_DESIGNED == {}                # skeleton state
    assert asm.rare_section({"item_states": {}}) == []
    assert asm.rare_section({}) == []
