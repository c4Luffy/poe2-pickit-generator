"""
ExileBot 2 Pickit Generator
---------------------------
Pulls live currency/item economy data from poe.ninja's real PoE2 API and
generates Exiled Bot 2 pickit rules:

[Type] == "Name" # [StashItem] == "true" // X.XXXXXX exalted | original: Y.YYYY divine

Endpoints verified against oubahell/PICKIT-Poe2 (https://github.com/oubahell/PICKIT-Poe2):
  - League list:     https://poe.ninja/poe2/api/data/index-state
  - Exchange data:   https://poe.ninja/poe2/api/economy/exchange/current/overview
  - Unique items:    https://poe.ninja/poe2/api/economy/stash/current/item/overview

Usage:
    python -m exilebot_pickit --cli --league "Fate of the Vaal"
    python -m exilebot_pickit --cli --list-leagues
"""

import argparse
import csv
import difflib
import io
import os
import re
import sys
import time

import requests

# ── Re-exports from sub-modules (backward compatible API) ─────────────────────
from exilebot_pickit.data.corrections import (  # noqa: F401
    ALWAYS_PICK_CURRENCY, ALWAYS_PICK_RUNES,
    ITEM_NAME_CORRECTIONS, ITEM_NAME_SKIP, WAYSTONE_FALLBACK_RULES,
    EXOTIC_BASES, SPECIAL_ITEMS, SPLINTERS, TABLET_TYPES,
    TABLET_UNIQUES, WOMBGIFTS,
)
from exilebot_pickit.data.base_types import (  # noqa: F401
    _BASE_TYPES_BY_CATEGORY,
)
from exilebot_pickit.api.client import (  # noqa: F401
    ALL_CATEGORIES, BASE_URL, EXCHANGE_CATEGORIES, INDEX_STATE_URL, MIN_EXALT,
    PICK_ALL_CATEGORIES, UNIQUE_CATEGORIES, USER_AGENT,
    _cache_get, _cache_set, _disk_cache_file, _DISK_CACHE_DIR,
    _request_with_retry, _RETRYABLE_STATUS,
    cache_info, clear_cache, detect_current_league, divine_value_from_exalt,
    exalted_rate, fetch_all_payloads, fetch_category, fetch_json,
    fetch_live_leagues, load_payload_from_disk, prune_disk_cache,
    save_payload_to_disk, set_disk_cache_dir,
)



def cfg_int(d: dict, key: str, default: int) -> int:
    """Non-negative int from a config/snapshot dict; bad/missing → default.
    Single canonical copy — ui_common and pickit_assembly alias this."""
    try:
        v = int(float(d.get(key, default)))
    except (TypeError, ValueError):
        v = default
    return max(0, v)


