"""Mod-weight templates for the Rare Gear tab's Per-base mode.

Weights are transcribed from a hand-tuned community pickit the user supplied
(verified in-bot), composed per (family, defence combo):

- ``full``   — every mod the section scores (the main rule).
- ``prefix`` / ``suffix`` — subsets for the auto-derived prefix-only /
  suffix-only rules (None → the family has no P/S split).
- ``thr``    — default full-rule threshold; prefix/suffix thresholds are
  derived at PREFIX_PCT / SUFFIX_PCT of it.
- ``tier``   — default [ItemTier] gate per bracket (low bases demand a higher
  tier variant; endgame bases can pass at lower tiers).
- ``magic``  — (stat, weight, threshold) single-mod Magic pickup, or None.

Note: Per-base mode does NOT apply the Simple mode's global min item level —
the low/mid/high brackets and [ItemTier] gates do that job (an ilvl gate would
nuke the leveling brackets entirely).
"""
import poe2_pickit_generator as gen

PREFIX_PCT = 0.60
SUFFIX_PCT = 0.55

DEFAULT_TIERS = {"low": 4, "mid": 3, "high": 2}

# ── Shared mod pools (weights from the user's tuned pickit) ───────────────────
_LIFE       = [("base_maximum_life", 0.67)]
_LIFE_HELM  = [("base_maximum_life", 0.57)]
_RES        = [("base_fire_damage_resistance_%", 2.22),
               ("base_cold_damage_resistance_%", 2.22),
               ("base_lightning_damage_resistance_%", 2.22),
               ("base_chaos_damage_resistance_%", 3.70)]
_RARITY     = [("base_item_found_rarity_+%", 4.00)]
_ARM_HYBRID = [("armour_%_applies_to_fire_cold_lightning_damage", 2.33)]
_EVA_DEFLECT = [("base_deflection_rating_%_of_evasion_rating", 4.35)]
_ADDED_ATK  = [("attack_minimum_added_physical_damage", 2.63),
               ("attack_maximum_added_physical_damage", 1.56),
               ("attack_maximum_added_lightning_damage", 1.41),
               ("attack_minimum_added_fire_damage", 1.72),
               ("attack_maximum_added_fire_damage", 1.11),
               ("attack_minimum_added_cold_damage", 2.08),
               ("attack_maximum_added_cold_damage", 1.35)]

# Defence prefix mods per combo (armour slots).
_DEFENCE = {
    "armour":         [("local_base_physical_damage_reduction_rating", 0.63),
                       ("local_physical_damage_reduction_rating_+%", 1.00)],
    "evasion":        [("local_base_evasion_rating", 0.70),
                       ("local_evasion_rating_+%", 1.00)],
    "es":             [("local_energy_shield", 1.67),
                       ("local_energy_shield_+%", 1.00)],
    "armour_evasion": [("local_armour_and_evasion_+%", 1.00),
                       ("local_base_physical_damage_reduction_rating", 1.54),
                       ("local_base_evasion_rating", 0.70)],
    "armour_es":      [("local_armour_and_energy_shield_+%", 1.00),
                       ("local_base_physical_damage_reduction_rating", 1.54),
                       ("local_energy_shield", 1.67)],
    "evasion_es":     [("local_evasion_and_energy_shield_+%", 1.00),
                       ("local_base_evasion_rating", 1.75),
                       ("local_energy_shield", 1.67)],
    "tri":            [],
}

# Attribute suffixes matching a combo's stat requirements.
_ATTRS = {
    "armour":         [("additional_strength", 3.03)],
    "evasion":        [("additional_dexterity", 3.03)],
    "es":             [("additional_intelligence", 3.03)],
    "armour_evasion": [("additional_strength", 3.03), ("additional_dexterity", 3.03)],
    "armour_es":      [("additional_strength", 3.03), ("additional_intelligence", 3.03)],
    "evasion_es":     [("additional_dexterity", 3.03), ("additional_intelligence", 3.03)],
    "tri":            [("additional_strength", 3.03), ("additional_dexterity", 3.03),
                       ("additional_intelligence", 3.03)],
}


def _hybrids(combo):
    """Armour%-applies / deflection suffixes, per what the combo defends with."""
    out = []
    if "armour" in combo or combo == "tri":
        out += _ARM_HYBRID
    if "evasion" in combo or combo == "tri":
        out += _EVA_DEFLECT
    return out


def _armour_slot(combo, life, slot_prefix, slot_suffix, thr, magic=None):
    prefix = _DEFENCE[combo] + life + slot_prefix
    suffix = slot_suffix + _RES + _RARITY + _hybrids(combo) + _ATTRS[combo]
    if isinstance(thr, dict):
        thr = thr.get(combo, thr.get("default", 420))
    return {"full": prefix + suffix, "prefix": prefix, "suffix": suffix,
            "thr": thr, "tier": dict(DEFAULT_TIERS), "magic": magic}


