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

# Runes not tracked by poe.ninja — always pick up regardless of threshold
ALWAYS_PICK_RUNES = [
    # Emergent runes (not tracked by poe.ninja)
    "Emergent Vigour",
    "Emergent Possibility",
    "Emergent Protection",
    "Emergent Instinct",
    # Standard runes (not always tracked; always pick to be safe)
    "Iron Rune",
    "Glacial Rune",
    "Arcane Rune",
    "Dire Rune",
    "Honed Rune",
    "Jagged Rune",
    "Phrecia Rune",
    "Skullbreaker Rune",
    "Destined Rune",
]


# Tablet types that get Normal/Magic/Rare pick-all rules.
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
    "Revelatory Wombgift",
    "Signet Wombgift",
]

# Special always-pick map-like items (stash, never use in rituals).
SPECIAL_ITEMS = [
    "An Audience with the King",
    "Expedition Logbook",
]


# Fallback waystone rules used when poe.ninja returns no waystone rows.
WAYSTONE_FALLBACK_RULES = [
    '[Category] == "Waystone" && [Rarity] == "Normal" && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Magic"  && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Rare"   && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
]

