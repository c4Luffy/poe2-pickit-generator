"""Fracture Bases — verified natural-affix lookup for Fracturing Orb targets.

Split out of generator.py (this module is re-exported there for backward
compatibility, matching the pattern used by corrections.py/base_types.py).
A reference/lookup tool: fracture_targets_for_class() and classify_fracture_item()
are pure lookups; build_fracture_pickit_rules() is the one function that emits
real pickit rules, and only for targets with a bot stat id verified in
_FRACTURE_VERIFIED_STAT_IDS — never for the reference-only ones.
"""

import re

FRACTURE_CLASS_GROUPS: list = [
    ("Armour",    ["Body Armours", "Helmets", "Gloves", "Boots"]),
    ("Off-hand",  ["Shields", "Foci", "Quivers"]),
    ("Weapons",   ["Bows", "Crossbows", "Quarterstaves", "Spears",
                   "One Hand Maces", "Two Hand Maces", "Sceptres", "Wands", "Staves"]),
    ("Jewellery", ["Amulets", "Rings", "Belts"]),
    ("Other",     ["Jewels", "Charms", "Flasks"]),
]
# ─────────────────────────────────────────────────────────────────────────────
#  Fracture Bases — a lookup/reference tool (NOT a pickit-rule generator).
#  Answers one question: "is this Magic/Rare base worth using a Fracturing Orb
#  on?" Every target below is a natural Magic/Rare affix verified against the
#  live PoE2 mod-tier data (Craft of Exile 2 + the extracted improved-modifier
#  tables) and cross-checked as droppable against NeverSink's live filter.
#  Essence/crafted/abyss/corrupted/unique/vendor/event mod pools are excluded
#  by construction: every entry below comes from each base's normal "Base" mod
#  group tier table, never a special pool.
# ─────────────────────────────────────────────────────────────────────────────
FRACTURE_TIERS = {"S+": 100, "S": 80, "A+": 60, "A": 40}