# Body armour: explicit per-combo templates transcribed from the user's pickit
# (weights and prefix/suffix splits differ from the generic armour-slot pattern).
_BODY_SPIRIT = [("base_spirit_from_equipment", 1.64)]
_BODY_LIFE   = [("base_maximum_life", 0.47)]
_BODY = {
    "evasion": {
        "prefix": [("local_evasion_rating_+%", 0.91), ("local_base_evasion_rating", 0.40)]
                  + _BODY_LIFE + _BODY_SPIRIT,
        "suffix": _RES + [("base_deflection_rating_%_of_evasion_rating", 3.85)],
        "thr": 390, "p_thr": 243, "s_thr": 246,
    },
    "es": {
        "prefix": [("local_energy_shield_+%", 0.91), ("local_energy_shield", 1.04)]
                  + _BODY_SPIRIT,
        "suffix": [("base_lightning_damage_resistance_%", 2.22),
                   ("base_cold_damage_resistance_%", 2.22),
                   ("base_fire_damage_resistance_%", 2.22),
                   ("additional_intelligence", 3.03)],
        "thr": 390, "p_thr": 195, "s_thr": 255,
    },
    "armour": {
        "prefix": [("local_physical_damage_reduction_rating_+%", 0.91),
                   ("local_base_physical_damage_reduction_rating", 0.36)]
                  + _BODY_LIFE + _BODY_SPIRIT,
        "suffix": _RES + [("armour_%_applies_to_fire_cold_lightning_damage", 2.00),
                          ("additional_strength", 3.03)],
        "thr": 420, "p_thr": 285, "s_thr": 270,
    },
    "armour_evasion": {
        "prefix": [("local_base_physical_damage_reduction_rating", 0.72),
                   ("local_armour_and_evasion_+%", 0.91)] + _BODY_LIFE + _BODY_SPIRIT,
        "suffix": [("base_deflection_rating_%_of_evasion_rating", 3.85)] + _RES
                  + [("armour_%_applies_to_fire_cold_lightning_damage", 2.00)],
        "thr": 450, "p_thr": 270, "s_thr": 270,
    },
    "armour_es": {
        "prefix": [("local_armour_and_energy_shield_+%", 0.91),
                   ("local_base_physical_damage_reduction_rating", 0.72),
                   ("local_energy_shield", 2.08)] + _BODY_LIFE + _BODY_SPIRIT,
        "suffix": _RES + [("armour_%_applies_to_fire_cold_lightning_damage", 2.00)],
        "thr": 420, "p_thr": 255, "s_thr": 240,
    },
    "evasion_es": {
        "prefix": [("local_evasion_and_energy_shield_+%", 0.91),
                   ("local_base_evasion_rating", 0.79),
                   ("local_energy_shield", 2.08)] + _BODY_LIFE
                  + [("base_spirit_from_equipment", 1.97)],
        "suffix": [("additional_dexterity", 3.03), ("additional_intelligence", 3.03)]
                  + _RES + [("base_deflection_rating_%_of_evasion_rating", 3.85)],
        "thr": 420, "p_thr": 225, "s_thr": 255,
    },
}


def _body_template(combo):
    t = _BODY.get(combo)
    if not t:                                   # tri etc. → generic pattern
        return _armour_slot(combo, _BODY_LIFE, _BODY_SPIRIT, [], 420)
    return {"full": t["prefix"] + t["suffix"], "prefix": t["prefix"],
            "suffix": t["suffix"], "thr": t["thr"],
            "p_pct": t["p_thr"] / t["thr"], "s_pct": t["s_thr"] / t["thr"],
            "tier": dict(DEFAULT_TIERS), "magic": None}


# Shields & bucklers: the user's active shield weights — one block-gated pool
# shared by every shield class ("pre" is an extra post-# condition requiring an
# actual % block roll before the sum is scored). His endgame bases use tier 3;
# lower brackets keep stricter tier gates.
_SHIELD = {
    "full": [("local_block_chance_+%", 0.20),
             ("base_physical_damage_reduction_rating", 0.30),
             ("local_physical_damage_reduction_rating_+%", 0.20),
             ("local_armour_and_energy_shield_+%", 0.20),
             ("local_armour_and_evasion_+%", 0.20),
             ("base_maximum_life", 1.00),
             ("base_fire_damage_resistance_%", 2.00),
             ("base_cold_damage_resistance_%", 2.00),
             ("base_lightning_damage_resistance_%", 2.00),
             ("base_maximum_cold_damage_resistance_%", 15.00),
             ("base_maximum_fire_damage_resistance_%", 15.00),
             ("base_maximum_lightning_damage_resistance_%", 15.00),
             ("base_resist_all_elements_%", 6.00)],
    "prefix": None, "suffix": None,
    "thr": 260, "tier": {"low": 5, "mid": 4, "high": 3}, "magic": None,
    "pre": '[local_block_chance_+%] >= "1"',
}


# ── Weapon templates (from the user's pickit; melee derived from the bow set) ─
_BOW = {
    "full": [("local_physical_damage_+%", 0.56),
             ("elemental_damage_with_attack_skills_+%", 1.00),
             ("local_minimum_added_cold_damage", 0.62), ("local_maximum_added_cold_damage", 0.41),
             ("local_minimum_added_fire_damage", 0.50), ("local_maximum_added_fire_damage", 0.32),
             ("attack_maximum_added_lightning_damage", 0.43),
             ("local_minimum_added_physical_damage", 1.28), ("local_maximum_added_physical_damage", 0.76),
             ("local_attack_speed_+%", 5.26),
             ("local_critical_strike_multiplier_+", 4.00), ("local_critical_strike_chance", 0.20),
             ("projectile_skill_gem_level_+", 20.00), ("number_of_additional_arrows", 50.00)],
    "prefix": [("elemental_damage_with_attack_skills_+%", 1.00), ("local_physical_damage_+%", 0.56),
               ("local_minimum_added_cold_damage", 0.62), ("local_maximum_added_cold_damage", 0.41),
               ("local_minimum_added_fire_damage", 0.50), ("local_maximum_added_fire_damage", 0.32),
               ("attack_maximum_added_lightning_damage", 0.43),
               ("local_minimum_added_physical_damage", 1.28), ("local_maximum_added_physical_damage", 0.76)],
    "suffix": [("number_of_additional_arrows", 50.00), ("local_critical_strike_chance", 0.20),
               ("projectile_skill_gem_level_+", 20.00), ("local_critical_strike_multiplier_+", 4.00),
               ("local_attack_speed_+%", 5.26)],
    "thr": 330, "tier": dict(DEFAULT_TIERS),
    "magic": ("local_physical_damage_+%", 0.56, 87),
}

