"""Unit tests for pickit_assembly — the pure rule-assembly logic lifted out of the
GUI's ``_generate``. These run with no display, no network, no file I/O, so the
generation pipeline is finally testable on its own.

Run with:  python -m pytest test_assembly.py -v
"""
import datetime

import pickit_assembly as asm
import poe2_pickit_generator as gen


# ── Helpers ──────────────────────────────────────────────────────────────────

def _exchange_payload(items, rate=1.0):
    """poe.ninja-shaped exchange payload. items: list of (id, name, primary_value)."""
    return {
        "core":  {"rates": {"exalted": rate}},
        "items": [{"id": i, "name": n} for i, n, _ in items],
        "lines": [{"id": i, "primaryValue": v} for i, _, v in items],
    }


def _unique_payload(rows, rate=1.0):
    """Unique payload. rows: list of (name, base_type, primary_value)."""
    return {
        "core":  {"rates": {"exalted": rate}},
        "lines": [{"name": n, "baseType": b, "primaryValue": v} for n, b, v in rows],
    }


# ── build_header_lines ───────────────────────────────────────────────────────

def test_header_banner_carries_league_and_id():
    ts = datetime.datetime(2026, 6, 28, 16, 37, 44)
    out = asm.build_header_lines("Fate of the Vaal", ts, "20260628_163744", 7.0, 50.0)
    text = "\n".join(out)
    assert "ID: 20260628_163744" in out[1]
    assert "Fate of the Vaal" in text
    assert out[0] == "/" * gen._W           # opening border
    assert "2026-06-28 16:37:44" in text    # generated timestamp


def test_header_documents_core_tokens():
    out = "\n".join(asm.build_header_lines("L", datetime.datetime.now(), "ID", 0, 0))
    for token in ("[TotalResistances]", "[ComputedArmour]", "[UniqueName]",
                  "[WaystoneTier]", "[IgnoreRitual]", "[StashUnid]", "WeaponCategory"):
        assert token in out, f"header missing {token}"
    # The all-important pre/post-identify split must be explained.
    assert "Before # = checked BEFORE identifying" in out


# ── compute_divine_rate ──────────────────────────────────────────────────────

def test_compute_divine_rate_found():
    payload = _exchange_payload([(1, "Divine Orb", 350.0), (2, "Chaos Orb", 1.0)], rate=1.0)
    divine, found, rate = asm.compute_divine_rate(payload)
    assert found is True
    assert divine == 350.0
    assert rate == 1.0


def test_compute_divine_rate_applies_exalted_rate():
    payload = _exchange_payload([(1, "Divine Orb", 2.0)], rate=180.0)
    divine, found, _ = asm.compute_divine_rate(payload)
    assert found is True
    assert divine == 360.0     # primaryValue * exalted rate


def test_compute_divine_rate_missing():
    payload = _exchange_payload([(1, "Chaos Orb", 1.0)], rate=1.0)
    divine, found, _ = asm.compute_divine_rate(payload)
    assert found is False
    assert divine == 1.0


# ── effective_min ────────────────────────────────────────────────────────────

