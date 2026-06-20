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
from concurrent.futures import ThreadPoolExecutor
import html as _html
import io
import os
import re
import sys
import threading
import time
from dataclasses import dataclass
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
    ("liquid_emotions",     "Delirium",           "Liquid Emotions",      False),
    ("catalysts",           "Breach",             "Catalysts",            False),
    ("abyssal_bones",       "Abyss",              "Abyssal Bones",        False),
    ("fragments",           "Fragments",          "Fragments",            False),
    ("runes",               "Runes",              "Runes",                False),
    ("omens",               "Ritual",             "Omens",                False),
    ("soul_cores",          "SoulCores",          "Soul Cores",           False),
    ("idols",               "Idols",              "Idols",                False),
    ("uncut_gems",          "UncutGems",          "Uncut Gems",           False),
    ("lineage_support_gems","LineageSupportGems", "Lineage Support Gems", False),
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

# Categories where EVERY item is picked regardless of price threshold.
# Lineage Support Gems are always wanted — they're too rare to skip any.
PICK_ALL_CATEGORIES = {"lineage_support_gems"}

# poe.ninja sometimes returns names that don't match in-game base types.
# Map the poe.ninja name → correct in-game name here.
ITEM_NAME_CORRECTIONS = {
    "Refined Necrotic Catalyst": "Refined Neural Catalyst",
}

# Items returned by poe.ninja that have no valid in-game base type and should
# be skipped entirely rather than written to the pickit.
ITEM_NAME_SKIP: set = set()

# Currency items that must always be picked up even if poe.ninja omits them
# (Exalted Orb is the PoE2 base pricing currency and won't appear in lines).
ALWAYS_PICK_CURRENCY = [
    "Exalted Orb",
    "Divine Orb",
    "Mirror of Kalandra",
]


# Fallback waystone rules used when poe.ninja returns no waystone rows.
WAYSTONE_FALLBACK_RULES = [
    '[Category] == "Waystone" && [Rarity] == "Normal" && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Magic"  && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Rare"   && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
]

# ─────────────────────────────────────────────────────────────────────────────
#  Poe2DB base-type scraping
# ─────────────────────────────────────────────────────────────────────────────

POE2DB_BASE_URL = "https://poe2db.tw/us"


@dataclass(frozen=True)
class BaseCategory:
    slug: str
    title: str
    socket_threshold: int
    min_level: int = 75


POE2DB_BASE_CATEGORIES = (
    # One-handed weapons
    BaseCategory("Wands",           "Wands",           2),
    BaseCategory("One_Hand_Axes",   "One Hand Axes",   2),
    BaseCategory("One_Hand_Maces",  "One Hand Maces",  2),
    BaseCategory("Sceptres",        "Sceptres",        2),
    BaseCategory("Spears",          "Spears",          2),
    # Two-handed weapons
    BaseCategory("Bows",            "Bows",            3),
    BaseCategory("Staves",          "Staves",          3),
    BaseCategory("Two_Hand_Axes",   "Two Hand Axes",   3),
    BaseCategory("Two_Hand_Maces",  "Two Hand Maces",  3),
    BaseCategory("Quarterstaves",   "Quarterstaves",   3),
    BaseCategory("Crossbows",       "Crossbows",       3),
    # Armour
    BaseCategory("Body_Armours",    "Body Armours",    3),
    BaseCategory("Helmets",         "Helmets",         2),
    BaseCategory("Gloves",          "Gloves",          2),
    BaseCategory("Boots",           "Boots",           2),
    # Off-hand / shields
    BaseCategory("Shields",         "Shields",         2),
    BaseCategory("Bucklers",        "Bucklers",        2),
    BaseCategory("Foci",            "Foci",            2),
)