_CROSSBOW = {
    "full": [("elemental_damage_with_attack_skills_+%", 0.72), ("local_physical_damage_+%", 0.56),
             ("local_minimum_added_cold_damage", 0.40), ("local_maximum_added_cold_damage", 0.26),
             ("local_minimum_added_fire_damage", 0.32), ("local_maximum_added_fire_damage", 0.21),
             ("attack_maximum_added_lightning_damage", 0.28),
             ("local_minimum_added_physical_damage", 0.91), ("local_maximum_added_physical_damage", 0.53),
             ("local_attack_speed_+%", 5.26), ("projectile_skill_gem_level_+", 14.29),
             ("local_critical_strike_multiplier_+", 4.00), ("local_critical_strike_chance", 0.20),
             ("base_number_of_crossbow_bolts", 50.00)],
    "prefix": [("elemental_damage_with_attack_skills_+%", 0.72), ("local_physical_damage_+%", 0.56),
               ("local_minimum_added_cold_damage", 0.40), ("local_maximum_added_cold_damage", 0.26),
               ("local_minimum_added_fire_damage", 0.32), ("local_maximum_added_fire_damage", 0.21),
               ("attack_maximum_added_lightning_damage", 0.28),
               ("local_minimum_added_physical_damage", 0.91), ("local_maximum_added_physical_damage", 0.53)],
    "suffix": [("base_number_of_crossbow_bolts", 50.00), ("local_critical_strike_chance", 0.20),
               ("projectile_skill_gem_level_+", 14.29), ("local_critical_strike_multiplier_+", 4.00),
               ("local_attack_speed_+%", 5.26)],
    "thr": 378, "tier": dict(DEFAULT_TIERS),
    "magic": ("local_physical_damage_+%", 0.56, 87),
}


def _melee(gem_stat):
    """Martial melee weapon template (maces, flails — quarterstaves/spears have
    their own transcribed templates below)."""
    prefix = [("local_physical_damage_+%", 0.56),
              ("elemental_damage_with_attack_skills_+%", 1.00),
              ("local_minimum_added_cold_damage", 0.62), ("local_maximum_added_cold_damage", 0.41),
              ("local_minimum_added_fire_damage", 0.50), ("local_maximum_added_fire_damage", 0.32),
              ("attack_maximum_added_lightning_damage", 0.43),
              ("local_minimum_added_physical_damage", 1.28), ("local_maximum_added_physical_damage", 0.76)]
    suffix = [("local_attack_speed_+%", 5.26),
              ("local_critical_strike_multiplier_+", 4.00), ("local_critical_strike_chance", 0.20),
              (gem_stat, 20.00)]
    return {"full": prefix + suffix, "prefix": prefix, "suffix": suffix,
            "thr": 330, "tier": dict(DEFAULT_TIERS),
            "magic": ("local_physical_damage_+%", 0.56, 87)}


# Explicit weapon/off-hand templates transcribed from the user's pickit.
_QSTAFF_ADDED = [("local_minimum_added_cold_damage", 0.40), ("local_maximum_added_cold_damage", 0.26),
                 ("local_minimum_added_fire_damage", 0.32), ("local_maximum_added_fire_damage", 0.21),
                 ("attack_maximum_added_lightning_damage", 0.28),
                 ("local_minimum_added_physical_damage", 0.91), ("local_maximum_added_physical_damage", 0.53)]
_QSTAFF_SUFFIX = [("local_attack_speed_+%", 3.57), ("melee_skill_gem_level_+", 14.29),
                  ("local_critical_strike_multiplier_+", 4.00), ("local_critical_strike_chance", 0.20)]
_QSTAFF_PREFIX = ([("elemental_damage_with_attack_skills_+%", 0.72),
                   ("local_physical_damage_+%", 0.56)] + _QSTAFF_ADDED)
_QUARTERSTAFF = {"full": _QSTAFF_PREFIX + _QSTAFF_SUFFIX,
                 "prefix": _QSTAFF_PREFIX, "suffix": _QSTAFF_SUFFIX,
                 "thr": 330, "p_pct": 240 / 330, "s_pct": 225 / 330,
                 "tier": dict(DEFAULT_TIERS),
                 "magic": ("local_physical_damage_+%", 0.56, 87)}

_SPEAR_ADDED = [("local_minimum_added_fire_damage", 0.50), ("local_maximum_added_fire_damage", 0.32),
                ("local_minimum_added_cold_damage", 0.62), ("local_maximum_added_cold_damage", 0.41),
                ("local_minimum_added_physical_damage", 1.28), ("local_maximum_added_physical_damage", 0.76),
                ("attack_maximum_added_lightning_damage", 0.43)]
_SPEAR_SUFFIX = [("local_attack_speed_+%", 3.57), ("projectile_skill_gem_level_+", 20.00),
                 ("local_critical_strike_chance", 0.20), ("local_critical_strike_multiplier_+", 4.00)]
_SPEAR = {"full": ([("elemental_damage_with_attack_skills_+%", 1.00),
                    ("local_physical_damage_+%", 0.56), ("local_accuracy_rating", 0.09)]
                   + _SPEAR_ADDED + _SPEAR_SUFFIX),
          "prefix": ([("elemental_damage_with_attack_skills_+%", 1.00),
                      ("local_physical_damage_+%", 0.56)] + _SPEAR_ADDED),
          "suffix": _SPEAR_SUFFIX,
          "thr": 360, "p_pct": 255 / 360, "s_pct": 255 / 360,
          "tier": dict(DEFAULT_TIERS),
          "magic": ("local_physical_damage_+%", 0.56, 87)}

_WAND_DMG = [("chaos_damage_+%", 0.84), ("cold_damage_+%", 0.84), ("fire_damage_+%", 0.84),
             ("lightning_damage_+%", 0.84), ("spell_damage_+%", 0.84)]
