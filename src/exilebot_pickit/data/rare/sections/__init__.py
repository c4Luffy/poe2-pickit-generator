"""Rare stat menu, aggregated by section.

Each section lives in its own file; this module stitches them into one
ordered ``STAT_MENU`` (section title -> {display name: bot stat id}).
Every id is verified against the bot's ModsList — see tests/test_rare.py.
"""

from .defensive import LIFE_MANA_ES, ARMOUR_EVASION_BLOCK
from .resistances import RESISTANCES
from .utility import UTILITY
from .caster import CASTER
from .attack import ATTACK
from .skill_gems import SKILL_GEMS

# Ordered catalog — insertion order is the display order.
STAT_MENU = {
    "Defensive: Life / Mana / ES":        LIFE_MANA_ES,
    "Defensive: Armour / Evasion / Block": ARMOUR_EVASION_BLOCK,
    "Resistances":                        RESISTANCES,
    "Utility":                            UTILITY,
    "Caster":                             CASTER,
    "Attack / Weapon":                    ATTACK,
    "Skill Gem Levels":                   SKILL_GEMS,
}
