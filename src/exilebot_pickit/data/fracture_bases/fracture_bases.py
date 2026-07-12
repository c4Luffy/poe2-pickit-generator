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
    ("Other",     ["Jewels", "Charms"]),
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
     "threshold": "48",   # gate on the MAX roll (min rolls start at 1 on every tier)
     "text": "Adds # to # Lightning damage to Attacks",
     "reason": "A target: added lightning damage quiver prefix — T1 or T2 both count "
               "(gated on the maximum roll: T2 max is 48-59, verified live CoE)."},
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
        "Spears", "One Hand Maces"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 max 202-234 / T2 max 157-196",
     "threshold": "157",  # gate on the MAX roll (min rolls start at 1 on every tier)
     "text": "Adds # to # Lightning Damage",
     "reason": "A+ target: added lightning on a 1H-class weapon — T1 or T2 both count "
               "(T2 max roll 157-196 at ilvl75, verified live CoE)."},
    {"id": "added_lightning_weapon_2h", "tier": "A+", "classes": [
        "Crossbows", "Quarterstaves", "Two Hand Maces"],
     "affix": "prefix", "mod_tier": "T1/T2", "value": "T1 max 310-358 / T2 max 239-300",
     "threshold": "239",  # 2H-class rolls a separate, higher table
     "text": "Adds # to # Lightning Damage",
     "reason": "A+ target: added lightning on a 2H-class weapon — T1 or T2 both count "
               "(T2 max roll 239-300 at ilvl75, verified live CoE)."},
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
    # Flasks moved to the Magic & Rare tab (data/magic_rare.py) — owner
    # request. They aren't a fracture target here anymore.
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
    # files. Every id below is confirmed present in the bot's ModsList
    # (data/bot_stat_ids), NOT copied from any reference pickit.
    # All skill-gem-level ids carry a trailing "+" in the bot's ModsList.html
    # (e.g. "melee_skill_gem_level_+", verified 2026-07-09). Omitting the "+"
    # made every skill-level rule fail the official exiled-bot.net validator
    # ("Not found in stats.json") — the "+" is part of the real id.
    # Bows roll "+X to Level of all PROJECTILE Skills" — bow_skill_gem_level_+
    # is not a rollable game mod (final audit 2026-07-12, same renamed-id
    # family as spirit_body).
    "weapon_skill_level_bow": "projectile_skill_gem_level_+",
    "weapon_skill_level_crossbow": "projectile_skill_gem_level_+",  # same fix as bow
    "weapon_skill_level_quarterstaff": "melee_skill_gem_level_+",
    "weapon_skill_level_2hmace": "melee_skill_gem_level_+",
    "weapon_skill_level_spear": "melee_skill_gem_level_+",
    "weapon_skill_level_1hmace": "melee_skill_gem_level_+",
    "weapon_skill_level_wand": "spell_skill_gem_level_+",
    "weapon_skill_level_staff": "spell_skill_gem_level_+",
    "weapon_skill_level_sceptre": "minion_skill_gem_level_+",
    "weapon_skill_level_sceptre_t2": "minion_skill_gem_level_+",
    # Body Spirit is the FLAT stat (base_spirit_from_equipment, T1 57-61,
    # body/amulet only — confirmed in the game's mod database 2026-07-12).
    # local_spirit_+% is SCEPTRE-ONLY; the old mapping emitted a rule that
    # could never match a body armour.
    "spirit_body": "base_spirit_from_equipment",
    "movement_speed": "base_movement_velocity_+%",
    "focus_spell": "spell_skill_gem_level_+",
    "quiver_projectile": "projectile_skill_gem_level_+",
    "melee_skill_level_gloves": "melee_skill_gem_level_+",
    # Defensive flat/percent rolls — all re-verified against the bot ModsList
    # 2026-07-10 (local flat ES = local_energy_shield, confirmed via the Boots
    # rare-gear work; flat evasion = evasion_rating; hybrid = the *_and_* id).
    "es_body": "local_energy_shield",
    "es_helmet": "local_energy_shield",
    "es_boots": "local_energy_shield",
    # Flat Evasion is local_base_evasion_rating (the mod that rolls the exact
    # 262-300 this target quotes is LocalIncreasedEvasionRating11, on the
    # dex_armour / str_dex_int_armour tags). The bare "evasion_rating" id is
    # granted by ZERO craftable affixes — caught by tools/check_game_data.py
    # 2026-07-12, same renamed-id family as spirit_body. Evasion itself is of
    # course in the game; only our id for it was wrong, so these three rules
    # could never match. Note the flat-ES twin above is local_energy_shield —
    # GGG's naming is not parallel between the two defences.
    "evasion_body": "local_base_evasion_rating",
    "evasion_helmet": "local_base_evasion_rating",
    "evasion_boots": "local_base_evasion_rating",
    "es_evasion_hybrid_helmet": "local_evasion_and_energy_shield_+%",
    "es_evasion_hybrid_boots": "local_evasion_and_energy_shield_+%",
    "es_evasion_pct_body": "local_energy_shield_+%",
    "rarity_helmet": "base_item_found_rarity_+%",
    # Weapons / offhand / accessories.
    "inc_phys_weapon": "local_physical_damage_+%",
    "added_phys_weapon": "local_minimum_added_physical_damage",
    "added_phys_weapon_2h": "local_minimum_added_physical_damage",
    "crit_chance_weapon": "local_critical_strike_chance_+%",
    "crit_chance_amulet": "critical_strike_chance_+%",
    "focus_crit_spells": "spell_critical_strike_chance_+%",
    # The only craftable elemental-damage affix is the with-attack-skills one
    # (the rare-gear weapon recipes already score it under this id); bare
    # elemental_damage_+% is not a normal affix — tools/check_game_data.py,
    # 2026-07-12.
    "elemental_dmg_with_attacks": "elemental_damage_with_attack_skills_+%",
    "added_lightning_weapon": "local_maximum_added_lightning_damage",
    "added_lightning_weapon_2h": "local_maximum_added_lightning_damage",
    "sceptre_spirit": "local_spirit_+%",
    "sceptre_allies_dmg": "allies_in_presence_damage_+%",
    # The rollable game stat is base_number_of_crossbow_bolts (audit 2026-07-12).
    "crossbow_load_bolt": "base_number_of_crossbow_bolts",
    "quiver_proj_speed": "base_projectile_speed_+%",
    # The rollable game stat is damage_+%_with_bow_skills (audit 2026-07-12).
    "quiver_bow_dmg": "damage_+%_with_bow_skills",
    "quiver_added_lightning": "local_maximum_added_lightning_damage",
    "quiver_crit_chance_attacks": "attack_critical_strike_chance_+%",
    "amulet_spirit": "base_spirit_from_equipment",
    "sceptre_minion_life": "minion_maximum_life_+%",
    "wand_crit_spells": "spell_critical_strike_chance_+%",
    "wand_spell_dmg": "spell_damage_+%",
    "staff_crit_spells": "spell_critical_strike_chance_+%",
    "staff_spell_dmg": "spell_damage_+%",
    "belt_life": "base_maximum_life",
    "belt_mana": "base_maximum_mana",
    # Crit-damage family, resolved 2026-07-11: PoE2 renamed the DISPLAY text
    # to "Critical Damage Bonus" but the ENGINE ids are still the legacy
    # *_critical_strike_multiplier_+ family — confirmed in the game's own mod
    # database (repoe-fork poe2 mods.json GGPK dump: gloves CriticalMultiplier5
    # rolls 30-34 base_critical_strike_multiplier_+, quiver
    # AttackCriticalStrikeMultiplier6 rolls 35-39, staff
    # SpellCriticalStrikeMultiplierTwoHand6 rolls 53-59 — all matching these
    # targets' value strings exactly), then re-checked present in the bot's
    # ModsList. The *_critical_hit_damage_bonus ids that ALSO sit in the
    # ModsList are not the rollable item mods — never switch to them.
    "crit_damage_gloves": "base_critical_strike_multiplier_+",
    "quiver_crit_dmg_attacks": "attack_critical_strike_multiplier_+",
    "staff_crit_spell_dmg_bonus": "base_spell_critical_strike_multiplier_+",
}
_AMULET_SKILL_IDS = ("spell_skill_gem_level_+", "minion_skill_gem_level_+",
                     "melee_skill_gem_level_+", "projectile_skill_gem_level_+")