_WAND_GAINS = [("non_skill_base_all_damage_%_to_gain_as_cold", 3.33),
               ("non_skill_base_all_damage_%_to_gain_as_fire", 3.33),
               ("non_skill_base_all_damage_%_to_gain_as_lightning", 3.33)]
_WAND_SUFFIX = [("spell_critical_strike_chance_+%", 1.37), ("base_spell_critical_strike_multiplier_+", 2.56),
                ("base_cast_speed_+%", 2.86),
                ("chaos_spell_skill_gem_level_+", 20.00), ("cold_spell_skill_gem_level_+", 20.00),
                ("fire_spell_skill_gem_level_+", 20.00), ("lightning_spell_skill_gem_level_+", 20.00),
                ("spell_skill_gem_level_+", 25.00)]
_WAND = {"full": _WAND_DMG + _WAND_GAINS + _WAND_SUFFIX,
         "prefix": _WAND_DMG + _WAND_GAINS, "suffix": _WAND_SUFFIX,
         "thr": 450, "p_pct": 0.50, "s_pct": 255 / 450,
         "tier": {"low": 3, "mid": 3, "high": 3}, "magic": None}

_STAFF = {"full": _WAND_DMG + [("base_maximum_mana", 0.43),
          ("non_skill_base_all_damage_%_to_gain_as_cold", 2.22),
          ("non_skill_base_all_damage_%_to_gain_as_fire", 2.22),
          ("non_skill_base_all_damage_%_to_gain_as_lightning", 2.22),
          ("base_cast_speed_+%", 1.92), ("spell_critical_strike_chance_+%", 0.92),
          ("base_spell_critical_strike_multiplier_+", 1.69), ("additional_intelligence", 3.03),
          ("chaos_spell_skill_gem_level_+", 14.29), ("cold_spell_skill_gem_level_+", 14.29),
          ("fire_spell_skill_gem_level_+", 14.29), ("lightning_spell_skill_gem_level_+", 14.29),
          ("spell_skill_gem_level_+", 16.67)],
          "prefix": None, "suffix": None,
          "thr": 510, "tier": {"low": 5, "mid": 5, "high": 5}, "magic": None}

_SCEPTRE = {"full": [("allies_in_presence_attack_minimum_added_cold_damage", 2.08),
                     ("allies_in_presence_attack_maximum_added_cold_damage", 1.35),
                     ("allies_in_presence_attack_minimum_added_fire_damage", 1.72),
                     ("allies_in_presence_attack_maximum_added_fire_damage", 1.11),
                     ("allies_in_presence_attack_maximum_added_lightning_damage", 1.41),
                     ("allies_in_presence_attack_minimum_added_physical_damage", 2.63),
                     ("allies_in_presence_attack_maximum_added_physical_damage", 1.56),
                     ("allies_in_presence_damage_+%", 0.84), ("local_spirit_+%", 1.54),
                     ("minion_skill_gem_level_+", 25.00),
                     ("allies_in_presence_attack_speed_+%", 6.25),
                     ("allies_in_presence_cast_speed_+%", 5.00),
                     ("allies_in_presence_critical_strike_multiplier_+", 2.56),
                     ("allies_in_presence_critical_strike_chance_+%", 2.63)],
            "prefix": None, "suffix": None,
            "thr": 390, "tier": {"low": 5, "mid": 5, "high": 5}, "magic": None}

_FOCUS_PREFIX = [("chaos_damage_+%", 0.84), ("cold_damage_+%", 0.84),
                 ("local_energy_shield_+%", 1.00), ("fire_damage_+%", 0.84),
                 ("lightning_damage_+%", 0.84), ("spell_damage_+%", 0.84),
                 ("local_energy_shield", 1.04)]
_FOCUS_SUFFIX = [("spell_critical_strike_chance_+%", 1.69),
                 ("base_spell_critical_strike_multiplier_+", 2.94), ("base_cast_speed_+%", 3.13),
                 ("spell_skill_gem_level_+", 50.00),
                 ("base_cold_damage_resistance_%", 2.22), ("base_fire_damage_resistance_%", 2.22),
                 ("base_lightning_damage_resistance_%", 2.22)]
_FOCUS = {"full": _FOCUS_PREFIX + _FOCUS_SUFFIX,
          "prefix": _FOCUS_PREFIX, "suffix": _FOCUS_SUFFIX,
          "thr": 390, "p_pct": 225 / 390, "s_pct": 255 / 390,
          "tier": {"low": 5, "mid": 5, "high": 5}, "magic": None}

_QUIVER = {"full": [("damage_+%_with_bow_skills", 1.69), ("base_projectile_speed_+%", 2.17)]
                   + _ADDED_ATK
                   + [("attack_speed_+%", 6.25), ("attack_critical_strike_multiplier_+", 2.56),
                      ("attack_critical_strike_chance_+%", 2.63), ("projectile_skill_gem_level_+", 50.00)],
           "prefix": None, "suffix": None,
           "thr": 420, "tier": dict(DEFAULT_TIERS), "magic": None}


def _from_preset(token, thr=None):
    """Caster/off-hand template from the bot's own per-slot preset (no P/S split)."""
    def_thr, mods = gen.WEIGHTED_SUM_PRESETS[token]
    return {"full": list(mods), "prefix": None, "suffix": None,
            "thr": thr if thr is not None else def_thr,
            "tier": dict(DEFAULT_TIERS), "magic": None}


def get_template(family, combo):
    """Template for a (family, combo) pair, or None if unsupported."""
    if family in _ARMOUR_BUILDERS:
        return _ARMOUR_BUILDERS[family](combo)
    return _WEAPON_TEMPLATES.get(family)


