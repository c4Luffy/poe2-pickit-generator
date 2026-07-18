"""Filter-only visual classification for IPD rules.

This module never creates, removes, enables, or disables a pickit rule.  It
only reads an existing rule and answers one question: which *appearance* should
the matching in-game loot-filter block use?

Market-priced rules use their generated ``ExValue`` comment.  Rules without a
price use their IPD section/purpose (chance base, craft base, fracture target,
and so on).  Both loot-filter writers call this module so importing a generated
IPD cannot flatten all of its items back into one generic colour.
"""
from __future__ import annotations

import re

DEFAULT_DIVINE_EXALT = 500.0
JACKPOT_DIVINE_FRACTION = 0.10
HIGH_VALUE_EXALT = 10.0
USEFUL_VALUE_EXALT = 1.0

_EXVALUE_RE = re.compile(r"\bExValue\s*=\s*([\d,.]+)", re.I)
_DIVINE_HEADER_RE = re.compile(
    r"\b1\s+Divine\s*=\s*([\d,.]+)\s+Exalted\b", re.I,
)
_DIVINE_RULE_RE = re.compile(r'\[Type\]\s*==\s*"Divine Orb"', re.I)
_TYPE_RE = re.compile(r'\[Type\]\s*==\s*"((?:[^"\\]|\\.)*)"')
_RARITY_RE = re.compile(r'\[Rarity\]\s*==\s*"(Normal|Magic|Rare|Unique)"', re.I)
_CATEGORY_RE = re.compile(r'\[Category\]\s*==\s*"(\w+)"', re.I)
_SECTION_RE = re.compile(r"^//\s*([A-Z][A-Z0-9 &'()/-]*?)\s*//$")

# Highest priority is emitted first because Path of Exile uses the first
# matching Show block.  Purpose styles sit between market tiers and quiet
# priced items so a curated unpriced rule never masquerades as worthless.
VISUAL_ORDER = (
    "mythic", "jackpot", "high", "useful",
    "chance", "fracture", "exceptional", "curated", "unique",
    "craft", "waystone", "gear", "named", "quiet",
)
VISUAL_PRIORITY = {kind: len(VISUAL_ORDER) - i for i, kind in enumerate(VISUAL_ORDER)}

VISUAL_LABELS = {
    "mythic": "Mythic value",
    "jackpot": "Jackpot value",
    "high": "High value",
    "useful": "Useful value",
    "quiet": "Quiet value",
    "chance": "Chance bases",
    "fracture": "Fracture targets",
    "exceptional": "Exceptional bases",
    "curated": "Curated items",
    "unique": "Unpriced uniques",
    "craft": "Craft bases",
    "waystone": "Waystones",
    "gear": "Gear rules",
    "named": "Unpriced named items",
}

_SECTION_KIND = {
    "WAYSTONES": "waystone",
    "REGULAR TABLETS (ALL RARITIES)": "curated",
    "BREACH WOMBGIFTS": "curated",
    "EXOTIC BASES": "curated",
    "CHANCE ORB BASES": "chance",
    "CRAFT BASES": "craft",
    "FRACTURE BASES": "fracture",
    "MAGIC & RARE": "gear",
    "EXCEPTIONAL BASES": "exceptional",
}


