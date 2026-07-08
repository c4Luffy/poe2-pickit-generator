"""Fracture Bases: verified-target lookup table shape and exclusion rules."""
from exilebot_pickit import generator as gen


def _names():
    return [n for _g, ns in gen.FRACTURE_CLASS_GROUPS for n in ns]


def test_class_roadmap_unchanged_by_the_swap():
    # Fracture Bases reuses the same 22-class, game-ordered roadmap as before.
    names = _names()
    assert len(names) == 22 and len(set(names)) == len(names)
    for banned in ("Talismans", "Bucklers", "Claws", "Daggers", "Flails"):
        assert banned not in names


def test_every_target_is_well_formed():
    assert len(gen.FRACTURE_TARGETS) >= 10
    for t in gen.FRACTURE_TARGETS:
        assert t["tier"] in gen.FRACTURE_TIERS
        assert t["classes"] and all(c in _names() for c in t["classes"])
        assert t["affix"] in ("prefix", "suffix")
        assert t["text"] and t["reason"]


def test_gloves_crit_chance_excluded_no_such_mod_in_data():
    # The spec's own rule: don't match anything not verified from data. Gloves
    # only roll Critical DAMAGE, never Critical CHANCE, so gloves must not
    # appear in the crit-chance targets.
    crit_targets = [t for t in gen.FRACTURE_TARGETS if "crit_chance" in t["id"]]
    assert crit_targets
    for t in crit_targets:
        assert "Gloves" not in t["classes"]
    assert "crit_chance_gloves" in gen.FRACTURE_EXCLUDED_UNVERIFIED


def test_quiver_target_is_the_real_t1_not_the_assumed_one():
    # Spec assumed +1 was the quiver max; live data shows T1 is actually +2.
    q = [t for t in gen.FRACTURE_TARGETS if t["id"] == "quiver_projectile"][0]
    assert q["value"] == "+2"


def test_amulet_skill_level_is_t1_only():
    a = [t for t in gen.FRACTURE_TARGETS if t["id"] == "amulet_skill_level"][0]
    assert a["mod_tier"] == "T1" and a["value"] == "+3"


def test_helmet_rarity_is_magic_only_prefix():
    r = [t for t in gen.FRACTURE_TARGETS if t["id"] == "rarity_helmet"][0]
    assert r["magic_only"] is True
    assert r["affix"] == "prefix"


def test_fracture_targets_for_class_sorted_by_priority():
    targets = gen.fracture_targets_for_class("Bows")
    assert targets
    order = {"S+": 0, "S": 1, "A+": 2, "A": 3}
    tiers = [order[t["tier"]] for t in targets]
    assert tiers == sorted(tiers)


def test_class_with_no_verified_target_returns_empty():
    # e.g. Charms/Jewels/Flasks have no verified fracture target in this data
    assert gen.fracture_targets_for_class("Charms") == []


def test_score_formula():
    assert gen.fracture_score("S+", explicit_mod_count=3, magic_match=False, meta_base=False) == 100
    assert gen.fracture_score("S", explicit_mod_count=4, magic_match=False, meta_base=False) == 95
    assert gen.fracture_score("A+", explicit_mod_count=4, magic_match=True, meta_base=True) == 60 + 15 + 10 + 10