_BOOTS_THR = {"armour": 420, "evasion": 420, "es": 420, "armour_evasion": 420,
              "armour_es": 480, "evasion_es": 450, "default": 450}

_ARMOUR_BUILDERS = {
    "Boots": lambda c: _armour_slot(
        c, _LIFE, [("base_movement_velocity_+%", 2.86)], [], _BOOTS_THR,
        magic=("base_movement_velocity_+%", 2.86, 87)),
    "Gloves": lambda c: _armour_slot(
        c, _LIFE, _ADDED_ATK,
        [("attack_speed_+%", 6.25), ("base_critical_strike_multiplier_+", 2.94),
         ("melee_skill_gem_level_+", 50.00)],
        {"evasion": 360, "evasion_es": 390, "armour_evasion": 450, "default": 420}),
    "Helmets": lambda c: _armour_slot(
        c, _LIFE_HELM, [],
        [("critical_strike_chance_+%", 2.94), ("minion_skill_gem_level_+", 50.00)],
        {"armour": 480, "evasion": 456, "es": 450, "armour_evasion": 450,
         "armour_es": 375, "evasion_es": 420, "default": 450}),
    "BodyArmours": _body_template,
    "Shields": lambda c: dict(_SHIELD),
    "Bucklers": lambda c: dict(_SHIELD),
}

_WEAPON_TEMPLATES = {
    "Bows":          _BOW,
    "Crossbows":     _CROSSBOW,
    "Quarterstaves": _QUARTERSTAFF,
    "OneHandMaces":  _melee("melee_skill_gem_level_+"),
    "TwoHandMaces":  _melee("melee_skill_gem_level_+"),
    "Spears":        _SPEAR,
    "Flails":        _melee("melee_skill_gem_level_+"),
    "Wands":         _WAND,
    "Sceptres":      _SCEPTRE,
    "Staves":        _STAFF,
    "Foci":          _FOCUS,
    "Quivers":       _QUIVER,
}

# ── Jewels: archetype rules (post-# bodies with {thr} placeholders) ───────────
# Double-WeightedSum archetypes match jewels whose prefix AND suffix halves both
# score; "rarities" controls which rarities get the rule (default Magic-only —
# the corrupt-fodder use case). The singles pick movement/quiver jewels anywhere.
JEWEL_ARCHETYPES = [
    ("caster", "ES / caster", 18,
     '[WeightedSum(maximum_energy_shield_+%:1.5,projectile_damage_+%:2,elemental_damage_+%:2,'
     'lightning_damage_+%:2,cold_damage_+%:2,spell_damage_+%:2,ailment_effect_+%:2,'
     'shock_effect_+%:1.5,projectile_speed_+%:3)] >= "{thr}" && '
     '[WeightedSum(base_maximum_fire_damage_resistance_%:10,base_maximum_cold_damage_resistance_%:10,'
     'base_maximum_lightning_damage_resistance_%:10,spell_critical_strike_chance_+%:2,'
     'base_spell_critical_strike_multiplier_+:1.5,critical_strike_chance_+%:2,'
     'base_critical_strike_multiplier_+:1.5,recover_%_maximum_mana_on_kill:10,'
     'base_cast_speed_+%:7,skill_effect_duration_+%:2)] >= "{thr}"'),
    ("bow", "Bow attacker", 28,
     '[WeightedSum(lightning_damage_+%:2.5,attack_damage_+%:2.5,evasion_rating_+%:2,'
     'ailment_effect_+%:2.5,bow_damage_+%:2.5,elemental_damage_+%:2.5,base_projectile_speed_+%:3.5,'
     'projectile_damage_+%:2.5,damage_+%_to_rare_and_unique_enemies:2,shock_effect_+%:2)] >= "{thr}" && '
     '[WeightedSum(attack_critical_strike_chance_+%:2.5,attack_critical_strike_multiplier_+:2,'
     'attack_speed_+%:8.5,bow_attack_speed_+%:8.5,base_maximum_lightning_damage_resistance_%:16)] >= "{thr}"'),
    ("quarterstaff", "Quarterstaff attacker", 28,
     '[WeightedSum(quarterstaff_damage_+%:2.5,lightning_damage_+%:2.5,attack_damage_+%:2.5,'
     'evasion_rating_+%:2,ailment_effect_+%:2.5,elemental_damage_+%:2.5,'
     'damage_+%_to_rare_and_unique_enemies:2,shock_effect_+%:2)] >= "{thr}" && '
     '[WeightedSum(attack_critical_strike_chance_+%:2.5,attack_critical_strike_multiplier_+:2,'
     'attack_speed_+%:8.5,quarterstaff_attack_speed_+%:8.5,'
     'base_maximum_lightning_damage_resistance_%:16)] >= "{thr}"'),
]

JEWEL_SINGLES = [
    ("movespeed", "Movement speed", "base_movement_velocity_+%"),
    ("quiver_effect", "Quiver effect", "quiver_mod_effect_+%"),
]

