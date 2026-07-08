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


def test_shields_still_has_no_targets_by_design():
    assert gen.fracture_targets_for_class("Shields") == []


def test_body_helmet_boots_have_no_pure_armour_targets():
    # Owner rule: ES/Evasion/Hybrid only across these three classes, never Armour.
    for cls in ("Body Armours", "Helmets", "Boots"):
        for t in gen.fracture_targets_for_class(cls):
            assert "Armour" not in t["text"] or "no Armour" in t["text"]


def test_staff_sigil_of_power_excluded_not_found_anywhere():
    ids = [t["id"] for t in gen.fracture_targets_for_class("Staves")]
    assert not any("sigil" in i for i in ids)
    assert "staff_sigil_of_power" in gen.FRACTURE_EXCLUDED_UNVERIFIED


def test_quiver_now_has_the_full_requested_set():
    ids = {t["id"] for t in gen.fracture_targets_for_class("Quivers")}
    assert {"quiver_projectile", "quiver_crit_chance_attacks", "quiver_crit_dmg_attacks",
            "quiver_bow_dmg", "quiver_proj_speed", "quiver_added_lightning"} <= ids


def test_sceptre_has_spirit_allies_and_minion_life_alongside_skill_level():
    ids = {t["id"] for t in gen.fracture_targets_for_class("Sceptres")}
    assert {"weapon_skill_level_sceptre", "weapon_skill_level_sceptre_t2",
            "sceptre_spirit", "sceptre_allies_dmg", "sceptre_minion_life"} <= ids


def test_belt_has_life_mana_and_all_four_resists():
    ids = {t["id"] for t in gen.fracture_targets_for_class("Belts")}
    assert {"belt_life", "belt_mana", "belt_resist"} <= ids


def test_example_rule_is_well_formed_and_labelled_illustrative():
    for tgt in gen.FRACTURE_TARGETS:
        line = gen.fracture_example_rule(tgt)
        assert line.startswith('[Category] ==')
        assert '[StashItem] == "true"' in line
        assert "FRACTURE BASES EXAMPLE" in line or "FRACTURE BASES EXAMPLE" in line.split("//")[-1]             or "unverified" in line
        # never a fabricated stat id for targets with no verified mapping
        if gen._FRACTURE_VERIFIED_STAT_IDS.get(tgt["id"]) in (None, "__unset__") and tgt["id"] != "amulet_skill_level":
            assert "UNVERIFIED_STAT_ID" in line


def test_verified_stat_ids_only_used_where_actually_confirmed():
    # Spot-check: movement speed and spirit use their confirmed bot ids.
    move_line = gen.fracture_example_rule(gen._FRACTURE_TARGETS_BY_ID["movement_speed"])
    assert "base_movement_velocity_+%" in move_line
    spirit_line = gen.fracture_example_rule(gen._FRACTURE_TARGETS_BY_ID["spirit_body"])
    assert "local_spirit_+%" in spirit_line
    # crit chance has no confirmed id -> must show the honest placeholder, not a guess
    crit_line = gen.fracture_example_rule(gen._FRACTURE_TARGETS_BY_ID["crit_chance_weapon"])
    assert "UNVERIFIED_STAT_ID" in crit_line


# ── Item classification samples (spec section 10) ──
# classify_fracture_item is a pure scoring helper only — it does NOT drive
# pickit/bot output. Fracture Bases never generates rules; see the module
# docstring on FRACTURE_TARGETS.

def test_magic_boots_t1_movement_is_prep_candidate():
    r = gen.classify_fracture_item("Boots", "Magic", ["movement_speed"], explicit_mod_count=1)
    assert r["verdict"] == "prep_candidate"
    assert r["matches"]


def test_rare_boots_t1_movement_4_explicits_is_best_fracture_setup():
    r = gen.classify_fracture_item("Boots", "Rare", ["movement_speed"], explicit_mod_count=4)
    assert r["verdict"] == "fracture_candidate"
    assert r["warning"] is None
    assert r["score"] == gen.FRACTURE_TIERS["S"] + 15   # +15 for exactly 4 explicits