def extract_ex_value(line: str) -> float | None:
    """Return a rule's generated exalt value, if its comment carries one."""
    m = _EXVALUE_RE.search(line or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def extract_divine_rate(lines) -> float:
    """Find the Exalted value of one Divine in a complete IPD.

    Generated files carry it in both the banner and the Divine Orb rule.  The
    banner wins; the rule is the fallback for hand-edited/minimal files.  A
    stable default keeps old third-party IPDs deterministic.
    """
    rows = list(lines)
    for line in rows:
        m = _DIVINE_HEADER_RE.search(line or "")
        if m:
            try:
                value = float(m.group(1).replace(",", ""))
                if value > 0:
                    return value
            except ValueError:
                pass
    for line in rows:
        if _DIVINE_RULE_RE.search(line or ""):
            value = extract_ex_value(line)
            if value is not None and value > 0:
                return value
    return DEFAULT_DIVINE_EXALT


def section_from_comment(line: str) -> str | None:
    """Return a normalized generated-IPD section heading, or ``None``."""
    m = _SECTION_RE.match((line or "").strip())
    if not m:
        return None
    section = " ".join(m.group(1).split()).upper()
    # This is a container banner; the next real heading is the useful one.
    return None if section == "ECONOMY ITEMS" else section


def jackpot_threshold(divine_rate: float) -> float:
    """Exalt value at which a drop earns the jackpot look.

    Normally 10% of a Divine, so it rises and falls with the Divine rate. But
    when Divine is cheap (< ~100 ex, e.g. league start), 10% of it would dip
    below the fixed High floor and a modest 9-ex orb would wrongly wear the red
    jackpot label. Clamping to at least the High floor keeps the ladder
    strictly ordered: useful < high < jackpot < mythic, always."""
    divine = divine_rate if divine_rate > 0 else DEFAULT_DIVINE_EXALT
    return max(divine * JACKPOT_DIVINE_FRACTION, HIGH_VALUE_EXALT)


def value_kind(ex_value: float, divine_rate: float) -> str:
    """Map a live exalt value to the filter's five-level value ladder."""
    divine = divine_rate if divine_rate > 0 else DEFAULT_DIVINE_EXALT
    if ex_value >= divine:
        return "mythic"
    if ex_value >= jackpot_threshold(divine):
        return "jackpot"
    if ex_value >= HIGH_VALUE_EXALT:
        return "high"
    if ex_value >= USEFUL_VALUE_EXALT:
        return "useful"
    return "quiet"


def classify_rule(line: str, section: str | None, divine_rate: float) -> str:
    """Choose a visual kind for one active IPD rule.

    Price is strongest when present.  Without it, generated section intent is
    more honest than inventing a market value.  Finally, syntax-only fallbacks
    keep arbitrary hand-written pickits useful.
    """
    ex_value = extract_ex_value(line)
    if ex_value is not None:
        return value_kind(ex_value, divine_rate)

    names = [n.replace('\\"', '"') for n in _TYPE_RE.findall(line or "")]
    if any(n in {"Mirror of Kalandra", "Divine Orb"} for n in names):
        return "mythic"

    sec = (section or "").upper()
    if sec.startswith("UNIQUE "):
        return "unique"
    if sec in _SECTION_KIND:
        return _SECTION_KIND[sec]

    category = _CATEGORY_RE.search(line or "")
    if category and category.group(1).lower() == "waystone":
        return "waystone"

    rarity = _RARITY_RE.search(line or "")
    rarity_name = rarity.group(1).title() if rarity else ""
    if rarity_name == "Unique":
        return "unique"
    if rarity_name == "Normal":
        return "chance"
    if rarity_name in {"Magic", "Rare"}:
        return "gear"
    if "[Quality]" in line or "[Sockets]" in line:
        return "gear"
    return "named"


def visual_sort_key(kind: str):
    """Sort key for strongest/most specific visual blocks first."""
    return -VISUAL_PRIORITY.get(kind, 0), kind


def visual_report(counts: dict, examples: dict) -> list[dict]:
    """JSON-friendly ordered rows for the Create-your-filter preview."""
    rows = []
    for kind in VISUAL_ORDER:
        count = int(counts.get(kind, 0) or 0)
        if not count:
            continue
        rows.append({
            "id": kind,
            "label": VISUAL_LABELS.get(kind, kind.title()),
            "count": count,
            "examples": list(dict.fromkeys(examples.get(kind, ())))[:3],
        })
    return rows


def threshold_summary(divine_rate: float) -> dict:
    """Thresholds shown in the UI/report; classification only, never pickup."""
    divine = divine_rate if divine_rate > 0 else DEFAULT_DIVINE_EXALT
    return {
        "divine_exalt": round(divine, 2),
        "mythic": round(divine, 2),
        "jackpot": round(jackpot_threshold(divine), 2),
        "high": HIGH_VALUE_EXALT,
        "useful": USEFUL_VALUE_EXALT,
    }