# Later batch from the user's pickit: more jewel archetypes, matched at BOTH
# rarities (these hunt finished jewels, not just corrupt fodder).
JEWEL_ARCHETYPES += [
    ("es_cold", "ES caster — cold/trigger", 32,
     '[WeightedSum(maximum_energy_shield_+%:2,triggered_spell_spell_damage_+%:1,elemental_damage_+%:2,'
     'cold_damage_+%:2,spell_damage_+%:2,energy_shield_recharge_rate_+%:0.5,energy_shield_delay_-%:0.5)] >= "{thr}" && '
     '[WeightedSum(base_maximum_fire_damage_resistance_%:10,base_maximum_cold_damage_resistance_%:10,'
     'base_maximum_lightning_damage_resistance_%:10,spell_critical_strike_chance_+%:2,'
     'base_spell_critical_strike_multiplier_+:2,critical_strike_chance_+%:2,base_critical_strike_multiplier_+:2,'
     'recover_%_maximum_mana_on_kill:10,base_cast_speed_+%:7)] >= "{thr}"',
     ("Rare", "Magic")),
    ("es_fire", "ES caster — fire/ignite", 35,
     '[WeightedSum(base_skill_area_of_effect_+%:2,base_ignite_effect_+%:2,maximum_energy_shield_+%:2,'
     'elemental_damage_+%:2,fire_damage_+%:2,spell_damage_+%:2,energy_shield_recharge_rate_+%:0.5,'
     'energy_shield_delay_-%:0.5,ailment_effect_+%:2)] >= "{thr}" && '
     '[WeightedSum(ignite_chance_+%:2,base_maximum_fire_damage_resistance_%:10,'
     'base_maximum_cold_damage_resistance_%:10,base_maximum_lightning_damage_resistance_%:10,'
     'spell_critical_strike_chance_+%:2,base_spell_critical_strike_multiplier_+:2,critical_strike_chance_+%:2,'
     'base_critical_strike_multiplier_+:2,recover_%_maximum_mana_on_kill:10,base_cast_speed_+%:7)] >= "{thr}"',
     ("Rare", "Magic")),
    ("es_light", "ES caster — lightning/projectile", 29,
     '[WeightedSum(shock_effect_+%:2,ailment_effect_+%:2,maximum_energy_shield_+%:2,projectile_speed_+%:2.5,'
     'triggered_spell_spell_damage_+%:1,projectile_damage_+%:2,elemental_damage_+%:2,lightning_damage_+%:2,'
     'spell_damage_+%:2,energy_shield_recharge_rate_+%:0.5,energy_shield_delay_-%:0.5)] >= "{thr}" && '
     '[WeightedSum(base_maximum_fire_damage_resistance_%:10,base_maximum_cold_damage_resistance_%:10,'
     'base_maximum_lightning_damage_resistance_%:10,spell_critical_strike_chance_+%:2,'
     'base_spell_critical_strike_multiplier_+:2,critical_strike_chance_+%:2,base_critical_strike_multiplier_+:2,'
     'recover_%_maximum_mana_on_kill:10,base_cast_speed_+%:7,skill_effect_duration_+%:2.5,'
     'base_chance_to_pierce_%:2)] >= "{thr}"',
     ("Rare", "Magic")),
    ("qstaff_endgame", "Quarterstaff — endgame", 33,
     '[WeightedSum(lightning_damage_+%:2.5,attack_damage_+%:2.5,evasion_rating_+%:2,ailment_effect_+%:2.5,'
     'quarterstaff_damage_+%:2.4,elemental_damage_+%:2.5,base_reduce_enemy_lightning_resistance_%:3.5,'
     'damage_+%_to_rare_and_unique_enemies:2)] >= "{thr}" && '
     '[WeightedSum(attack_critical_strike_chance_+%:2.5,attack_critical_strike_multiplier_+:2,attack_speed_+%:7,'
     'quarterstaff_attack_speed_+%:7,base_maximum_lightning_damage_resistance_%:10)] >= "{thr}"',
     ("Rare", "Magic")),
    ("minions", "Minions / curses", 24,
     '[WeightedSum(minion_accuracy_rating_+%:1,minion_damage_+%:1.33,maximum_energy_shield_+%:1,'
     'elemental_damage_+%:1.33,curse_area_of_effect_+%:0.8,offering_life_+%:0.8,curse_effect_+%:4,'
     'energy_shield_recharge_rate_+%:1,energy_shield_delay_-%:1)] >= "{thr}" && '
     '[WeightedSum(minion_critical_strike_chance_+%:1,base_cast_speed_+%:7,minion_elemental_resistance_%:2,'
     'minion_critical_strike_multiplier_+:0.8,attack_and_cast_speed_+%:1,base_skill_area_of_effect_+%:2,'
     'base_curse_duration_+%:0.8,offering_duration_+%:0.8,skill_effect_duration_+%:1.33,'
     'recover_%_maximum_mana_on_kill:10)] >= "{thr}"',
     ("Rare", "Magic")),
    # (his file omits the delay weight — normalised to :0.5 like the other ES sets)
    ("es_chaos", "ES caster — chaos/misc", 35,
     '[WeightedSum(chaos_damage_+%:2,base_skill_area_of_effect_+%:2,maximum_energy_shield_+%:2,'
     'energy_shield_recharge_rate_+%:0.5,energy_shield_delay_-%:0.5)] >= "{thr}" && '
     '[WeightedSum(base_maximum_fire_damage_resistance_%:10,base_maximum_cold_damage_resistance_%:10,'
     'base_maximum_lightning_damage_resistance_%:10,spell_critical_strike_chance_+%:2,'
     'base_spell_critical_strike_multiplier_+:2,critical_strike_chance_+%:2,base_critical_strike_multiplier_+:2,'
     'recover_%_maximum_mana_on_kill:10,base_cast_speed_+%:7)] >= "{thr}"',
     ("Rare", "Magic")),
    # 34/33 pair in the source pickit — the attack-suffix sum stays fixed at 33.
    ("bow_endgame", "Bow — endgame", 34,
     '[WeightedSum(lightning_damage_+%:2.5,attack_damage_+%:2.5,evasion_rating_+%:2,ailment_effect_+%:2.5,'
     'bow_damage_+%:2.4,elemental_damage_+%:2.5,base_reduce_enemy_lightning_resistance_%:3.5,'
     'base_projectile_speed_+%:3.5,projectile_damage_+%:2.5,damage_+%_to_rare_and_unique_enemies:2,'
     'shock_effect_+%:2)] >= "{thr}" && '
     '[WeightedSum(attack_critical_strike_chance_+%:2.5,attack_critical_strike_multiplier_+:2,attack_speed_+%:7,'
     'bow_attack_speed_+%:7,base_maximum_lightning_damage_resistance_%:10,'
     'base_chance_to_pierce_%:2)] >= "33"',
     ("Rare", "Magic")),
]

