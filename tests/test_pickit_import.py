"""Tests for generators/pickit_import.py — the "any pickit → loot filter"
converter. The invariant under test everywhere: the filter shows everything
the pickit could take — equal or more, never less."""
from exilebot_pickit.generators.pickit_import import convert_pickit_text

SAMPLE = "\n".join([
    "// ExileBot pickit — hand-made",
    "",
    '[Type] == "Divine Orb" # [StashItem] == "true"',
    '[Type] == "Exalted Orb" && [Type] == "Chaos Orb" # [StashItem] == "true"',
    '[Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"',
    '[Type] == "Sacred Focus" && [Quality] >= "25" # [StashItem] == "true"',
    '[Type] == "Stellar Amulet" && [Sockets] > "1" # [StashItem] == "true"',
    '[Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"',
    '[Rarity] == "Rare" && [Sockets] >= "2" # [Salvage] == "true"',
    '// [Type] == "Disabled Orb" # [StashItem] == "true"',
])


def _joined(res):
    return "\n".join(res["filter_lines"])


def test_sample_converts_every_enabled_type_name():
    res = convert_pickit_text(SAMPLE)
    assert res["ok"]
    txt = _joined(res)
    for name in ("Divine Orb", "Exalted Orb", "Chaos Orb", "Heavy Belt",
                 "Sacred Focus", "Stellar Amulet"):
        assert f'"{name}"' in txt, f"{name} missing from the filter"
    assert '"Disabled Orb"' not in txt
    assert 'Class == "Waystones"' in txt
    r = res["report"]
    assert r["rules"] == 7
    assert r["converted"] == 7
    assert r["disabled"] == 2          # header comment + disabled rule
    assert r["untranslatable_total"] == 0


def test_unique_rarity_and_buckets():
    res = convert_pickit_text(SAMPLE)
    txt = _joined(res)
    # Headhunter's base is gated by Rarity = Unique, quality/socket rules keep
    # their thresholds ([Sockets] > "1" becomes >= 2).
    assert "Rarity = Unique" in txt
    assert "Quality >= 25" in txt
    assert "Sockets >= 2" in txt


def test_post_hash_conditions_never_narrow():
    # Quality sits AFTER the # (a keep-decision, not a pickup condition):
    # the base must be shown unconditionally, with no Quality gate.
    res = convert_pickit_text('[Type] == "Gemcutter\'s Prism" # [Quality] >= "15" && [StashItem] == "true"')
    txt = _joined(res)
    assert '"Gemcutter\'s Prism"' in txt
    assert "Quality" not in txt


def test_bot_only_checks_widen_but_still_show():
    res = convert_pickit_text('[Type] == "Sapphire Ring" && [ItemTier] >= "3" # [StashItem] == "true"')
    assert res["ok"]
    assert '"Sapphire Ring"' in _joined(res)
    assert res["report"]["widened"] == 1


def test_rule_without_action_is_still_included():
    res = convert_pickit_text('[Type] == "Mirror of Kalandra"')
    assert '"Mirror of Kalandra"' in _joined(res)
    assert res["report"]["assumed_pickup"] == 1


def test_hide_rest_applies_when_everything_translates():
    res = convert_pickit_text(SAMPLE, hide_rest=True)
    assert res["report"]["hide_applied"]
    txt = _joined(res)
    assert "\nHide" in txt
    # gold must survive any hide — bots pick it up regardless of the pickit
    assert 'BaseType == "Gold"' in txt
    assert txt.index('BaseType == "Gold"') < txt.index("\nHide")


def test_category_rules_translate_to_class_blocks():
    text = "\n".join([
        '[Category] == "Ring" && [ItemTier] >= "2" # [StashItem] == "true"',
        '[Category] == "Flask" && [Quality] >= "10" # [StashItem] == "true"',
        '[Category] == "BodyArmour" && [Rarity] == "Rare" # [Salvage] == "true"',
    ])
    res = convert_pickit_text(text)
    txt = _joined(res)
    assert 'Class == "Rings"' in txt
    assert 'Class == "Life Flasks" "Mana Flasks"' in txt
    assert 'Class == "Body Armours"' in txt
    assert "Rarity = Rare" in txt
    assert res["report"]["untranslatable_total"] == 0


def test_hide_rest_still_hides_but_warns_on_untranslatable_rule():
    # An unknown category can't be translated — hide must STILL apply
    # (owner's call: hide means hide), with the risk flagged loudly.
    text = SAMPLE + "\n" + '[Category] == "SomethingWeird" # [StashItem] == "true"'
    res = convert_pickit_text(text, hide_rest=True)
    r = res["report"]
    assert r["untranslatable_total"] == 1
    assert r["hide_applied"] and r["hide_risky"]
    txt = _joined(res)
    assert "\nHide" in txt
    assert "WARNING" in txt
    assert '"SomethingWeird"' in r["untranslatable"][0]["reason"]


def test_widened_only_counts_rules_that_made_it_into_the_filter():
    # A rule that produces NOTHING must not count as "shown wider" — that
    # hint claims the item still gets a label, which would be a lie here.
    res = convert_pickit_text('[ItemTier] >= "5" # [StashItem] == "true"')
    r = res["report"]
    assert r["widened"] == 0
    assert r["untranslatable_total"] == 1
    assert r["converted"] == 0


