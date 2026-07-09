"""Caster rare-gear stats: spell damage, cast speed, spell crit, spell elements.

Crit here is the SPELL variant (spell_critical_strike_*), which is what
Foci / Wands / Staves use — distinct from the attack crit ids in attack.py.
"""

CASTER = {
    "Spell Damage %":          "spell_damage_+%",
    "Cast Speed %":            "base_cast_speed_+%",
    "Spell Crit Chance %":     "spell_critical_strike_chance_+%",
    "Spell Crit Multi":        "base_spell_critical_strike_multiplier_+",
    "Fire Damage %":           "fire_damage_+%",
    "Cold Damage %":           "cold_damage_+%",
    "Lightning Damage %":      "lightning_damage_+%",
    "Chaos Damage %":          "chaos_damage_+%",
    "Spell Fire Damage %":     "spell_fire_damage_+%",
    "Spell Cold Damage %":     "spell_cold_damage_+%",
    "Spell Lightning Damage %": "base_spell_lightning_damage_+%",
}
