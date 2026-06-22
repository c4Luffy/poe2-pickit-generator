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
    python poe2_pickit_generator.py --league "Fate of the Vaal"
    python poe2_pickit_generator.py --list-leagues
"""

import argparse
import csv
import difflib
from concurrent.futures import ThreadPoolExecutor
import io
import json
import os
import re
import sys
import threading
import time
from typing import List, Optional, Set
import requests

BASE_URL = "https://poe.ninja/poe2/api/economy"
INDEX_STATE_URL = "https://poe.ninja/poe2/api/data/index-state"
USER_AGENT = "poe2-pickit-generator/1.0 (+local)"
MIN_EXALT = 10.0


EXCHANGE_CATEGORIES = [
    # Order matches the in-game stash-tab list
    ("currency",            "Currency",           "Currency",             False),
    ("essences",            "Essences",           "Essences",             False),
    ("liquid_emotions",     "Delirium",           "Delirium",             False),
    ("catalysts",           "Breach",             "Catalysts",            False),
    ("abyssal_bones",       "Abyss",              "Abyss",                False),
    ("fragments",           "Fragments",          "Fragments",            False),
    ("runes",               "Runes",              "Runes",                False),
    ("omens",               "Ritual",             "Omens",                False),
    ("soul_cores",          "SoulCores",          "Soul Cores",           False),
    ("idols",               "Idols",              "Idols",                False),
    ("uncut_gems",          "UncutGems",          "Uncut Gems",           False),
    ("lineage_support_gems","LineageSupportGems", "Support Gems",         False),
    ("expedition",          "Expedition",         "Expedition",           False),
    ("waystones",           "Waystones",          "Waystones",            False),
]

UNIQUE_CATEGORIES = [
    ("unique_weapons",    "UniqueWeapons",      "Unique Weapons",     True),
    ("unique_armours",    "UniqueArmours",      "Unique Armours",     True),
    ("unique_accessories","UniqueAccessories",  "Unique Accessories", True),
    ("unique_flasks",     "UniqueFlasks",       "Unique Flasks",      True),
    ("unique_charms",     "UniqueCharms",       "Unique Charms",      True),
    ("unique_jewels",     "UniqueJewels",       "Unique Jewels",      True),
    ("unique_relics",     "UniqueSanctumRelics","Unique Relics",      True),
]

ALL_CATEGORIES = EXCHANGE_CATEGORIES + UNIQUE_CATEGORIES

# Categories where EVERY item is picked regardless of price threshold —
# inclusion is driven purely by the per-item selections (the Items-tab
# checkboxes), not by value.
#   • Lineage Support Gems: too rare to skip any.
#   • Currency: picked by selection, never value-filtered.
PICK_ALL_CATEGORIES = {"lineage_support_gems", "currency"}

# poe.ninja sometimes returns names that don't match in-game base types.
# Map the poe.ninja name → correct in-game name here.
ITEM_NAME_CORRECTIONS: dict = {}

# Items returned by poe.ninja that have no valid in-game base type and should
# be skipped entirely rather than written to the pickit. (Exiled Bot's pickit
# validator rejects these base types, so writing them just fails validation.)
ITEM_NAME_SKIP: set = {
    "Necrotic Catalyst",
    "Refined Necrotic Catalyst",
}

# Currency items that must always be picked up even if poe.ninja omits them
# (Exalted Orb is the PoE2 base pricing currency and won't appear in lines).
ALWAYS_PICK_CURRENCY = [
    "Exalted Orb",
    "Divine Orb",
    "Mirror of Kalandra",
]

# Runes not tracked by poe.ninja — always pick up regardless of threshold
ALWAYS_PICK_RUNES = [
    "Emergent Vigour",
    "Emergent Possibility",
    "Emergent Protection",
    "Emergent Instinct",
]


# Fallback waystone rules used when poe.ninja returns no waystone rows.
WAYSTONE_FALLBACK_RULES = [
    '[Category] == "Waystone" && [Rarity] == "Normal" && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Magic"  && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Rare"   && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
]

# ─────────────────────────────────────────────────────────────────────────────
#  Endgame base types — sourced from game data (baseitemtypes.json)
#  Format per entry: (item_name, socket_threshold)
#  socket_threshold=0 means no socket rule is generated for that category.
# ─────────────────────────────────────────────────────────────────────────────

_BASE_TYPES_BY_CATEGORY: dict = {
    "Body Armours": (
        ("Abyssal Cuirass", 3), ("Arcane Raiment", 3), ("Armoured Vest", 3),
        ("Assassin Garb", 3), ("Austere Garb", 3), ("Ceremonial Robe", 3),
        ("Conjurer Mantle", 3), ("Conqueror Plate", 3), ("Corsair Coat", 3),
        ("Corvus Mantle", 3), ("Dastard Armour", 3), ("Death Mail", 3),
        ("Death Mantle", 3), ("Devout Garb", 3),
        ("Enlightened Robe", 3), ("Exquisite Vest", 3), ("Falconer's Jacket", 3),
        ("Feathered Raiment", 3), ("Flowing Raiment", 3), ("Glorious Plate", 3),
        ("Golden Mail", 3), ("Grand Regalia", 3), ("Havoc Raiment", 3),
        ("Hawker's Jacket", 3), ("Heartcarver Mantle", 3), ("Heroic Armour", 3),
        ("Lizardscale Coat", 3), ("Mail Coat", 3), ("Ornate Plate", 3),
        ("Rambler Jacket", 3), ("Revered Vestments", 3), ("Sacramental Robe", 3),
        ("Seastorm Mantle", 3), ("Shrouded Mail", 3), ("Slayer Armour", 3),
        ("Sleek Jacket", 3), ("Slipstrike Vest", 3), ("Soldier Cuirass", 3),
        ("Stone Cuirass", 3), ("Swiftstalker Coat", 3), ("Thane Mail", 3),
        ("Torment Jacket", 3), ("Tournament Mail", 3), ("Utzaal Cuirass", 3),
        ("Vile Robe", 3), ("Warlord Cuirass", 3), ("Wolfskin Mantle", 3),
        ("Wyrmscale Coat", 3), ("Zenith Vestments", 3),
    ),
    "Helmets": (
        ("Ancestral Tiara", 2), ("Archon Crown", 2), ("Armoured Cap", 2),
        ("Brigand Mask", 2), ("Champion Helm", 2), ("Cryptic Crown", 2),
        ("Cryptic Helm", 2), ("Death Mask", 2), ("Desert Cap", 2),
        ("Divine Crown", 2), ("Druidic Crown", 2), ("Faridun Mask", 2),
        ("Freebooter Cap", 2), ("Gallant Helm", 2), ("Gladiatorial Helm", 2),
        ("Grand Visage", 2), ("Grinning Mask", 2), ("Guardian Greathelm", 2),
        ("Imperial Greathelm", 2), ("Kamasan Tiara", 2), ("Magus Tiara", 2),
        ("Masked Greathelm", 2), ("Paragon Greathelm", 2), ("Saintly Crown", 2),
        ("Skycrown Tiara", 2), ("Soaring Mask", 2), ("Sorcerous Tiara", 2),
        ("Trapper Hood", 2), ("Warded Helm", 2), ("Warmonger Greathelm", 2),
        ("Woven Cap", 2),
    ),
    "Gloves": (
        ("Adherent Cuffs", 2), ("Ancient Cuffs", 2), ("Adorned Gloves", 2),
        ("Barbed Bracers", 2), ("Blacksteel Gauntlets", 2), ("Bound Cuffs", 2),
        ("Commander Gauntlets", 2), ("Cultist Gauntlets", 2),
        ("Elegant Wraps", 2), ("Engraved Bracers", 2), ("Gleaming Cuffs", 2),
        ("Grand Bracers", 2), ("Grand Manchettes", 2), ("Grand Mitts", 2),
        ("Grim Gloves", 2), ("Knightly Mitts", 2), ("Massive Mitts", 2),
        ("Opulent Gloves", 2), ("Ornate Gauntlets", 2), ("Ornate Mitts", 2),
        ("Polished Bracers", 2), ("Secured Wraps", 2), ("Signet Cuffs", 2),
        ("Sirenscale Gloves", 2), ("Stalking Bracers", 2),
        ("Steelmail Gauntlets", 2), ("Utility Wraps", 2), ("Vaal Gloves", 2),
        ("Vaal Mitts", 2), ("Vaal Wraps", 2), ("War Wraps", 2),
    ),
    "Boots": (
        ("Apostle Leggings", 2), ("Blacksteel Sabatons", 2), ("Bladed Shoes", 2),
        ("Bold Sabatons", 2), ("Bound Sandals", 2), ("Bulwark Greaves", 2),
        ("Cavalry Boots", 2), ("Charmed Shoes", 2), ("Cinched Boots", 2),
        ("Cryptic Leggings", 2), ("Daggerfoot Shoes", 2), ("Dragonscale Boots", 2),
        ("Drakeskin Boots", 2), ("Elaborate Sandals", 2), ("Embroidered Boots", 2),
        ("Faithful Leggings", 2), ("Fortress Sabatons", 2), ("Grand Cuisses", 2),
        ("Luxurious Slippers", 2), ("Noble Sabatons", 2), ("Ornate Greaves", 2),
        ("Pious Leggings", 2), ("Quickslip Shoes", 2), ("Sandsworn Sandals", 2),
        ("Sekhema Sandals", 2), ("Tasalian Greaves", 2), ("Totemic Greaves", 2),
        ("Vaal Greaves", 2), ("Veteran Sabatons", 2), ("Wanderer Shoes", 2),
        ("Warlock Leggings", 2),
    ),
    "Shields": (
        ("Avian Targe", 2), ("Baroque Targe", 2), ("Blacksteel Crest Shield", 2),
        ("Blacksteel Tower Shield", 2), ("Deified Crest Shield", 2),
        ("Fortress Tower Shield", 2), ("Glowering Crest Shield", 2),
        ("Goldworked Tower Shield", 2), ("Golden Targe", 2),
        ("Grand Targe", 2), ("Intricate Crest Shield", 2),
        ("Mammoth Targe", 2), ("Royal Tower Shield", 2),
        ("Sekheman Crest Shield", 2), ("Soaring Targe", 2),
        ("Tawhoan Tower Shield", 2), ("Vaal Crest Shield", 2),
        ("Vaal Tower Shield", 2),
    ),
    "Bucklers": (
        ("Aegis Buckler", 2), ("Ancient Buckler", 2), ("Bladeguard Buckler", 2),
        ("Desert Buckler", 2), ("Gutspike Buckler", 2), ("Ornate Buckler", 2),
    ),
    "Foci": (
        ("Druidic Focus", 2), ("Hallowed Focus", 2), ("Leyline Focus", 2),
        ("Magus Focus", 2), ("Sacred Focus", 2), ("Tasalian Focus", 2),
    ),
    "Quivers": (
        ("Visceral Quiver", 0), ("Volant Quiver", 0),
    ),
    "One Hand Maces": (
        ("Akoyan Club", 2), ("Crown Mace", 2), ("Flanged Mace", 2),
        ("Fortified Hammer", 2), ("Marauding Mace", 2), ("Molten Hammer", 2),
        ("Strife Pick", 2), ("Structured Hammer", 2), ("Torment Club", 2),
    ),
    "Spears": (
        ("Akoyan Spear", 2), ("Flying Spear", 2), ("Grand Spear", 2),
        ("Helix Spear", 2), ("Massive Spear", 2), ("Orichalcum Spear", 2),
        ("Pronged Spear", 2), ("Spiked Spear", 2), ("Stalking Spear", 2),
    ),
    "Quarterstaves": (
        ("Aegis Quarterstaff", 3), ("Bolting Quarterstaff", 3),
        ("Dreaming Quarterstaff", 3), ("Guardian Quarterstaff", 3),
        ("Lunar Quarterstaff", 3), ("Razor Quarterstaff", 3),
        ("Sinister Quarterstaff", 3), ("Striking Quarterstaff", 3),
        ("Wyrm Quarterstaff", 3),
    ),
    "Crossbows": (
        ("Bleak Crossbow", 3), ("Desolate Crossbow", 3), ("Elegant Crossbow", 3),
        ("Engraved Crossbow", 3), ("Esoteric Crossbow", 3), ("Flexed Crossbow", 3),
        ("Gemini Crossbow", 3), ("Siege Crossbow", 3), ("Stout Crossbow", 3),
    ),
    "Bows": (
        ("Cavalry Bow", 3), ("Fanatic Bow", 3), ("Gemini Bow", 3),
        ("Guardian Bow", 3), ("Heavy Bow", 3), ("Ironwood Shortbow", 3),
        ("Militant Bow", 3), ("Obliterator Bow", 3), ("Warmonger Bow", 3),
    ),
    "Two Hand Maces": (
        ("Anvil Maul", 3), ("Disintegrating Maul", 3), ("Fanatic Greathammer", 3),
        ("Giant Maul", 3), ("Ironwood Greathammer", 3), ("Massive Greathammer", 3),
        ("Ruination Maul", 3), ("Sacred Maul", 3), ("Tawhoan Greatclub", 3),
    ),
    "Staves": (
        ("Dark Staff", 3), ("Permafrost Staff", 3), ("Ravenous Staff", 3),
    ),
    "Claws":          (("Talon Claw", 2),),
    "Daggers":        (("Cinquedea", 2),),
    "Wands":          (("Dueling Wand", 2),),
    "One Hand Swords":(("Dark Blade", 2),),
    "One Hand Axes":  (("Dread Hatchet", 2),),
    "Two Hand Axes":  (("Vile Greataxe", 3),),
    "Two Hand Swords":(("Ultra Greatsword", 3),),
    "Sceptres":       (("Hallowed Sceptre", 2),),
    "Flails":         (("Abyssal Flail", 2),),
    "Belts":          (("Fine Belt", 0),),
}

# Runeforged / Runemastered variants not yet in game data files.
# Format: (item_name, socket_threshold)
_RUNEFORGED_BASES: tuple = (
    ("Runeforged Adherent Cuffs",       2), ("Runeforged Ancestral Tiara",      2),
    ("Runeforged Ancient Buckler",      2), ("Runeforged Austere Garb",         3),
    ("Runeforged Barbed Bracers",       2), ("Runeforged Blacksteel Crest Shield", 2),
    ("Runeforged Blacksteel Gauntlets", 2), ("Runeforged Blacksteel Sabatons",  2),
    ("Runeforged Champion Helm",        2), ("Runeforged Corsair Coat",         3),
    ("Runeforged Cryptic Crown",        2), ("Runeforged Cryptic Leggings",     3),
    ("Runeforged Cultist Gauntlets",    2), ("Runeforged Daggerfoot Shoes",     2),
    ("Runeforged Death Mail",           3), ("Runeforged Death Mantle",         3),
    ("Runeforged Desert Buckler",       2), ("Runeforged Divine Crown",         2),
    ("Runeforged Dragonscale Boots",    2), ("Runeforged Drakeskin Boots",      2),
    ("Runeforged Falconer's Jacket",    3), ("Runeforged Feathered Raiment",    3),
    ("Runeforged Fortress Sabatons",    2), ("Runeforged Freebooter Cap",       2),
    ("Runeforged Gladiatorial Helm",    2), ("Runeforged Gleaming Cuffs",       2),
    ("Runeforged Golden Targe",         2), ("Runeforged Grinning Mask",        2),
    ("Runeforged Imperial Greathelm",   2), ("Runeforged Kamasan Tiara",        2),
    ("Runeforged Massive Mitts",        2), ("Runeforged Paragon Greathelm",    2),
    ("Runeforged Polished Bracers",     2), ("Runeforged Quickslip Shoes",      2),
    ("Runeforged Sacramental Robe",     3), ("Runeforged Sacred Focus",         2),
    ("Runeforged Sandsworn Sandals",    2), ("Runeforged Seastorm Mantle",      3),
    ("Runeforged Secured Wraps",        2), ("Runeforged Sekhema Sandals",      2),
    ("Runeforged Sirenscale Gloves",    2), ("Runeforged Soaring Mask",         2),
    ("Runeforged Soaring Targe",        2), ("Runeforged Tasalian Focus",       2),
    ("Runeforged Tasalian Greaves",     2), ("Runeforged Tawhoan Tower Shield", 2),
    ("Runeforged Thane Mail",           3), ("Runeforged Trapper Hood",         2),
    ("Runeforged Utzaal Cuirass",       3), ("Runeforged Vaal Crest Shield",    2),
    ("Runeforged Vaal Gloves",          2), ("Runeforged Vaal Greaves",         2),
    ("Runeforged Vaal Mitts",           2), ("Runeforged Vaal Tower Shield",    2),
    ("Runeforged Vaal Wraps",           2), ("Runeforged Warlock Leggings",     2),
    ("Runeforged Warlord Cuirass",      3), ("Runeforged Wyrmscale Coat",       3),
    ("Runemastered Armoured Vest",      3), ("Runemastered Enlightened Robe",   3),
    ("Runemastered Plumed Focus",       2), ("Runemastered Primal Markings",    3),
    ("Runemastered Vaal Tower Shield",  2),
)


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

VALID_EQUIPMENT_BASES: frozenset = (
    frozenset(name for entries in _BASE_TYPES_BY_CATEGORY.values() for name, _ in entries)
    | frozenset(name for name, _ in _RUNEFORGED_BASES)
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

        if line.count('"') % 2 != 0:
            errors.append((i, "Unbalanced quotes in rule"))
            continue
        if line.count("[") != line.count("]"):
            errors.append((i, "Unbalanced [ ] brackets in rule"))
            continue
        if "[StashItem]" not in line:
            errors.append((i, "Rule has no [StashItem] action"))
            continue

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


def build_base_rules(min_quality: int = 28, min_level: int = 82, progress_callback=None) -> list:
    """Build endgame base-type pickup rules from local game data — no network requests.

    Uses _BASE_TYPES_BY_CATEGORY (sourced from baseitemtypes.json) for all equipment
    bases with DropLevel >= 60, plus _RUNEFORGED_BASES for Runeforged/Runemastered
    variants not yet present in the game data files.

    Each category gets its own header_minor section, then per base:
      [Type] == "Name" && [Quality] >= "min_quality" # [StashItem] == "true"
      [Type] == "Name" && [Sockets] >= "N"           # [StashItem] == "true"  (if sock > 0)
    """
    all_lines: list = []
    cats = sorted(_BASE_TYPES_BY_CATEGORY.keys())
    total = len(cats) + 1  # +1 for runeforged section

    for idx, cat in enumerate(cats, 1):
        if progress_callback:
            progress_callback(idx, total, cat)
        entries = _BASE_TYPES_BY_CATEGORY[cat]
        all_lines.append(header_minor(cat))
        all_lines.append("")
        cat_rules: set = set()
        for name, sock in entries:
            safe = _quote_ipd(name)
            cat_rules.add(f'[Type] == "{safe}" && [Quality] >= "{min_quality}" && [ItemLevel] >= "{min_level}" # [StashItem] == "true"')
            if sock > 0:
                cat_rules.add(f'[Type] == "{safe}" && [Sockets] >= "{sock}" && [ItemLevel] >= "{min_level}" # [StashItem] == "true"')
        all_lines.extend(sorted(cat_rules))
        all_lines.append("")

    # Runeforged / Runemastered supplement
    if progress_callback:
        progress_callback(total, total, "Runeforged & Runemastered")
    all_lines.append(header_minor("Runeforged & Runemastered"))
    all_lines.append("")
    rf_rules: set = set()
    for name, sock in _RUNEFORGED_BASES:
        safe = _quote_ipd(name)
        rf_rules.add(f'[Type] == "{safe}" && [Quality] >= "{min_quality}" && [ItemLevel] >= "{min_level}" # [StashItem] == "true"')
        if sock > 0:
            rf_rules.add(f'[Type] == "{safe}" && [Sockets] >= "{sock}" && [ItemLevel] >= "{min_level}" # [StashItem] == "true"')
    all_lines.extend(sorted(rf_rules))
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
CRAFT_BASE_MIN_ILVL = 82

# Ordered slot -> best base(s). Armour/off-hand = best of each defence type
# (Armour/STR, Evasion/DEX, Energy Shield/INT). Weapons = best base per kept type.
_CRAFT_BEST_BASES: dict = {
    "Body Armours":  ["Glorious Plate", "Assassin Garb", "Vile Robe"],
    "Helmets":       ["Imperial Greathelm", "Soaring Mask", "Sorcerous Tiara"],
    "Gloves":        ["Blacksteel Gauntlets", "Sirenscale Gloves", "Grand Mitts"],
    "Boots":         ["Fortress Sabatons", "Drakeskin Boots", "Warlock Leggings"],
    "Shields":       ["Goldworked Tower Shield", "Soaring Targe"],
    "Foci":          ["Sacred Focus"],
    "Spears":        ["Orichalcum Spear"],
    "Quarterstaves": ["Wyrm Quarterstaff"],
    "Crossbows":     ["Siege Crossbow"],
    "Bows":          ["Warmonger Bow"],
    "Staves":        ["Ravenous Staff"],
    "Wands":         ["Dueling Wand"],
    "Sceptres":      ["Hallowed Sceptre"],
}


def craft_base_categories() -> list:
    """Ordered ``[(category, [base_name, ...]), ...]`` for the curated craft bases."""
    return [(cat, list(names)) for cat, names in _CRAFT_BEST_BASES.items() if names]


def build_craft_base_rules(disabled=None, min_ilvl: int = CRAFT_BASE_MIN_ILVL) -> list:
    """Return pickit lines that pick Normal-rarity bases at item level >= min_ilvl
    — ideal blank bases for crafting. Skips any base names in ``disabled``."""
    skip = set(disabled) if disabled else set()
    body: list = []
    for cat, names in craft_base_categories():
        active = [n for n in names if n not in skip]
        if not active:
            continue
        body.append(f"// -- {cat} " + "-" * max(0, 73 - len(cat)))
        for name in active:
            safe = _quote_ipd(name)
            body.append(
                f'[Type] == "{safe}" && [Rarity] == "Normal" '
                f'&& [ItemLevel] >= "{min_ilvl}" # [StashItem] == "true"'
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



STATIC_TABLET_RULES = """\
/////////////////////////////////////////////////////////////////////////////////////
//                                                                                 //
//                               UNIQUE TABLETS                                    //
//                                                                                 //
/////////////////////////////////////////////////////////////////////////////////////