# Multi-stat targets: ONE rule whose post-# condition is an OR-group — the
# same (a || b) syntax the amulet_skill_level rule already uses (validator-
# proven). Per-stat thresholds because the qualifying roll differs per
# element. Rolls verified 2026-07-11 against the game's own mod database
# (repoe-fork poe2 mods.json); every stat id re-checked in the bot ModsList.
_FRACTURE_OR_GROUP_IDS = {
    # Owner rule "T1 or T2 both count" -> threshold is the T2 minimum roll.
    # Added damage gates on the MAX-roll stat (min rolls are tiny) — same
    # approach as the added-lightning weapon targets. T2 = AddedX8 (ilvl 65):
    # phys max 18-26, fire max 33-36, cold max 25-31, lightning max 48-59.
    "added_dmg_gloves": (
        ("attack_maximum_added_physical_damage", "18"),
        ("attack_maximum_added_fire_damage", "33"),
        ("attack_maximum_added_cold_damage", "25"),
        ("attack_maximum_added_lightning_damage", "48"),
    ),
    # Any single-element res, T1 or T2: elemental T2 = 36-40 (Resist7),
    # chaos T2 = 20-23 (ChaosResist5) — matches this target's value string.
    "belt_resist": (
        ("base_fire_damage_resistance_%", "36"),
        ("base_cold_damage_resistance_%", "36"),
        ("base_lightning_damage_resistance_%", "36"),
        ("base_chaos_damage_resistance_%", "20"),
    ),
}