def test_effective_min_category_override_wins():
    snap = {"cat_thresh": {"currency": 12.0}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 12.0


def test_effective_min_falls_back_to_gear_global():
    snap = {"cat_thresh": {"currency": -1.0}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 5.0


def test_effective_min_uses_unique_global_for_uniques():
    snap = {"cat_thresh": {}}
    assert asm.effective_min(snap, "unique_weapons", True, 5.0, 50.0) == 50.0


def test_effective_min_tolerates_bad_value():
    snap = {"cat_thresh": {"currency": "oops"}}
    assert asm.effective_min(snap, "currency", False, 5.0, 50.0) == 5.0


# ── enabled_names_for ────────────────────────────────────────────────────────

def test_enabled_names_excludes_disabled():
    payload = _exchange_payload([(1, "Chaos Orb", 1), (2, "Divine Orb", 1), (3, "Mirror", 1)])
    states = {"Divine Orb": {"enabled": False}}
    names = asm.enabled_names_for("currency", False, payload, states)
    assert names == {"Chaos Orb", "Mirror"}


def test_enabled_names_none_for_uniques():
    payload = _unique_payload([("Headhunter", "Heavy Belt", 1)])
    assert asm.enabled_names_for("unique_weapons", True, payload, {"x": {}}) is None


def test_enabled_names_none_when_no_states():
    payload = _exchange_payload([(1, "Chaos Orb", 1)])
    assert asm.enabled_names_for("currency", False, payload, {}) is None


# ── build_category_lines ─────────────────────────────────────────────────────

def test_build_category_lines_unique():
    payload = _unique_payload([("Headhunter", "Heavy Belt", 100.0)])
    lines = asm.build_category_lines("unique_weapons", True, payload, 1.0, 10.0, 5.0, None)
    joined = "\n".join(lines)
    assert '[UniqueName] == "Headhunter"' in joined
    assert '[Type] == "Heavy Belt"' in joined


def test_build_category_lines_currency_pick_all():
    # currency is a PICK_ALL category — every item active regardless of threshold.
    payload = _exchange_payload([(1, "Chaos Orb", 0.001)], rate=1.0)
    lines = asm.build_category_lines("currency", False, payload, 1.0, 9999.0, 5.0, None)
    active = [l for l in lines if l.startswith("[Type]")]
    assert any('"Chaos Orb"' in l for l in active)   # not commented out despite tiny value


def test_build_category_lines_waystones_ignores_payload():
    lines = asm.build_category_lines("waystones", False, {}, 1.0, 0.0, 5.0, None)
    assert lines == gen.build_waystone_lines()


# ── build_rare_gear_rules (WeightedSum per slot) ──────────────────────────────

def test_rare_gear_empty_by_default():
    assert asm.build_rare_gear_rules({}) == []
    assert asm.build_rare_gear_rules({"rare_gear": {}}) == []


def test_rare_gear_enabled_slot_uses_preset_and_threshold():
    # Magic included by default; custom threshold honored; uses the BodyArmour preset.
    snap = {"rare_gear": {"BodyArmour": {"enabled": True, "threshold": 400}}}
    lines = asm.build_rare_gear_rules(snap)
    assert len(lines) == 1
    rule = lines[0]
    assert rule.startswith('[Category] == "BodyArmour" && ([Rarity] == "Rare" || [Rarity] == "Magic") #')
    assert '[WeightedSum(' in rule and '>= "400"' in rule and rule.endswith('[StashItem] == "true"')
    # WeightedSum reads identified mods → after the #; uses real preset mods.
    before, after = rule.split("#", 1)
    assert "WeightedSum" not in before
    assert "base_maximum_life:1" in after


def test_rare_gear_default_threshold_when_unset():
    snap = {"rare_gear": {"Amulet": {"enabled": True}}}      # no threshold → preset default
    rule = asm.build_rare_gear_rules(snap)[0]
    default_th = gen.WEIGHTED_SUM_PRESETS["Amulet"][0]
    assert f'>= "{default_th}"' in rule


def test_rare_gear_weapon_uses_weaponcategory_selector():
    snap = {"rare_gear": {"Shield": {"enabled": True, "threshold": 260}}}
    rule = asm.build_rare_gear_rules(snap)[0]
    assert rule.startswith('[WeaponCategory] == "Shield"')


def test_rare_gear_rare_only_when_magic_off():
    snap = {"rare_gear_magic": False,
            "rare_gear": {"Ring": {"enabled": True, "threshold": 320}}}
    rule = asm.build_rare_gear_rules(snap)[0]
    assert '[Rarity] == "Rare"' in rule and "Magic" not in rule


def test_rare_gear_disabled_slot_omitted():
    snap = {"rare_gear": {"Helmet": {"enabled": False, "threshold": 300}}}
    assert asm.build_rare_gear_rules(snap) == []


def test_rare_gear_bad_threshold_falls_back_to_default():
    snap = {"rare_gear": {"Ring": {"enabled": True, "threshold": "abc"}}}
    rule = asm.build_rare_gear_rules(snap)[0]
    default_th = gen.WEIGHTED_SUM_PRESETS["Ring"][0]
    assert f'>= "{default_th}"' in rule


# ── build_weighted_sum_rule (Phase 2 validation slice) ────────────────────────

def test_weighted_sum_term_format():
    # Bot format: stat_id:weight
    assert asm.weighted_sum_term("base_maximum_life", 1.2) == "base_maximum_life:1.2"
    assert asm.weighted_sum_term("base_fire_damage_resistance_%", 1) == "base_fire_damage_resistance_%:1"


def test_build_weighted_sum_rule():
    rule = asm.build_weighted_sum_rule(
        '[Category] == "BodyArmour"',
        [("base_maximum_life", 1.2), ("base_resist_all_elements_%", 5)],
        390)
    assert rule == (
        '[Category] == "BodyArmour" && [Rarity] == "Rare" '
        '# [WeightedSum(base_maximum_life:1.2,base_resist_all_elements_%:5)] >= "390" '
        '&& [StashItem] == "true"')
    # [WeightedSum(...)] reads identified mods → must live AFTER the #.
    before, after = rule.split("#", 1)
    assert "WeightedSum" not in before and "WeightedSum" in after


def test_build_weighted_sum_rule_include_magic():
    rule = asm.build_weighted_sum_rule('[Category] == "Ring"',
                                       [("base_maximum_life", 1)], 100, include_magic=True)
    assert '([Rarity] == "Rare" || [Rarity] == "Magic")' in rule


# ── top_items_from_lines ─────────────────────────────────────────────────────

def test_top_items_from_lines_reads_exvalue():
    lines = [
        '[Type] == "Divine Orb" # [StashItem] == "true" // ExValue = 350.00',
        '//[Type] == "Junk" # [StashItem] == "true" // ExValue = 0.10',   # commented → skip
        '[Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true" // ExValue = 5000.00',
    ]
    out = dict(asm.top_items_from_lines(lines))
    assert out == {"Divine Orb": 350.0, "Headhunter": 5000.0}


# ── extract_rule_name / active_rule_ids ──────────────────────────────────────

def test_extract_rule_name_prefers_unique():
    line = '[Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"'
    assert asm.extract_rule_name(line) == "Headhunter"


def test_extract_rule_name_falls_back_to_type():
    assert asm.extract_rule_name('[Type] == "Chaos Orb" # [StashItem] == "true"') == "Chaos Orb"


def test_active_rule_ids_skips_comments_and_blanks():
    lines = [
        "// header",
        "",
        '[Type] == "Chaos Orb" # [StashItem] == "true"',
        '//[Type] == "Disabled" # [StashItem] == "true"',
    ]
    assert asm.active_rule_ids(lines) == {"Chaos Orb"}


# ── craft_base_section — regression test for the ilvl WYSIWYG fix ─────────────

def test_craft_base_section_emits_per_base_overrides():
    """The bug we fixed: the tab showed ilvl 82 but the file said 79. The GUI now
    bakes each visible craft card's ilvl into item_states['_craftbase'][name]['ilvl'];
    craft_base_section must emit exactly those, regardless of the global base_min_level.
    """
    snap = {
        "base_min_level": 79,                       # global box (the old, wrong source)
        "item_states": {"_craftbase": {
            "Sirenscale Gloves": {"ilvl": 82},
            "Sekhema Sandals":   {"ilvl": 82},
        }},
    }
    lines, count, floor = asm.craft_base_section(snap)
    joined = "\n".join(lines)
    assert '[Type] == "Sirenscale Gloves" && [Rarity] == "Normal" # [ItemLevel] >= "82"' in joined
    assert '[Type] == "Sekhema Sandals" && [Rarity] == "Normal" # [ItemLevel] >= "82"' in joined
    assert '>= "79"' not in joined                  # the global must NOT leak in
    assert floor == 82
    assert count >= 2


def test_craft_base_section_floor_is_min_of_enabled():
    snap = {
        "base_min_level": 82,
        "item_states": {"_craftbase": {
            "Gold Ring":         {"ilvl": 75},
            "Sirenscale Gloves": {"ilvl": 82},
        }},
    }
    _lines, _count, floor = asm.craft_base_section(snap)
    assert floor == 75


def test_craft_base_section_respects_disabled():
    snap = {
        "base_min_level": 82,
        "item_states": {"_craftbase": {
            "Sirenscale Gloves": {"enabled": False},
        }},
    }
    lines, _count, _floor = asm.craft_base_section(snap)
    assert all("Sirenscale Gloves" not in l for l in lines)


# ── chance_base_disabled ─────────────────────────────────────────────────────

def test_chance_base_disabled_collects_off_bases():
    snap = {"item_states": {"_chance": {
        "Gold Ring":  {"enabled": False},
        "Heavy Belt": {"enabled": True},
    }}}
    assert asm.chance_base_disabled(snap) == {"Gold Ring"}


# ── compute_price_alerts ─────────────────────────────────────────────────────

_CATS = [("currency", "Currency", "Currency", False)]


def test_price_alerts_flags_big_move():
    payloads = {"currency": _exchange_payload([(1, "Chaos Orb", 200.0)], rate=1.0)}
    prev = {"currency": {"Chaos Orb": 100.0}}        # doubled → +100%
    new_prices, alerts = asm.compute_price_alerts(_CATS, payloads, prev, chaos_ex_val=1.0)
    assert new_prices["currency"]["Chaos Orb"] == 200.0
    assert len(alerts) == 1
    _delta, text = alerts[0]
    assert "▲" in text and "+100%" in text


def test_price_alerts_skips_small_move():
    payloads = {"currency": _exchange_payload([(1, "Chaos Orb", 105.0)], rate=1.0)}
    prev = {"currency": {"Chaos Orb": 100.0}}        # +5% < 20% threshold
    _new, alerts = asm.compute_price_alerts(_CATS, payloads, prev, chaos_ex_val=1.0)
    assert alerts == []


def test_price_alerts_skips_worthless_items():
    # Huge % move but both prices round to <1 chaos → suppressed as noise.
    payloads = {"currency": _exchange_payload([(1, "Scrap", 0.6)], rate=1.0)}
    prev = {"currency": {"Scrap": 0.2}}
    _new, alerts = asm.compute_price_alerts(_CATS, payloads, prev, chaos_ex_val=1.0)
    assert alerts == []


def test_price_alerts_no_baseline_no_alert():
    payloads = {"currency": _exchange_payload([(1, "Chaos Orb", 200.0)], rate=1.0)}
    new_prices, alerts = asm.compute_price_alerts(_CATS, payloads, {}, chaos_ex_val=1.0)
    assert alerts == []                              # nothing to compare against
    assert new_prices["currency"]["Chaos Orb"] == 200.0
