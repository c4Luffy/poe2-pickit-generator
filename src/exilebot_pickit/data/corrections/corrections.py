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
# (breach rings, dusk/gloam jewellery...). Extracted from NeverSink's PoE2
# filter ($type->exoticbases) 2026-07-05, then pruned of unique-host bases.
#
# NeverSink's list mixes two things: bases that genuinely drop as white/rare
# (kept below) and bases that exist ONLY as a specific unique's host, which
# never drop plain — their rule could never fire. 17 of the latter were
# removed: Reflecting Staff (Atziri's Rule) and Perching Staff (The Raven's
# Flock) on 2026-07-20, then 15 more on 2026-07-21 after the owner confirmed
# on the trade site that each shows only as its unique, never as a base
# (Runic Fork→Runeseeker's Call, Ornate Ringmail→Loreweave,
# Glacial Fortress→Nightfall, the three Decree armours, etc.). See
# [[unique-host-base-droppability]] — no data source proves this, only the
# owner's trade/in-game check. The uniques are still picked up via poe.ninja.
EXOTIC_BASES = [
    "Absent Amulet", "Abyssal Signet", "Biostatic Ring",
    "Breach Ring", "Corona Amulet", "Distorted Amulet",
    "Dusk Amulet", "Dusk Ring", "Forking Belt",
    "Gloam Amulet", "Gloam Ring", "Grasping Mail", "Grasping Ring",
    "Invoking Belt", "Kinetic Ring", "Lament Amulet",
    "Mnemonic Ring", "Oneiric Ring", "Pearlescent Amulet",
    "Penumbra Amulet", "Penumbra Ring", "Portent Amulet",
    "Refined Breach Ring",
    "Sacrificial Regalia", "Sinew Belt", "Stalking Belt", "Tenebrous Amulet",
    "Tenebrous Ring", "Twisted Amulet",
    "Two-Stone Ring",
    "Vitalic Ring",
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
    "Grasping Mail": "Body Armours",
    "Sacrificial Regalia": "Body Armours",
}

# Section order for the above. Weapon and other-armour slots dropped out when
# the unique-host bases were pruned (see the EXOTIC_BASES note) — every
# remaining exotic base is jewellery, a belt, or a body armour.
EXOTIC_SLOT_ORDER = [
    "Amulets",
    "Rings",
    "Belts",
    "Body Armours",
]


# The Keys view: every boss key, vault key and invitation gathered into one
# place, wherever poe.ninja happens to file it. Most of these are ordinary
# priced items living in "Fragments" (a couple in "Omens"), so the Keys entry
# is a LENS over the real categories, not a category of its own — a switch
# flipped here is the same switch as in Fragments, not a second copy.
#
# Membership is checked against what poe.ninja prices today, per
# poe-ninja-is-primary-source: the game files also list Primary/Secondary/
# Tertiary Calamity Fragment, which poe.ninja does not price at all, so they
# are treated as gone and left out. Sections come from the game's own item
# class (PinnacleKeyStackable / VaultKey / MapFragment).
#
# "An Audience with the King" and "Kulemak's Invitation" also appear in
# SPECIAL_ITEMS above — intentional, not drift. SPECIAL_ITEMS drives force-pick
# behavior (they're always kept, [IgnoreRitual] on the Invitation); this dict
# only drives which Keys-lens heading each name is shown under. Both need the
# same two names; audited 2026-07-21, do not "deduplicate" one out.
KEY_ITEM_SECTIONS = {
    # Crisis Fragments — the three that combine for one pinnacle key
    "Ancient Crisis Fragment": "Crisis Fragments",
    "Faded Crisis Fragment": "Crisis Fragments",
    "Weathered Crisis Fragment": "Crisis Fragments",
    # Origin — the three that combine for another
    "Origin Core": "Origin",
    "Origin Spark": "Origin",
    "Origin Cradle": "Origin",
    # Reliquary Keys
    "The Arbiter's Reliquary Key": "Reliquary Keys",
    "The Trialmaster's Reliquary Key": "Reliquary Keys",
    "Xesht's Reliquary Key": "Reliquary Keys",
    "Zarokh's Reliquary Key: Against the Darkness": "Reliquary Keys",
    "Olroth's Reliquary Key": "Reliquary Keys",
    "Tangmazu's Reliquary Key": "Reliquary Keys",
    "Azmeri Reliquary Key": "Reliquary Keys",
    "Ritualistic Reliquary Key": "Reliquary Keys",
    "Twilight Reliquary Key": "Reliquary Keys",
    # Boss Invitations
    "An Audience with the King": "Boss Invitations",
    "Kulemak's Invitation": "Boss Invitations",
    "Call of the Shadows": "Boss Invitations",
    "Raven's Reflection": "Boss Invitations",
    "Simulacrum": "Boss Invitations",
}

# Section order for the Keys view.
KEY_SECTION_ORDER = ["Crisis Fragments", "Origin", "Reliquary Keys", "Boss Invitations"]

# Fallback waystone rules used when poe.ninja returns no waystone rows.
WAYSTONE_FALLBACK_RULES = [
    '[Category] == "Waystone" && [Rarity] == "Normal" && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Magic"  && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
    '[Category] == "Waystone" && [Rarity] == "Rare"   && [WaystoneTier] >= "1" # [StashItem] == "true" && [IgnoreRitual] == "true"',
]