[Type] == "Irradiated Tablet" && [Rarity] == "Unique" # [UniqueName] == "Visions of Paradise" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Irradiated Tablet" && [Rarity] == "Unique" # [UniqueName] == "The Grand Project" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Irradiated Tablet" && [Rarity] == "Unique" # [UniqueName] == "Mastered Domain" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Abyss Tablet" && [Rarity] == "Unique" # [UniqueName] == "Unforeseen Consequences" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Ritual Tablet" && [Rarity] == "Unique" # [UniqueName] == "Freedom of Faith" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Breach Tablet" && [Rarity] == "Unique" # [UniqueName] == "Wraeclast Besieged" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Overseer Tablet" && [Rarity] == "Unique" # [UniqueName] == "Cruel Hegemony" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Overseer Tablet" && [Rarity] == "Unique" # [UniqueName] == "Season of the Hunt" && [StashItem] == "true" && [IgnoreRitual] == "true"
[Type] == "Delirium Tablet" && [Rarity] == "Unique" # [UniqueName] == "Clear Skies" && [StashItem] == "true" && [IgnoreRitual] == "true"

/////////////////////////////////////////////////////////////////////////////////////
//                                                                                 //
//                          REGULAR TABLETS (ALL RARITIES)                         //
//                                                                                 //
/////////////////////////////////////////////////////////////////////////////////////

