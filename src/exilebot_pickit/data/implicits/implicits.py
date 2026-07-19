"""Base type -> its implicit modifier, in short readable form.

Generated from the live GGPK dump (repoe-fork base_items + mods) — the same
source tools/check_game_data.py already diffs against, so this cannot drift
from a wiki. There is no published stat-translation file, so each stat id is
rendered as "<roll> <short label>"; the wording is ours, the numbers and the
stat itself come straight from the game data.

Only bases this app actually ships appear here (52 of them have an
implicit at all). Display-only stats are omitted — they aren't a number the
player reads off the item.
"""
from __future__ import annotations

BASE_IMPLICITS: dict = {
    'Amber Amulet': '+10-15 Strength',
    'Amethyst Ring': '+7-13% Chaos Resistance',
    'Austere Garb': '+10-15% reduced Ailment duration on you',
    'Biostatic Ring': '+1% Maximum all resistances',
    'Corsair Coat': '+5% Movement Speed',
    'Dastard Armour': '+60-80 max Life',
    'Death Mantle': '+1% Maximum all elemental resistances',
    'Dusk Ring': '+1 Maximum prefixes allowed · -1 Maximum suffixes allowed',
    'Elegant Crossbow': '+20-30% Chance to pierce',
    'Emerald Ring': '+120-160 Accuracy',
    "Falconer's Jacket": '+5% Movement Speed',
    'Feathered Raiment': '+5-10% Damage removed from mana before life',
    'Fine Belt': '+10 Generate x charges for any flask per minute',
    'Flexed Crossbow': '+20-30 Projectile speed with crossbow skills',
    'Flying Spear': '+25-35% Projectile speed',
    'Fortified Hammer': '+40% Weapon daze chance',
    'Gloam Ring': '-1 Maximum prefixes allowed · +1 Maximum suffixes allowed',
    'Gold Amulet': '+12-20% Item Rarity',
    'Gold Ring': '+6-15% Item Rarity',
    'Grand Spear': '+25 Weapon range',
    'Guardian Bow': '+25-35% Attack chain chance',
    'Heavy Belt': '+20-30% Stun threshold',
    'Iron Ring': '+1 min Physical Damage · +4 max Physical Damage',
    'Ironwood Greathammer': '+30-50% Hit damage stun multiplier',
    'Jade Amulet': '+10-15 Dexterity',
    'Lapis Amulet': '+10-15 Intelligence',
    'Molten Hammer': '+50 Weapon implicit hidden base damage is fire',
    'Obliterator Bow': '-50% Projectile attack range',
    'Ornate Belt': '-10-15% Charm charges used',
    'Penetrating Quiver': '+100% Chance to pierce',
    'Penumbra Ring': '+2 Maximum prefixes allowed · -2 Maximum suffixes allowed',
    'Prismatic Ring': '+7-10% all Elemental Resistances',
    'Ruby Ring': '+20-30% Fire Resistance',
    'Sacramental Robe': '+20-25% Energy shield recharge rate',
    'Sapphire Ring': '+20-30% Cold Resistance',
    'Seastorm Mantle': '+8-14% Damage taken goes to life over 4 seconds',
    'Solar Amulet': '+10-15 Spirit from equipment',
    'Stalking Spear': '+15-25% Maim on hit',
    'Stellar Amulet': '+5-7 all Attributes',
    'Striking Quarterstaff': '+16 Weapon range',
    'Tawhoan Greatclub': '+1 Warcry empowers next x melee attacks',
    'Tenebrous Ring': '-2 Maximum prefixes allowed · +2 Maximum suffixes allowed',
    'Thane Mail': '+15-25% Self critical strike multiplier -',
    'Topaz Ring': '+20-30% Lightning Resistance',
    'Two-Stone Ring': '+12-16% Cold and lightning damage resistance',
    'Unset Ring': '+1 Item additional skill slots',
    'Utility Belt': '+20 Flask recovery amount to recover instantly',
    'Utzaal Cuirass': '+30-40% Stun threshold',
    'Visceral Quiver': '+20-30% Attack Crit Chance',
    'Volant Quiver': '+20-30% Arrow speed',
    'Warlord Cuirass': '+15-25 Armour applies to fire cold lightning damage',
    'Wyrmscale Coat': '+30-40% Ailment threshold',
}