def fracture_example_rule(target: dict) -> str:
    """Illustrative .ipd lines for a Fracture Bases target — the SAME lines the
    real emitted rule produces: ONE line per base (top-N, never an OR-group)
    and per rarity, so the tab shows exactly what the bot gets. Uses a verified
    bot stat expression where one has been confirmed against the bot's own
    files; otherwise an explicit "unverified" placeholder rather than a guess."""
    cls = target["classes"][0]
    selectors = _fracture_base_selectors(cls) or [f'[Category] == "{cls}"']
    rarities = ["Magic"] if target.get("magic_only") else ["Magic", "Rare"]
    tail = "// FRACTURE BASES EXAMPLE — illustration only, not an active pickit rule"
    # Reuse the REAL condition builder so the shown line is byte-for-byte what
    # the pickit emits (a concrete threshold like "57", never a "<value: …>"
    # placeholder that the bot validator would reject as non-numeric).
    cond = _fracture_target_condition(target)
    if cond is None:
        cond = "[UNVERIFIED_STAT_ID]"
        tail = (f'// unverified: no bot expression confirmed for "{target["text"]}" — '
                f'FRACTURE BASES EXAMPLE, illustration only')
    return "\n".join(
        f'{sel} && [Rarity] == "{rar}" && [ItemTier] >= "{FRACTURE_MIN_ITEM_TIER}" '
        f'# {cond} && [StashItem] == "true"  {tail}'
        for sel in selectors for rar in rarities)


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
}

_FRACTURE_TOP_N = 3

# Ground-label gate for every emitted fracture rule: [ItemTier] is readable
# BEFORE pickup (unlike ItemLevel), so the bot skips low-tier drops instead of
# hauling them home to vendor. Tier 4+ ≈ endgame bases (owner-tested value).
FRACTURE_MIN_ITEM_TIER = 4

# Manual base picks for slots with no defence/ilvl ranking data (accessories).
# Owner-chosen: amulets fracture only on Solar (+Spirit implicit) and Gold
# (rarity implicit) bases, each as its own rule line — not the whole category.
_FRACTURE_BASE_OVERRIDES: dict = {
    "Amulets": ["Solar Amulet", "Gold Amulet"],
}


