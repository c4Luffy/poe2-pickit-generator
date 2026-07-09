"""Rare-gear data package.

Public surface for the (in-progress) Magic & Rare "Rare gear by slot" feature.
For now it exposes the verified stat menu, grouped by section, that future
per-class WeightedSum rules will be built from. No rules are emitted yet.
"""

from .sections import STAT_MENU

# Mods that appear in-game but have NO clean single bot stat id, so they must
# never be written into a rule (the bot would silently ignore the rule).
NOT_AVAILABLE = {
    "#% increased Armour (jewellery)":
        "only an aggregate id (combined_armour_+%) exists",
    "#% increased Critical Damage Bonus (jewellery, attack)":
        "no plain global critical_strike_multiplier_+% id",
    "#% Damage Recouped as Life/Mana":
        "dropped by owner — not needed",
}


def stat_menu() -> dict:
    """The full stat menu: {section title: {display name: bot stat id}}."""
    return STAT_MENU


def all_stat_ids() -> set:
    """Flat set of every bot stat id in the menu (for validation/tests)."""
    return {sid for section in STAT_MENU.values() for sid in section.values()}
