"""Attack / weapon rare-gear stats: phys/ele damage, attack crit, added damage.

Crit here is the ATTACK variant (local + global), distinct from the spell
crit ids in caster.py. Added-damage ids are the "minimum added" rolls
(the bot pairs each with its maximum internally).
"""

ATTACK = {
    "Increased Attack Damage %":    "attack_damage_+%",
    "Increased Elemental Damage %": "elemental_damage_+%",
    "Phys Damage %":                "local_physical_damage_+%",
    "Attack Crit Chance % (local)": "local_critical_strike_chance_+%",
    "Attack Crit Multi (flat)":     "base_critical_strike_multiplier_+",
    "Global Crit Chance %":         "critical_strike_chance_+%",
    "Added Phys (flat)":            "local_minimum_added_physical_damage",
    "Added Fire (flat)":            "local_minimum_added_fire_damage",
    "Added Cold (flat)":            "local_minimum_added_cold_damage",
    "Added Lightning (flat)":       "local_minimum_added_lightning_damage",
    "Added Chaos (flat)":           "local_minimum_added_chaos_damage",
}
