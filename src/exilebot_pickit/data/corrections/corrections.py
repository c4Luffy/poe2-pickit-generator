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
# Emptied 2026-07-20. It held both Necrotic Catalysts on the grounds that
# "Exiled Bot's pickit validator rejects these base types" — but that is a claim
# about the BOT'S validator, not about whether the item drops, and it was costing
# a ~145 ex pickup every time one fell.
#
# Two things settled it. The shipped pickit already carries five names that same
# validator flags (the four Orbs of Sacrifice and Tethering Bands) and the bot
# loads the file perfectly well, so the warning is cosmetic rather than fatal.
# And the app already picks up Refined Sibilant Catalyst at ~2374 ex — the
# identical family and naming pattern. Both Necrotic Catalysts are released
# StackableCurrency at drop levels 30 and 50 with ordinary quality-currency
# descriptions.
ITEM_NAME_SKIP: set = set()

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
    # Raven's Reflection — the Delirium pinnacle key, dropped from Simulacrum
    # (owner, in-game, 2026-07-20). Added because it had NO rule at all: poe.ninja
    # prices it in no category, and almost every rule this app writes comes from a
    # price. An unpriced item only ever gets picked up if it is named here, which
    # is what this list is for. Metadata Currency/Delirium/DeliriumPinnacleKey,
    # class MapFragment, released — the same shape as Kulemak's Invitation.
    "Raven's Reflection",
]

# Special Items the bot MAY buy back from a Ritual altar — i.e. the ones whose
# rule must NOT carry [IgnoreRitual].
#
# An Audience with the King is the Ritual pinnacle fragment
# (MapFragments/CurrencyRitualBossFragment), so a Ritual reward window is a
# place you would actually want it. The flag is one-sided there: if the item
# appears in the window the bot walks past ~50ex, and if it only ever drops on
# the ground the flag does nothing at all — so it can only cost, never help.
# The other two keep the flag: Expedition Logbook is a genuine ground drop
# (drop_level 78), so declining to re-buy a copy with tribute is a real saving,
# and Kulemak's Invitation is Abyss content, where the flag never applies.
# Owner decision 2026-07-19.
RITUAL_BUYABLE = {"An Audience with the King"}


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



# Which gear slot each exotic base occupies, so the Economy tab can show them
# grouped instead of as one 48-row alphabetical run. Read from the game's own
# base_items data — the name does not give the slot away ("Veridical Chain" is
# an amulet, "Primal Markings" a body armour, "Runic Fork" a wand).
# EXOTIC_BASES self-updates from game_data.json, so a base added remotely that
# is missing here is shown under "Other" rather than dropped.
EXOTIC_BASE_SLOTS = {
    # Amulets
    "Absent Amulet": "Amulets",
    "Corona Amulet": "Amulets",
    "Distorted Amulet": "Amulets",
    "Dusk Amulet": "Amulets",
    "Gloam Amulet": "Amulets",
    "Lament Amulet": "Amulets",
    "Pearlescent Amulet": "Amulets",
    "Penumbra Amulet": "Amulets",
    "Portent Amulet": "Amulets",
    "Tenebrous Amulet": "Amulets",
    "Twisted Amulet": "Amulets",
    "Veridical Chain": "Amulets",
    # Rings
    "Abyssal Signet": "Rings",
    "Biostatic Ring": "Rings",
    "Breach Ring": "Rings",
    "Dusk Ring": "Rings",
    "Gloam Ring": "Rings",
    "Grasping Ring": "Rings",
    "Kinetic Ring": "Rings",
    "Mnemonic Ring": "Rings",
    "Oneiric Ring": "Rings",
    "Penumbra Ring": "Rings",
    "Refined Breach Ring": "Rings",
    "Tenebrous Ring": "Rings",
    "Two-Stone Ring": "Rings",
    "Vitalic Ring": "Rings",
    # Belts
    "Forking Belt": "Belts",
    "Invoking Belt": "Belts",
    "Sinew Belt": "Belts",
    "Stalking Belt": "Belts",
    # Body Armours
    "Ancient Mail": "Body Armours",
    "Grasping Mail": "Body Armours",
    "Ornate Ringmail": "Body Armours",
    "Primal Markings": "Body Armours",
    "Sacrificial Regalia": "Body Armours",
    # Helmets
    "Ancient Visor": "Helmets",
    "Tenebrous Crown": "Helmets",
    # Gloves
    "Ancient Gauntlets": "Gloves",
    # Boots
    "Ancient Leggings": "Boots",
    # Shields
    "Glacial Fortress": "Shields",
    "Venerable Defender": "Shields",
    # Wands
    "Runic Fork": "Wands",
    "Twisted Wand": "Wands",
    # Staves
    "Perching Staff": "Staves",
    "Reflecting Staff": "Staves",
    # Quarterstaves
    "Warding Quarterstaff": "Quarterstaves",
    # Bows
    "Heartwood Shortbow": "Bows",
    # Two Hand Maces
    "Aberrant Sledge": "Two Hand Maces",
}

# Section order for the above — gear people think of first, then weapons.
EXOTIC_SLOT_ORDER = [
    "Amulets",
    "Rings",
    "Belts",
    "Body Armours",
    "Helmets",
    "Gloves",
    "Boots",
    "Shields",
    "Wands",
    "Staves",
    "Quarterstaves",
    "Bows",
    "Two Hand Maces",
]

# Fallback waystone rules used when poe.ninja returns no waystone rows.
WAYSTONE_FALLBACK_RULES = [
    '[Category] == "Waystone" && [Rarity] == "Normal" && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Magic"  && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Rare"   && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
]

