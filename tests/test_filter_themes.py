"""Tests for generators/filter_themes.py and the themed loot-filter output of
generator.build_loot_filter. The invariants: every theme styles every rule
kind with commands the PoE2 client actually parses, the jackpot tier fires
only on real live value, and no theme choice can ever strip the gold guard."""
import re

from exilebot_pickit import generator as gen
from exilebot_pickit.generators.filter_themes import (
    DEFAULT_THEME, JACKPOT_EXALT, THEME_CHOICES, THEMES, get_style,
)

# The full command vocabulary the PoE2 client accepts for appearance lines —
# anything outside this set would make the game reject the block.
_CMD_RE = re.compile(
    r"^(SetFontSize \d{2}"
    r"|Set(?:Text|Border|Background)Color \d{1,3} \d{1,3} \d{1,3}( \d{1,3})?"
    r"|PlayAlertSound \d{1,2} \d{1,3}"
    r"|PlayEffect (?:Red|Green|Blue|Brown|White|Yellow|Cyan|Grey|Orange|Pink|Purple)"
    r"|MinimapIcon [0-2] (?:Red|Green|Blue|Brown|White|Yellow|Cyan|Grey|Orange|Pink|Purple) "
    r"(?:Circle|Diamond|Hexagon|Square|Star|Triangle|Cross|Moon|Raindrop|Kite|Pentagon|UpsideDownHouse))$"
)

_KINDS = ("jackpot", "named", "unique", "chance", "gear", "waystone", "gold")


def test_every_theme_covers_every_kind_with_valid_commands():
    for theme_id, table in THEMES.items():
        for kind in _KINDS:
            lines = table.get(kind)
            assert lines, f"{theme_id}.{kind} has no style"
            for ln in lines:
                assert _CMD_RE.match(ln), f"{theme_id}.{kind}: bad command {ln!r}"


def test_theme_choices_match_the_table_and_lead_with_default():
    assert [k for k, _, _ in THEME_CHOICES] == list(THEMES)
    assert THEME_CHOICES[0][0] == DEFAULT_THEME


def test_no_sounds_anywhere():
    # Owner's call (2026-07-17): the filters never play sounds — the bot
    # doesn't listen and pings annoy. (Beams follow the owner's filter scheme.)
    for theme_id, table in THEMES.items():
        for kind in _KINDS:
            assert not any("PlayAlertSound" in ln for ln in table[kind]), \
                f"{theme_id}.{kind} plays a sound"


def test_get_style_falls_back_and_copies():
    assert get_style("bogus", "named") == get_style(DEFAULT_THEME, "named")
    assert get_style(DEFAULT_THEME, "bogus-kind") == []
    s = get_style(DEFAULT_THEME, "named")
    s.append("mutated")
    assert "mutated" not in get_style(DEFAULT_THEME, "named")


# ── build_loot_filter theming ────────────────────────────────────────────────

_IPD = [
    '[Type] == "Divine Orb" # [StashItem] == "true" // ExValue = 320.00',
    '[Type] == "Chaos Orb" # [StashItem] == "true" // ExValue = 2.50',
    '[Type] == "Stellar Amulet" && [Rarity] == "Normal" && [ItemLevel] >= "82" # [StashItem] == "true"',
    '[Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"',
    '[Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"',
]


def _flt(theme=None):
    return "\n".join(gen.build_loot_filter(_IPD, theme=theme))


def test_jackpot_tier_fires_on_live_value_only():
    # Styles follow the BaseType line, so a forward slice covers one block.
    txt = _flt()
    jackpot_block = txt[txt.index('"Divine Orb"'):txt.index('"Chaos Orb"')]
    assert "PlayEffect Red" in jackpot_block
    chaos_block = txt[txt.index('"Chaos Orb"'):txt.index('"Heavy Belt"')]
    assert "PlayEffect" not in chaos_block
    # jackpot blocks must come first: the game takes the FIRST matching block
    assert txt.index('"Divine Orb"') < txt.index('"Chaos Orb"')


def test_always_jackpot_names_scream_even_without_a_price_comment():
    # Always-pick rules are written bare when poe.ninja omits the item — a
    # dropped Mirror must NEVER wear the quiet label just because the price
    # feed had no line for it.
    ipd = ['[Type] == "Mirror of Kalandra" # [StashItem] == "true"',
           '[Type] == "Chaos Orb" # [StashItem] == "true"']
    txt = "\n".join(gen.build_loot_filter(ipd))
    mirror = txt[txt.index('"Mirror of Kalandra"'):txt.index('"Chaos Orb"')]
    assert "PlayEffect Red" in mirror
    assert "PlayEffect" not in txt[txt.index('"Chaos Orb"'):]


def test_jackpot_threshold_is_honored_exactly():
    at = f'[Type] == "At Floor" # [StashItem] == "true" // ExValue = {JACKPOT_EXALT:.2f}'
    below = f'[Type] == "Below" # [StashItem] == "true" // ExValue = {JACKPOT_EXALT - 0.01:.2f}'
    txt = "\n".join(gen.build_loot_filter([at, below]))
    assert txt.index('"At Floor"') < txt.index('"Below"')
    assert "PlayEffect Red" in txt[: txt.index('"Below"')]
    assert "PlayEffect" not in txt[txt.index('"Below"'):]


def test_normal_rarity_bases_get_the_chance_look():
    txt = _flt()
    stellar = txt[txt.index('"Stellar Amulet"'):txt.index('"Stellar Amulet"') + 300]
    assert "Rarity = Normal" in txt
    for ln in THEMES[DEFAULT_THEME]["chance"]:
        assert ln in stellar


def test_generated_filter_always_shows_gold():
    txt = _flt()
    assert 'BaseType == "Gold"' in txt
    assert txt.index('BaseType == "Gold"') < txt.index("# Hide everything else")


def test_waystone_block_is_styled():
    txt = _flt()
    ws = txt[txt.index('Class "Waystone"'):txt.index('Class "Waystone"') + 300]
    for ln in THEMES[DEFAULT_THEME]["waystone"]:
        assert ln in ws


def test_single_theme_and_stale_names_fall_back():
    # One theme by owner decision (2026-07-17); configs from the brief
    # multi-theme window may still carry retired names — never unstyled.
    assert list(THEMES) == [DEFAULT_THEME]
    for stale in ("minimal", "contrast", "colorblind", "does-not-exist"):
        txt = _flt(stale)
        assert "SetBackgroundColor 245 139 87" in txt   # classic named style
        assert "PlayEffect Red" in txt                  # classic jackpot kept


def test_conditions_come_before_style_lines_inside_a_block():
    # NeverSink ordering: conditions first, then appearance — keep it that way
    # so the filter reads like every other community filter.
    txt = _flt()
    block = txt[txt.index("Rarity = Unique"):]
    assert block.index("Rarity = Unique") < block.index("BaseType ==") < \
        block.index("SetFontSize")
