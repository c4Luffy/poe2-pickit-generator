"""Defensive rare-gear stats: Life / Mana / Energy Shield and mitigation.

Each entry maps a human-readable stat name to its verified bot stat id
(from ModsList). LOCAL vs GLOBAL matters: the "local_" id is used on the
item that natively has the stat (an armour piece); on jewellery the same
stat is global (no "local_" prefix).
"""

# Life / Mana / Energy Shield
LIFE_MANA_ES = {
    "Maximum Life (flat)":        "base_maximum_life",
    "Maximum Life %":             "maximum_life_+%",
    "Maximum Mana (flat)":        "base_maximum_mana",
    "Maximum Mana %":             "maximum_mana_+%",
    "Maximum ES (flat, local)":   "local_energy_shield",
    "Maximum ES (flat, global)":  "base_maximum_energy_shield",
    "Increased ES % (local)":     "local_energy_shield_+%",
    "Maximum ES % (global)":      "maximum_energy_shield_+%",
}

# Armour / Evasion / Block (incl. the three hybrid-defence bases)
ARMOUR_EVASION_BLOCK = {
    "Armour % (local)":           "local_physical_damage_reduction_rating_+%",
    "Evasion % (local)":          "local_evasion_rating_+%",
    "Evasion % (global)":         "evasion_rating_+%",
    "Armour + ES % (hybrid)":     "local_armour_and_energy_shield_+%",
    "Evasion + ES % (hybrid)":    "local_evasion_and_energy_shield_+%",
    "Armour + Evasion % (hybrid)": "local_armour_and_evasion_+%",
    "Block Chance":               "additional_block_%",
}