# Static list of known endgame base types — used as fallback when poe2db scraping
# returns nothing (site down, HTML changed, network error, etc.).
# Format: (item_name, socket_threshold)
_STATIC_ENDGAME_BASES: tuple = (
    # ── One-handed weapons ────────────────────────────────────────────────────
    ("Akoyan Club",                 2), ("Fortified Hammer",             2),
    ("Marauding Mace",              2), ("Molten Hammer",                2),
    ("Akoyan Spear",                2), ("Flying Spear",                 2),
    ("Grand Spear",                 2), ("Guardian Spear",               2),
    ("Spiked Spear",                2), ("Stalking Spear",               2),
    ("Strife Pick",                 2),
    # ── Two-handed weapons ────────────────────────────────────────────────────
    ("Fanatic Bow",                 3), ("Gemini Bow",                   3),
    ("Guardian Bow",                3), ("Obliterator Bow",              3),
    ("Warmonger Bow",               3),
    ("Desolate Crossbow",           3), ("Elegant Crossbow",             3),
    ("Flexed Crossbow",             3), ("Gemini Crossbow",              3),
    ("Siege Crossbow",              3),
    ("Aegis Quarterstaff",          3), ("Bolting Quarterstaff",         3),
    ("Dreaming Quarterstaff",       3), ("Razor Quarterstaff",           3),
    ("Skullcrusher Quarterstaff",   3), ("Striking Quarterstaff",        3),
    ("Permafrost Staff",            3),
    ("Fanatic Greathammer",         3), ("Ironwood Greathammer",         3),
    ("Massive Greathammer",         3), ("Ruination Maul",               3),
    ("Tawhoan Greatclub",           3),
    # ── Body Armours ──────────────────────────────────────────────────────────
    ("Austere Garb",                3), ("Corsair Coat",                 3),
    ("Death Mail",                  3), ("Death Mantle",                 3),
    ("Falconer's Jacket",           3), ("Feathered Raiment",            3),
    ("Sacramental Robe",            3), ("Seastorm Mantle",              3),
    ("Thane Mail",                  3), ("Utzaal Cuirass",               3),
    ("Warlord Cuirass",             3), ("Wyrmscale Coat",               3),
    ("Cryptic Leggings",            3), ("Warlock Leggings",             3),
    # ── Helmets ───────────────────────────────────────────────────────────────
    ("Ancestral Tiara",             2), ("Champion Helm",                2),
    ("Cryptic Crown",               2), ("Divine Crown",                 2),
    ("Freebooter Cap",              2), ("Gladiatorial Helm",            2),
    ("Grinning Mask",               2), ("Imperial Greathelm",           2),
    ("Kamasan Tiara",               2), ("Paragon Greathelm",            2),
    ("Soaring Mask",                2), ("Trapper Hood",                 2),
    # ── Gloves ────────────────────────────────────────────────────────────────
    ("Adherent Cuffs",              2), ("Barbed Bracers",               2),
    ("Blacksteel Gauntlets",        2), ("Cultist Gauntlets",            2),
    ("Gleaming Cuffs",              2), ("Massive Mitts",                2),
    ("Polished Bracers",            2), ("Secured Wraps",                2),
    ("Sirenscale Gloves",           2), ("Vaal Gloves",                  2),
    ("Vaal Mitts",                  2), ("Vaal Wraps",                   2),
    # ── Boots ─────────────────────────────────────────────────────────────────
    ("Blacksteel Sabatons",         2), ("Daggerfoot Shoes",             2),
    ("Dragonscale Boots",           2), ("Drakeskin Boots",              2),
    ("Fortress Sabatons",           2), ("Quickslip Shoes",              2),
    ("Sandsworn Sandals",           2), ("Sekhema Sandals",              2),
    ("Tasalian Greaves",            2), ("Vaal Greaves",                 2),
    # ── Shields ───────────────────────────────────────────────────────────────
    ("Blacksteel Crest Shield",     2), ("Golden Targe",                 2),
    ("Soaring Targe",               2), ("Tawhoan Tower Shield",         2),
    ("Vaal Crest Shield",           2), ("Vaal Tower Shield",            2),
    # ── Bucklers ──────────────────────────────────────────────────────────────
    ("Ancient Buckler",             2), ("Desert Buckler",               2),
    # ── Foci ──────────────────────────────────────────────────────────────────
    ("Sacred Focus",                2), ("Tasalian Focus",               2),
    # ── Runeforged variants ───────────────────────────────────────────────────
    ("Runeforged Adherent Cuffs",       2), ("Runeforged Ancestral Tiara",   2),
    ("Runeforged Ancient Buckler",      2), ("Runeforged Austere Garb",      3),
    ("Runeforged Barbed Bracers",       2), ("Runeforged Blacksteel Crest Shield", 2),
    ("Runeforged Blacksteel Gauntlets", 2), ("Runeforged Blacksteel Sabatons", 2),
    ("Runeforged Champion Helm",        2), ("Runeforged Corsair Coat",      3),
    ("Runeforged Cryptic Crown",        2), ("Runeforged Cryptic Leggings",  3),
    ("Runeforged Cultist Gauntlets",    2), ("Runeforged Daggerfoot Shoes",  2),
    ("Runeforged Death Mail",           3), ("Runeforged Death Mantle",      3),
    ("Runeforged Desert Buckler",       2), ("Runeforged Divine Crown",      2),
    ("Runeforged Dragonscale Boots",    2), ("Runeforged Drakeskin Boots",   2),
    ("Runeforged Falconer's Jacket",    3), ("Runeforged Feathered Raiment", 3),
    ("Runeforged Fortress Sabatons",    2), ("Runeforged Freebooter Cap",    2),
    ("Runeforged Gladiatorial Helm",    2), ("Runeforged Gleaming Cuffs",    2),
    ("Runeforged Golden Targe",         2), ("Runeforged Grinning Mask",     2),
    ("Runeforged Imperial Greathelm",   2), ("Runeforged Kamasan Tiara",     2),
    ("Runeforged Massive Mitts",        2), ("Runeforged Paragon Greathelm", 2),
    ("Runeforged Polished Bracers",     2), ("Runeforged Quickslip Shoes",   2),
    ("Runeforged Sacramental Robe",     3), ("Runeforged Sacred Focus",      2),
    ("Runeforged Sandsworn Sandals",    2), ("Runeforged Seastorm Mantle",   3),
    ("Runeforged Secured Wraps",        2), ("Runeforged Sekhema Sandals",   2),
    ("Runeforged Sirenscale Gloves",    2), ("Runeforged Soaring Mask",      2),
    ("Runeforged Soaring Targe",        2), ("Runeforged Tasalian Focus",    2),
    ("Runeforged Tasalian Greaves",     2), ("Runeforged Tawhoan Tower Shield", 2),
    ("Runeforged Thane Mail",           3), ("Runeforged Trapper Hood",      2),
    ("Runeforged Utzaal Cuirass",       3), ("Runeforged Vaal Crest Shield", 2),
    ("Runeforged Vaal Gloves",          2), ("Runeforged Vaal Greaves",      2),
    ("Runeforged Vaal Mitts",           2), ("Runeforged Vaal Tower Shield", 2),
    ("Runeforged Vaal Wraps",           2), ("Runeforged Warlock Leggings",  2),
    ("Runeforged Warlord Cuirass",      3), ("Runeforged Wyrmscale Coat",    3),
    # ── Runemastered variants ─────────────────────────────────────────────────
    ("Runemastered Armoured Vest",  3), ("Runemastered Enlightened Robe", 3),
    ("Runemastered Plumed Focus",   2), ("Runemastered Primal Markings",  3),
    ("Runemastered Vaal Tower Shield", 2),
)