# Each target: tier, item classes it applies to, the exact mod text (as it
# rolls), affix slot, required tier label, min value, and why it matters.
FRACTURE_TARGETS: list = [
    {"id": "amulet_skill_level", "tier": "S+", "classes": ["Amulets"],
     "affix": "suffix", "mod_tier": "T1", "value": "+3",
     "text": "+3 to Level of all Spell/Minion/Melee/Projectile Skills",
     "reason": "S+ target: max +skill level amulet mod (T1, verified from live data)."},
    {"id": "amulet_spirit", "tier": "S+", "classes": ["Amulets"],
     "affix": "prefix", "mod_tier": "T1", "value": "47-50",
     "text": "+47-50 to Spirit",
     "reason": "S+ target: T1 Spirit amulet prefix (mod id 5076, ilvl54, verified "
               "from live CoE2 data — the only natural Spirit mod on amulets)."},
    {"id": "weapon_skill_level_bow", "tier": "S+", "classes": ["Bows"],
     "affix": "suffix", "mod_tier": "T1", "value": "+4",
     "text": "+4 to Level of all Projectile Skills",
     "reason": "S+ target: top-tier bow skill-level mod verified from live data."},
    {"id": "weapon_skill_level_crossbow", "tier": "S+", "classes": ["Crossbows"],
     "affix": "suffix", "mod_tier": "T1", "value": "+5",
     "text": "+5 to Level of all Projectile Skills",
     "reason": "S+ target: top-tier crossbow skill-level mod verified from live data."},
    {"id": "weapon_skill_level_quarterstaff", "tier": "S+", "classes": ["Quarterstaves"],
     "affix": "suffix", "mod_tier": "T1", "value": "+5",
     "text": "+5 to Level of all Melee Skills",
     "reason": "S+ target: top-tier quarterstaff (Warstaff) skill-level mod verified from live data."},
    {"id": "weapon_skill_level_2hmace", "tier": "S+", "classes": ["Two Hand Maces"],
     "affix": "suffix", "mod_tier": "T1", "value": "+5",
     "text": "+5 to Level of all Melee Skills",
     "reason": "S+ target: top-tier 2H mace skill-level mod verified from live data."},
    {"id": "weapon_skill_level_spear", "tier": "S+", "classes": ["Spears"],
     "affix": "suffix", "mod_tier": "T1", "value": "+4",
     "text": "+4 to Level of all Melee Skills",
     "reason": "S+ target: top-tier spear skill-level mod verified from live data."},
    {"id": "weapon_skill_level_1hmace", "tier": "S+", "classes": ["One Hand Maces"],
     "affix": "suffix", "mod_tier": "T1", "value": "+4",
     "text": "+4 to Level of all Melee Skills",
     "reason": "S+ target: top-tier 1H mace skill-level mod verified from live data."},
    {"id": "weapon_skill_level_wand", "tier": "S+", "classes": ["Wands"],
     "affix": "suffix", "mod_tier": "T1", "value": "+5",
     "text": "+5 to Level of all Fire/Cold/Lightning/Chaos/Physical Spell Skills "
             "(element-specific rolls higher than the generic +4 all-Spell-Skills mod)",
     "reason": "S+ target: top-tier wand skill-level mod verified from live data — the "
               "element-specific suffix (+5, ilvl81) beats the generic Spell Skills suffix (+4, ilvl78)."},
    {"id": "weapon_skill_level_staff", "tier": "S+", "classes": ["Staves"],
     "affix": "suffix", "mod_tier": "T1", "value": "+7",
     "text": "+7 to Level of all Fire/Cold/Lightning/Chaos/Physical Spell Skills "
             "(element-specific rolls higher than the generic +5-6 all-Spell-Skills mod)",
     "reason": "S+ target: top-tier staff skill-level mod verified from live data — the "
               "element-specific suffix (+7, ilvl81) beats the generic Spell Skills suffix (+5-6, ilvl78)."},
    {"id": "weapon_skill_level_sceptre", "tier": "S+", "classes": ["Sceptres"],
     "affix": "suffix", "mod_tier": "T1", "value": "+4",
     "text": "+4 to Level of all Minion Skills",
     "reason": "S+ target: top-tier sceptre skill-level mod verified from live data."},
    {"id": "weapon_skill_level_sceptre_t2", "tier": "S+", "classes": ["Sceptres"],
     "affix": "suffix", "mod_tier": "T2", "value": "+3",
     "text": "+3 to Level of all Minion Skills",
     "reason": "S+ target: T2 sceptre skill-level mod — owner-approved second tier "
               "for Sceptres only (verified from live data, ilvl55)."},
    {"id": "spirit_body", "tier": "S+", "classes": ["Body Armours"],
     "affix": "prefix", "mod_tier": "T1", "value": "57-61",
     "text": "+57-61 to Spirit",
     "reason": "S+ target: T1 Spirit (verified natural body armour affix)."},
    {"id": "es_body", "tier": "S", "classes": ["Body Armours"],
     "affix": "prefix", "mod_tier": "T1", "value": "91-96",
     "text": "+91-96 to maximum Energy Shield (pure ES base only, no Armour)",
     "reason": "S target: T1 flat Energy Shield on a pure-ES or ES-hybrid body armour."},
    {"id": "evasion_body", "tier": "S", "classes": ["Body Armours"],
     "affix": "prefix", "mod_tier": "T1", "value": "262-300",
     "text": "+262-300 to Evasion Rating (pure Evasion base only, no Armour)",
     "reason": "S target: T1 flat Evasion on a pure-Evasion or Evasion-hybrid body armour."},
    {"id": "es_evasion_pct_body", "tier": "S", "classes": ["Body Armours"],
     "affix": "prefix", "mod_tier": "T1", "value": "101-110%",
     "text": "101-110% increased Energy Shield / Evasion Rating (no Armour)",
     "reason": "S target: T1 %ES or %Evasion on a non-Armour body armour base."},
    {"id": "es_helmet", "tier": "S", "classes": ["Helmets"],
     "affix": "prefix", "mod_tier": "T1", "value": "61-73",
     "text": "+61-73 to maximum Energy Shield (pure ES base only, no Armour)",
     "reason": "S target: T1 flat Energy Shield helmet (no Armour)."},
    {"id": "evasion_helmet", "tier": "S", "classes": ["Helmets"],
     "affix": "prefix", "mod_tier": "T1", "value": "177-207",
     "text": "+177-207 to Evasion Rating (pure Evasion base only, no Armour)",
     "reason": "S target: T1 flat Evasion helmet (no Armour)."},
    {"id": "es_evasion_hybrid_helmet", "tier": "S", "classes": ["Helmets"],
     "affix": "prefix", "mod_tier": "T1", "value": "92-100%",
     "text": "92-100% increased Evasion and Energy Shield",
     "reason": "S target: T1 Evasion+ES hybrid prefix helmet (no Armour)."},
    {"id": "es_boots", "tier": "S", "classes": ["Boots"],
     "affix": "prefix", "mod_tier": "T1", "value": "48-60",
     "text": "+48-60 to maximum Energy Shield (pure ES base only, no Armour)",
     "reason": "S target: T1 flat Energy Shield boots (no Armour)."},
    {"id": "evasion_boots", "tier": "S", "classes": ["Boots"],
     "affix": "prefix", "mod_tier": "T1", "value": "147-176",
     "text": "+147-176 to Evasion Rating (pure Evasion base only, no Armour)",
     "reason": "S target: T1 flat Evasion boots (no Armour)."},
    {"id": "es_evasion_hybrid_boots", "tier": "S", "classes": ["Boots"],
     "affix": "prefix", "mod_tier": "T1", "value": "92-100%",
     "text": "92-100% increased Evasion and Energy Shield",
     "reason": "S target: T1 Evasion+ES hybrid prefix boots (no Armour)."},
    {"id": "movement_speed", "tier": "S", "classes": ["Boots"],
     "affix": "prefix", "mod_tier": "T1", "value": "35%",
     "text": "35% increased Movement Speed",
     "reason": "S target: T1 movement speed boots."},
    {"id": "rarity_helmet", "tier": "S", "classes": ["Helmets"], "magic_only": True,
     "affix": "prefix", "mod_tier": "T1", "value": "16-19%",
     "text": "16-19% increased Rarity of Items Found",
     "reason": "S target: Magic helmet rarity prefix (T1, confirmed prefix from live data; this mod caps at ilvl 47)."},
    {"id": "inc_phys_weapon", "tier": "A+", "classes": [
        "Bows", "Crossbows", "Quarterstaves", "Spears", "One Hand Maces", "Two Hand Maces"],
     "affix": "prefix", "mod_tier": "T1", "value": "170-179%",
     "text": "170-179% increased Physical Damage",
     "reason": "A+ target: T1 increased physical damage weapon."},
    {"id": "added_phys_weapon", "tier": "A+", "classes": [
        "Bows", "Quarterstaves", "Spears", "One Hand Maces"],
     "affix": "prefix", "mod_tier": "T1", "value": "26-39 to 44-66",
     "text": "Adds 26-39 to 44-66 Physical Damage",
     "reason": "A+ target: T1 added physical damage weapon."},
    {"id": "added_phys_weapon_2h", "tier": "A+", "classes": ["Crossbows", "Two Hand Maces"],
     "affix": "prefix", "mod_tier": "T1", "value": "37-55 to 63-94",
     "text": "Adds 37-55 to 63-94 Physical Damage",
     "reason": "A+ target: T1 added physical damage weapon (2H tier is a separate, higher roll)."},
    {"id": "crit_chance_weapon", "tier": "A", "classes": [
        "Bows", "Crossbows", "Quarterstaves", "Spears", "One Hand Maces", "Two Hand Maces"],
     "affix": "suffix", "mod_tier": "T1", "value": "+4.4-5%",
     "text": "+4.41-5% to Critical Hit Chance",
     "reason": "A target: T1 critical chance on a valid weapon class."},
    {"id": "crit_chance_amulet", "tier": "A", "classes": ["Amulets"],
     "affix": "suffix", "mod_tier": "T1", "value": "35-38%",
     "text": "35-38% increased Critical Hit Chance",
     "reason": "A target: T1 critical chance on a valid item class (amulet)."},
    {"id": "quiver_projectile", "tier": "A", "classes": ["Quivers"],
     "affix": "suffix", "mod_tier": "T1", "value": "+1",
     "text": "+1 to Level of all Projectile Skills",
     "reason": "A target: the ONLY projectile-skill mod that exists on Quiver in live data is +1 — it is simultaneously the minimum and the max, so it is T1 by definition."},
    {"id": "focus_spell", "tier": "A", "classes": ["Foci"],
     "affix": "suffix", "mod_tier": "T1", "value": "+2",
     "text": "+2 to Level of all Spell Skills",
     "reason": "A target: max +2 spell skill focus."},
    {"id": "crit_damage_gloves", "tier": "A", "classes": ["Gloves"],
     "affix": "suffix", "mod_tier": "T1", "value": "30-34%",
     "text": "30-34% increased Critical Damage Bonus",
     "reason": "A target: T1 critical damage on gloves (added by owner request — "
               "gloves have no Critical Hit Chance affix, only Critical Damage)."},
    {"id": "melee_skill_level_gloves", "tier": "A", "classes": ["Gloves"],
     "affix": "suffix", "mod_tier": "T1", "value": "+2",
     "text": "+2 to Level of all Melee Skills",
     "reason": "A target: T1 melee skill-level mod on gloves (natural Base-pool suffix; "
               "a +1 version also exists but only from the Corrupted pool, excluded)."},
    {"id": "added_dmg_gloves", "tier": "A", "classes": ["Gloves"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1: Phys 12-19/22-32, Fire 25-29/37-45, "
                                                        "Cold 21-24/32-37, Lightning 1-4/60-71",
     "text": "Adds # to # Physical/Fire/Cold/Lightning Damage to Attacks",
     "reason": "A target: flat added damage to attacks on gloves — T1 or T2 both count (owner-approved)."},
    {"id": "focus_crit_spells", "tier": "S", "classes": ["Foci"],
     "affix": "suffix", "mod_tier": "T1/T2", "value": "T1 59% / T2 54-59%",
     "text": "54-59% increased Critical Hit Chance for Spells",
     "reason": "S target: T1 or T2 critical-hit-chance-for-spells focus mod (owner-approved)."},
    {"id": "quiver_crit_chance_attacks", "tier": "A", "classes": ["Quivers"],
     "affix": "suffix", "mod_tier": "T1/T2", "value": "T1 35-38% / T2 30-34%",
     "text": "30-38% increased Critical Hit Chance for Attacks",
     "reason": "A target: crit chance for attacks on quiver — T1 or T2 both count."},
    {"id": "quiver_crit_dmg_attacks", "tier": "A", "classes": ["Quivers"],
     "affix": "suffix", "mod_tier": "T1/T2", "value": "T1 35-39% / T2 30-34%",
     "text": "30-39% increased Critical Damage Bonus for Attack Damage",
     "reason": "A target: crit damage for attacks on quiver — T1 or T2 both count."},
    {"id": "quiver_bow_dmg", "tier": "A", "classes": ["Quivers"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 51-59% / T2 43-50%",
     "text": "43-59% increased Damage with Bow Skills",
     "reason": "A target: damage-with-bow-skills quiver prefix — T1 or T2 both count."},
    {"id": "quiver_proj_speed", "tier": "A", "classes": ["Quivers"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 42-46% / T2 34-41%",
     "text": "34-46% increased Projectile Speed",
     "reason": "A target: projectile speed quiver prefix — T1 or T2 both count."},
    {"id": "quiver_added_lightning", "tier": "A", "classes": ["Quivers"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 1-4/60-71 / T2 1-3/48-59",
     "text": "Adds # to # Lightning damage to Attacks",
     "reason": "A target: added lightning damage quiver prefix — T1 or T2 both count."},
    {"id": "crossbow_load_bolt", "tier": "S", "classes": ["Crossbows"],
     "affix": "suffix", "mod_tier": "T1", "value": "2",
     "text": "Loads 2 additional bolts",
     "reason": "S target: max-tier bolt-loading suffix, unique to crossbows."},
    {"id": "elemental_dmg_with_attacks", "tier": "A+", "classes": [
        "Crossbows", "Quarterstaves", "Spears", "One Hand Maces", "Two Hand Maces"],
     "affix": "prefix", "mod_tier": "T1", "value": "87-139%",
     "text": "87-139% increased Elemental Damage with Attacks (value varies by weapon speed class)",
     "reason": "A+ target: T1 elemental damage with attacks — a strong prefix on martial weapons."},
    {"id": "added_lightning_weapon", "tier": "A+", "classes": [
        "Crossbows", "Quarterstaves", "Spears", "One Hand Maces", "Two Hand Maces"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "varies by class, e.g. Crossbow T1 1-19/310-358",
     "text": "Adds # to # Lightning Damage",
     "reason": "A+ target: added lightning damage weapon prefix — T1 or T2 both count."},
    {"id": "sceptre_spirit", "tier": "S+", "classes": ["Sceptres"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 61-65% / T2 56-60%",
     "text": "56-65% increased Spirit",
     "reason": "S+ target: pure Spirit prefix on sceptre — T1 or T2 both count (already have the Body Armour flat-Spirit target; this is the sceptre %-Spirit version)."},
    {"id": "sceptre_allies_dmg", "tier": "S+", "classes": ["Sceptres"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 105-119% / T2 90-104%",
     "text": "Allies in your Presence deal 90-119% increased Damage",
     "reason": "S+ target: minion-support sceptre prefix — T1 or T2 both count."},
    {"id": "sceptre_minion_life", "tier": "S+", "classes": ["Sceptres"],
     "affix": "suffix", "mod_tier": "T1/T2", "value": "T1 46-50% / T2 41-45%",
     "text": "Minions have 41-50% increased maximum Life",
     "reason": "S+ target: minion-life sceptre suffix — T1 or T2 both count."},
    {"id": "wand_crit_spells", "tier": "S", "classes": ["Wands"],
     "affix": "suffix", "mod_tier": "T1", "value": "60-73%",
     "text": "60-73% increased Critical Hit Chance for Spells",
     "reason": "S target: T1 crit-chance-for-spells on wand."},
    {"id": "wand_spell_dmg", "tier": "S", "classes": ["Wands"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 105-119% / T2 90-104%",
     "text": "90-119% increased Spell Damage",
     "reason": "S target: spell damage wand prefix — T1 or T2 both count."},
    {"id": "staff_crit_spells", "tier": "S", "classes": ["Staves"],
     "affix": "suffix", "mod_tier": "T1", "value": "90-109%",
     "text": "90-109% increased Critical Hit Chance for Spells",
     "reason": "S target: T1 crit-chance-for-spells on staff."},
    {"id": "staff_spell_dmg", "tier": "S", "classes": ["Staves"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 209-238% / T2 189-208%",
     "text": "189-238% increased Spell Damage",
     "reason": "S target: spell damage staff prefix — T1 or T2 both count."},
    {"id": "staff_crit_spell_dmg_bonus", "tier": "S", "classes": ["Staves"],
     "affix": "suffix", "mod_tier": "T1", "value": "53-59%",
     "text": "53-59% increased Critical Spell Damage Bonus",
     "reason": "S target: T1 critical spell damage bonus, unique to staves."},
    {"id": "belt_life", "tier": "A", "classes": ["Belts"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 150-174 / T2 120-149",
     "text": "120-174 to maximum Life",
     "reason": "A target: life belt prefix — T1 or T2 both count."},
    {"id": "belt_mana", "tier": "A", "classes": ["Belts"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 105-124 / T2 90-104",
     "text": "90-124 to maximum Mana",
     "reason": "A target: mana belt prefix — T1 or T2 both count."},
    {"id": "belt_resist", "tier": "A", "classes": ["Belts"],
     "affix": "suffix", "mod_tier": "T1/T2",
     "value": "Fire/Cold/Lightning T1 41-45% T2 36-40%; Chaos T1 24-27% T2 20-23%",
     "text": "20-45% to Fire/Cold/Lightning/Chaos Resistance",
     "reason": "A target: any single-element resistance belt suffix — T1 or T2 both count."},
    {"id": "flasks_max_charges", "tier": "S+", "classes": ["Flasks"],
     "affix": "suffix", "mod_tier": "T1", "value": "63-70%",
     "text": "63-70% increased Charges",
     "reason": "S+ target: top-tier Flask charges mod (ilvl81, verified from live "
               "CoE2 data — modifier id 5347, group FlaskNumCharges, Base pool)."},
]
# Targets the spec's own verification step rejected — kept here (not shown in
# the UI) so a future data refresh can re-check without re-deriving the answer.
FRACTURE_EXCLUDED_UNVERIFIED = {
    "crit_chance_gloves": "No Critical Hit Chance affix exists on Gloves (verified "
                           "against live CoE data across all 6 attribute variants) — "
                           "only Critical Damage Bonus (excluded by spec) and a fixed "
                           "socket-rune effect, not a rollable mod, are present.",
    "focus_minion": "No natural (Base-pool) +Minion Skills mod exists on Focus. "
                     "The only Minion Skills mod found on Focus comes from the "
                     "Desecrated pool (a boss/Well of Souls mechanic, not a "
                     "normal drop pool) — explicitly excluded per the spec's "
                     "own source rules.",
    "staff_sigil_of_power": "\"Grants Skill: Level # Sigil of Power\" does not exist "
                             "anywhere in the live Craft of Exile 2 data — not as a "
                             "natural affix, not in any special pool. Cannot be verified, "
                             "so per the spec's own rule it is not matched.",
}


def fracture_targets_for_class(item_class: str) -> list:
    """Verified fracture targets applicable to one item class, S+ first."""
    order = {"S+": 0, "S": 1, "A+": 2, "A": 3}
    return sorted(
        (t for t in FRACTURE_TARGETS if item_class in t["classes"]),
        key=lambda t: order[t["tier"]])


def fracture_score(tier: str, explicit_mod_count: int, magic_match: bool, meta_base: bool) -> int:
    """Score for a matched target: base tier value + bonuses (spec formula)."""
    score = FRACTURE_TIERS.get(tier, 0)
    if explicit_mod_count == 4:
        score += 15
    if magic_match:
        score += 10
    if meta_base:
        score += 10
    return score


_FRACTURE_TARGETS_BY_ID = {t["id"]: t for t in FRACTURE_TARGETS}


# Bot condition expressions VERIFIED against the bot's own ModsList.html /
# default.ipd for a subset of targets (the "_skill_gem_level_" family, plus a
# few others confirmed earlier). Anything not in this map has no confirmed
# bot-side stat id, so its example line uses a clearly-flagged placeholder
# instead of inventing one — never fabricate an expression that hasn't been
# checked against the bot's real mod list.
_FRACTURE_VERIFIED_STAT_IDS = {
    "amulet_skill_level": None,  # multiple families — see _AMULET_SKILL_IDS below
    # NOTE (owner rule, 2026-07-08): reference pickit files are READ-ONLY
    # learning material — stat ids may only be verified against the bot's own
    # files (ModsList.html / its shipped default.ipd). amulet_spirit and the
    # flat ES/Evasion targets were briefly wired from ids seen in a reference
    # file; unwired again until re-verified against the bot's own docs.
    "weapon_skill_level_bow": "bow_skill_gem_level_",
    "weapon_skill_level_crossbow": "crossbow_skill_gem_level_",
    "weapon_skill_level_quarterstaff": "melee_skill_gem_level_",
    "weapon_skill_level_2hmace": "melee_skill_gem_level_",
    "weapon_skill_level_spear": "melee_skill_gem_level_",
    "weapon_skill_level_1hmace": "melee_skill_gem_level_",
    "weapon_skill_level_wand": "spell_skill_gem_level_",
    "weapon_skill_level_staff": "spell_skill_gem_level_",
    "weapon_skill_level_sceptre": "minion_skill_gem_level_",
    "weapon_skill_level_sceptre_t2": "minion_skill_gem_level_",
    "spirit_body": "local_spirit_+%",
    "movement_speed": "base_movement_velocity_+%",
    "focus_spell": "spell_skill_gem_level_",
    "quiver_projectile": "projectile_skill_gem_level_",
    "melee_skill_level_gloves": "melee_skill_gem_level_",
    "focus_crit_spells": None,
    "flasks_max_charges": "local_max_charges_+%",
}
_AMULET_SKILL_IDS = ("spell_skill_gem_level_", "minion_skill_gem_level_",
                     "melee_skill_gem_level_", "projectile_skill_gem_level_")


def fracture_example_rule(target: dict) -> str:
    """One illustrative .ipd-style line for a Fracture Bases target. Shows the
    SAME pre-# selector the real emitted rule uses (the top-N [Type] OR-group
    from _fracture_class_selector, never the whole category) so the tab
    displays exactly what the bot will get. Uses a verified bot stat
    expression where one has been confirmed against the bot's own files;
    otherwise shows an explicit "unverified" placeholder rather than guessing
    at a bot expression id."""
    cls = target["classes"][0]
    sel = _fracture_class_selector(cls) or f'[Category] == "{cls}"'
    rarity = ('[Rarity] == "Magic"' if target.get("magic_only")
              else '[Rarity] == "Magic" || [Rarity] == "Rare"')
    stat_id = _FRACTURE_VERIFIED_STAT_IDS.get(target["id"], "__unset__")
    tail = "// FRACTURE BASES EXAMPLE — illustration only, not an active pickit rule"
    if target["id"] == "amulet_skill_level":
        cond = " || ".join(f'[{sid}] >= "3"' for sid in _AMULET_SKILL_IDS)
        cond = f"({cond})"
    elif stat_id and stat_id != "__unset__":
        cond = f'[{stat_id}] >= "<value: {target["value"]}>"'
    else:
        cond = "[UNVERIFIED_STAT_ID]"
        tail = (f'// unverified: no bot expression confirmed for "{target["text"]}" — '
                f'FRACTURE BASES EXAMPLE, illustration only')
    return (f'{sel} && ({rarity}) # {cond} '
            f'&& [StashItem] == "true"  {tail}')


# Item-class -> pre-# selector, reused verbatim from the old Rare Items tab
# (RARE_DESIGNED, removed in "Rare tab skeleton" history) — same class names,
# same selector syntax, the closest prior art for per-class item-class gating.
_FRACTURE_CLASS_SEL: dict = {
    "Body Armours": '[Category] == "BodyArmour"',
    "Helmets": '[Category] == "Helmet"',
    "Gloves": '[Category] == "Gloves"',
    "Boots": '[Category] == "Boots"',
    "Shields": '[WeaponCategory] == "Shield"',
    "Foci": '[WeaponCategory] == "Focus"',
    "Quivers": '[WeaponCategory] == "Quiver"',
    "Bows": '[WeaponCategory] == "Bow"',
    "Crossbows": '[WeaponCategory] == "Crossbow"',
    "Quarterstaves": '[WeaponCategory] == "Quarterstaff"',
    "Spears": '[WeaponCategory] == "Spear"',
    "One Hand Maces": '[WeaponCategory] == "OneHandMace"',
    "Two Hand Maces": '[WeaponCategory] == "TwoHandMace"',
    "Sceptres": '[WeaponCategory] == "Sceptre"',
    "Wands": '[WeaponCategory] == "Wand"',
    "Staves": '[WeaponCategory] == "Staff"',
    "Amulets": '[Category] == "Amulet"',
    "Rings": '[Category] == "Ring"',
    "Belts": '[Category] == "Belt"',
    "Jewels": '[Category] == "Jewel"',
    "Charms": '[Category] == "Charm"',
    "Flasks": '[Category] == "Flask"',
}

_FRACTURE_TOP_N = 3


def _fracture_class_selector(cls: str) -> str | None:
    """Narrow a class-wide selector (matches EVERY Magic/Rare item of that
    slot) down to the top _FRACTURE_TOP_N highest-level bases, using the same
    verified exceptional-base list the Exceptional Bases tab already uses —
    real game data, not a fabricated ranking. Falls back to the class-wide
    selector for slots with no base-type data (Amulets, Rings, Jewels,
    Charms, Flasks) since there's no verified way to rank those."""
    base_sel = _FRACTURE_CLASS_SEL.get(cls)
    if not base_sel:
        return None
    from exilebot_pickit.data.base_types import _BASE_TYPES_BY_CATEGORY
    from exilebot_pickit.data.icons import BASE_STATS
    entries = _BASE_TYPES_BY_CATEGORY.get(cls)
    if not entries:
        return base_sel
    ranked = sorted(entries, key=lambda e: -BASE_STATS.get(e[0], {}).get("lvl", 0))
    top = [name for name, _sockets in ranked[:_FRACTURE_TOP_N]]
    return "(" + " || ".join(f'[Type] == "{t}"' for t in top) + ")"


_FRACTURE_VALUE_RE = re.compile(r"\d+")


def _fracture_value_threshold(target: dict) -> str:
    """Lowest whole number in a target's ``value`` string, used as the ``>=``
    threshold for the wired pickup rule (e.g. "+4" -> "4", "57-61" -> "57")."""
    m = _FRACTURE_VALUE_RE.search(target["value"])
    return m.group(0) if m else "1"


def fracture_has_verified_target(item_class: str) -> bool:
    """True if at least one of this class's fracture targets has a real,
    non-placeholder bot stat id wired into pickit output."""
    for t in fracture_targets_for_class(item_class):
        sid = _FRACTURE_VERIFIED_STAT_IDS.get(t["id"], "__unset__")
        if t["id"] == "amulet_skill_level" or (sid and sid != "__unset__"):
            return True
    return False


def fracture_default(name: str) -> dict:
    """Default per-class Fracture Bases pickup state — on by default (owner
    preference). Classes with no verified target never emit rules regardless
    of this flag, so the default only has real effect on wired classes."""
    return {"enabled": True}


def _fracture_target_condition(target: dict) -> str | None:
    """Post-# stat condition for one verified fracture target, or None if the
    target has no verified bot stat id (must never be emitted as a rule)."""
    if target["id"] == "amulet_skill_level":
        cond = " || ".join(f'[{sid}] >= "3"' for sid in _AMULET_SKILL_IDS)
        return f"({cond})"
    stat_id = _FRACTURE_VERIFIED_STAT_IDS.get(target["id"], "__unset__")
    if not stat_id or stat_id == "__unset__":
        return None
    return f'[{stat_id}] >= "{_fracture_value_threshold(target)}"'


def build_fracture_pickit_rules(states: dict) -> list:
    """See docstring below."""
    from exilebot_pickit.generator import header_major as _header_major  # avoid circular import
    return _build_fracture_pickit_rules(states, _header_major)


def _build_fracture_pickit_rules(states: dict, _header_major) -> list:
    """Return pickit lines picking up Magic/Rare bases matching a verified
    Fracture Bases target, for each enabled class in ``states``
    (``{class_name: {"enabled": bool}}``).

    Only targets with a real, confirmed bot stat expression in
    ``_FRACTURE_VERIFIED_STAT_IDS`` (plus the special-cased
    ``amulet_skill_level`` OR-of-4-families) are ever emitted — targets
    without one stay reference-only in the Fracture Bases tab and never
    produce a rule here, no matter the enabled state."""
    states = states or {}
    body: list = []
    for _group, classes in FRACTURE_CLASS_GROUPS:
        for cls in classes:
            st = states.get(cls) or fracture_default(cls)
            if not st.get("enabled", True):
                continue
            sel = _fracture_class_selector(cls)
            if not sel:
                continue
            cls_lines = []
            for target in fracture_targets_for_class(cls):
                cond = _fracture_target_condition(target)
                if cond is None:
                    continue  # unverified — reference-only, never wired
                rarity = ('[Rarity] == "Magic"' if target.get("magic_only")
                          else '[Rarity] == "Magic" || [Rarity] == "Rare"')
                cls_lines.append(
                    f'{sel} && ({rarity}) # {cond} && [StashItem] == "true"'
                )
            if not cls_lines:
                continue
            body.append(f"// -- {cls} " + "-" * max(0, 73 - len(cls)))
            body.extend(cls_lines)
            body.append("")
    if not body:
        return []
    return [
        _header_major("Fracture Bases"),
        "",
        "//  Magic/Rare bases matching a verified fracture-worthy affix target.             //",
        "//  Manage individual classes in the Fracture Bases tab.                           //",
        "",
    ] + body


def classify_fracture_item(item_class: str, rarity: str, matched_target_ids: list,
                           explicit_mod_count: int, meta_base: bool = False) -> dict:
    """Classify one item for Fracture Bases purposes.

    NOTE: this is a pure scoring helper — the app has no live item-scanning
    capability, so ``matched_target_ids`` must already be pre-identified as
    real ids from ``FRACTURE_TARGETS`` (i.e. mods already confirmed natural
    Magic/Rare Base-pool affixes). Any mod that is generic, from a special
    pool (Essence/crafted/Abyss/corrupted/unique/vendor/event/Desecrated), or
    simply not in ``FRACTURE_TARGETS`` at all is NOT a valid id here and is
    silently ignored — it produces no match, exactly like every "excluded"
    category in the spec (hybrid phys+accuracy, generic/elemental/spell/chaos
    damage, damage-with-ailments, etc.).

    IMPORTANT: this function does not drive the pickit/bot output in any way —
    Fracture Bases is a reference lookup only (see FRACTURE_TARGETS docstring).
    It exists purely so "would this item be flagged in the tab" is testable.

    Returns {"matches": [...], "verdict": "fracture_candidate"|"prep_candidate"
    |"ignored", "score": int|None, "warning": str|None}.
    """
    matches = []
    for tid in matched_target_ids:
        t = _FRACTURE_TARGETS_BY_ID.get(tid)
        if not t or item_class not in t["classes"]:
            continue                                   # unknown/generic/wrong-class mod: ignored
        if t.get("magic_only") and rarity != "Magic":
            continue                                    # e.g. helmet rarity: Magic-only rule
        matches.append(t)
    warning = "more than 4 explicit modifiers" if explicit_mod_count > 4 else None
    if not matches:
        return {"matches": [], "verdict": "ignored", "score": None, "warning": warning}
    best = min(matches, key=lambda t: {"S+": 0, "S": 1, "A+": 2, "A": 3}[t["tier"]])
    magic_match = rarity == "Magic" and bool(best.get("magic_only"))
    score = fracture_score(best["tier"], explicit_mod_count, magic_match, meta_base)
    verdict = "prep_candidate" if rarity == "Magic" else "fracture_candidate"
    return {"matches": matches, "verdict": verdict, "score": score, "warning": warning}


