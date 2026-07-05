# ─────────────────────────────────────────────────────────────────────────────
#  Endgame base types — sourced from game data (baseitemtypes.json)
#  Format per entry: (item_name, socket_threshold)
#  socket_threshold=0 means no socket rule is generated for that category.
# ─────────────────────────────────────────────────────────────────────────────

_BASE_TYPES_BY_CATEGORY: dict = {
    "Body Armours": (
        ("Tattered Robe", 3), ("Abyssal Cuirass", 3), ("Arcane Raiment", 3), ("Armoured Vest", 3),
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
        ("Cultist Crown", 2), ("Ancestral Tiara", 2), ("Archon Crown", 2), ("Armoured Cap", 2),
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
        ("Fine Bracers", 2), ("Spiral Wraps", 2), ("Adherent Cuffs", 2), ("Ancient Cuffs", 2), ("Adorned Gloves", 2),
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
        ("Braced Sabatons", 2), ("Apostle Leggings", 2), ("Ancient Leggings", 2), ("Blacksteel Sabatons", 2), ("Bladed Shoes", 2),
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
        ("Antler Focus", 2), ("Arrayed Focus", 2), ("Crystal Focus", 2), ("Cultist Focus", 2),
        ("Druidic Focus", 2), ("Engraved Focus", 2), ("Hallowed Focus", 2), ("Jingling Focus", 2),
        ("Leyline Focus", 2), ("Magus Focus", 2), ("Sacred Focus", 2), ("Staghorn Focus", 2),
        ("Tasalian Focus", 2), ("Tonal Focus", 2), ("Twig Focus", 2), ("Voodoo Focus", 2),
        ("Woven Focus", 2), ("Wreath Focus", 2),
    ),
    "Quivers": (
        ("Blunt Quiver", 0), ("Broadhead Quiver", 0), ("Fire Quiver", 0), ("Penetrating Quiver", 0),
        ("Primed Quiver", 0), ("Sacral Quiver", 0), ("Serrated Quiver", 0), ("Toxic Quiver", 0),
        ("Two-Point Quiver", 0), ("Visceral Quiver", 0), ("Volant Quiver", 0),
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
        ("Ashen Staff", 3), ("Chiming Staff", 3), ("Dark Staff", 3), ("Gelid Staff", 3),
        ("Paralysing Staff", 3), ("Permafrost Staff", 3), ("Pyrophyte Staff", 3),
        ("Ravenous Staff", 3), ("Reaping Staff", 3), ("Roaring Staff", 3),
        ("Sanctified Staff", 3), ("Voltaic Staff", 3),
    ),
    "Wands": (
        ("Acrid Wand", 2), ("Attuned Wand", 2), ("Bone Wand", 2), ("Dueling Wand", 2),
        ("Galvanic Wand", 2), ("Siphoning Wand", 2), ("Volatile Wand", 2), ("Withered Wand", 2),
    ),
    "Sceptres": (
        ("Hallowed Sceptre", 2), ("Omen Sceptre", 2), ("Rattling Sceptre", 2),
        ("Shrine Sceptre", 2), ("Stoic Sceptre", 2), ("Wrath Sceptre", 2),
    ),
    # Talismans — the Druid's signature weapon (class released in PoE2 0.4, Dec 2025).
    # Names sourced from the PoE2 base-item list; a wrong name yields only an inert rule.
    "Talismans": (
        ("Alpha Talisman", 2), ("Ashbark Talisman", 2), ("Changeling Talisman", 2),
        ("Cinderbark Talisman", 2), ("Condemned Talisman", 2), ("Cruel Talisman", 2),
        ("Familial Talisman", 2), ("Fang Talisman", 2), ("Frenzied Talisman", 2),
        ("Fungal Talisman", 2), ("Fury Talisman", 2), ("Howling Talisman", 2),
        ("Jade Talisman", 2), ("Lumbering Talisman", 2), ("Maji Talisman", 2),
        ("Nettle Talisman", 2), ("Primal Talisman", 2), ("Rabid Talisman", 2),
        ("Roaring Talisman", 2), ("Spiny Talisman", 2), ("Thunder Talisman", 2),
        ("Vicious Talisman", 2), ("Voltfang Talisman", 2), ("Wildwood Talisman", 2),
        ("Wingbeat Talisman", 2),
    ),
    "Belts":          (("Fine Belt", 0), ("Heavy Belt", 0), ("Utility Belt", 0), ("Ornate Belt", 0),),
    # Claws, Daggers, One/Two Hand Swords, One/Two Hand Axes and Flails exist
    # in the extracted game data (and on datamined wiki base tables) but are
    # NOT droppable in the current PoE2 release — they belong to unreleased
    # classes, so their base rules are omitted. RE-confirmed by the project
    # owner 2026-07-05 (Talon Claw / Cinquedea / Dark Blade / Dread Hatchet
    # were briefly added from a community pickit and removed again — that
    # pickit carried inert rules). Don't re-add from wiki tables or
    # kitchen-sink configs, which list every base in the game FILES whether
    # or not it drops.
}

# NOTE on Runeforged / Runemastered variants: these are NOT droppable bases —
# they are created at the anvil (a crafting mechanic) from dropped items, so
# they never appear as ground loot and pickup rules for them are inert.
# A 63-entry _RUNEFORGED_BASES supplement used to live here; removed 2026-07
# per the project owner. poe.ninja pricing uniques on Runemastered bases only
# proves they are traded (player-crafted), not that they drop.

