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


def test_value_ladder_fires_on_live_value_only():
    # Divine (320 ex = the file's own Divine rate) is mythic purple; Chaos at
    # 2.5 ex is "useful" - readable, but no beam. First matching block wins,
    # so the expensive tier must be emitted first.
    txt = _flt()
    divine_block = txt[txt.index('"Divine Orb"'):txt.index('"Chaos Orb"')]
    assert "PlayEffect Purple" in divine_block
    ci = txt.index('"Chaos Orb"')
    chaos_block = txt[ci:txt.index("\nShow", ci)]   # just Chaos's own block
    assert "PlayEffect" not in chaos_block
    assert txt.index('"Divine Orb"') < txt.index('"Chaos Orb"')


def test_always_jackpot_names_scream_even_without_a_price_comment():
    # Always-pick rules are written bare when poe.ninja omits the item — a
    # dropped Mirror must NEVER wear the quiet label just because the price
    # feed had no line for it.
    ipd = ['[Type] == "Mirror of Kalandra" # [StashItem] == "true"',
           '[Type] == "Chaos Orb" # [StashItem] == "true"']
    txt = "\n".join(gen.build_loot_filter(ipd))
    mirror = txt[txt.index('"Mirror of Kalandra"'):txt.index('"Chaos Orb"')]
    assert "PlayEffect Purple" in mirror
    assert "PlayEffect Purple" not in txt[txt.index('"Chaos Orb"'):]


def test_jackpot_threshold_is_honored_exactly():
    # No Divine header in this minimal file -> default 500-ex Divine: the
    # jackpot band starts at exactly 50 ex (red); 49.99 falls to "high"
    # (orange). Both beam, but with different colors.
    at = f'[Type] == "At Floor" # [StashItem] == "true" // ExValue = {JACKPOT_EXALT:.2f}'
    below = f'[Type] == "Below" # [StashItem] == "true" // ExValue = {JACKPOT_EXALT - 0.01:.2f}'
    txt = "\n".join(gen.build_loot_filter([at, below]))
    assert txt.index('"At Floor"') < txt.index('"Below"')
    assert "PlayEffect Red" in txt[: txt.index('"Below"')]
    assert "PlayEffect Red" not in txt[txt.index('"Below"'):]
    assert "PlayEffect Orange" in txt[txt.index('"Below"'):]


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
        assert "SetTextColor 79 0 122 255" in txt      # mythic Divine kept
        assert "PlayEffect Purple" in txt


def test_conditions_come_before_style_lines_inside_a_block():
    # NeverSink ordering: conditions first, then appearance — keep it that way
    # so the filter reads like every other community filter.
    txt = _flt()
    block = txt[txt.index("Rarity = Unique"):]
    assert block.index("Rarity = Unique") < block.index("BaseType ==") < \
        block.index("SetFontSize")


# ── value ladder adapts to the live Divine rate ──────────────────────────────

def test_value_tiers_track_the_divine_rate():
    from exilebot_pickit.generators.filter_classification import value_kind
    # Same 60-ex orb, three economies: its tier moves as Divine moves.
    assert value_kind(60, 450) == "jackpot"   # 60 >= 45 (10% of 450), < 450
    assert value_kind(60, 800) == "high"       # jackpot floor now 80; 60 is High
    assert value_kind(60, 55) == "mythic"      # Divine crashed to 55; 60 >= 55
    # Divine itself is always mythic, whatever the rate.
    for rate in (80, 450, 2000):
        assert value_kind(rate, rate) == "mythic"


def test_cheap_divine_never_makes_a_modest_orb_jackpot():
    # The clamp: when Divine is cheap, 10% of it dips under the 10-ex High
    # floor. A 9-ex orb must stay High/Useful, never wear the red jackpot look.
    from exilebot_pickit.generators.filter_classification import (
        jackpot_threshold, value_kind,
    )
    assert jackpot_threshold(80) == 10.0        # not 8 — clamped to the High floor
    assert value_kind(9, 80) == "useful"        # 9 < 10 High floor
    assert value_kind(12, 80) == "jackpot"      # 12 >= 10 clamped floor, < 80
    # ladder stays strictly ordered at any rate
    for rate in (40, 80, 150, 450, 3000):
        t = jackpot_threshold(rate)
        assert 10.0 <= t <= rate, rate
