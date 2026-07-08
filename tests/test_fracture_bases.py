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


def test_quiver_target_is_the_real_t1():
    # Live CoE data has exactly ONE projectile-skill mod on Quiver: +1. It is
    # simultaneously the min and max roll, so it is T1 by definition — the
    # original spec's +1 assumption was correct.
    q = [t for t in gen.FRACTURE_TARGETS if t["id"] == "quiver_projectile"][0]
    assert q["value"] == "+1"


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


def test_gloves_has_crit_damage_and_melee_but_not_crit_chance():
    g = gen.fracture_targets_for_class("Gloves")
    ids = [t["id"] for t in g]
    assert "crit_damage_gloves" in ids
    assert "melee_skill_level_gloves" in ids
    assert not any("crit_chance" in i for i in ids)


def test_sceptre_has_both_t1_and_t2_skill_level():
    s = gen.fracture_targets_for_class("Sceptres")
    ids = {t["id"]: t for t in s}
    assert ids["weapon_skill_level_sceptre"]["mod_tier"] == "T1"
    assert ids["weapon_skill_level_sceptre"]["value"] == "+4"
    assert ids["weapon_skill_level_sceptre_t2"]["mod_tier"] == "T2"
    assert ids["weapon_skill_level_sceptre_t2"]["value"] == "+3"
    # T2 is Sceptre-only — every other class keeps exactly one skill-level tier
    other_multi = [t for t in gen.FRACTURE_TARGETS
                   if t["id"].startswith("weapon_skill_level_") and "sceptre" not in t["id"]]
    ids_seen = [t["id"].replace("_t2", "") for t in other_multi]
    assert len(ids_seen) == len(set(ids_seen))


def test_wand_staff_use_the_stronger_element_specific_skill_mod():
    wand = [t for t in gen.FRACTURE_TARGETS if t["id"] == "weapon_skill_level_wand"][0]
    staff = [t for t in gen.FRACTURE_TARGETS if t["id"] == "weapon_skill_level_staff"][0]
    assert wand["value"] == "+5"      # beats the generic +4 all-Spell-Skills roll
    assert staff["value"] == "+7"     # beats the generic +5-6 all-Spell-Skills roll


def test_focus_minion_excluded_desecrated_pool_only():
    # The only +Minion Skills mod on Focus comes from the Desecrated pool
    # (a boss mechanic), not the natural Base mod pool — must be excluded.
    focus_targets = gen.fracture_targets_for_class("Foci")
    assert all("minion" not in t["id"] for t in focus_targets)
    assert "focus_minion" in gen.FRACTURE_EXCLUDED_UNVERIFIED


def test_score_formula():
    assert gen.fracture_score("S+", explicit_mod_count=3, magic_match=False, meta_base=False) == 100
    assert gen.fracture_score("S", explicit_mod_count=4, magic_match=False, meta_base=False) == 95
    assert gen.fracture_score("A+", explicit_mod_count=4, magic_match=True, meta_base=True) == 60 + 15 + 10 + 10
