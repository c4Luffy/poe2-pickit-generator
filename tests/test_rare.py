"""Rare tab: roadmap shape, T1/T2-only rule emission, per-class ilvl clamps."""
from exilebot_pickit import generator as gen
from exilebot_pickit.generators import assembly as asm


def _names():
    return [n for _g, ns in gen.RARE_CLASS_GROUPS for n in ns]


def test_rare_groups_are_well_formed():
    names = _names()
    assert len(names) == 22, names
    assert len(set(names)) == len(names)
    for banned in ("Talismans", "Bucklers", "Claws", "Daggers", "Flails",
                   "One Hand Swords", "Two Hand Swords", "One Hand Axes",
                   "Two Hand Axes", "Traps"):
        assert banned not in names
    assert set(names) == set(gen.RARE_DESIGNED)


def test_default_rules_are_valid():
    lines = gen.build_rare_rules({})
    rules = [l for l in lines if l.startswith("[")]
    assert len(rules) > 30
    v = gen.validate_pickit(lines)
    assert v["errors"] == [] and v["warnings"] == []
    for r in rules:
        assert '[StashItem] == "true"' in r and "#" in r
    body = [r for r in rules if '"BodyArmour"' in r]
    assert body and all('[Rarity] == "Rare"' in r for r in body)
    # T1/T2 thresholds: body armour life route uses the T2 minimum (190)
    assert any('[base_maximum_life] >= "190"' in r for r in body)
    assert all('# [ItemLevel] >= "80"' in r for r in body)


def test_skill_level_mods_are_covered():
    lines = "\n".join(gen.build_rare_rules({}))
    assert '[bow_skill_gem_level_] >= "4"' in lines          # bows
    assert '[melee_skill_gem_level_] >= "5"' in lines        # quarterstaves/2h
    assert '[all_skill_gem_level_] >= "3"' in lines          # amulets (T1 only)
    assert '[spell_skill_gem_level_] >= "4"' in lines        # casters


def test_disabled_classes_emit_nothing():
    off = {n: {"enabled": False} for n in _names()}
    assert gen.build_rare_rules(off) == []
    assert asm.rare_section({"item_states": {"_rare": off}}) == []


def test_ilvl_is_clamped_to_80_82():
    st = {"Body Armours": {"enabled": True, "ilvl": 99},
          "Gloves": {"enabled": True, "ilvl": 12}}
    lines = gen.build_rare_rules(st)
    assert any('"BodyArmour"' in l and '[ItemLevel] >= "82"' in l for l in lines)
    assert any('"Gloves"' in l and '[ItemLevel] >= "80"' in l for l in lines)


def test_small_classes_have_no_ilvl_gate():
    lines = gen.build_rare_rules({"Jewels": {"enabled": True}})
    jl = [l for l in lines if '"Jewel"' in l]
    assert jl and all("[ItemLevel]" not in l for l in jl)
    assert any("Time-Lost Emerald" in l for l in lines)
