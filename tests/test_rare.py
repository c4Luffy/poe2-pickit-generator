"""Rare stat-menu integrity: every id must be a real bot stat id, no dupes."""

from exilebot_pickit.data.bot_stat_ids import BOT_STAT_IDS
from exilebot_pickit.data import rare


def test_every_stat_id_is_valid_in_bot_modslist():
    bad = {name: sid
           for section in rare.STAT_MENU.values()
           for name, sid in section.items()
           if sid not in BOT_STAT_IDS}
    assert not bad, f"stat ids not in bot ModsList: {bad}"


def test_menu_has_all_sections():
    assert set(rare.STAT_MENU) == {
        "Defensive: Life / Mana / ES",
        "Defensive: Armour / Evasion / Block",
        "Resistances",
        "Utility",
        "Caster",
        "Attack / Weapon",
        "Skill Gem Levels",
    }


def test_no_duplicate_ids_within_a_section():
    for title, section in rare.STAT_MENU.items():
        ids = list(section.values())
        assert len(ids) == len(set(ids)), f"duplicate id in section {title!r}"


def test_all_skill_gem_level_is_excluded():
    # desecration/unique-only mod — must never be offered as a normal rare roll
    assert "all_skill_gem_level_+" not in rare.all_stat_ids()


def test_not_available_documents_the_unmapped_mods():
    assert rare.NOT_AVAILABLE and all(v for v in rare.NOT_AVAILABLE.values())
