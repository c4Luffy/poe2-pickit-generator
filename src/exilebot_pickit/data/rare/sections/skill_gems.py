"""Skill-gem-level rare-gear stats.

Only the four normal craftable "+# to Level of all <type> Skills" rolls.
"+# to Level of all Skills" (all_skill_gem_level_+) is intentionally excluded:
it comes only from desecration / unique helmets, never a normal rare roll.
"""

SKILL_GEMS = {
    "+Spell gems":      "spell_skill_gem_level_+",
    "+Minion gems":     "minion_skill_gem_level_+",
    "+Melee gems":      "melee_skill_gem_level_+",
    "+Projectile gems": "projectile_skill_gem_level_+",
}