# ── Rings: build archetypes over every ring base (from the user's pickit) ─────
_RING_ADDED = list(_ADDED_ATK)
_RING_RES = [("base_resist_all_elements_%", 6.25), ("base_chaos_damage_resistance_%", 3.70),
             ("base_cold_damage_resistance_%", 2.22), ("base_fire_damage_resistance_%", 2.22),
             ("base_lightning_damage_resistance_%", 2.22)]
_RING_LEECH = [("base_life_leech_from_physical_attack_damage_permyriad", 0.13),
               ("base_mana_leech_from_physical_attack_damage_permyriad", 0.14)]
_RING_ELE = [("cold_damage_+%", 3.33), ("fire_damage_+%", 3.33), ("lightning_damage_+%", 3.33)]

RING_ARCHETYPES = [
    {"key": "melee", "label": "Melee", "thr": 360,
     "full": _RING_ELE + [("base_maximum_life", 0.84)] + _RING_ADDED
             + [("base_item_found_rarity_+%", 2.00)] + _RING_RES + _RING_LEECH},
    {"key": "added_dmg", "label": "Added damage", "thr": 180,
     "full": [("attack_minimum_added_cold_damage", 2.08), ("attack_maximum_added_cold_damage", 1.35),
              ("attack_minimum_added_fire_damage", 1.72), ("attack_maximum_added_fire_damage", 1.11),
              ("attack_maximum_added_lightning_damage", 3.38),
              ("attack_minimum_added_physical_damage", 2.63), ("attack_maximum_added_physical_damage", 1.56)]},
    {"key": "ev_acc", "label": "Evasion + accuracy", "thr": 240,
     "full": [("base_maximum_life", 0.84), ("base_evasion_rating", 0.49), ("lightning_damage_+%", 3.33),
              ("attack_maximum_added_lightning_damage", 1.41),
              ("attack_minimum_added_physical_damage", 2.63), ("attack_maximum_added_physical_damage", 1.56)]},
    {"key": "acc_added", "label": "Accuracy + added", "thr": 390,
     "full": [("base_maximum_life", 0.84)] + _RING_ADDED
             + [("accuracy_rating", 0.22)] + _RING_RES + _RING_LEECH
             + [("base_item_found_rarity_+%", 2.00)]},
    {"key": "resistance", "label": "Resistances", "thr": 240, "full": list(_RING_RES)},
    {"key": "stat_stack", "label": "Stat stacking", "thr": 270,
     "full": [("additional_strength", 3.03), ("additional_intelligence", 3.03),
              ("additional_dexterity", 3.03), ("additional_all_attributes", 7.69)]},
    {"key": "caster", "label": "Caster", "thr": 426,
     "full": [("base_cast_speed_+%", 4.17)] + _RING_RES[2:] + [("base_resist_all_elements_%", 6.25),
              ("additional_intelligence", 3.03)] + _RING_ELE + [("base_maximum_mana", 0.56)]},
    {"key": "blood_caster", "label": "Blood caster", "thr": 450,
     "full": [("base_maximum_life", 0.84)] + _RING_ELE
             + [("base_cast_speed_+%", 4.17), ("additional_strength", 3.03)] + _RING_RES
             + [("additional_intelligence", 3.03), ("base_item_found_rarity_+%", 2.00)]},
    {"key": "phys_chaos", "label": "Phys + chaos", "thr": 360,
     "full": [("chaos_damage_+%", 3.33), ("attack_minimum_added_physical_damage", 2.63),
              ("attack_maximum_added_physical_damage", 1.56), ("base_maximum_life", 0.84)]
             + _RING_RES + _RING_LEECH + [("base_item_found_rarity_+%", 2.00)]},
    {"key": "life_mana_chaos", "label": "Life/mana chaos", "thr": 360,
     "full": [("base_item_found_rarity_+%", 2.00), ("base_cast_speed_+%", 4.17),
              ("base_maximum_mana", 0.56), ("base_maximum_life", 0.84),
              ("chaos_damage_+%", 3.33)] + _RING_RES},
    {"key": "ninja_used", "label": "poe.ninja most used", "thr": 480,
     "full": _RING_RES + [("base_item_found_rarity_+%", 2.00), ("base_maximum_mana", 0.56),
              ("base_maximum_life", 0.84)] + _RING_ADDED
             + [("base_evasion_rating", 0.49), ("lightning_damage_+%", 3.33),
                ("additional_intelligence", 3.03)]},
]

RING_MAGIC = (_RING_ADDED + [("base_maximum_life", 0.84)] + _RING_RES
              + [("base_item_found_rarity_+%", 2.63)], 180)
RING_RARITY = ("base_item_found_rarity_+%", 50)   # Category rule, Rare AND Magic

# Magic-tier fallback: families without a transcribed single-mod Magic rule can
# still opt in — the full mod set is scored against Magic items at this fraction
# of the section threshold (a Magic item has at most 2 explicit mods).
MAGIC_FALLBACK_PCT = 0.40

# ── Amulets: build archetypes over every amulet base (from the user's pickit) ─
_AMU_GEMS = [("projectile_skill_gem_level_+", 33.33), ("spell_skill_gem_level_+", 33.33),
             ("minion_skill_gem_level_+", 33.33)]
_AMU_CASTER_SUFFIX = [("critical_strike_chance_+%", 2.63),
                      ("base_critical_strike_multiplier_+", 2.56),
                      ("base_cast_speed_+%", 3.57)]