[Type] == "Overseer Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Overseer Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Overseer Tablet" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Abyss Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Abyss Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Abyss Tablet" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Breach Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Breach Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Breach Tablet" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Ritual Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Ritual Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Ritual Tablet" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Irradiated Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Irradiated Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Irradiated Tablet" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Temple Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Temple Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Temple Tablet" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Delirium Tablet" && [Rarity] == "Normal" # [StashItem] == "true"
[Type] == "Delirium Tablet" && [Rarity] == "Magic" # [StashItem] == "true"
[Type] == "Delirium Tablet" && [Rarity] == "Rare" # [StashItem] == "true"

/////////////////////////////////////////////////////////////////////////////////////
//                                                                                 //
//                                   SPLINTERS                                     //
//                                                                                 //
/////////////////////////////////////////////////////////////////////////////////////

[Type] == "Breach Splinter" # [StashItem] == "true"
[Type] == "Simulacrum Splinter" # [StashItem] == "true"
"""


STATIC_WOMBGIFT_RULES = """\
/////////////////////////////////////////////////////////////////////////////////////
//                                                                                 //
//                             BREACH WOMBGIFTS                                    //
//                                                                                 //
/////////////////////////////////////////////////////////////////////////////////////

[Type] == "Banded Wombgift" # [StashItem] == "true"
[Type] == "Lavish Wombgift" # [StashItem] == "true"
[Type] == "Ornate Wombgift" # [StashItem] == "true"
[Type] == "Revelatory Wombgift" # [StashItem] == "true"
[Type] == "Signet Wombgift" # [StashItem] == "true"
"""

STATIC_SPECIAL_WAYSTONE_RULES = """\
/////////////////////////////////////////////////////////////////////////////////////
//                                                                                 //
//                           SPECIAL WAYSTONES                                     //
//                                                                                 //
/////////////////////////////////////////////////////////////////////////////////////