def test_magic_helmet_rarity_prefix_is_prep_candidate():
    r = gen.classify_fracture_item("Helmets", "Magic", ["rarity_helmet"], explicit_mod_count=1)
    assert r["verdict"] == "prep_candidate"
    assert r["matches"]


def test_rare_helmet_rarity_ignored_by_magic_only_rule():
    r = gen.classify_fracture_item("Helmets", "Rare", ["rarity_helmet"], explicit_mod_count=1)
    assert r["verdict"] == "ignored"
    assert r["matches"] == []


def test_wand_natural_top_tier_spell_skills_is_valid():
    r = gen.classify_fracture_item("Wands", "Rare", ["weapon_skill_level_wand"], explicit_mod_count=3)
    assert r["verdict"] == "fracture_candidate"
    assert r["matches"]


def test_wand_essence_spell_skills_is_ignored():
    # An Essence-sourced +spell-skills mod is NOT a valid target id at all —
    # there is no "essence_*" entry in FRACTURE_TARGETS, so passing one in
    # (as an app would after correctly excluding it upstream) matches nothing.
    r = gen.classify_fracture_item("Wands", "Rare", ["essence_spell_skills"], explicit_mod_count=3)
    assert r["verdict"] == "ignored"
    assert r["matches"] == []


def test_weapon_t1_phys_is_valid():
    r = gen.classify_fracture_item("Bows", "Rare", ["inc_phys_weapon"], explicit_mod_count=4)
    assert r["verdict"] == "fracture_candidate"
    assert r["matches"]


def test_weapon_hybrid_phys_accuracy_only_is_ignored():
    # "#% increased Physical Damage, +# to Accuracy Rating" is a real live mod
    # but it is NOT one of the approved targets (hybrid, not the pure T1 phys%
    # target) — not in FRACTURE_TARGETS, so it is ignored, exactly like the
    # spec's "ignored unless explicitly allowed later" instruction.
    r = gen.classify_fracture_item("Bows", "Rare", ["hybrid_phys_accuracy"], explicit_mod_count=4)
    assert r["verdict"] == "ignored"


def test_excluded_generic_categories_never_match_anything():
    # elemental/spell/generic/chaos damage and damage-with-ailments are not
    # represented as FRACTURE_TARGETS ids anywhere (except the specific,
    # already-approved wand/staff spell-damage targets) — any attempt to pass
    # a generic id for these categories matches nothing.
    for fake_id in ("elemental_damage_generic", "spell_damage_generic",
                     "generic_damage", "chaos_damage_generic",
                     "damage_with_ailments"):
        r = gen.classify_fracture_item("Wands", "Rare", [fake_id], explicit_mod_count=3)
        assert r["verdict"] == "ignored", fake_id
        assert r["matches"] == []


def test_more_than_4_explicits_warns_but_can_still_match():
    r = gen.classify_fracture_item("Boots", "Rare", ["movement_speed"], explicit_mod_count=5)
    assert r["verdict"] == "fracture_candidate"
    assert r["warning"] == "more than 4 explicit modifiers"


def test_score_formula():
    assert gen.fracture_score("S+", explicit_mod_count=3, magic_match=False, meta_base=False) == 100
    assert gen.fracture_score("S", explicit_mod_count=4, magic_match=False, meta_base=False) == 95
    assert gen.fracture_score("A+", explicit_mod_count=4, magic_match=True, meta_base=True) == 60 + 15 + 10 + 10


# ── Pickit-rule wiring (build_fracture_pickit_rules) ──
# Classes default to enabled (owner preference), so isolating "only this one
# class" requires explicitly disabling every other class in the states dict.

def _all_off(**overrides):
    states = {cls: {"enabled": False}
              for _g, classes in gen.FRACTURE_CLASS_GROUPS for cls in classes}
    for cls, en in overrides.items():
        states[cls] = {"enabled": en}
    return states


