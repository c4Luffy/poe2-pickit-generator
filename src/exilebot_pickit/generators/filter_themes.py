"""Label themes for every loot filter the app writes.

One table, two consumers: ``generator.build_loot_filter`` (the .filter written
next to every generated pickit) and ``generators/pickit_import`` (Create your
filter). A theme maps rule KINDS — what a Show block represents — to the style
lines placed inside that block, so both filters get one consistent look the
user picks once (``filter_theme`` in config).

Kinds:
    mythic/jackpot/high/useful/quiet
              five live-value tiers read from each rule's ``ExValue`` comment.
              Their top thresholds follow the Divine rate stored in the IPD.
    named     a named rule whose price/purpose is unknown
    unique    Rarity Unique rules
    chance    white (Normal-rarity) named bases the pickit keeps — chance
              bases in their dedicated section
    craft/fracture/exceptional/curated
              generated, unpriced rules whose section says why they are kept
    gear      magic/rare gear, quality/socket/salvage and category rules
    waystone  waystone blocks
    gold      the always-show Gold block that survives "hide everything else"

Command vocabulary (SetTextColor/SetBorderColor/SetBackgroundColor/SetFontSize/
PlayEffect/MinimapIcon/PlayAlertSound) matches what NeverSink's live PoE2
filter emits — the same visual language FilterBlade produces, so the colors
read instantly to anyone who has used a community filter.

Restraint rules: NO sounds anywhere (owner's call 2026-07-17 — the bot doesn't
listen and pings annoy). Beams follow the owner's filter scheme (Brown for
uniques/chance, White for gear, Orange for waystones, Red for jackpots);
"named" currency stays beam-free so cheap drops don't light up the map.

Pure module: data + one lookup, no I/O, no imports from the engine (the engine
imports us, never the other way around).
"""
from __future__ import annotations

from exilebot_pickit.generators.filter_classification import (
    DEFAULT_DIVINE_EXALT, JACKPOT_DIVINE_FRACTION,
)

DEFAULT_THEME = "classic"

# Backward-compatible public constant used by older callers/tests.  Actual
# classification follows the Divine rate found in each IPD; 50 is the fallback
# for old files with no rate and no priced Divine rule.
JACKPOT_EXALT = DEFAULT_DIVINE_EXALT * JACKPOT_DIVINE_FRACTION

# ONE theme, on the owner's order (2026-07-17: "don't need too many themes").
# The table/lookup mechanism stays so a second theme is a data change away,
# and get_style's fallback quietly maps any stored pre-cut value ("minimal",
# "contrast", "colorblind") to classic.
THEME_CHOICES = [
    ("classic", "Community classic",
     "The owner's filter colors: red screamer for jackpots, orange currency and uniques."),
]

# The category styles retain the owner's established community palette.  The
# five value styles are this app's own explicit importance ladder: purple,
# red, orange, gold, then quiet neutral.  It is driven by the IPD's own prices,
# not by a third-party filter's item tier list.  No PlayAlertSound anywhere
# (owner's standing order).
_CLASSIC = {
    # Value ladder.  Only High+ creates a beam; useful/quiet loot stays readable
    # without recreating the wall of identical beams this feature fixes.
    "mythic": ["SetFontSize 45", "SetTextColor 79 0 122 255",
               "SetBorderColor 79 0 122 255",
               "SetBackgroundColor 237 233 222 240",
               "PlayEffect Purple", "MinimapIcon 0 Purple Star"],
    "jackpot": ["SetFontSize 42", "SetTextColor 180 20 20 255",
                "SetBorderColor 180 20 20 255",
                "SetBackgroundColor 237 233 222 235",
                "PlayEffect Red", "MinimapIcon 0 Red Circle"],
    "high": ["SetFontSize 39", "SetTextColor 151 72 8 255",
             "SetBorderColor 151 72 8 255",
             "SetBackgroundColor 237 233 222 230",
             "PlayEffect Orange", "MinimapIcon 1 Orange Circle"],
    "useful": ["SetFontSize 35", "SetTextColor 238 190 72 255",
               "SetBorderColor 174 126 34 255",
               "SetBackgroundColor 28 22 14 220"],
    "quiet": ["SetFontSize 30", "SetTextColor 205 196 178 255",
              "SetBorderColor 95 82 62 210",
              "SetBackgroundColor 0 0 0 165"],
    "named": ["SetFontSize 33", "SetTextColor 215 202 178 255",
              "SetBorderColor 123 95 58 220",
              "SetBackgroundColor 18 14 10 190"],
    "unique": ["SetFontSize 37", "SetTextColor 53 30 14 255",
               "SetBorderColor 53 30 14 255", "SetBackgroundColor 175 96 37 240",
               "PlayEffect Brown", "MinimapIcon 1 Brown Kite"],
    "chance": ["PlayEffect Brown", "MinimapIcon 2 Brown Kite"],
    "craft": ["SetFontSize 34", "SetTextColor 235 235 235 255",
              "SetBorderColor 170 170 170 230",
              "SetBackgroundColor 20 20 20 190",
              "PlayEffect White", "MinimapIcon 2 White Kite"],
    "fracture": ["SetFontSize 37", "SetTextColor 255 160 210 255",
                 "SetBorderColor 220 80 155 255",
                 "SetBackgroundColor 32 8 24 220",
                 "PlayEffect Pink", "MinimapIcon 1 Pink Diamond"],
    "exceptional": ["SetFontSize 37", "SetTextColor 105 235 235 255",
                    "SetBorderColor 45 190 200 255",
                    "SetBackgroundColor 5 30 34 220",
                    "PlayEffect Cyan", "MinimapIcon 1 Cyan Kite"],
    "curated": ["SetFontSize 36", "SetTextColor 245 220 105 255",
                "SetBorderColor 190 155 45 255",
                "SetBackgroundColor 30 24 5 210",
                "MinimapIcon 2 Yellow Diamond"],
    "gear": ["PlayEffect White", "MinimapIcon 2 White Kite"],
    "waystone": ["PlayEffect Orange", "MinimapIcon 2 Orange Diamond"],
    "gold": ["SetBackgroundColor 0 0 0 170"],
}

THEMES = {
    "classic": _CLASSIC,
}


def get_style(theme: str, kind: str) -> list:
    """Style lines for one rule kind. Unknown theme falls back to the default
    (a stale config value must never strip styling); unknown kind is empty.
    Returns a fresh list — callers may append without mutating the table."""
    table = THEMES.get(theme) or THEMES[DEFAULT_THEME]
    return list(table.get(kind) or ())