def test_named_rules_translate_all_conditions_exactly():
    # Rarity AND Quality on one named rule both survive into the same block
    # (previously the bucket chain silently dropped the second condition).
    res = convert_pickit_text(
        '[Type] == "Sacred Focus" && [Rarity] == "Normal" && [Quality] >= "25" # [StashItem] == "true"')
    txt = _joined(res)
    assert "Rarity = Normal" in txt and "Quality >= 25" in txt
    assert res["report"]["widened"] == 0   # nothing was dropped


def test_hash_inside_a_name_cannot_hide_a_sibling_name():
    # split('#') used to cut inside the quoted name: the second name vanished
    # from the filter with ZERO report trace — the worst possible failure.
    res = convert_pickit_text(
        '[Type] == "Good Blade" && [Type] == "Hash # Axe" # [StashItem] == "true"')
    txt = _joined(res)
    assert '"Good Blade"' in txt              # sibling still shown
    assert "Hash # Axe" not in txt            # inexpressible name excluded…
    assert res["report"]["untranslatable_total"] == 1   # …but loudly reported


def test_unknown_rarity_token_is_dropped_not_passed_through():
    # 'Rarity = rare' (bad token) could make the game reject the whole filter.
    res = convert_pickit_text('[Category] == "Ring" && [Rarity] == "rare" # [StashItem] == "true"')
    txt = _joined(res)
    assert "Rarity = rare" not in txt
    assert 'Class == "Rings"' in txt          # rule still shown, wider
    assert res["report"]["widened"] == 1


def test_unmapped_category_with_other_conditions_counts_as_widened():
    res = convert_pickit_text('[Category] == "Weird" && [Rarity] == "Rare" # [Salvage] == "true"')
    txt = _joined(res)
    assert "Rarity = Rare" in txt             # superset kept
    assert res["report"]["widened"] == 1      # …and the widening is admitted


def test_bom_before_comment_is_still_a_comment():
    res = convert_pickit_text('﻿// header comment\n[Type] == "Divine Orb" # [StashItem] == "true"')
    r = res["report"]
    assert r["disabled"] == 1 and r["rules"] == 1 and r["untranslatable_total"] == 0


def test_non_string_input_is_safe():
    for bad in (None, 42, [b"x"], b"bytes"):
        res = convert_pickit_text(bad)
        assert res["ok"] is False and res["filter_lines"] == []


def test_hide_not_applied_when_nothing_converted():
    res = convert_pickit_text("no rules here at all", hide_rest=True)
    assert res["ok"] is False
    assert res["report"]["hide_applied"] is False


def test_show_blocks_are_styled():
    # Classic = the owner's own in-game filter codes: named currency keeps the
    # orange backdrop; uniques wear his dark-brown-on-orange with Brown Kite.
    res = convert_pickit_text(SAMPLE, hide_rest=True)
    txt = _joined(res)
    assert "SetBackgroundColor 237 233 222 230" in txt  # named cream backdrop
    assert "SetBackgroundColor 175 96 37 240" in txt   # his unique style
    assert "PlayEffect Brown" in txt
    assert "MinimapIcon 1 Brown Kite" in txt
    # imported pickits carry no prices — the jackpot screamer NEVER fires here
    assert "PlayAlertSound" not in txt
    # gold block keeps his dark backdrop
    gold = txt.index('BaseType == "Gold"')
    assert "SetBackgroundColor 0 0 0 170" in txt[gold:gold + 120]


def test_unknown_theme_falls_back_to_default_not_unstyled():
    # Includes the retired v4.36.0 theme names ("minimal", "contrast",
    # "colorblind") a pre-cut config may still carry.
    for stale in ("no-such-theme", "minimal", "contrast", "colorblind"):
        res = convert_pickit_text(SAMPLE, theme=stale)
        txt = _joined(res)
        assert "SetBackgroundColor 237 233 222 230" in txt  # classic named style
        assert "MinimapIcon" in txt


def test_renamed_game_filter_is_detected():
    # A FilterBlade .filter renamed to .ipd is the #1 real-world misuse —
    # the report must say "wrong direction", not a generic failure.
    filter_text = "\n".join([
        "Show",
        '    BaseType == "Divine Orb"',
        "    SetFontSize 45",
        "Hide",
    ])
    res = convert_pickit_text(filter_text)
    assert res["ok"] is False
    assert res["report"]["looks_like_filter"] is True
    # …and a real pickit must never trip the detector
    ok = convert_pickit_text(SAMPLE)
    assert ok["report"]["looks_like_filter"] is False


def test_garbage_input_never_crashes():
    for bad in ("", "\x00\x01\x02 binary junk", "just some prose\nwith lines",
                "[Type == broken quotes \" # ,,,"):
        res = convert_pickit_text(bad)
        assert res["ok"] is False
        assert res["filter_lines"] == []
        assert isinstance(res["report"]["rules"], int)


def test_untranslatable_list_is_capped():
    text = "\n".join(f'[Category] == "Ring{i}" # [StashItem] == "true"' for i in range(50))
    res = convert_pickit_text(text)
    r = res["report"]
    assert r["untranslatable_total"] == 50
    assert len(r["untranslatable"]) == 30
