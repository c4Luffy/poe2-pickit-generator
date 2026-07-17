"""Label themes for every loot filter the app writes.

One table, two consumers: ``generator.build_loot_filter`` (the .filter written
next to every generated pickit) and ``generators/pickit_import`` (Create your
filter). A theme maps rule KINDS — what a Show block represents — to the style
lines placed inside that block, so both filters get one consistent look the
user picks once (``filter_theme`` in config).

Kinds:
    jackpot   [Type] rules whose live ExValue >= JACKPOT_EXALT, plus the
              always-scream names in generator._LF_JACKPOT_ALWAYS. Rules whose
              builder carries no price (exotic bases, wombgifts, splinters)
              can't be tiered and stay "named" — a quiet label is the honest
              fallback when the value is unknown. Imported pickits carry no
              prices, so import never uses this kind.
    named     every other [Type] rule: currency, runes, essences, valuable bases
    unique    Rarity Unique rules
    chance    white (Normal-rarity) named bases the pickit keeps — chance
              bases, craft bases and normal tablets all share this look; the
              filter sees only the rule's conditions, not why it was written
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

DEFAULT_THEME = "classic"

# A generated [Type] rule at/above this live exalt value gets the jackpot look.
# ~a tenth of a Divine at the usual ~500 ex rate: rare enough to stay special.
JACKPOT_EXALT = 50.0

# ONE theme, on the owner's order (2026-07-17: "don't need too many themes").
# The table/lookup mechanism stays so a second theme is a data change away,
# and get_style's fallback quietly maps any stored pre-cut value ("minimal",
# "contrast", "colorblind") to classic.
THEME_CHOICES = [
    ("classic", "Community classic",
     "The owner's filter colors: red screamer for jackpots, orange currency and uniques."),
]

# Values below are the OWNER'S OWN in-game filter codes (supplied 2026-07-17):
# unique = his uniques style (dark-brown text on unique-orange, Brown Kite),
# chance = his "Favourite Chance Bases" (Brown beam + Brown Kite), gear = his
# "Good Exceptional" (White beam + White Kite), waystone = his rare-waystone
# Orange Diamond, gold = his normal-stack dark backdrop. jackpot/named keep
# the earlier NeverSink-derived currency look (red-on-white screamer / orange
# Exalted tier) because the currency section of his filter wasn't provided —
# swap these when he supplies those codes. No PlayAlertSound anywhere
# (owner's standing order).
_CLASSIC = {
    "jackpot": ["SetFontSize 45", "SetTextColor 255 0 0",
                "SetBorderColor 255 0 0", "SetBackgroundColor 255 255 255",
                "PlayEffect Red", "MinimapIcon 1 Red Kite"],
    "named": ["SetFontSize 42", "SetTextColor 0 0 0",
              "SetBorderColor 0 0 0", "SetBackgroundColor 245 139 87",
              "MinimapIcon 1 Yellow Circle"],
    "unique": ["SetFontSize 37", "SetTextColor 53 30 14 255",
               "SetBorderColor 53 30 14 255", "SetBackgroundColor 175 96 37 240",
               "PlayEffect Brown", "MinimapIcon 1 Brown Kite"],
    "chance": ["PlayEffect Brown", "MinimapIcon 2 Brown Kite"],
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