_AMU_RES = [("base_resist_all_elements_%", 5.56), ("base_chaos_damage_resistance_%", 3.70),
            ("base_cold_damage_resistance_%", 2.22), ("base_fire_damage_resistance_%", 2.22),
            ("base_lightning_damage_resistance_%", 2.22)]

AMULET_ARCHETYPES = [
    {"key": "es_caster", "label": "ES caster", "thr": 390, "p_thr": 240, "s_thr": 240,
     "full": [("maximum_energy_shield_+%", 2.00), ("maximum_mana_+%", 12.50),
              ("spell_damage_+%", 3.33), ("base_maximum_energy_shield", 1.12),
              ("base_maximum_mana", 0.53), ("base_spirit_from_equipment", 2.00)]
             + _AMU_CASTER_SUFFIX
             + [("base_item_found_rarity_+%", 4.00), ("damage_taken_goes_to_mana_%", 4.17)]
             + _AMU_GEMS + _AMU_RES,
     "prefix": [("maximum_energy_shield_+%", 2.00), ("base_maximum_energy_shield", 1.12),
                ("base_spirit_from_equipment", 2.40)],
     "suffix": _AMU_CASTER_SUFFIX + [("base_item_found_rarity_+%", 4.00)] + _AMU_GEMS},
    {"key": "stat_stacker", "label": "Stat stacker", "thr": 420,
     "full": [("additional_strength", 3.03), ("additional_all_attributes", 4.17),
              ("additional_dexterity", 3.03), ("additional_intelligence", 3.03),
              ("melee_skill_gem_level_+", 33.33), ("projectile_skill_gem_level_+", 33.33),
              ("base_maximum_life", 0.67), ("base_maximum_energy_shield", 1.12),
              ("maximum_life_+%", 12.50), ("maximum_energy_shield_+%", 2.00),
              ("evasion_rating_+%", 2.00), ("base_spirit_from_equipment", 2.00)],
     "prefix": None, "suffix": None},
    {"key": "blood_magic", "label": "Blood magic caster", "thr": 390,
     "p_thr": 225, "s_thr": 210,
     "full": _AMU_CASTER_SUFFIX
             + [("base_item_found_rarity_+%", 2.00),
                ("damage_taken_goes_to_life_over_4_seconds_%", 4.17),
                ("maximum_life_+%", 12.50), ("spell_damage_+%", 3.33),
                ("base_maximum_life", 0.67), ("base_spirit_from_equipment", 2.00),
                ("projectile_skill_gem_level_+", 33.33), ("spell_skill_gem_level_+", 33.33)]
             + _AMU_RES,
     "prefix": [("maximum_life_+%", 12.50), ("base_maximum_life", 0.67),
                ("base_spirit_from_equipment", 2.00), ("spell_damage_+%", 3.33)],
     "suffix": _AMU_CASTER_SUFFIX
               + [("base_item_found_rarity_+%", 2.00),
                  ("projectile_skill_gem_level_+", 33.33),
                  ("spell_skill_gem_level_+", 33.33)]},
    {"key": "life_caster", "label": "Life caster", "thr": 390, "p_thr": 240,
     "full": [("maximum_life_+%", 12.50), ("base_maximum_life", 0.67),
              ("spell_damage_+%", 3.33), ("base_spirit_from_equipment", 2.00)]
             + _AMU_CASTER_SUFFIX
             + [("damage_taken_goes_to_life_over_4_seconds_%", 4.17),
                ("base_item_found_rarity_+%", 4.00),
                ("projectile_skill_gem_level_+", 33.33), ("spell_skill_gem_level_+", 33.33)]
             + _AMU_RES,
     "prefix": [("maximum_life_+%", 12.50), ("base_maximum_life", 0.67),
                ("spell_damage_+%", 3.33), ("base_spirit_from_equipment", 2.00)],
     "suffix": None},
    {"key": "projectile", "label": "Projectile + life/ES", "thr": 420, "p_thr": 240,
     "full": [("evasion_rating_+%", 2.00), ("maximum_life_+%", 12.50),
              ("base_maximum_energy_shield", 1.12), ("base_maximum_life", 0.67),
              ("base_spirit_from_equipment", 2.00), ("maximum_energy_shield_+%", 2.00),
              ("critical_strike_chance_+%", 2.63), ("base_critical_strike_multiplier_+", 2.56),
              ("base_item_found_rarity_+%", 4.00), ("melee_skill_gem_level_+", 33.33),
              ("projectile_skill_gem_level_+", 33.33), ("minion_skill_gem_level_+", 33.33)]
             + _AMU_RES,
     "prefix": [("evasion_rating_+%", 2.00), ("maximum_energy_shield_+%", 2.00),
                ("maximum_life_+%", 12.50), ("base_maximum_life", 0.67),
                ("base_spirit_from_equipment", 2.00)],
     "suffix": None},
]

# Magic amulets: +N to a skill-gem family (>= 70 ≈ a +3, or high +2) — per base —
# plus the catch-all "any Magic amulet with 50%+ rarity" category rule.
AMULET_MAGIC_GEMS = ([("spell_skill_gem_level_+", 33.33), ("projectile_skill_gem_level_+", 33.33),
                      ("minion_skill_gem_level_+", 33.33), ("melee_skill_gem_level_+", 33.33)], 70)
AMULET_MAGIC_RARITY = ("base_item_found_rarity_+%", 50)

# ── Belts (prefix/suffix rule pair + Magic rule, from the user's pickit) ──────
BELT_TEMPLATE = {
    "prefix": [("base_maximum_life", 0.57), ("base_physical_damage_reduction_rating", 0.39)]
              + _RES,
    "suffix": list(_RES),
    "thr": 300, "s_pct": 0.70, "tier": 3,
    "magic": ([("base_maximum_life", 0.57)] + _RES, 180, 5),   # (mods, thr, tier)
}