def test_no_classes_enabled_emits_nothing():
    assert gen.build_fracture_pickit_rules(_all_off()) == []
    assert gen.build_fracture_pickit_rules(_all_off(Boots=False)) == []


def test_disabled_class_emits_nothing():
    lines = gen.build_fracture_pickit_rules(_all_off(Boots=False))
    assert lines == []


def test_class_missing_from_states_defaults_to_enabled():
    # A class absent from the states dict entirely (e.g. never toggled by the
    # user) must still emit its rule, matching the "on by default" UI value —
    # regression test for a bug where missing == disabled at generate time.
    lines = gen.build_fracture_pickit_rules({})
    assert any("base_movement_velocity_+%" in l for l in lines)


def test_enabled_class_with_verified_target_emits_valid_rule():
    lines = gen.build_fracture_pickit_rules(_all_off(Boots=True))
    assert lines
    rule_lines = [l for l in lines
                  if l.startswith("[Category]") or l.startswith("[WeaponCategory]") or l.startswith("(")]
    assert rule_lines
    assert any("base_movement_velocity_+%" in l for l in rule_lines)
    result = gen.validate_pickit(lines)
    assert result["errors"] == []
    for l in rule_lines:
        assert '[StashItem] == "true"' in l
        assert "UNVERIFIED_STAT_ID" not in l


def test_narrowed_selector_only_matches_top_bases_not_whole_category():
    # Boots has real exceptional-base data -> the wired rule must be narrowed
    # to an OR of specific [Type] names, never the old whole-category match.
    lines = gen.build_fracture_pickit_rules(_all_off(Boots=True))
    rule = next(l for l in lines if "base_movement_velocity_+%" in l)
    assert '[Type] ==' in rule
    assert rule.count('[Type] ==') <= 4
    assert '[Category] == "Boots"' not in rule


def test_class_with_only_unverified_targets_emits_nothing_even_when_enabled():
    # Charms/Jewels/Flasks have no fracture targets at all -> nothing to wire.
    lines = gen.build_fracture_pickit_rules(_all_off(Charms=True))
    assert lines == []
    lines = gen.build_fracture_pickit_rules(_all_off(Jewels=True))
    assert lines == []


def test_shields_enabled_emits_nothing_no_targets():
    assert gen.build_fracture_pickit_rules(_all_off(Shields=True)) == []


def test_amulets_enabled_emits_or_of_four_skill_families():
    lines = gen.build_fracture_pickit_rules(_all_off(Amulets=True))
    assert lines
    rule = [l for l in lines if l.startswith("[Category]")][0]
    for sid in gen._AMULET_SKILL_IDS:
        assert sid in rule
    assert "UNVERIFIED_STAT_ID" not in rule
    result = gen.validate_pickit(lines)
    assert result["errors"] == []


def test_all_wired_targets_use_real_verified_stat_ids_never_placeholder():
    all_states = {cls: {"enabled": True} for _g, classes in gen.FRACTURE_CLASS_GROUPS for cls in classes}
    lines = gen.build_fracture_pickit_rules(all_states)
    assert lines
    for l in lines:
        assert "UNVERIFIED_STAT_ID" not in l
    result = gen.validate_pickit(lines)
    assert result["errors"] == []


def test_fracture_default_is_enabled():
    # Owner preference: every class defaults ON, wired or not — a not-yet-wired
    # class emits no rules regardless (no verified stat id to build a
    # condition from), so the flag only has real effect once it's wired.
    assert gen.fracture_default("Boots") == {"enabled": True}
    assert gen.fracture_default("Shields") == {"enabled": True}


def test_fracture_has_verified_target():
    assert gen.fracture_has_verified_target("Boots") is True
    assert gen.fracture_has_verified_target("Amulets") is True
    assert gen.fracture_has_verified_target("Shields") is False
    assert gen.fracture_has_verified_target("Charms") is False
