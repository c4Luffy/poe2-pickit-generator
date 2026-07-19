# ─────────────────────────────────────────────────────────────────────────────
#  Endgame base types — sourced from game data (baseitemtypes.json)
#  Format per entry: (item_name, socket_threshold)
#  socket_threshold=0 means no socket rule is generated for that category.
# ─────────────────────────────────────────────────────────────────────────────

_BASE_TYPES_BY_CATEGORY: dict = {
    # Curated best-in-slot exceptional bases (top 3 per attribute
    # subcategory, ranked by defence/DPS from Craft of Exile data,
    # 2026-07-06). Talismans and Bucklers removed entirely. Belts kept.
    "Body Armours": (("Soldier Cuirass", 3), ("Warlord Cuirass", 3), ("Utzaal Cuirass", 3), ("Slipstrike Vest", 3), ("Corsair Coat", 3), ("Wyrmscale Coat", 3), ("Vile Robe", 3), ("Feathered Raiment", 3), ("Sacramental Robe", 3), ("Death Mail", 3), ("Dastard Armour", 3), ("Thane Mail", 3), ("Wolfskin Mantle", 3), ("Seastorm Mantle", 3), ("Death Mantle", 3), ("Sleek Jacket", 3), ("Austere Garb", 3), ("Falconer's Jacket", 3),),
    "Helmets": (("Imperial Greathelm", 2), ("Paragon Greathelm", 2), ("Masked Greathelm", 2), ("Freebooter Cap", 2), ("Trapper Hood", 2), ("Desert Cap", 2), ("Ancestral Tiara", 2), ("Kamasan Tiara", 2), ("Sorcerous Tiara", 2), ("Gladiatorial Helm", 2), ("Champion Helm", 2), ("Cryptic Helm", 2), ("Cryptic Crown", 2), ("Divine Crown", 2), ("Saintly Crown", 2), ("Grinning Mask", 2), ("Soaring Mask", 2), ("Faridun Mask", 2), ("Grand Visage", 2),),
    "Gloves": (("Massive Mitts", 2), ("Vaal Mitts", 2), ("Ornate Mitts", 2), ("Polished Bracers", 2), ("Barbed Bracers", 2), ("Grand Bracers", 2), ("Sirenscale Gloves", 2), ("Vaal Gloves", 2), ("Opulent Gloves", 2), ("Blacksteel Gauntlets", 2), ("Cultist Gauntlets", 2), ("Commander Gauntlets", 2), ("Adherent Cuffs", 2), ("Gleaming Cuffs", 2), ("Ancient Cuffs", 2), ("Secured Wraps", 2), ("War Wraps", 2), ("Vaal Wraps", 2), ("Grand Manchettes", 2),),
    "Boots": (("Tasalian Greaves", 2), ("Vaal Greaves", 2), ("Ornate Greaves", 2), ("Drakeskin Boots", 2), ("Dragonscale Boots", 2), ("Cavalry Boots", 2), ("Sekhema Sandals", 2), ("Sandsworn Sandals", 2), ("Luxurious Slippers", 2), ("Blacksteel Sabatons", 2), ("Fortress Sabatons", 2), ("Noble Sabatons", 2), ("Cryptic Leggings", 2), ("Warlock Leggings", 2), ("Apostle Leggings", 2), ("Daggerfoot Shoes", 2), ("Quickslip Shoes", 2), ("Charmed Shoes", 2), ("Grand Cuisses", 2),),
    "Shields": (("Tawhoan Tower Shield", 2), ("Vaal Tower Shield", 2), ("Fortress Tower Shield", 2), ("Golden Targe", 2), ("Soaring Targe", 2), ("Baroque Targe", 2), ("Blacksteel Crest Shield", 2), ("Vaal Crest Shield", 2), ("Sekheman Crest Shield", 2),),
    "Foci": (("Tasalian Focus", 2), ("Sacred Focus", 2), ("Leyline Focus", 2),),
    "Quivers": (("Visceral Quiver", 0), ("Volant Quiver", 0), ("Penetrating Quiver", 0),),
    "One Hand Maces": (("Molten Hammer", 2), ("Marauding Mace", 2), ("Fortified Hammer", 2),),
    # Hallowed Sceptre removed 2026-07-12: it is still in the game's item table
    # but does NOT drop (owner searched in-game; NeverSink doesn't list it, nor
    # any sceptre above Wrath). The table keeps legacy + [DNT] dev definitions.
    # Shrine Sceptre was briefly removed 2026-07-19 as "unique-only" and PUT BACK
    # the same day: it has FOUR metadata entries — FourSceptre6a/6b/6c (ordinary
    # drops, one per Purity skill) plus FourSceptreUnique1. Only the last hosts a
    # unique. A name is unique-only when ALL of its paths are Unique-suffixed,
    # not when any one of them is; Shrine Sceptre drops normally and stays.
    "Sceptres": (("Wrath Sceptre", 2), ("Shrine Sceptre", 2), ("Omen Sceptre", 2),),
    "Spears": (("Flying Spear", 2), ("Grand Spear", 2), ("Stalking Spear", 2),),
    "Wands": (("Dueling Wand", 2), ("Acrid Wand", 2), ("Galvanic Wand", 2),),
    "Two Hand Maces": (("Massive Greathammer", 3), ("Ironwood Greathammer", 3), ("Tawhoan Greatclub", 3),),
    "Quarterstaves": (("Dreaming Quarterstaff", 3), ("Razor Quarterstaff", 3), ("Striking Quarterstaff", 3),),
    # Dark Staff removed 2026-07-12 — in the item table, doesn't drop (owner
    # searched in-game). Permafrost Staff and Reflecting Staff removed
    # 2026-07-19: their metadata is FourStaffUnique1/Unique3 — unique-only bases
    # that exist to host The Whispering Ice and Atziri's Rule (an Atziri temple
    # drop). A white one never drops, so the rules here could never fire and the
    # Exceptional-tab toggles did nothing. Reflecting Staff stays in
    # EXOTIC_BASES, where an ungated rule catches the unique itself.
    "Staves": (("Ravenous Staff", 3),),
    "Bows": (("Obliterator Bow", 3), ("Warmonger Bow", 3), ("Guardian Bow", 3),),
    "Crossbows": (("Desolate Crossbow", 3), ("Flexed Crossbow", 3), ("Elegant Crossbow", 3),),
    "Belts": (("Fine Belt", 0), ("Heavy Belt", 0), ("Utility Belt", 0), ("Ornate Belt", 0),),
}

# NOTE on Runeforged / Runemastered variants: these are NOT droppable bases —
# they are created at the anvil (a crafting mechanic) from dropped items, so
# they never appear as ground loot and pickup rules for them are inert.
# A 63-entry _RUNEFORGED_BASES supplement used to live here; removed 2026-07
# per the project owner. poe.ninja pricing uniques on Runemastered bases only
# proves they are traded (player-crafted), not that they drop.