# Matches <a class="whiteitem ..."> links exactly as poe2db renders them.
# Requires \s+ after "whiteitem" and a href attribute (same as reference impl).
_BASE_LINK_PAT = re.compile(
    r'<a\s+class="whiteitem\s+[^">]*"[^>]*href="[^"]+"[^>]*>(.*?)</a>',
    re.IGNORECASE | re.DOTALL,
)


def _clean_html(text: str) -> str:
    text = re.sub(r'<[^>]+>', ' ', text)          # replace tags with space (not empty)
    text = _html.unescape(text)
    return re.sub(r'\s+', ' ', text).strip()


def _poe2db_required_level(chunk: str):
    """Return the required level found in the 1800-char chunk after a link, or None."""
    text = _clean_html(chunk)
    m = re.search(r'Requires:\s*Level\s+(\d+)', text)
    return int(m.group(1)) if m else None


def _quote_ipd(name: str) -> str:
    """Escape double quotes inside an item name for the IPD rule format."""
    return name.replace('"', '\\"')


def fetch_text(url: str) -> str:
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    return r.text


def parse_poe2db_bases(page: str, category: BaseCategory, min_level: int = None) -> list:
    """Return list of endgame base-type names scraped from a poe2db category page."""
    threshold = min_level if min_level is not None else category.min_level
    names, seen = [], set()
    for m in _BASE_LINK_PAT.finditer(page):
        name = _clean_html(m.group(1))
        if not name or name in seen:
            continue
        # Use a 3000-char window so items near the end of the page still have
        # enough context to find their "Requires: Level" value.
        chunk_end = min(m.end() + 3000, len(page))
        chunk = page[m.end(): chunk_end]
        level = _poe2db_required_level(chunk)
        if level is not None and level < threshold:
            continue
        if level is None and "Endgame" not in chunk:
            continue
        seen.add(name)
        names.append(name)
    return names


