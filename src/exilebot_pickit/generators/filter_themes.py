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

Restraint rules: only the jackpot tier plays a SOUND; light beams (PlayEffect)
are reserved for jackpot + uniques. A beam or ping on every cheap drop turns a
juiced map into a light show — that is why "named" stays quiet in every theme.

Pure module: data + one lookup, no I/O, no imports from the engine (the engine
imports us, never the other way around).
"""
from __future__ import annotations

DEFAULT_THEME = "classic"

# A generated [Type] rule at/above this live exalt value gets the jackpot look.
# ~a tenth of a Divine at the usual ~500 ex rate: rare enough to stay special.
JACKPOT_EXALT = 50.0

# UI order: (key, label, one-line description shown next to the dropdown).
THEME_CHOICES = [
    ("classic", "Community classic",
     "The familiar tiered look: red screamer for jackpots, gold currency, orange uniques."),
    ("minimal", "Minimal",
     "The quiet look the app shipped before themes — thin borders, no backgrounds."),
    ("contrast", "High contrast",
     "Black backgrounds, bright text, bigger labels — for busy screens."),
    ("colorblind", "Colorblind safe",
     "Blue/orange palette — no red-vs-green distinctions anywhere."),
]

# classic is written once in full; colorblind overrides only the kinds where
# red/green must go (spread below), so a palette tweak to classic's neutral
# rows can never silently diverge between the two.
#
# Values below are NeverSink's OWN (owner's request 2026-07-17): extracted
# verbatim from his live PoE2 SOFT filter (the gamedata_cache copy tools/
# check_game_data.py maintains) — jackpot = his S-tier currency (Divine Orb
# block), named = his Exalted-Orb C-tier, unique = his standard unique brown,
# chance = his $tier->chancing green, gear = his salvage border, gold = his
# gold-stack white. ONE deliberate deviation: sounds/beams stay on jackpot
# (+ the unique beam) only — his per-tier sounds are strictness-gated, ours
# would ping on every cheap pickup.
_CLASSIC = {
    "jackpot": ["SetFontSize 45", "SetTextColor 255 0 0",
                "SetBorderColor 255 0 0", "SetBackgroundColor 255 255 255",
                "PlayAlertSound 6 300", "PlayEffect Red",
                "MinimapIcon 0 Red Star"],
    "named": ["SetFontSize 42", "SetTextColor 0 0 0",
              "SetBorderColor 0 0 0", "SetBackgroundColor 245 139 87",
              "MinimapIcon 1 Yellow Circle"],
    "unique": ["SetFontSize 42", "SetTextColor 255 255 255",
               "SetBorderColor 255 255 255", "SetBackgroundColor 188 96 37",
               "PlayEffect Brown", "MinimapIcon 1 Brown Star"],
    "chance": ["SetFontSize 38", "SetTextColor 125 255 89",
               "SetBorderColor 125 255 89", "SetBackgroundColor 0 50 0",
               "MinimapIcon 1 Green Diamond"],
    "gear": ["SetFontSize 35", "SetBorderColor 127 127 127"],
    "waystone": ["SetFontSize 42", "SetTextColor 255 255 255",
                 "SetBorderColor 200 200 200", "MinimapIcon 1 White Square"],
    "gold": ["SetFontSize 35", "SetTextColor 255 255 255"],
}

# The exact style commands v4.35.x shipped (named/unique/gear/gold), so a user
# who liked the pre-theme look keeps it. jackpot deliberately ALIASES named:
# minimal has no screamer tier, and aliasing (not copying) makes that
# un-drift-able. Note the commands are the same but block layout moved: styles
# now sit after the BaseType line (NeverSink order) instead of before it —
# the PoE2 parser is order-agnostic inside a block.
_MINIMAL_NAMED = ["SetFontSize 38", "SetBorderColor 255 207 92",
                  "MinimapIcon 2 Yellow Circle"]
_MINIMAL = {
    "jackpot": _MINIMAL_NAMED,
    "named": _MINIMAL_NAMED,
    "unique": ["SetFontSize 40", "SetTextColor 175 96 37",
               "SetBorderColor 175 96 37", "PlayEffect Brown",
               "MinimapIcon 1 Brown Star"],
    "chance": ["SetFontSize 34"],
    "gear": ["SetFontSize 32"],
    "waystone": ["SetFontSize 34"],
    "gold": ["SetFontSize 35"],
}

_CONTRAST = {
    "jackpot": ["SetFontSize 45", "SetTextColor 0 0 0",
                "SetBorderColor 255 255 255", "SetBackgroundColor 255 255 255",
                "PlayAlertSound 6 300", "PlayEffect White",
                "MinimapIcon 0 White Star"],
    "named": ["SetFontSize 42", "SetTextColor 255 255 0",
              "SetBorderColor 255 255 0", "SetBackgroundColor 0 0 0",
              "MinimapIcon 1 Yellow Circle"],
    "unique": ["SetFontSize 42", "SetTextColor 255 140 60",
               "SetBorderColor 255 140 60", "SetBackgroundColor 0 0 0",
               "PlayEffect Orange", "MinimapIcon 0 Orange Star"],
    "chance": ["SetFontSize 40", "SetTextColor 0 255 255",
               "SetBorderColor 0 255 255", "SetBackgroundColor 0 0 0",
               "MinimapIcon 1 Cyan Moon"],
    "gear": ["SetFontSize 34", "SetBorderColor 200 200 200"],
    "waystone": ["SetFontSize 40", "SetTextColor 255 255 255",
                 "SetBorderColor 255 255 255", "SetBackgroundColor 40 40 40",
                 "MinimapIcon 1 White Square"],
    "gold": ["SetFontSize 36", "SetTextColor 255 255 150"],
}

THEMES = {
    "classic": _CLASSIC,
    "minimal": _MINIMAL,
    "contrast": _CONTRAST,
    # Colorblind = classic with every red/green-dependent kind moved onto the
    # blue/orange axis; neutral kinds (named/gear/gold) are inherited, so they
    # can never drift from classic.
    "colorblind": {
        **_CLASSIC,
        "jackpot": ["SetFontSize 45", "SetTextColor 255 255 255",
                    "SetBorderColor 255 255 255", "SetBackgroundColor 0 90 190",
                    "PlayAlertSound 6 300", "PlayEffect Blue",
                    "MinimapIcon 0 Blue Star"],
        "unique": ["SetFontSize 42", "SetTextColor 255 150 40",
                   "SetBorderColor 255 150 40", "SetBackgroundColor 0 0 0 208",
                   "PlayEffect Orange", "MinimapIcon 1 Orange Star"],
        "chance": ["SetFontSize 38", "SetTextColor 130 200 255",
                   "SetBorderColor 130 200 255", "MinimapIcon 2 Blue Moon"],
        "waystone": ["SetFontSize 38", "SetTextColor 255 255 255",
                     "SetBorderColor 130 200 255", "MinimapIcon 1 Blue Square"],
    },
}


def get_style(theme: str, kind: str) -> list:
    """Style lines for one rule kind. Unknown theme falls back to the default
    (a stale config value must never strip styling); unknown kind is empty.
    Returns a fresh list — callers may append without mutating the table."""
    table = THEMES.get(theme) or THEMES[DEFAULT_THEME]
    return list(table.get(kind) or ())
