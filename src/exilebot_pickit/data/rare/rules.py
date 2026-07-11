"""Rare-gear WeightedSum rules, per slot.

Each slot spec carries:
  - ``bases``    : the craft bases to match (one rule line per base, Rare only).
  - ``weights``  : bot stat id -> weight, where weight = 100 / the stat's live
                   T1 max-roll from Craft of Exile (normalisation, so every
                   stat contributes ~100 points at a perfect roll).
  - ``threshold``: the WeightedSum cutoff (strictness dial).
  - ``item_tier``: minimum [ItemTier] gate.

Every stat id is verified in the bot's ModsList; every base is a real craft
base (see generator._CRAFT_BEST_BASES). Nothing here is guessed — the comments
record the live max-roll each weight was derived from.
"""

# Human labels for the recipe view in the Magic & Rare tab.
STAT_LABELS = {
    "base_maximum_life": "maximum Life",
    "minion_skill_gem_level_+": "+ Minion Skill levels",
    "melee_skill_gem_level_+": "+ Melee Skill levels",
    "attack_speed_+%": "Attack Speed %",
    "base_critical_strike_multiplier_+": "Crit Damage Bonus (flat)",
    "base_item_found_rarity_+%": "Rarity of Items Found %",
    "critical_strike_chance_+%": "Global Crit Chance %",
    "base_spirit_from_equipment": "flat Spirit",
    "base_fire_damage_resistance_%": "Fire res %",
    "base_cold_damage_resistance_%": "Cold res %",
    "base_lightning_damage_resistance_%": "Lightning res %",
    "base_chaos_damage_resistance_%": "Chaos res %",
    "base_movement_velocity_+%": "Movement Speed %",
    "local_energy_shield": "flat Energy Shield",
    "local_energy_shield_+%": "increased Energy Shield %",
}