def _fracture_base_selectors(cls: str) -> list | None:
    """Return the list of pre-# selectors for a class — ONE per base, never a
    combined OR-group (owner rule: every base gets its own rule line). Priority:
    an explicit owner override (_FRACTURE_BASE_OVERRIDES) → the top
    _FRACTURE_TOP_N highest-level bases from verified base-type data → the
    single class-wide selector for slots with neither. None if no selector."""
    base_sel = _FRACTURE_CLASS_SEL.get(cls)
    if not base_sel:
        return None
    override = _FRACTURE_BASE_OVERRIDES.get(cls)
    if override:
        return [f'[Type] == "{name}"' for name in override]
    from exilebot_pickit.data.base_types import _BASE_TYPES_BY_CATEGORY
    from exilebot_pickit.data.icons import BASE_STATS
    entries = _BASE_TYPES_BY_CATEGORY.get(cls)
    if not entries:
        return [base_sel]
    ranked = sorted(entries, key=lambda e: -BASE_STATS.get(e[0], {}).get("lvl", 0))
    return [f'[Type] == "{name}"' for name, _sockets in ranked[:_FRACTURE_TOP_N]]


_FRACTURE_VALUE_RE = re.compile(r"\d+")


def _fracture_value_threshold(target: dict) -> str:
    """Lowest qualifying roll in a target's ``value`` string, used as the
    ``>=`` threshold for the wired pickup rule (e.g. "+4" -> "4",
    "57-61" -> "57", "T1 35-38% / T2 30-34%" -> "30").

    Tier tags like "T1"/"T2" are stripped FIRST — the old version matched the
    1 in "T1", emitting useless ``>= "1"`` thresholds (owner-caught bug,
    2026-07-10). For multi-tier values the minimum across every listed range
    is correct: the owner's rule for those targets is "T1 or T2 both count"."""
    if target.get("threshold"):          # explicit override wins (used where
        return str(target["threshold"])  # the value string can't express it)
    cleaned = re.sub(r"\bT\d+\b", " ", target["value"])
    nums = [int(n) for n in re.findall(r"\d+", cleaned)]
    return str(min(nums)) if nums else "1"


def fracture_has_verified_target(item_class: str) -> bool:
    """True if at least one of this class's fracture targets has a real,
    non-placeholder bot stat id wired into pickit output."""
    for t in fracture_targets_for_class(item_class):
        sid = _FRACTURE_VERIFIED_STAT_IDS.get(t["id"], "__unset__")
        if (t["id"] == "amulet_skill_level" or t["id"] in _FRACTURE_OR_GROUP_IDS
                or (sid and sid != "__unset__")):
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
    group = _FRACTURE_OR_GROUP_IDS.get(target["id"])
    if group:
        cond = " || ".join(f'[{sid}] >= "{thr}"' for sid, thr in group)
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
            selectors = _fracture_base_selectors(cls)
            if not selectors:
                continue
            cls_lines = []
            # Dedupe: same base+rarity+stat with two thresholds keeps only the
            # LOWEST (a ">= 3" rule makes a ">= 4" twin pointless — the pair of
            # sceptre skill-level targets used to emit both, owner-caught).
            best: dict = {}
            order: list = []
            for target in fracture_targets_for_class(cls):
                cond = _fracture_target_condition(target)
                if cond is None:
                    continue  # unverified — reference-only, never wired
                m = re.match(r'^\[([^\]]+)\] >= "(\d+)"$', cond)
                # One line per base AND per rarity (owner rule) — never a
                # combined ([Type]||[Type]) group and never a combined
                # (Magic||Rare) group. Every base × rarity is its own rule.
                rarities = (["Magic"] if target.get("magic_only")
                            else ["Magic", "Rare"])
                for sel in selectors:
                    for rar in rarities:
                        key = (sel, rar, m.group(1)) if m else (sel, rar, cond)
                        thr = int(m.group(2)) if m else None
                        if key not in best:
                            best[key] = thr
                            order.append(key)
                        elif thr is not None and best[key] is not None:
                            best[key] = min(best[key], thr)
            for key in order:
                sel, rar, stat = key
                thr = best[key]
                cond = f'[{stat}] >= "{thr}"' if thr is not None else stat
                cls_lines.append(
                    f'{sel} && [Rarity] == "{rar}" && [ItemTier] >= "{FRACTURE_MIN_ITEM_TIER}" '
                    f'# {cond} && [StashItem] == "true"'
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