def write_text_atomic(path: str, content: str, encoding: str = "utf-8", newline: str | None = None) -> None:
    """Write text to *path* via a temp file + atomic rename.

    Plain ``open(path, "w")`` leaves a truncated/corrupt file in place if the
    process dies mid-write (crash, forced shutdown, disk full). Writing to a
    sibling temp file first and swapping it in with ``os.replace`` (atomic on
    both Windows and POSIX) means readers only ever see the old complete file
    or the new complete file, never a partial one."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding=encoding, newline=newline) as f:
        f.write(content)
    os.replace(tmp, path)

# (ITEM_NAME_CORRECTIONS, ITEM_NAME_SKIP, ALWAYS_PICK_CURRENCY, ALWAYS_PICK_RUNES,
#  WAYSTONE_FALLBACK_RULES and _BASE_TYPES_BY_CATEGORY
#  are imported from exilebot_pickit.data.corrections/base_types)


def _quote_ipd(name: str) -> str:
    """Escape double quotes inside an item name for the IPD rule format."""
    return name.replace('"', '\\"')


# ─────────────────────────────────────────────────────────────────────────────
#  Pickit validation (mirrors what exiled-bot.net flags, best-effort)
# ─────────────────────────────────────────────────────────────────────────────
#  Exiled Bot's full accepted base-type list isn't public, so we can't replicate
#  it perfectly for economy items. We DO reliably check:
#    • rule syntax (balanced quotes/brackets, a [StashItem] action)
#    • equipment base-type rules against the bases we ship (catches typos / a
#      unique name wrongly used as a base, e.g. "Dustbloom")
#    • maintained lists of names Exiled Bot rejects / deprecates
#  The maintained lists are easy to extend as new cases surface.

# Accessories (rings, amulets) don't have socket/quality gate rules so they
# aren't in _BASE_TYPES_BY_CATEGORY, but they appear in CHANCE_BASES and need
# to be accepted by the validator.
_ACCESSORY_BASES: frozenset = frozenset({
    # Rings
    "Gold Ring", "Iron Ring", "Ruby Ring", "Topaz Ring", "Sapphire Ring",
    "Emerald Ring", "Two-Stone Ring", "Prismatic Ring", "Unset Ring",
    # Amulets
    "Coral Amulet", "Paua Amulet", "Amber Amulet", "Jade Amulet",
    "Lapis Amulet", "Gold Amulet", "Agate Amulet", "Citrine Amulet",
    "Turquoise Amulet", "Onyx Amulet", "Solar Amulet", "Stellar Amulet",
})

VALID_EQUIPMENT_BASES: frozenset = (
    frozenset(name for entries in _BASE_TYPES_BY_CATEGORY.values() for name, _ in entries)
    | _ACCESSORY_BASES
)

# Names Exiled Bot rejects outright (validation error). Seeded with the cases we
# already hit so they're caught immediately if a data update reintroduces them as
# a [Type] (note: "Dustbloom" is still valid as a [UniqueName], which we don't flag).
KNOWN_INVALID_TYPES: set = {
    "Necrotic Catalyst",
    "Refined Necrotic Catalyst",
    "Dustbloom",
}

# Names Exiled Bot still accepts but marks as deprecated (validation warning).
DEPRECATED_TYPES: set = {"Aldur's Legacy"}

_VAL_TYPE_RE   = re.compile(r'\[Type\]\s*==\s*"((?:[^"\\]|\\.)*)"')
_VAL_UNIQUE_RE = re.compile(r'\[UniqueName\]\s*==\s*"((?:[^"\\]|\\.)*)"')


def validate_pickit(lines) -> dict:
    """Statically validate generated pickit lines (no network).

    Returns {"errors": [(lineno, msg), ...], "warnings": [(lineno, msg), ...]}.
    Only active (non-commented) rule lines are checked; ``//`` lines and
    headers/blanks are skipped.
    """
    errors: list = []
    warnings: list = []
    for i, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("/"):
            continue  # blank line, header, or commented-out (disabled) rule
        if "#" not in line and "[StashItem]" not in line:
            continue  # not a rule line
        if "[StashItem]" in line and "#" not in line:
            errors.append((i, "Rule has [StashItem] but is missing the # separator"))
            continue

        if line.count('"') % 2 != 0:
            errors.append((i, "Unbalanced quotes in rule"))
            continue
        if line.count("[") != line.count("]"):
            errors.append((i, "Unbalanced [ ] brackets in rule"))
            continue
        if "[StashItem]" not in line:
            errors.append((i, "Rule has no [StashItem] action"))
            continue

        # [ItemLevel] is only readable after pickup — must appear AFTER the #
        # separator. Flag as a warning if found in the condition block (before #).
        if "[ItemLevel]" in line and "#" in line:
            pre_hash = line.split("#", 1)[0]
            if "[ItemLevel]" in pre_hash:
                warnings.append((i, "[ItemLevel] appears before # — move it to the action block after #"))

        m  = _VAL_TYPE_RE.search(line)
        mu = _VAL_UNIQUE_RE.search(line)
        tname = m.group(1).replace('\\"', '"') if m else None
        uname = mu.group(1).replace('\\"', '"') if mu else None

        if tname and tname in KNOWN_INVALID_TYPES:
            errors.append((i, f'Invalid base type: "{tname}"'))
            continue
        if tname and tname in DEPRECATED_TYPES:
            warnings.append((i, f'Deprecated base type: "{tname}"'))

        # Equipment base-type rule = a [Type] rule with a Quality/Sockets gate
        # that is NOT a unique. These map 1:1 to the bases we ship, so an unknown
        # name here is a real error.
        is_base_rule = (
            tname is not None and uname is None
            and '[Rarity] == "Unique"' not in line
            and ('[Quality]' in line or '[Sockets]' in line)
        )
        if is_base_rule and tname not in VALID_EQUIPMENT_BASES:
            msg = f'Invalid base type: "{tname}"'
            near = difflib.get_close_matches(tname, VALID_EQUIPMENT_BASES, n=3, cutoff=0.6)
            if near:
                msg += "  — did you mean: " + " or ".join(f'"{s}"' for s in near)
            errors.append((i, msg))

    return {"errors": errors, "warnings": warnings}


def build_base_rules(min_quality: int = 25, min_level: int = 82, progress_callback=None, disabled=None) -> list:
    """Build endgame base-type pickup rules from local game data — no network requests.

    Uses _BASE_TYPES_BY_CATEGORY (sourced from baseitemtypes.json) for all equipment
    bases with DropLevel >= 60. (Runeforged/Runemastered variants are deliberately
    NOT included: they are anvil-crafted from dropped bases and never drop
    themselves, so pickup rules for them would be inert.)

    Each category gets its own header_minor section, then per base:
      [Type] == "Name" && [Quality] >= "min_quality" # [StashItem] == "true"
      [Type] == "Name" && [Sockets] >= "N"           # [StashItem] == "true"  (if sock > 0)
    """
    all_lines: list = []
    cats = sorted(_BASE_TYPES_BY_CATEGORY.keys())
    total = len(cats)

    for idx, cat in enumerate(cats, 1):
        if progress_callback:
            progress_callback(idx, total, cat)
        entries = _BASE_TYPES_BY_CATEGORY[cat]
        all_lines.append(header_minor(cat))
        all_lines.append("")
        cat_rules: set = set()
        _dis = set(disabled or ())
        for name, sock in entries:
            if name in _dis:
                continue
            safe = _quote_ipd(name)
            cat_rules.add(f'[Type] == "{safe}" && [Quality] >= "{min_quality}" # [ItemLevel] >= "{min_level}" && [StashItem] == "true"')
            if sock > 0:
                cat_rules.add(f'[Type] == "{safe}" && [Sockets] >= "{sock}" # [ItemLevel] >= "{min_level}" && [StashItem] == "true"')
        all_lines.extend(sorted(cat_rules))
        all_lines.append("")

    return all_lines


# ─────────────────────────────────────────────────────────────────────────────
#  Craft bases — pick the BEST WHITE (Normal) base of each defence type per slot
#  at high item level, as blank bases worth crafting on. Curated (not the full
#  base list) to keep the stash from filling up. Emitted as:
#    [Type] == "Name" && [Rarity] == "Normal" && [ItemLevel] >= "82" # [StashItem] == "true"
#
#  These are best-effort meta picks (verified to exist in the base list); they are
#  toggleable in the Craft Bases tab and easy to swap here. Sword/axe/mace are
#  intentionally omitted.
# ─────────────────────────────────────────────────────────────────────────────

# Item classes in game order, grouped — the roadmap shared by Craft Bases and
# Fracture Bases. (Historically named RARE_CLASS_GROUPS; kept spelled out here
# since Fracture Bases replaced the old Rare tab that first introduced it.)
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
     "affix": "suffix", "mod_tier": "T1", "value": "+4",
     "text": "+4 to Level of all Spell Skills",
     "reason": "S+ target: top-tier wand skill-level mod verified from live data."},
    {"id": "weapon_skill_level_staff", "tier": "S+", "classes": ["Staves"],
     "affix": "suffix", "mod_tier": "T1", "value": "+5 to +6",
     "text": "+5-6 to Level of all Spell Skills",
     "reason": "S+ target: top-tier staff skill-level mod verified from live data."},
    {"id": "weapon_skill_level_sceptre", "tier": "S+", "classes": ["Sceptres"],
     "affix": "suffix", "mod_tier": "T1", "value": "+4",
     "text": "+4 to Level of all Minion Skills",
     "reason": "S+ target: top-tier sceptre skill-level mod verified from live data."},
    {"id": "spirit_body", "tier": "S+", "classes": ["Body Armours"],
     "affix": "prefix", "mod_tier": "T1", "value": "57-61",
     "text": "+57-61 to Spirit",
     "reason": "S+ target: T1 Spirit (verified natural body armour affix)."},
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
]
# Targets the spec's own verification step rejected — kept here (not shown in
# the UI) so a future data refresh can re-check without re-deriving the answer.
FRACTURE_EXCLUDED_UNVERIFIED = {
    "crit_chance_gloves": "No Critical Hit Chance affix exists on Gloves in the "
                           "current mod data — only Critical Damage Bonus rolls "
                           "there, which the spec explicitly excludes.",
    "focus_minion": "No natural (Base-pool) +Minion Skills mod exists on Focus. "
                     "The only Minion Skills mod found on Focus comes from the "
                     "Desecrated pool (a boss/Well of Souls mechanic, not a "
                     "normal drop pool) — explicitly excluded per the spec's "
                     "own source rules.",
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


CRAFT_BASE_MIN_ILVL = 82

# Ordered slot -> [(base_name, defence_type), ...].  Armour slots cover ALL six
# defence types — the three pure attributes (STR=Armour, DEX=Evasion, INT=Energy
# Shield) plus the three hybrids (STR/DEX, STR/INT, DEX/INT) — using the highest
# item-level-82 base of each type (verified against poe2db).  Off-hand + weapons
# keep the top base(s) per type ranked by base phys DPS (Craft of Exile 2 data);
# attribute hybrids don't apply to them.
_CRAFT_BEST_BASES: dict = {
    "Body Armours":  [("Warlord Cuirass", "STR"),     ("Corsair Coat", "DEX"),
                      ("Feathered Raiment", "INT"),    ("Thane Mail", "STR/DEX"),
                      ("Seastorm Mantle", "STR/INT"),  ("Austere Garb", "DEX/INT")],
    "Helmets":       [("Imperial Greathelm", "STR"),   ("Freebooter Cap", "DEX"),
                      ("Ancestral Tiara", "INT"),      ("Gladiatorial Helm", "STR/DEX"),
                      ("Cryptic Crown", "STR/INT"),    ("Grinning Mask", "DEX/INT")],
    "Gloves":        [("Massive Mitts", "STR"),        ("Polished Bracers", "DEX"),
                      ("Sirenscale Gloves", "INT"),    ("Blacksteel Gauntlets", "STR/DEX"),
                      ("Adherent Cuffs", "STR/INT"),   ("Secured Wraps", "DEX/INT")],
    "Boots":         [("Tasalian Greaves", "STR"),     ("Drakeskin Boots", "DEX"),
                      ("Sekhema Sandals", "INT"),      ("Blacksteel Sabatons", "STR/DEX"),
                      ("Cryptic Leggings", "STR/INT"), ("Daggerfoot Shoes", "DEX/INT")],
    "Foci":          [("Tasalian Focus", "INT")],
    "Spears":        [("Grand Spear", "STR/DEX")],
    "Quarterstaves": [("Aegis Quarterstaff", "DEX/INT"), ("Sinister Quarterstaff", "DEX/INT")],
    "Crossbows":     [("Desolate Crossbow", "STR/DEX")],
    "Bows":          [("Obliterator Bow", "DEX"), ("Warmonger Bow", "DEX"),
                      ("Guardian Bow", "DEX")],
    "Staves":        [("Permafrost Staff", "INT")],
    "Wands":         [("Dueling Wand", "INT")],
    # Accessories — high-value Normal bases worth crafting on from item level 75.
    "Amulets":       [("Stellar Amulet", ""), ("Gold Amulet", ""), ("Solar Amulet", "")],
    "Rings":         [("Gold Ring", ""), ("Prismatic Ring", "")],
}

# Flat base_name -> defence_type lookup (used for the Craft Bases card labels).
_CRAFT_BASE_DEFENCE = {n: dt for items in _CRAFT_BEST_BASES.values() for n, dt in items}

# Craft bases are their own curated list (not the pruned exceptional-base list),
# so their names must also count as valid equipment bases for the validator.
VALID_EQUIPMENT_BASES = VALID_EQUIPMENT_BASES | frozenset(_CRAFT_BASE_DEFENCE)

# Per-base minimum item level overrides — accessories are worth crafting on from a
# lower ilvl than armour, so they're not gated by the global min (default 82).
_CRAFT_BASE_ILVL_OVERRIDES: dict = {
    "Stellar Amulet": 75, "Gold Amulet": 75, "Solar Amulet": 75,
    "Gold Ring": 75, "Prismatic Ring": 75,
}


def craft_base_categories() -> list:
    """Ordered ``[(category, [base_name, ...]), ...]`` for the curated craft bases."""
    return [(cat, [n for n, _ in items]) for cat, items in _CRAFT_BEST_BASES.items() if items]


def craft_base_defence(name: str) -> str:
    """Defence-type label (STR / DEX / INT / STR/DEX / …) for a craft base, '' for weapons."""
    return _CRAFT_BASE_DEFENCE.get(name, "")


def craft_base_default_ilvl(name: str, global_min: int = CRAFT_BASE_MIN_ILVL) -> int:
    """Default item level for a craft base: the built-in per-base override (e.g. 75
    for accessories) if one exists, otherwise the global minimum (default 82)."""
    return _CRAFT_BASE_ILVL_OVERRIDES.get(name, global_min)


def build_craft_base_rules(disabled=None, min_ilvl: int = CRAFT_BASE_MIN_ILVL,
                           ilvl_overrides: dict = None) -> list:
    """Return pickit lines that pick Normal-rarity bases at item level >= their
    per-base level — ideal blank bases for crafting. Skips names in ``disabled``.

    Per-base item level precedence: ``ilvl_overrides[name]`` (user-set in the GUI)
    → the built-in accessory default → ``min_ilvl`` (the global default)."""
    skip = set(disabled) if disabled else set()
    overrides = ilvl_overrides or {}
    body: list = []
    for cat, names in craft_base_categories():
        active = [n for n in names if n not in skip]
        if not active:
            continue
        body.append(f"// -- {cat} " + "-" * max(0, 73 - len(cat)))
        for name in active:
            safe = _quote_ipd(name)
            ilvl = overrides.get(name, _CRAFT_BASE_ILVL_OVERRIDES.get(name, min_ilvl))
            body.append(
                f'[Type] == "{safe}" && [Rarity] == "Normal" '
                f'# [ItemLevel] >= "{ilvl}" && [StashItem] == "true"'
            )
        body.append("")
    if not body:
        return []
    return [
        "/////////////////////////////////////////////////////////////////////////////////////",
        "//                                                                                 //",
        "//                              CRAFT BASES                                        //",
        f"//  Normal-rarity bases at item level {min_ilvl}+ - blank bases worth crafting on.        //",
        "//  Manage individual bases in the Craft Bases tab.                                //",
        "//                                                                                 //",
        "/////////////////////////////////////////////////////////////////////////////////////",
        "",
    ] + body


# ─────────────────────────────────────────────────────────────────────────────

_W = 85  # total line width for all headers


def header_major(title: str) -> str:
    border  = "/" * _W
    blank   = "//" + " " * (_W - 4) + "//"
    content = "//" + title.upper().center(_W - 4) + "//"
    return "\n".join([border, blank, content, blank, border])


def header_sub(title: str) -> str:
    border  = "/" * _W
    content = "//" + title.upper().center(_W - 4) + "//"
    return "\n".join([border, content, border])


def header_minor(title: str) -> str:
    inner = f" ── {title} "
    dashes = "─" * (_W - len(inner) - 5)
    return f"//{inner}{dashes} //"


# ── Always-pick static sections (tablets / wombgifts / specials) ─────────────
# Item names live in data/corrections.py and are remote-updatable via
# game_data.json; only the rule syntax is built here.

def build_tablet_rules(disabled=None) -> list:
    """Unique tablets by name, all regular tablets, and splinters.

    ``disabled`` — item names the user switched off in the Economy tab
    (tablet type, unique tablet name, or splinter name)."""
    dis = set(disabled or ())
    out = []
    uniq = [(t, n) for t, n in TABLET_UNIQUES if n not in dis]
    if uniq:
        out += header_major("Unique Tablets").splitlines() + [""]
        for typ, name in uniq:
            out.append(f'[Type] == "{typ}" && [Rarity] == "Unique" # [UniqueName] == "{name}" && [StashItem] == "true" && [IgnoreRitual] == "true"')
        out.append("")
    types = [t for t in TABLET_TYPES if t not in dis]
    if types:
        out += header_major("Regular Tablets (all rarities)").splitlines() + [""]
        for typ in types:
            for rar in ("Normal", "Magic", "Rare"):
                out.append(f'[Type] == "{typ}" && [Rarity] == "{rar}" # [StashItem] == "true"')
        out.append("")
    spl = [s for s in SPLINTERS if s not in dis]
    if spl:
        out += header_major("Splinters").splitlines() + [""]
        for s in spl:
            out.append(f'[Type] == "{s}" # [StashItem] == "true"')
    while out and out[-1] == "":
        out.pop()
    return out


def build_wombgift_rules(disabled=None) -> list:
    dis = set(disabled or ())
    keep = [w for w in WOMBGIFTS if w not in dis]
    if not keep:
        return []
    out = header_major("Breach Wombgifts").splitlines() + [""]
    for w in keep:
        out.append(f'[Type] == "{w}" # [StashItem] == "true"')
    return out



def build_special_item_rules(disabled=None) -> list:
    dis = set(disabled or ())
    keep = [s for s in SPECIAL_ITEMS if s not in dis]
    if not keep:
        return []
    out = header_major("Special Items").splitlines() + [""]
    for s in keep:
        out.append(f'[Type] == "{s}" # [StashItem] == "true" && [IgnoreRitual] == "true"')
    return out


def build_exotic_base_rules(disabled=None) -> list:
    """Drop-only exotic bases (breach rings, dusk jewellery, Runic Fork...)
    picked at any rarity — they sell as bases. List is remote-updatable."""
    dis = set(disabled or ())
    keep = [b for b in EXOTIC_BASES if b not in dis]
    if not keep:
        return []
    out = header_major("Exotic Bases").splitlines() + [
        "",
        "// Special drop-only bases that sell as bases at any rarity.",
        "",
    ]
    for b in keep:
        out.append(f'[Type] == "{b}" # [StashItem] == "true"')
    return out



# NOTE: type-less catch-all rules ([Quality] >= "21" / [Sockets] >= "3" with
# no [Type]) were tried and REMOVED (owner, 2026-07-05): Exiled Bot treats a
# rule without [Type] as matching EVERYTHING and would pick the whole ground.
# Do not re-add. Exceptional pickup is per-base (build_base_rules quality/
# sockets pairs). Uniques are picked purely by their poe.ninja value.


# Structured list of chance orb bases — used by the Chance Bases tab and
# build_chance_base_rules(). Each entry: (category_label, base_type, target_unique).
# Curated by the owner (2026-07-06); all bases confirmed droppable in the
# current patch against NeverSink's live filter.
CHANCE_BASES: list = [
    ("Belts",   "Utility Belt",   "Mageblood"),
    ("Belts",   "Heavy Belt",     "Headhunter"),
    ("Rings",   "Gold Ring",      "Ventor's Gamble / Andvarius / Perandus Seal"),
    ("Amulets", "Stellar Amulet", "Astramentis"),
    ("Belts",   "Ornate Belt",    "Ryslatha's Coil"),
    ("Amulets", "Solar Amulet",   "Fireflower"),
    ("Rings",   "Emerald Ring",   "Thief's Torment / Death Rush"),
    ("Amulets", "Gold Amulet",    "Eye of Chayula / Serpent's Egg"),
]


def build_chance_base_rules(disabled_bases=None) -> list:
    """Return pickit lines for chance orb bases, skipping any in disabled_bases."""
    disabled = set(disabled_bases) if disabled_bases else set()
    active   = [(cat, base, tgt) for cat, base, tgt in CHANCE_BASES if base not in disabled]
    if not active:
        return []
    out = [
        "/////////////////////////////////////////////////////////////////////////////////////",
        "//                                                                                 //",
        "//                           CHANCE ORB BASES                                      //",
        "//  Normal bases worth using Orb of Chance on to target specific uniques.          //",
        "//  Manage individual bases in the Chance Bases tab.                               //",
        "//                                                                                 //",
        "/////////////////////////////////////////////////////////////////////////////////////",
        "",
    ]
    cur_cat = None
    for cat, base_type, target in active:
        if cat != cur_cat:
            cur_cat = cat
            out.append(f"// -- {cat} " + "-" * (73 - len(cat)))
        out.append(f'[Type] == "{base_type}" && [Rarity] == "Normal" # [StashItem] == "true" // {target}')
    out.append("")
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  PoE2 client loot-filter export
#  Translates the generated .ipd pickit into an in-game .filter file: every item
#  the bot would pick becomes a `Show` block, everything else is hidden. The
#  game filter only understands BaseType / Rarity / Quality / Sockets / Class —
#  it cannot replicate [UniqueName] or value thresholds, so uniques are shown by
#  base type (matching reference filters generated from IPD).
# ─────────────────────────────────────────────────────────────────────────────
_LF_TYPE_RE     = re.compile(r'\[Type\]\s*==\s*"((?:[^"\\]|\\.)*)"')
_LF_RARITY_RE   = re.compile(r'\[Rarity\]\s*==\s*"(\w+)"')
_LF_QUALITY_RE  = re.compile(r'\[Quality\]\s*>=\s*"(\d+)"')
_LF_SOCKETS_RE  = re.compile(r'\[Sockets\]\s*>=\s*"(\d+)"')
_LF_CATEGORY_RE = re.compile(r'\[Category\]\s*==\s*"(\w+)"')

_LF_CHUNK = 30  # BaseTypes per Show block (matches reference IPD-derived filters)


def _lf_show_blocks(names, extra_lines, chunk: int = _LF_CHUNK) -> list:
    """Build Show-block lines for a list of base names, de-duped and chunked.

    ``extra_lines`` are extra condition lines placed inside each block
    (e.g. 'Rarity = Unique', 'Quality >= 28'). A '# Part i/n' comment is added
    only when the names span more than one chunk.
    """
    names = list(dict.fromkeys(names))  # order-preserving de-dupe
    if not names:
        return []
    chunks = [names[i:i + chunk] for i in range(0, len(names), chunk)]
    multi  = len(chunks) > 1
    out: list = []
    for idx, ch in enumerate(chunks, 1):
        out.append("Show")
        if multi:
            out.append(f"    # Part {idx}/{len(chunks)}")
        for ex in extra_lines:
            out.append(f"    {ex}")
        bt = " ".join(f'"{_quote_ipd(n)}"' for n in ch)
        out.append(f"    BaseType == {bt}")   # exact match — faithful to the .ipd [Type] == rules
        out.append("")
    return out


def build_loot_filter(ipd_lines, generated_iso: str | None = None) -> list:
    """Parse generated .ipd rule lines and return PoE2 client loot-filter lines."""
    if generated_iso is None:
        generated_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

    plain: list = []          # [Type] only (currency, essences, runes, gems, …)
    unique: list = []         # [Rarity] == "Unique"
    by_rarity = {"Normal": [], "Magic": [], "Rare": []}
    by_quality: dict = {}     # quality int -> [names]
    by_sockets: dict = {}     # socket  int -> [names]
    has_waystone = False

    for raw in ipd_lines:
        line = raw.strip()
        if not line or line.startswith("/"):
            continue              # blank, header, or commented-out (disabled) rule
        if "[StashItem]" not in line:
            continue
        mt = _LF_TYPE_RE.search(line)
        if not mt:
            mc = _LF_CATEGORY_RE.search(line)
            if mc and mc.group(1) == "Waystone":
                has_waystone = True
            continue
        name = mt.group(1).replace('\\"', '"')
        mr = _LF_RARITY_RE.search(line)
        mq = _LF_QUALITY_RE.search(line)
        ms = _LF_SOCKETS_RE.search(line)
        if mr and mr.group(1) == "Unique":
            unique.append(name)
        elif mr and mr.group(1) in by_rarity:
            by_rarity[mr.group(1)].append(name)
        elif mq:
            by_quality.setdefault(int(mq.group(1)), []).append(name)
        elif ms:
            by_sockets.setdefault(int(ms.group(1)), []).append(name)
        else:
            plain.append(name)

    out: list = [
        "# Path of Exile 2 Filter - Generated from IPD",
        "# IMPORTANT: Shows items based on PICKUP conditions (before #)",
        "# Bot will pick these up and decide what to keep after identification",
        "# NOTE: [UniqueName] filters cannot be replicated here — unique items",
        "#       are shown by base type only. Value filtering stays in the .ipd.",
        f"# Generated on: {generated_iso}",
        "",
    ]
    out += _lf_show_blocks(plain, [])
    out += _lf_show_blocks(unique, ["Rarity = Unique"])
    for rar in ("Normal", "Magic", "Rare"):
        out += _lf_show_blocks(by_rarity[rar], [f"Rarity = {rar}"])
    for q in sorted(by_quality):
        out += _lf_show_blocks(by_quality[q], [f"Quality >= {q}"])
    for s in sorted(by_sockets):
        out += _lf_show_blocks(by_sockets[s], [f"Sockets >= {s}"])
    if has_waystone:
        out += ["Show", '    Class "Waystone"', ""]

    out += [
        "# Hide everything else",
        "Hide",
        "",
        "# WARNING: This filter only shows items from parsed IPD rules",
        "# Make sure to show other important items your build needs",
    ]
    return out


# (fetch_json, _request_with_retry, _cache_get/set, clear_cache, prune_disk_cache,
#  set_disk_cache_dir, _disk_cache_file, save_payload_to_disk, load_payload_from_disk,
#  cache_info, fetch_live_leagues, detect_current_league, fetch_category,
#  fetch_all_payloads, exalted_rate, divine_value_from_exalt, _RETRYABLE_STATUS,
#  _PAYLOAD_CACHE, _CACHE_LOCK, _CACHE_TTL, _DISK_CACHE_DIR
#  are imported from exilebot_pickit.api.client)

_ESSENCE_TIER_ORDER = {"lesser": 0, "": 1, "greater": 2, "perfect": 3}
_ESSENCE_TIER_LABELS = {0: "Lesser", 1: "", 2: "Greater", 3: "Perfect"}

def _essence_tier_key(name: str):
    """Sort key: (tier 0-3, base_name) so Lesser < base < Greater < Perfect."""
    low = name.lower()
    for prefix in ("lesser essence", "greater essence", "perfect essence"):
        if low.startswith(prefix):
            tier_word = prefix.split()[0]
            base = name[len(prefix):].strip()
            return (_ESSENCE_TIER_ORDER[tier_word], base)
    if low.startswith("essence"):
        base = name[len("essence"):].strip()
        return (_ESSENCE_TIER_ORDER[""], base)
    return (99, name)


def format_rule(name: str, exalt_value: float, _divine_value: float, header: str = "Type",
                min_exalt: float | None = None, ritual_threshold: float | None = None) -> str:
    threshold = min_exalt if min_exalt is not None else MIN_EXALT
    action = '[StashItem] == "true"'
    if ritual_threshold is not None and exalt_value < ritual_threshold:
        action += ' && [IgnoreRitual] == "true"'
    rule = f'[{header}] == "{name}" # {action} // ExValue = {exalt_value:.2f}'
    return rule if exalt_value >= threshold else f"//{rule}"


def build_exchange_lines(
    payload: dict,
    divine_rate_exalts: float,
    pick_all: bool = False,
    min_exalt: float | None = None,
    tier_sort: bool = False,
    enabled_names: set[str] | None = None,
    always_names: list[str] | None = None,
    force_names: set[str] | None = None,
    ritual_threshold: float | None = None,
) -> list:
    """``force_names``: priced items whose rule stays ACTIVE regardless of the
    value floor (always-pick items ninja happens to price, e.g. Expedition
    Logbook). An explicit user disable (enabled_names) still wins."""
    force = set(force_names or ())
    items_by_id = {i["id"]: i for i in payload.get("items", [])}
    rate = exalted_rate(payload)
    rows = []
    for line in payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if not item or not item.get("name"):
            continue
        if item["name"] in ITEM_NAME_SKIP:
            continue
        name = ITEM_NAME_CORRECTIONS.get(item["name"], item["name"])
        if name is None:  # corrections dict maps to None = skip this item
            continue
        if enabled_names is not None and name not in enabled_names:
            continue
        primary_value = float(line.get("primaryValue") or 0.0)
        exalt_value = primary_value * rate if rate else primary_value
        divine_value = divine_value_from_exalt(exalt_value, divine_rate_exalts)
        rows.append((name, exalt_value, divine_value))

    if tier_sort:
        rows.sort(key=lambda r: _essence_tier_key(r[0]))
    else:
        rows.sort(key=lambda r: -r[1])

    if pick_all:
        result = [
            f'[Type] == "{name}" # [StashItem] == "true" // ExValue = {ev:.2f}'
            for name, ev, _ in rows
        ]
    else:
        result = [
            (f'[Type] == "{_quote_ipd(name)}" # [StashItem] == "true" // ExValue = {ev:.2f} (always pick)'
             if name in force else
             format_rule(name, ev, dv, min_exalt=min_exalt, ritual_threshold=ritual_threshold))
            for name, ev, dv in rows
        ]

    # Prepend hardcoded always-pick rules for items poe.ninja omits (e.g. base currency).
    # Respect enabled_names: if the user explicitly disabled one of these items in
    # Categories, don't add it back here.
    if always_names:
        scraped = {name for name, _, _ in rows}
        prefix = [
            f'[Type] == "{n}" # [StashItem] == "true"'
            for n in always_names
            if n not in scraped
            and (enabled_names is None or n in enabled_names)
        ]
        result = prefix + result

    return result


def build_uncut_gem_lines(payload: dict, divine_rate_exalts: float, min_exalt: float | None = None,
                          enabled_names: set | None = None) -> list:
    items_by_id = {i["id"]: i for i in payload.get("items", [])}
    rate = exalted_rate(payload)
    threshold = min_exalt if min_exalt is not None else MIN_EXALT

    # Collect all gems with their type, level, and values
    gems = []
    for line in payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if not item or not item.get("name"):
            continue
        name = item["name"]
        if enabled_names is not None and name not in enabled_names:
            continue
        # Extract gem type and level from name e.g. "Uncut Skill Gem (Level 7)"
        m = re.match(r"Uncut (Skill|Spirit|Support) Gem \(Level (\d+)\)", name)
        if not m:
            continue
        gem_type = m.group(1)
        level = int(m.group(2))
        primary_value = float(line.get("primaryValue") or 0.0)
        exalt_value = primary_value * rate if rate else primary_value
        divine_value = divine_value_from_exalt(exalt_value, divine_rate_exalts)
        gems.append((gem_type, level, name, exalt_value, divine_value))

    # Group by type, sort each group by level ascending
    output = []
    for gem_type in ("Skill", "Spirit", "Support"):
        group = sorted([g for g in gems if g[0] == gem_type], key=lambda g: g[1])
        if not group:
            continue
        output.append(header_minor(f"Uncut {gem_type} Gems"))
        output.append("")
        for _, _level, name, ev, _ in group:
            rule = f'[Type] == "{name}" # [StashItem] == "true" // ExValue = {ev:.2f}'
            output.append(rule if ev >= threshold else f"//{rule}")
        output.append("")

    return output


def build_unique_lines(payload: dict, _divine_rate_exalts: float, min_exalt: float | None = None,
                       disabled_names=None) -> list:
    threshold = min_exalt if min_exalt is not None else MIN_EXALT
    dis = set(disabled_names or ())
    rate = exalted_rate(payload)
    rows = []
    seen = set()
    for line in payload.get("lines", []):
        name = line.get("name")
        base_type = line.get("baseType", "")
        if not name or (name, base_type) in seen:
            continue
        seen.add((name, base_type))
        primary_value = float(line.get("primaryValue") or 0.0)
        exalt_value = primary_value * rate if rate else primary_value
        rule = (
            f'[Type] == "{base_type}" && [Rarity] == "Unique" # [UniqueName] == "{name}" '
            f'&& [StashItem] == "true" // ExValue = {exalt_value:.2f}'
        )
        keep = exalt_value >= threshold and name not in dis
        rows.append((exalt_value, rule if keep else f"//{rule}"))
    # Sort by value, highest first — matches every other category. (Previously
    # `key=-r[0]` *with* reverse=True cancelled out, listing uniques cheapest-first.)
    rows.sort(key=lambda r: r[0], reverse=True)
    return [rule for _, rule in rows]


def always_pick_force_names() -> set:
    """Always-pick item names that must stay ACTIVE even when poe.ninja
    prices them below the value floor (single source for dedupe too)."""
    return set(SPECIAL_ITEMS) | set(SPLINTERS) | set(WOMBGIFTS) | set(TABLET_TYPES)


# Economy-tab row names for the three waystone pickup rules.
WAYSTONE_TOGGLE_NAMES = {
    "Normal": "Normal Waystones",
    "Magic":  "Magic Waystones",
    "Rare":   "Rare Waystones",
}


def build_waystone_lines(disabled=None) -> list:
    """Always pick all waystones tier 1+ — per-rarity rows can be switched
    off in the Economy tab (``disabled`` holds the row names)."""
    dis = set(disabled or ())
    out = []
    for rule in WAYSTONE_FALLBACK_RULES:
        m = re.search(r'\[Rarity\]\s*==\s*"(\w+)"', rule)
        if m and WAYSTONE_TOGGLE_NAMES.get(m.group(1)) in dis:
            continue
        out.append(rule)
    return out


# ─────────────────────────────────────────────────────────────────────────────
#  CSV report
# ─────────────────────────────────────────────────────────────────────────────

CSV_FIELDS = ["category", "name", "base_type", "poe_ninja_value", "ex_value", "threshold", "included", "reason"]

def build_csv_report(report_rows: list) -> str:
    """Serialise a list of report dicts to a CSV string."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    writer.writeheader()
    writer.writerows(report_rows)
    return buf.getvalue()