RARE_GEAR = {
    # Body Armour — owner-approved 2026-07-12. Recipe designed from the live
    # poe.ninja Runes of Aldur ladder (124k chars: ~44% attack builds -> Life+
    # res; ~13% Spirit Walker & minion users -> flat Spirit, a body/amulet-
    # exclusive chase stat; ~18% casters -> ES). T1 max-rolls from the game's
    # own mod database, 2026-07-12: Life 214 (body-exclusive top tier), Spirit
    # 61, ele res 45, chaos res 27, flat ES 96, %ES 110 (body-exclusive tier).
    # Threshold 250 ~= 2.5 perfect stats' worth. A bare T1-%ES body scores
    # under it on purpose — the Fracture %ES>=101 rule already catches those.
    "Body Armour": {
        "bases": ["Warlord Cuirass", "Corsair Coat", "Feathered Raiment"],
        "weights": {
            "base_maximum_life": 0.47,                   # T1 max 214
            "base_spirit_from_equipment": 1.64,          # T1 max 61
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 0.91,              # T1 max 110
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Helmet — owner-approved 2026-07-12. Helmet-specific premiums on top of
    # the Life+res backbone: +2 Minion Skills is a helmet-exclusive suffix
    # (minion classes ~17% of the poe.ninja ladder), Rarity feeds MF farmers,
    # global crit feeds crit builds. T1 max-rolls from the game's mod database
    # 2026-07-12: Life 174 (helmet cap, IncreasedLife10), minion skills 2,
    # rarity 19, global crit 34, ele res 45, chaos 27, flat ES 96.
    "Helmet": {
        "bases": ["Imperial Greathelm", "Freebooter Cap", "Ancestral Tiara"],
        "weights": {
            "base_maximum_life": 0.57,                   # T1 max 174
            "minion_skill_gem_level_+": 50.0,            # T1 max +2
            "base_item_found_rarity_+%": 5.26,           # T1 max 19
            "critical_strike_chance_+%": 2.94,           # T1 max 34
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 2.38,              # T1 max 42 (audit add)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Gloves — owner-approved 2026-07-12. The attack slot: attack speed +
    # melee skill levels + crit multi on the Life/res backbone (attack builds
    # are ~44% of the poe.ninja ladder; Martial Artist alone 20%). Added
    # attack damage deliberately EXCLUDED — the Fracture tab's OR-rule already
    # hunts those gloves (magic + rare); scoring it here would double-cover.
    # T1 max-rolls from the game's mod database 2026-07-12: attack speed 16,
    # melee skills 2, crit multi 34, life 149 (gloves cap), ele res 45,
    # chaos 27, flat ES 96.
    "Gloves": {
        "bases": ["Massive Mitts", "Polished Bracers", "Sirenscale Gloves"],
        "weights": {
            "attack_speed_+%": 6.25,                     # T1 max 16
            "melee_skill_gem_level_+": 50.0,             # T1 max +2
            "base_critical_strike_multiplier_+": 2.94,   # T1 max 34
            "base_maximum_life": 0.67,                   # T1 max 149
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 2.38,              # T1 max 42 (audit add)
            "base_item_found_rarity_+%": 5.56,           # T1 max 18 (audit add)
        },
        "threshold": "250",
        "item_tier": "4",
    },
    # Boots — movement speed is the identity stat (fixed steps 10..35, so
    # 30/35 dominate the score) on the Life/res backbone, plus Rarity for the
    # MF market (owner call 2026-07-12: rarity boots sell). Audited vs the
    # game's mod database 2026-07-12: added missing Life (boots T1 120-149)
    # and chaos res, fixed the flat-ES weight (real T1 is 91-96, the old
    # "max 60" over-scored ES boots by ~60%), aligned ItemTier to 4.
    "Boots": {
        "bases": ["Tasalian Greaves", "Drakeskin Boots", "Sekhema Sandals"],
        "weights": {
            "base_movement_velocity_+%": 2.86,           # T1 max 35
            "base_maximum_life": 0.67,                   # T1 max 149 (boots cap)
            "base_item_found_rarity_+%": 5.56,           # T1 max 18 (MF market)
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_chaos_damage_resistance_%": 3.7,       # T1 max 27 (premium)
            "local_energy_shield": 1.04,                 # T1 max 96 (ES bases)
            "local_energy_shield_+%": 2.38,              # T1 max 42 (audit add)
        },
        "threshold": "240",
        "item_tier": "4",
    },
}


def _slot_lines(spec: dict) -> list:
    """One validated rule line per base for a slot spec.

    Post-# order: hard gates (required minimums) first, then the WeightedSum
    over the remaining stats, then the pickup action."""
    terms = ",".join(f"{sid}:{w}" for sid, w in spec["weights"].items())
    gates = "".join(f'[{sid}] >= "{v}" && '
                    for sid, v in spec.get("gates", {}).items())
    return [
        f'[Type] == "{base}" && [ItemTier] >= "{spec["item_tier"]}" '
        f'&& [Rarity] == "Rare" # {gates}[WeightedSum({terms})] >= '
        f'"{spec["threshold"]}" && [StashItem] == "true"'
        for base in spec["bases"]
    ]


def rare_gear_body(disabled=None) -> list:
    """Rule lines for all enabled rare-gear slots (no major header — this is
    appended into the Magic & Rare section). Empty when everything is off."""
    disabled = set(disabled or ())
    body: list = []
    for slot, spec in RARE_GEAR.items():
        if slot in disabled:
            continue
        body.append(f"// -- Rare {slot} ({len(spec['bases'])} bases, "
                    f"WeightedSum >= {spec['threshold']}) "
                    + "-" * 20)
        body.extend(_slot_lines(spec))
        body.append("")
    return body


def rare_gear_example_lines(slot: str) -> list:
    """The exact emitted lines for one slot, for tab display (== output)."""
    spec = RARE_GEAR.get(slot)
    return _slot_lines(spec) if spec else []


def rare_gear_slots() -> list:
    """Slot names that currently have wired rules (for the tab)."""
    return list(RARE_GEAR)