def _build_static_base_rules(min_quality: int = 28) -> list:
    """Generate base rules from the hardcoded endgame-item list (fallback)."""
    lines: list = []
    lines.append(header_minor("Endgame Bases (static list)"))
    lines.append("")
    rules: set = set()
    for name, sock in _STATIC_ENDGAME_BASES:
        safe = _quote_ipd(name)
        rules.add(f'[Type] == "{safe}" && [Quality] >= "{min_quality}" # [StashItem] == "true"')
        rules.add(f'[Type] == "{safe}" && [Sockets] >= "{sock}" # [StashItem] == "true"')
    lines.extend(sorted(rules))
    lines.append("")
    return lines


def build_base_rules(min_quality: int = 28, min_level: int = 75, progress_callback=None) -> list:
    """Scrape endgame base types from Poe2DB and return categorised .ipd pickup rules.

    Behaviour:
    - Scrapes all categories in POE2DB_BASE_CATEGORIES for live data.
    - Any item from _STATIC_ENDGAME_BASES not already covered by scraping is
      appended in a supplementary section so weapon bases always appear even when
      poe2db weapon pages don't return parseable results.
    - If scraping returns nothing at all, _STATIC_ENDGAME_BASES is used alone.

    Each category gets its own header_minor section, then two rules per base:
      [Type] == "Name" && [Quality] >= "28" # [StashItem] == "true"
      [Type] == "Name" && [Sockets] >= "N"  # [StashItem] == "true"
    """
    all_lines: list = []
    any_scraped = False
    scraped_names: set = set()
    total = len(POE2DB_BASE_CATEGORIES)

    for idx, cat in enumerate(POE2DB_BASE_CATEGORIES, 1):
        if progress_callback:
            progress_callback(idx, total, cat.title)
        try:
            page = fetch_text(f"{POE2DB_BASE_URL}/{cat.slug}")
            time.sleep(0.2)
            names = parse_poe2db_bases(page, cat, min_level=min_level)
        except requests.RequestException as e:
            print(f"Warning: bases for {cat.title}: {e}", file=sys.stderr)
            names = []
        if not names:
            continue
        any_scraped = True
        # Normalise curly/typographic quotes to ASCII so the dedup check below
        # matches static-list names regardless of what poe2db sends.
        scraped_names.update(
            n.replace("‘", "'").replace("’", "'")
             .replace("“", '"').replace("”", '"')
            for n in names
        )
        all_lines.append(header_minor(cat.title))
        all_lines.append("")
        cat_rules: set = set()
        for name in names:
            safe = _quote_ipd(name)
            cat_rules.add(f'[Type] == "{safe}" && [Quality] >= "{min_quality}" # [StashItem] == "true"')
            cat_rules.add(f'[Type] == "{safe}" && [Sockets] >= "{cat.socket_threshold}" # [StashItem] == "true"')
        all_lines.extend(sorted(cat_rules))
        all_lines.append("")

    if not any_scraped:
        # Site completely unreachable — use full static list
        print(
            "Warning: poe2db scraping returned no results — using built-in static fallback list",
            file=sys.stderr,
        )
        return _build_static_base_rules(min_quality)

    # Supplement with static items not covered by scraping (e.g. weapon pages that
    # return no parseable results in poe2db's current HTML structure).
    extra: list = [
        (name, sock)
        for name, sock in _STATIC_ENDGAME_BASES
        if name not in scraped_names
    ]
    if extra:
        all_lines.append(header_minor("Additional Bases (weapons & misc)"))
        all_lines.append("")
        extra_rules: set = set()
        for name, sock in extra:
            safe = _quote_ipd(name)
            extra_rules.add(f'[Type] == "{safe}" && [Quality] >= "{min_quality}" # [StashItem] == "true"')
            extra_rules.add(f'[Type] == "{safe}" && [Sockets] >= "{sock}" # [StashItem] == "true"')
        all_lines.extend(sorted(extra_rules))
        all_lines.append("")

    return all_lines


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


def clear_cache():
    """Discard all cached poe.ninja payloads."""
    with _CACHE_LOCK:
        _PAYLOAD_CACHE.clear()


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
            return active[0].get("name", "Standard")
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Warning: could not auto-detect league ({e}); falling back to 'Standard'")
    return "Standard"


