# Map the poe.ninja name → correct in-game name here.
ITEM_NAME_CORRECTIONS: dict = {
    # poe.ninja name             → correct in-game base type
    # Add new entries here as mismatches are discovered.
    # Format: "poe.ninja display name": "ExiledBot base type name"
    # Map None to silently skip an item (items already in ITEM_NAME_SKIP
    # don't need a None entry here — they're already excluded).
    "Stamped Wombgift":          "Signet Wombgift",      # renamed in 0.2.0
    "Pressurised Wombgift":      "Ornate Wombgift",      # renamed in 0.2.0
}

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

# Runes not tracked by poe.ninja — always pick up regardless of threshold.
# Names verified against poe2db (patch 0.5.x, 2026-07-05).
ALWAYS_PICK_RUNES = [
    # Emergent runes (not tracked by poe.ninja)
    "Emergent Vigour",
    "Emergent Possibility",
    "Emergent Protection",
    "Emergent Instinct",
    # Core runes, base tier (not always tracked; always pick to be safe)
    "Iron Rune",
    "Glacial Rune",
    "Desert Rune",
    "Storm Rune",
    "Body Rune",
    "Mind Rune",
    "Rebirth Rune",
    "Inspiration Rune",
    "Stone Rune",
    "Vision Rune",
    "Robust Rune",
    "Adept Rune",
    "Resolve Rune",
    "Ward Rune",
    "Charging Rune",
]


# Tablet types that get Normal/Magic/Rare pick-all rules.
# Verified against NeverSink's live PoE2 filter (FilterBlade data): exactly
# these 7 drop. poe2db also lists "Expedition Tablet" but it's datamined
# unreleased content — do NOT add it until it appears in NeverSink/ninja.
TABLET_TYPES = [
    "Overseer Tablet",
    "Abyss Tablet",
    "Breach Tablet",
    "Ritual Tablet",
    "Irradiated Tablet",
    "Temple Tablet",
    "Delirium Tablet",
]

# Unique tablets picked by name: (tablet type, unique name).
TABLET_UNIQUES = [
    ("Irradiated Tablet", "Visions of Paradise"),
    ("Irradiated Tablet", "The Grand Project"),
    ("Irradiated Tablet", "Mastered Domain"),
    ("Abyss Tablet",      "Unforeseen Consequences"),
    ("Ritual Tablet",     "Freedom of Faith"),
    ("Breach Tablet",     "Wraeclast Besieged"),
    ("Overseer Tablet",   "Cruel Hegemony"),
    ("Overseer Tablet",   "Season of the Hunt"),
    ("Delirium Tablet",   "Clear Skies"),
]

# Splinter types — always picked.
SPLINTERS = [
    "Breach Splinter",
    "Simulacrum Splinter",
]

# Breach wombgift types — always picked.
WOMBGIFTS = [
    "Banded Wombgift",
    "Lavish Wombgift",
    "Ornate Wombgift",
    "Signet Wombgift",
]

# Special always-pick items: map-like keys and standalone valuables
# (stash, never use in rituals).
SPECIAL_ITEMS = [
    "An Audience with the King",
    "Expedition Logbook",
    "Kulemak's Invitation",
]


# Exotic bases — drop-only special bases that sell as bases at any rarity
# (breach rings, dusk/gloam jewellery, Runic Fork...). Extracted verbatim
# from NeverSink's PoE2 filter ($type->exoticbases), 2026-07-05.
EXOTIC_BASES = [
    "Aberrant Sledge", "Absent Amulet", "Abyssal Signet", "Ancient Gauntlets",
    "Ancient Leggings", "Ancient Mail", "Ancient Visor", "Biostatic Ring",
    "Breach Ring", "Corona Amulet", "Distorted Amulet",
    "Dusk Amulet", "Dusk Ring", "Forking Belt", "Glacial Fortress",
    "Gloam Amulet", "Gloam Ring", "Grasping Mail", "Grasping Ring",
    "Heartwood Shortbow", "Invoking Belt", "Kinetic Ring", "Lament Amulet",
    "Mnemonic Ring", "Oneiric Ring", "Ornate Ringmail", "Pearlescent Amulet",
    "Penumbra Amulet", "Penumbra Ring", "Perching Staff", "Portent Amulet",
    "Primal Markings", "Refined Breach Ring", "Reflecting Staff", "Runic Fork",
    "Sacrificial Regalia", "Sinew Belt", "Stalking Belt", "Tenebrous Amulet",
    "Tenebrous Crown", "Tenebrous Ring", "Twisted Amulet",
    "Twisted Wand", "Two-Stone Ring", "Venerable Defender", "Veridical Chain",
    "Vitalic Ring", "Warding Quarterstaff",
]


# Fallback waystone rules used when poe.ninja returns no waystone rows.
WAYSTONE_FALLBACK_RULES = [
    '[Category] == "Waystone" && [Rarity] == "Normal" && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Magic"  && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Rare"   && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
]