def make_report_row(category_label: str, name: str, base_type: str,
                    poe_ninja_value: float, ex_value: float,
                    threshold: float, included: bool, reason: str = "") -> dict:
    return {
        "category":        category_label,
        "name":            name,
        "base_type":       base_type,
        "poe_ninja_value": f"{poe_ninja_value:.4g}",
        "ex_value":        f"{ex_value:.4g}",
        "threshold":       f"{threshold:.4g}",
        "included":        "yes" if included else "no",
        "reason":          reason or ("included" if included else f"below threshold {threshold:.4g}"),
    }


def collect_exchange_report_rows(label: str, payload: dict, divine_rate_exalts: float,
                                  pick_all: bool = False, min_exalt: float | None = None) -> list:
    threshold = min_exalt if min_exalt is not None else MIN_EXALT
    items_by_id = {i["id"]: i for i in payload.get("items", [])}
    rate = exalted_rate(payload)
    rows = []
    for line in payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if not item or not item.get("name"):
            continue
        if item["name"] in ITEM_NAME_SKIP:
            continue
        name = ITEM_NAME_CORRECTIONS.get(item["name"], item["name"])
        if name is None:  # corrections dict maps to None = skip this item
            continue
        pv   = float(line.get("primaryValue") or 0.0)
        ev   = pv * rate if rate else pv
        included = pick_all or ev >= threshold
        rows.append(make_report_row(label, name, "", pv, ev, threshold, included))
    return rows