def fetch_category(league: str, key: str, ninja_type: str, is_unique: bool) -> dict:
    endpoint = "stash/current/item/overview" if is_unique else "exchange/current/overview"
    return _request_with_retry(f"{BASE_URL}/{endpoint}", {"league": league, "type": ninja_type})


def fetch_all_payloads(league: str, categories: list, *, max_workers: int = 5,
                       use_cache: bool = True) -> dict:
    """Fetch all category payloads in parallel.

    Returns {key: payload} for successes and {key: Exception} for failures.
    Results are returned in the same order as `categories`.
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
                results[key] = e

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
    min_exalt: float = None,
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
        # Sort by essence tier (Lesser → base → Greater → Perfect), then alphabetically
        rows.sort(key=lambda r: _essence_tier_key(r[0]))
    else:
        rows.sort(key=lambda r: -r[1])  # default: highest value first

    if pick_all:
        result = [
            f'[Type] == "{name}" # [StashItem] == "true" // ExValue = {ev:.2f}'
            for name, ev, _ in rows
        ]
    else:
        result = [format_rule(name, ev, dv, min_exalt=min_exalt,
                              ritual_threshold=ritual_threshold) for name, ev, dv in rows]

    # Prepend hardcoded always-pick rules for items poe.ninja omits (e.g. base currency)
    if always_names:
        scraped = {name for name, _, _ in rows}
        prefix = [
            f'[Type] == "{n}" # [StashItem] == "true"'
            for n in always_names if n not in scraped
        ]
        result = prefix + result

    return result


def build_uncut_gem_lines(payload: dict, divine_rate_exalts: float, min_exalt: float = None,
                          enabled_names: set = None) -> list:
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
        for _, level, name, ev, _ in group:
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



def build_waystone_lines(payload: dict, divine_rate_exalts: float, min_exalt: Optional[float] = None) -> list:
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
                                  pick_all: bool = False, min_exalt: float = None) -> list:
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


def collect_unique_report_rows(label: str, payload: dict, divine_rate_exalts: float, min_exalt: float = None) -> list:
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
    global MIN_EXALT
    parser = argparse.ArgumentParser(description="Generate ExileBot 2 pickit rules from poe.ninja's real economy API.")
    parser.add_argument("--league",          default=None,              help="Exact league name. Omit to auto-detect.")
    parser.add_argument("--min-exalt",       type=float, default=MIN_EXALT, help="Threshold below which items are commented out")
    parser.add_argument("--output",          default="poe2_pickit.txt", help="Output file path")
    parser.add_argument("--list-leagues",    action="store_true",       help="Print live leagues and exit")
    parser.add_argument("--check-endpoints", action="store_true",       help="Test all poe.ninja category endpoints and print results")
    parser.add_argument("--variant",         choices=("all","currency","exchange","uniques","maps"), default="all")
    parser.add_argument("--include-bases",   action="store_true",       help="Scrape endgame base types from Poe2DB and append rules")
    parser.add_argument("--base-quality",    type=int, default=28,      help="Min quality %% for base-type rules (default 28)")
    parser.add_argument("--base-min-level",  type=int, default=80,      help="Min required level for base-type rules (default 80)")
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
        f"// Source  : poe.ninja PoE2 economy API",
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

    for key, ninja_type, label, is_unique in categories:
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
                lines = build_waystone_lines(payload, divine_rate_exalts, min_exalt=min_exalt)
                report_rows.extend(collect_exchange_report_rows(label, payload, divine_rate_exalts, min_exalt=min_exalt))
            else:
                pick_all  = key in PICK_ALL_CATEGORIES
                always    = ALWAYS_PICK_CURRENCY if key == "currency" else None
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

    # ── Base types (optional) ─────────────────────────────────────────────────
    if args.include_bases:
        print("Fetching base types from Poe2DB…")
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

    active    = sum(1 for l in output_lines if l and not l.startswith("//") and "[StashItem]" in l)
    commented = sum(1 for l in output_lines if l.startswith("//") and "[StashItem]" in l)
    print(f"Written to   : {args.output}")
    print(f"Latest copy  : {latest}")
    print(f"Item report  : {csv_path}")
    print(f"Active rules : {active}   Commented out: {commented}")
    if getattr(sys, 'frozen', False):
        input("\nDone! Press Enter to exit...")


if __name__ == "__main__":
    main()