[Type] == "An Audience with the King" # [StashItem] == "true"
"""

# Structured list of chance orb bases — used by the GUI tab and build_chance_base_rules().
# Each entry: (category_label, base_type, target_unique)
CHANCE_BASES: list = [
    ("Belts",        "Heavy Belt",        "Headhunter"),
    ("Belts",        "Utility Belt",      "Mageblood"),
    ("Belts",        "Fine Belt",         "Ingenuity / Darkness Enthroned"),
    ("Body Armours", "Glorious Plate",    "Kaom's Heart"),
    ("Body Armours", "Warlord Cuirass",   "Morior Invictus"),
    ("Body Armours", "Assassin Garb",     "Hyrri's Ire"),
    ("Body Armours", "Flowing Raiment",   "Ghostwrithe"),
    ("Body Armours", "Sacramental Robe",  "Soul Mantle"),
    ("Helmets",      "Archon Crown",      "Indigon"),
    ("Helmets",      "Grand Visage",      "Crown of the Pale King"),
    ("Gloves",       "Vaal Gloves",       "Hateforge"),
    ("Gloves",       "Elegant Wraps",     "Maligaro's Virtuosity"),
    ("Gloves",       "Ornate Gauntlets",  "Hand of Wisdom and Action"),
    ("Boots",        "Dragonscale Boots", "Darkray Vectors"),
    ("Boots",        "Embroidered Boots", "Shadows and Dust"),
    ("Weapons",      "Heavy Bow",         "Quill Rain"),
    ("Weapons",      "Fanatic Bow",       "Lioneye's Glare"),
    ("Weapons",      "Hallowed Sceptre",  "Font of Power"),
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


def build_loot_filter(ipd_lines, generated_iso: Optional[str] = None) -> list:
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


# Scout (poe2scout.com) — unique item categories supplementing poe.ninja.
# Fetched at generate time; silently skipped if the API is unavailable.
SCOUT_CATEGORIES = [
    ("scout_accessories", "accessory", "Scout: Accessories", True),
    ("scout_armour",      "armour",    "Scout: Armour",      True),
    ("scout_jewels",      "jewel",     "Scout: Jewels",      True),
    ("scout_weapons",     "weapon",    "Scout: Weapons",     True),
    ("scout_sanctum",     "sanctum",   "Scout: Sanctum",     True),
    ("scout_maps",        "map",       "Scout: Maps",        True),
]
SCOUT_BASE_URL = "https://poe2scout.com/api/items/unique/{cat}?page=1&perPage=250&league={league}&search=&referenceCurrency=exalted"


# ─────────────────────────────────────────────────────────────────────────────
#  API helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_json(url: str, params: dict) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


# ── Retry with exponential backoff ───────────────────────────────────────────

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


def _request_with_retry(url: str, params: dict, *, retries: int = 3, backoff: float = 1.5) -> dict:
    """fetch_json with exponential-backoff retry on 429/5xx and transient network errors."""
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(retries):
        try:
            return fetch_json(url, params)
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code not in _RETRYABLE_STATUS:
                raise
            last_exc = e
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))  # 1.5 s, 3 s
    raise last_exc


# ── In-memory payload cache (per session) ────────────────────────────────────

_PAYLOAD_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL: float = 900.0  # 15 minutes


def _cache_get(league: str, key: str):
    with _CACHE_LOCK:
        entry = _PAYLOAD_CACHE.get((league, key))
        if entry and (time.time() - entry[0]) < _CACHE_TTL:
            return entry[1]
    return None


def _cache_set(league: str, key: str, payload: dict):
    with _CACHE_LOCK:
        _PAYLOAD_CACHE[(league, key)] = (time.time(), payload)
    save_payload_to_disk(league, key, payload)


def clear_cache():
    """Discard all cached poe.ninja payloads."""
    with _CACHE_LOCK:
        _PAYLOAD_CACHE.clear()


# ── Disk cache (survives restarts → powers offline mode) ─────────────────────

_DISK_CACHE_DIR: str = ""


def set_disk_cache_dir(path: str):
    """Point the offline cache at a directory. Called once by the GUI on startup."""
    global _DISK_CACHE_DIR
    _DISK_CACHE_DIR = path
    if path:
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass


def _disk_cache_file(league: str, key: str) -> str:
    safe = re.sub(r'[^\w\-]', '_', f"{league}__{key}")
    return os.path.join(_DISK_CACHE_DIR, safe + ".json")


def save_payload_to_disk(league: str, key: str, payload: dict):
    """Persist one payload so it can be reused when poe.ninja is unreachable."""
    if not _DISK_CACHE_DIR or not isinstance(payload, dict):
        return
    try:
        fname = _disk_cache_file(league, key)
        tmp   = fname + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "payload": payload}, f)
        os.replace(tmp, fname)   # atomic on Windows + POSIX
    except (OSError, TypeError, ValueError):
        pass


def load_payload_from_disk(league: str, key: str):
    """Return a previously saved payload (and its age in seconds), or (None, None)."""
    if not _DISK_CACHE_DIR:
        return None, None
    try:
        with open(_disk_cache_file(league, key), encoding="utf-8") as f:
            data = json.load(f)
        return data.get("payload"), time.time() - float(data.get("ts", 0))
    except (OSError, ValueError):
        return None, None


def cache_info() -> dict:
    """Return counts and age info about the current cache."""
    now = time.time()
    with _CACHE_LOCK:
        entries = [(k, now - v[0]) for k, v in _PAYLOAD_CACHE.items()]
    return {
        "count": len(entries),
        "oldest_secs": max((a for _, a in entries), default=0),
        "ttl_secs": _CACHE_TTL,
    }


# ── Scout (poe2scout.com) helpers ─────────────────────────────────────────────

def fetch_scout_payload(cat_slug: str, league: str) -> Optional[dict]:
    """Fetch unique items from poe2scout.com for one category.
    Returns None (silently) if the API is unavailable or returns no data."""
    try:
        from urllib.parse import quote as _quote
        url = SCOUT_BASE_URL.format(cat=cat_slug, league=_quote(league))
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=12)
        if r.status_code != 200:
            return None
        data = r.json()
        items = data.get("items", data.get("data", []))
        if not items:
            return None
        return {"items": items}
    except Exception:
        return None


def build_scout_lines(
    items: list,
    divine_rate_exalts: float,
    min_exalt: Optional[float] = None,
) -> list:
    """Convert poe2scout.com unique items into pickit rules."""
    rows = []
    for item in items:
        name      = item.get("name", "")
        ex_value  = float(item.get("exaltedValue") or item.get("value") or 0)
        div_value = divine_value_from_exalt(ex_value, divine_rate_exalts)
        if not name:
            continue
        rows.append((name, ex_value, div_value))
    rows.sort(key=lambda r: -r[1])
    return [format_rule(name, ev, dv, min_exalt=min_exalt) for name, ev, dv in rows]


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_live_leagues() -> list:
    data = _request_with_retry(INDEX_STATE_URL, {})
    leagues = []
    for item in data.get("economyLeagues", []):
        leagues.append((item.get("name", ""), item.get("url", ""), item.get("displayName", item.get("name", ""))))
    for item in data.get("oldEconomyLeagues", []):
        leagues.append((item.get("name", ""), item.get("url", ""), item.get("displayName", item.get("name", "")) + " (old)"))
    return [l for l in leagues if l[0] and l[1]]


def detect_current_league() -> str:
    try:
        data = _request_with_retry(INDEX_STATE_URL, {})
        active = data.get("economyLeagues", [])
        for item in active:
            name = item.get("name", "")
            if name.lower() not in ("standard", "hardcore"):
                return name
        if active:
            return active[0].get("name", "Mercenaries")
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Warning: could not auto-detect league ({e}); falling back to 'Mercenaries'")
    return "Mercenaries"


def fetch_category(league: str, key: str, ninja_type: str, is_unique: bool) -> dict:
    endpoint = "stash/current/item/overview" if is_unique else "exchange/current/overview"
    return _request_with_retry(f"{BASE_URL}/{endpoint}", {"league": league, "type": ninja_type})


def fetch_all_payloads(league: str, categories: list, *, max_workers: int = 5,
                       use_cache: bool = True, offline_fallback: bool = True,
                       stale_out: Optional[set] = None) -> dict:
    """Fetch all category payloads in parallel.

    Returns {key: payload} for successes and {key: Exception} for failures.
    Results are returned in the same order as `categories`.

    If a live fetch fails and `offline_fallback` is on, the last payload saved to
    disk is used instead and its key is added to `stale_out` (so callers can warn
    the user that prices may be out of date).
    """
    results: dict = {}
    to_fetch = []

    for key, ninja_type, label, is_unique in categories:
        if use_cache:
            cached = _cache_get(league, key)
            if cached is not None:
                results[key] = cached
                continue
        to_fetch.append((key, ninja_type, label, is_unique))

    if not to_fetch:
        return results

    def _fetch_one(item):
        k, ninja_type, _label, is_unique = item
        return k, fetch_category(league, k, ninja_type, is_unique)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [(item[0], executor.submit(_fetch_one, item)) for item in to_fetch]
        for key, future in futures:
            try:
                _, payload = future.result()
                if use_cache:
                    _cache_set(league, key, payload)
                results[key] = payload
            except Exception as e:
                disk, _age = load_payload_from_disk(league, key) if offline_fallback else (None, None)
                if disk is not None:
                    results[key] = disk
                    if stale_out is not None:
                        stale_out.add(key)
                else:
                    results[key] = e

    return results


def fetch_all_scout_payloads(league: str) -> dict:
    """Fetch all Scout (poe2scout.com) category payloads in parallel.
    Returns {key: payload_dict} for any that succeed, silently omits failures."""
    results: dict = {}

    def _fetch(item):
        key, cat_slug = item[0], item[1]
        return key, fetch_scout_payload(cat_slug, league)

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [(cat[0], executor.submit(_fetch, cat)) for cat in SCOUT_CATEGORIES]
        for key, future in futures:
            try:
                _, payload = future.result()
                if payload:
                    results[key] = payload
            except Exception:
                pass

    return results


def exalted_rate(payload: dict) -> float:
    return float(payload.get("core", {}).get("rates", {}).get("exalted") or 0.0)


def divine_value_from_exalt(exalt_value: float, divine_rate_exalts: float) -> float:
    return exalt_value / divine_rate_exalts if divine_rate_exalts else 0.0


_ESSENCE_TIER_ORDER = {"lesser": 0, "": 1, "greater": 2, "perfect": 3}
_ESSENCE_TIER_LABELS = {0: "Lesser", 1: "", 2: "Greater", 3: "Perfect"}

def _essence_tier_key(name: str):
    """Sort key: (tier 0-3, base_name) so Lesser < base < Greater < Perfect."""
    low = name.lower()
    for prefix in ("lesser essence", "greater essence", "perfect essence"):
        if low.startswith(prefix):
            tier_word = prefix.split()[0]          # "lesser" / "greater" / "perfect"
            base = name[len(prefix):].strip()      # " of X" → "of X"
            return (_ESSENCE_TIER_ORDER[tier_word], base)
    # Plain "Essence of X"
    if low.startswith("essence"):
        base = name[len("essence"):].strip()
        return (_ESSENCE_TIER_ORDER[""], base)
    return (99, name)                               # non-essence items fall to end


def format_rule(name: str, exalt_value: float, _divine_value: float, header: str = "Type",
                min_exalt: Optional[float] = None, ritual_threshold: Optional[float] = None) -> str:
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
    min_exalt: Optional[float] = None,
    tier_sort: bool = False,
    enabled_names: Optional[Set[str]] = None,
    always_names: Optional[List[str]] = None,
    ritual_threshold: Optional[float] = None,
) -> list:
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
            format_rule(name, ev, dv, min_exalt=min_exalt, ritual_threshold=ritual_threshold)
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


def build_uncut_gem_lines(payload: dict, divine_rate_exalts: float, min_exalt: Optional[float] = None,
                          enabled_names: Optional[set] = None) -> list:
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


def build_unique_lines(payload: dict, _divine_rate_exalts: float, min_exalt: Optional[float] = None) -> list:
    threshold = min_exalt if min_exalt is not None else MIN_EXALT
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
        rows.append((exalt_value, rule if exalt_value >= threshold else f"//{rule}"))
    rows.sort(key=lambda r: -r[0])
    return [rule for _, rule in rows]



def build_waystone_lines() -> list:
    """Always pick all waystones tier 1-15 regardless of value."""
    return list(WAYSTONE_FALLBACK_RULES)


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
                                  pick_all: bool = False, min_exalt: Optional[float] = None) -> list:
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
        pv   = float(line.get("primaryValue") or 0.0)
        ev   = pv * rate if rate else pv
        included = pick_all or ev >= threshold
        rows.append(make_report_row(label, name, "", pv, ev, threshold, included))
    return rows


def collect_unique_report_rows(label: str, payload: dict, divine_rate_exalts: float, min_exalt: Optional[float] = None) -> list:
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
    parser.add_argument("--list-leagues",    action="store_true",       help="Print live leagues and exit")
    parser.add_argument("--check-endpoints", action="store_true",       help="Test all poe.ninja category endpoints and print results")
    parser.add_argument("--variant",         choices=("all","currency","exchange","uniques","maps"), default="all")
    parser.add_argument("--include-bases",   action="store_true",       help="Build endgame base type rules from game data and append to output")
    parser.add_argument("--base-quality",    type=int, default=28,      help="Min quality %% for base-type rules (default 28)")
    parser.add_argument("--base-min-level",  type=int, default=75,      help="Min required level for base-type rules (default 75)")
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
                lines = build_exchange_lines(payload, divine_rate_exalts, pick_all=pick_all, min_exalt=min_exalt, tier_sort=(key == "essences"), always_names=always)
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
    output_lines.extend(STATIC_TABLET_RULES.splitlines())

    # ── Breach Wombgifts ──────────────────────────────────────────────────────
    output_lines.extend(STATIC_WOMBGIFT_RULES.splitlines())

    # ── Special Waystones ─────────────────────────────────────────────────────
    output_lines.extend(STATIC_SPECIAL_WAYSTONE_RULES.splitlines())

    # ── Chance Orb Bases ──────────────────────────────────────────────────────
    output_lines.extend(build_chance_base_rules())

    # ── Base types (optional) ─────────────────────────────────────────────────
    if args.include_bases:
        print("Building base type rules from game data…")
        def _prog(idx, total, title):
            print(f"  [{idx}/{total}] {title}")
        base_lines = build_base_rules(min_quality=args.base_quality, min_level=args.base_min_level, progress_callback=_prog)
        output_lines.append("")
        output_lines.append(header_major("Base Types"))
        output_lines.append("")
        output_lines.extend(base_lines)
        output_lines.append("")
        print(f"  {len(base_lines)} base rules added.")

    # ── Write output ──────────────────────────────────────────────────────────
    content = "\n".join(output_lines)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(content)

    # ── Also write latest.ipd beside the output file ──────────────────────────
    out_dir  = os.path.dirname(os.path.abspath(args.output)) or "."
    latest   = os.path.join(out_dir, "latest.ipd")
    with open(latest, "w", encoding="utf-8") as f:
        f.write(content)

    # ── Write CSV item report ─────────────────────────────────────────────────
    csv_path = os.path.splitext(args.output)[0] + "_items.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        f.write(build_csv_report(report_rows))

    # ── Also write a matching PoE2 client loot filter ─────────────────────────
    filter_path = os.path.splitext(args.output)[0] + ".filter"
    with open(filter_path, "w", encoding="utf-8") as f:
        f.write("\n".join(build_loot_filter(output_lines)))

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
