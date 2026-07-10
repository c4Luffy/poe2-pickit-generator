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

RARE_GEAR = {
    # Boots — 3 elemental resistances + movement speed + flat ES, all weighted
    # in one WeightedSum (MS rolls in fixed steps 10/15/20/25/30/35, max 35).
    # (ES only rolls on the ES/hybrid base; it scores 0 on the others, harmless.)
    "Boots": {
        "bases": ["Tasalian Greaves", "Drakeskin Boots", "Sekhema Sandals"],
        "weights": {
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_movement_velocity_+%": 2.86,           # T1 max 35
            "local_energy_shield": 1.67,                 # T1 max 60 (ES base)
        },
        "threshold": "240",
        "item_tier": "3",
    },

    # --- Armour: Life + 3 elemental resistances (universal defensive draft) ---
    # Same archetype across body/helmet/gloves; only the life weight differs
    # (life's max-roll shrinks on smaller slots, so its weight = 100/max-roll
    # grows). Auto-drafted from live CoE max-rolls — tune thresholds as needed.
    "Body Armours": {
        "bases": ["Soldier Cuirass", "Slipstrike Vest", "Vile Robe"],
        "weights": {
            "base_maximum_life": 0.47,                   # T1 max 214
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
        },
        "threshold": "260",
        "item_tier": "3",
    },
    "Helmets": {
        "bases": ["Imperial Greathelm", "Freebooter Cap", "Ancestral Tiara"],
        "weights": {
            "base_maximum_life": 0.57,                   # T1 max 174
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
        },
        "threshold": "250",
        "item_tier": "3",
    },
    "Gloves": {
        "bases": ["Massive Mitts", "Polished Bracers", "Sirenscale Gloves"],
        "weights": {
            "base_maximum_life": 0.67,                   # T1 max 149
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
        },
        "threshold": "250",
        "item_tier": "3",
    },

    # --- Accessories: Life + 3 res + the slot's signature stat ---
    "Amulets": {
        "bases": ["Solar Amulet", "Gold Amulet"],
        "weights": {
            "base_maximum_life": 0.67,                   # T1 max 149
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_spirit_from_equipment": 2.00,          # T1 max 50
        },
        "threshold": "260",
        "item_tier": "3",
    },
    "Rings": {
        "bases": ["Gold Ring"],
        "weights": {
            "base_maximum_life": 0.84,                   # T1 max 119
            "base_fire_damage_resistance_%": 2.22,       # T1 max 45
            "base_cold_damage_resistance_%": 2.22,       # T1 max 45
            "base_lightning_damage_resistance_%": 2.22,  # T1 max 45
            "base_item_found_rarity_+%": 5.26,           # T1 max 19
        },
        "threshold": "240",
        "item_tier": "3",
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