def collect_unique_report_rows(label: str, payload: dict, divine_rate_exalts: float, min_exalt: float | None = None) -> list:
    threshold = min_exalt if min_exalt is not None else MIN_EXALT
    rate = exalted_rate(payload)
    seen = set()
    rows = []
    for line in payload.get("lines", []):
        name      = line.get("name")
        base_type = line.get("baseType", "")
        if not name:
            continue
        pv = float(line.get("primaryValue") or 0.0)
        ev = pv * rate if rate else pv
        key = (name, base_type)
        if key in seen:
            rows.append(make_report_row(label, name, base_type, pv, ev, threshold,
                                        False, "duplicate (name+base already included)"))
            continue
        seen.add(key)
        included = ev >= threshold
        rows.append(make_report_row(label, name, base_type, pv, ev, threshold, included))
    return rows


# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate ExileBot 2 pickit rules from poe.ninja's real economy API.")
    parser.add_argument("--league",          default=None,              help="Exact league name. Omit to auto-detect.")
    parser.add_argument("--min-exalt",       type=float, default=MIN_EXALT, help="Threshold below which items are commented out")
    parser.add_argument("--output",          default="poe2_pickit.txt", help="Output file path")
    from . import VERSION as _ver
    parser.add_argument("--version",         action="version",
                        version=f"%(prog)s {_ver}",
                        help="Show version and exit")
    parser.add_argument("--list-leagues",    action="store_true",       help="Print live leagues and exit")
    parser.add_argument("--check-endpoints", action="store_true",       help="Test all poe.ninja category endpoints and print results")
    parser.add_argument("--variant",         choices=("all","currency","exchange","uniques","maps"), default="all")
    parser.add_argument("--include-bases",   action="store_true",       help="Build endgame base type rules from game data and append to output")
    parser.add_argument("--base-quality",    type=int, default=25,      help="Min quality %% for base-type rules (default 25)")
    parser.add_argument("--base-min-level",  type=int, default=CRAFT_BASE_MIN_ILVL, help=f"Min required level for base-type rules (default {CRAFT_BASE_MIN_ILVL})")
    args = parser.parse_args()
    min_exalt = args.min_exalt

    if args.list_leagues:
        for name, slug, display in fetch_live_leagues():
            print(f"{display} | name={name} | url={slug}")
        return

    league = args.league or detect_current_league()

    if args.check_endpoints:
        print(f"Checking endpoints for league: {league}")
        for key, ninja_type, label, is_unique in ALL_CATEGORIES:
            try:
                payload = fetch_category(league, key, ninja_type, is_unique)
                row_count = len(payload.get("lines", []))
                print(f"  ✓  {label:<30} {row_count} rows")
            except requests.HTTPError as e:
                print(f"  ✗  {label:<30} HTTP {e.response.status_code if e.response else '?'}")
            except requests.RequestException as e:
                print(f"  ✗  {label:<30} {e}")
            time.sleep(0.2)
        return

    print(f"Using league: {league}")

    if args.variant == "all":
        categories = ALL_CATEGORIES
    elif args.variant == "currency":
        categories = [c for c in EXCHANGE_CATEGORIES if c[0] == "currency"]
    elif args.variant == "exchange":
        categories = EXCHANGE_CATEGORIES
    elif args.variant == "maps":
        categories = [c for c in EXCHANGE_CATEGORIES if c[0] == "fragments"]
    else:
        categories = UNIQUE_CATEGORIES

    # ── File header ──────────────────────────────────────────────────────────
    output_lines = [
        "/" * _W,
        "//" + "  EXILEBOT 2  |  AUTO-GENERATED PICKIT".center(_W - 4) + "//",
        "/" * _W,
        f"// League  : {league}",
        f"// Threshold: items below {min_exalt:.0f} Exalted are commented out",
        "// Source  : poe.ninja PoE2 economy API",
        "/" * _W,
        "",
    ]

    # ── Currency (establish divine rate) ─────────────────────────────────────
    currency_payload = fetch_category(league, "currency", "Currency", False)
    _cache_set(league, "currency", currency_payload)
    items_by_id      = {i["id"]: i for i in currency_payload.get("items", [])}
    rate             = exalted_rate(currency_payload)
    divine_rate_exalts = 1.0
    _divine_found = False
    for line in currency_payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if item and item.get("name") == "Divine Orb":
            pv = float(line.get("primaryValue") or 0.0)
            divine_rate_exalts = pv * rate if rate else pv
            _divine_found = True
            break
    if not _divine_found:
        print("Warning: Divine Orb not found in currency payload — divine conversion unavailable", file=sys.stderr)
    if rate == 0:
        print("Warning: exalted rate is 0 in currency payload — item values may be inaccurate", file=sys.stderr)

    output_lines.append(f"// Conversion: 1 Divine = {divine_rate_exalts:.6f} Exalted")
    output_lines.append("")

    # ── Economy sections ─────────────────────────────────────────────────────
    output_lines.append(header_major("Economy Items"))
    output_lines.append("")

    report_rows = []

    # Fetch all non-currency categories in parallel (currency already cached above)
    non_currency_cats = [(k, t, l, u) for k, t, l, u in categories if k != "currency"]
    print(f"Fetching {len(non_currency_cats)} categories in parallel…")
    all_payloads = fetch_all_payloads(league, non_currency_cats)
    all_payloads["currency"] = currency_payload

    for key, _ninja_type, label, is_unique in categories:
        payload = all_payloads.get(key)

        if isinstance(payload, Exception):
            output_lines.append(header_sub(label))
            e = payload
            output_lines.append(f"// Failed to fetch {label}: {e}")
            if isinstance(e, requests.HTTPError) and e.response is not None and e.response.status_code == 404:
                output_lines.append(
                    f"// 404 — check poe.ninja Network tab for the correct 'type' string for {label}"
                )
            output_lines.append("")
            print(f"  ✗ {label}: {type(e).__name__}", file=sys.stderr)
            continue
        if payload is None:
            output_lines += [header_sub(label), f"// No payload returned for {label}", ""]
            continue

        try:
            if is_unique:
                lines = build_unique_lines(payload, divine_rate_exalts, min_exalt=min_exalt)
                report_rows.extend(collect_unique_report_rows(label, payload, divine_rate_exalts, min_exalt=min_exalt))
            elif key == "uncut_gems":
                lines = build_uncut_gem_lines(payload, divine_rate_exalts, min_exalt=min_exalt)
                report_rows.extend(collect_exchange_report_rows(label, payload, divine_rate_exalts, min_exalt=min_exalt))
            elif key == "waystones":
                lines = build_waystone_lines()
                report_rows.extend(collect_exchange_report_rows(label, payload, divine_rate_exalts, min_exalt=min_exalt))
            else:
                pick_all  = key in PICK_ALL_CATEGORIES
                always    = ALWAYS_PICK_CURRENCY if key == "currency" else (ALWAYS_PICK_RUNES if key == "runes" else None)
                lines = build_exchange_lines(payload, divine_rate_exalts, pick_all=pick_all, min_exalt=min_exalt, tier_sort=(key == "essences"), always_names=always, force_names=always_pick_force_names())
                report_rows.extend(collect_exchange_report_rows(label, payload, divine_rate_exalts, pick_all=pick_all, min_exalt=min_exalt))

            output_lines.append(header_sub(label))
            output_lines.append("")
            if not lines:
                output_lines.append(f"// poe.ninja returned no rows for {label} in this league")
            output_lines.extend(lines)
            output_lines.append("")

        except Exception as e:
            output_lines += [header_sub(label), f"// Processing failed: {e}", ""]
            print(f"  ✗ {label}: {e}", file=sys.stderr)

    # ── Tablets ───────────────────────────────────────────────────────────────
    output_lines.extend(build_tablet_rules())

    # ── Breach Wombgifts ──────────────────────────────────────────────────────
    output_lines.extend(build_wombgift_rules())

    # ── Special Waystones ─────────────────────────────────────────────────────
    output_lines.extend(build_special_item_rules())

    # ── Chance Orb Bases ──────────────────────────────────────────────────────
    output_lines.extend(build_chance_base_rules())

    # ── Base types (optional) ─────────────────────────────────────────────────
    if args.include_bases:
        print("Building base type rules from game data…")
        def _prog(idx, total, title):
            print(f"  [{idx}/{total}] {title}")
        base_lines = build_base_rules(min_quality=args.base_quality, min_level=args.base_min_level, progress_callback=_prog)
        output_lines.append("")
        output_lines.append(header_major("Exceptional Bases"))
        output_lines.append("")
        output_lines.extend(base_lines)
        output_lines.append("")
        print(f"  {len(base_lines)} base rules added.")

    # ── Write output ──────────────────────────────────────────────────────────
    content = "\n".join(output_lines)
    write_text_atomic(args.output, content)

    # ── Also write latest.ipd beside the output file ──────────────────────────
    out_dir  = os.path.dirname(os.path.abspath(args.output)) or "."
    latest   = os.path.join(out_dir, "latest.ipd")
    write_text_atomic(latest, content)

    # ── Write CSV item report ─────────────────────────────────────────────────
    csv_path = os.path.splitext(args.output)[0] + "_items.csv"
    write_text_atomic(csv_path, build_csv_report(report_rows), newline="")

    # ── Also write a matching PoE2 client loot filter ─────────────────────────
    filter_path = os.path.splitext(args.output)[0] + ".filter"
    write_text_atomic(filter_path, "\n".join(build_loot_filter(output_lines)))

    active    = sum(1 for l in output_lines if l and not l.startswith("//") and "[StashItem]" in l)
    commented = sum(1 for l in output_lines if l.startswith("//") and "[StashItem]" in l)
    print(f"Written to   : {args.output}")
    print(f"Latest copy  : {latest}")
    print(f"Item report  : {csv_path}")
    print(f"Loot filter  : {filter_path}")
    print(f"Active rules : {active}   Commented out: {commented}")
    if getattr(sys, 'frozen', False):
        input("\nDone! Press Enter to exit...")


if __name__ == "__main__":
    main()
