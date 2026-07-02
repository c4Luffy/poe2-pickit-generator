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
    # Rare-only by default; custom threshold honored; uses the BodyArmour preset.
    snap = {"rare_gear": {"BodyArmour": {"enabled": True, "threshold": 400}}}
    lines = asm.build_rare_gear_rules(snap)
    assert len(lines) == 1
    rule = lines[0]
    assert rule.startswith('[Category] == "BodyArmour" && [Rarity] == "Rare" #')
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


def test_rare_gear_rare_only_by_default():
    # Magic is opt-in: absent OR explicit False → Rare-only rule.
    for snap in ({"rare_gear": {"Ring": {"enabled": True, "threshold": 320}}},
                 {"rare_gear_magic": False,
                  "rare_gear": {"Ring": {"enabled": True, "threshold": 320}}}):
        rule = asm.build_rare_gear_rules(snap)[0]
        assert '[Rarity] == "Rare"' in rule and "Magic" not in rule


def test_rare_gear_magic_included_when_enabled():
    snap = {"rare_gear_magic": True,
            "rare_gear": {"Ring": {"enabled": True, "threshold": 320}}}
    rule = asm.build_rare_gear_rules(snap)[0]
    assert '([Rarity] == "Rare" || [Rarity] == "Magic")' in rule


def test_rare_gear_min_ilvl_default_post_hash():
    # Default gate: [ItemLevel] >= "65" — after the # (ilvl reads post-identify).
    snap = {"rare_gear": {"Helmet": {"enabled": True}}}
    rule = asm.build_rare_gear_rules(snap)[0]
    before, after = rule.split("#", 1)
    assert "[ItemLevel]" not in before
    assert f'[ItemLevel] >= "{gen.RARE_GEAR_MIN_ILVL_DEFAULT}"' in after


def test_rare_gear_min_ilvl_custom_and_off():
    base = {"rare_gear": {"Helmet": {"enabled": True}}}
    rule = asm.build_rare_gear_rules({**base, "rare_gear_min_ilvl": 79})[0]
    assert '[ItemLevel] >= "79"' in rule
    rule = asm.build_rare_gear_rules({**base, "rare_gear_min_ilvl": 0})[0]
    assert "[ItemLevel]" not in rule


def test_rare_gear_min_tier_pre_hash_and_jewel_exempt():
    snap = {"rare_gear_min_tier": 3,
            "rare_gear": {"Boots": {"enabled": True}, "Jewel": {"enabled": True}}}
    rules = asm.build_rare_gear_rules(snap)
    boots = next(r for r in rules if '"Boots"' in r)
    jewel = next(r for r in rules if '"Jewel"' in r)
    assert '[ItemTier] >= "3"' in boots.split("#", 1)[0]   # pre-# → gates pickup
    assert "[ItemTier]" not in jewel                        # jewels have no base tier
    # 0 / bad value → no tier clause
    for off in (0, "abc"):
        rule = asm.build_rare_gear_rules(
            {"rare_gear_min_tier": off,
             "rare_gear": {"Boots": {"enabled": True}}})[0]
        assert "[ItemTier]" not in rule


def test_rare_gear_bad_min_ilvl_falls_back_to_default():
    snap = {"rare_gear_min_ilvl": "abc",
            "rare_gear": {"Helmet": {"enabled": True}}}
    rule = asm.build_rare_gear_rules(snap)[0]
    assert f'[ItemLevel] >= "{gen.RARE_GEAR_MIN_ILVL_DEFAULT}"' in rule


# ── build_rare_gear_pro_rules (Per-base mode) ─────────────────────────────────

import rare_gear_catalog as rgc
import rare_gear_templates as rgt


def _pro_snap(sections=None, jewels=None):
    return {"rare_gear_pro": {"sections": sections or {}, "jewels": jewels or {}}}


def test_pro_empty_by_default():
    assert asm.build_rare_gear_pro_rules({}) == []
    assert asm.build_rare_gear_pro_rules(_pro_snap()) == []


def test_pro_section_emits_one_full_rule_per_base():
    key = asm.pro_section_key("Boots", "armour_es", "high")
    lines = asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": True, "thr": 480, "ps": False}}))
    bases = rgc.CATALOG["Boots"]["armour_es"]["high"]
    rules = [l for l in lines if l.startswith("[Type]")]
    assert len(rules) == len(bases) and len(bases) >= 4
    assert "Faithful Leggings" in " ".join(rules)
    for r in rules:
        assert '[ItemTier] >= "2"' in r          # high-bracket default tier gate
        assert '[Rarity] == "Rare"' in r
        assert '>= "480"' in r and r.endswith('[StashItem] == "true"')
        assert "local_energy_shield" in r        # ES combo scores ES mods
        # WeightedSum after the #, selector before it
        before, after = r.split("#", 1)
        assert "WeightedSum" not in before and "WeightedSum" in after


def test_pro_prefix_suffix_rules_derived():
    key = asm.pro_section_key("Boots", "armour_es", "high")
    lines = asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": True, "thr": 480}}))  # ps defaults on
    n_bases = len(rgc.CATALOG["Boots"]["armour_es"]["high"])
    assert "//PREFIXES" in lines and "//SUFFIXES" in lines
    assert sum(1 for l in lines if l.startswith("[Type]")) == n_bases * 3
    assert any('>= "290"' in l for l in lines)   # 480*0.60=288 → 290
    assert any('>= "265"' in l for l in lines)   # 480*0.55=264 → 265


def test_pro_magic_rule_when_enabled():
    key = asm.pro_section_key("Boots", "evasion", "high")
    lines = asm.build_rare_gear_pro_rules(
        _pro_snap({key: {"on": True, "ps": False, "magic": True}}))
    magic = [l for l in lines if '[Rarity] == "Magic"' in l]
    assert magic and all("base_movement_velocity_+%" in l and '>= "87"' in l for l in magic)


def test_pro_no_ps_split_for_preset_families():
    key = asm.pro_section_key("Staves", "all", "high")
    lines = asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": True, "ps": True}}))
    assert "//PREFIXES" not in lines             # staff template has no P/S split
    assert any(l.startswith("[Type]") for l in lines)


def test_pro_jewel_archetype_and_single():
    lines = asm.build_rare_gear_pro_rules(_pro_snap(jewels={
        "caster": {"on": True, "thr": 20},
        "movespeed": {"on": True},
    }))
    caster = [l for l in lines if "maximum_energy_shield_+%" in l]
    assert len(caster) == 1
    assert caster[0].count("WeightedSum") == 2 and caster[0].count('>= "20"') == 2
    assert '[Rarity] == "Magic"' in caster[0]
    singles = [l for l in lines if "[base_movement_velocity_+%]" in l]
    assert len(singles) == 2                     # Magic + Rare
    assert all('>= "1"' in l for l in singles)


def test_pro_disabled_and_unknown_sections_ignored():
    key = asm.pro_section_key("Boots", "armour", "high")
    assert asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": False}})) == []
    assert asm.build_rare_gear_pro_rules(_pro_snap({"Nope|x|high": {"on": True}})) == []


def test_pro_catalog_covers_all_template_families():
    # Every catalog family must resolve to a template for at least one combo.
    for family, groups in rgc.CATALOG.items():
        assert any(rgt.get_template(family, c) for c in groups), family


def test_pro_catalog_no_name_in_multiple_brackets():
    # [Type] matches by display name only; a name straddling brackets would let
    # a looser low/mid rule override the user's stricter endgame tuning.
    for family, groups in rgc.CATALOG.items():
        for combo, brackets in groups.items():
            seen = set()
            for br in ("low", "mid", "high"):
                for name in brackets.get(br, []):
                    assert name not in seen, (family, combo, br, name)
                    seen.add(name)


def test_pro_magic_fallback_for_families_without_single_mod_rule():
    key = asm.pro_section_key("Gloves", "armour", "high")
    lines = asm.build_rare_gear_pro_rules(
        _pro_snap({key: {"on": True, "thr": 420, "ps": False, "magic": True}}))
    magic = [l for l in lines if '[Rarity] == "Magic"' in l]
    assert magic and all('>= "170"' in l for l in magic)   # 420*0.40=168 → 170


def test_pro_body_armour_uses_transcribed_weights_and_ratios():
    key = asm.pro_section_key("BodyArmours", "es", "high")
    lines = asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": True}}))
    full = next(l for l in lines if l.startswith("[Type]"))
    assert "local_energy_shield:1.04" in full and '>= "390"' in full
    assert any('>= "195"' in l for l in lines)   # explicit prefix threshold
    assert any('>= "255"' in l for l in lines)   # explicit suffix threshold


def test_pro_amulet_archetype_rules():
    lines = asm.build_rare_gear_pro_rules(
        _pro_snap() | {"rare_gear_pro": {"amulets": {"es_caster": {"on": True},
                                                     "magic": {"on": True}}}})
    full = [l for l in lines if l.startswith("[Type]") and '"Rare"' in l
            and "maximum_mana_+%" in l]
    assert len(full) == len(rgc.AMULET_BASES) and all('>= "390"' in l for l in full)
    assert "//PREFIXES" in lines and "//SUFFIXES" in lines
    gems = [l for l in lines if '"Magic"' in l and "spell_skill_gem_level" in l]
    assert len(gems) == len(rgc.AMULET_BASES) and all('>= "70"' in l for l in gems)
    assert any('[Category] == "Amulet"' in l and '[base_item_found_rarity_+%] >= "50"' in l
               for l in lines)


def test_pro_belt_rules():
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"belts": {"on": True, "magic": True}}})
    assert sum(1 for l in lines if '>= "300"' in l) == len(rgc.BELT_BASES)   # prefixes
    assert sum(1 for l in lines if '>= "210"' in l) == len(rgc.BELT_BASES)   # suffixes
    assert sum(1 for l in lines if '>= "180"' in l) == len(rgc.BELT_BASES)   # magic


def test_pro_ring_archetypes_legacy_master_switch():
    # Old configs: single on/off means "every archetype at preset thresholds".
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"rings": {"on": True, "magic": True}}})
    rare = [l for l in lines if l.startswith("[Type]") and '"Rare"' in l]
    assert len(rare) == len(rgt.RING_ARCHETYPES) * len(rgc.RING_BASES)
    assert any('>= "426"' in l for l in rare)          # caster archetype threshold
    magic = [l for l in lines if l.startswith("[Type]") and '"Magic"' in l]
    assert len(magic) == len(rgc.RING_BASES) and all('>= "180"' in l for l in magic)
    assert sum(1 for l in lines if '[Category] == "Ring"' in l
               and '[base_item_found_rarity_+%] >= "50"' in l) == 2


def test_pro_ring_archetypes_individual_selection():
    # New configs: per-archetype on/off with an editable threshold each.
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"rings": {"on": True, "magic": False, "archetypes": {
            "caster": {"on": True, "thr": 500},
            "melee": {"on": False, "thr": 360},
        }}}})
    rules = [l for l in lines if l.startswith("[Type]")]
    assert len(rules) == len(rgc.RING_BASES)           # only the caster archetype
    assert all('>= "500"' in l and '"Rare"' in l for l in rules)
    assert not any('"Magic"' in l for l in lines)
    # magic works without any archetype enabled
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"rings": {"magic": True, "archetypes": {}}}})
    assert sum(1 for l in lines if '"Magic"' in l) == len(rgc.RING_BASES) + 1


def test_pro_jewel_multi_rarity_archetype():
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"jewels": {"minions": {"on": True}}}})
    assert sum(1 for l in lines if '[Rarity] == "Rare"' in l) == 1
    assert sum(1 for l in lines if '[Rarity] == "Magic"' in l) == 1
    assert all("minion_damage_+%" in l for l in lines if l.startswith("[Category]"))


def test_pro_shield_block_gate_and_weights():
    # Shields and bucklers share the block-gated pool from the user's pickit.
    for family in ("Shields", "Bucklers"):
        combo = next(c for c, b in rgc.CATALOG[family].items() if b.get("high"))
        key = asm.pro_section_key(family, combo, "high")
        lines = asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": True}}))
        rules = [l for l in lines if l.startswith("[Type]")]
        assert rules, family
        for r in rules:
            assert '[ItemTier] >= "3"' in r                       # his endgame tier
            assert '# [local_block_chance_+%] >= "1" && [WeightedSum(' in r
            assert "local_block_chance_+%:0.2" in r
            assert "base_maximum_cold_damage_resistance_%:15" in r
            assert '>= "260"' in r
        assert "//PREFIXES" not in lines                          # no P/S split


def test_pro_shield_magic_fallback_keeps_gate():
    combo = next(c for c, b in rgc.CATALOG["Shields"].items() if b.get("high"))
    key = asm.pro_section_key("Shields", combo, "high")
    lines = asm.build_rare_gear_pro_rules(_pro_snap({key: {"on": True, "magic": True}}))
    magic = [l for l in lines if '[Rarity] == "Magic"' in l]
    assert magic                                                  # 260*0.40=104 → 105
    assert all('[local_block_chance_+%] >= "1"' in l and '>= "105"' in l for l in magic)


def test_pro_jewel_bow_endgame_dual_thresholds():
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"jewels": {"bow_endgame": {"on": True}}}})
    rules = [l for l in lines if l.startswith("[Category]")]
    assert len(rules) == 2                                        # Rare + Magic
    for r in rules:
        assert '>= "34"' in r and '>= "33"' in r                  # 34/33 pair
        assert "base_reduce_enemy_lightning_resistance_%:3.5" in r
        assert "base_chance_to_pierce_%:2" in r


def test_pro_jewel_es_chaos_archetype():
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"jewels": {"es_chaos": {"on": True}}}})
    rules = [l for l in lines if l.startswith("[Category]")]
    assert len(rules) == 2
    assert all("chaos_damage_+%:2" in l and l.count('>= "35"') == 2 for l in rules)


def test_pro_expert_rules_verbatim():
    text = ('// my focus ladder\n'
            '[WeaponCategory] == "Focus" && [ItemTier] >= "5" && [Rarity] == "Rare" # '
            '[WeightedSum(base_maximum_mana:1,spell_damage_+%:2)] >= "420" && '
            '[StashItem] == "true"\n'
            '\n'
            '[WeaponCategory] == "Spear" && [ItemTier] >= "4" && [Rarity] == "Rare" # '
            '[PhysicalDPS] >= "350" && [StashItem] == "true"\n')
    lines = asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"expert": {"on": True, "text": text}}})
    assert "// my focus ladder" in lines
    # every non-blank input line survives byte-for-byte, in order
    body = [l for l in text.splitlines()]
    idx = lines.index("// my focus ladder")
    assert lines[idx:idx + len(body)] == [l.rstrip() for l in body]


def test_pro_expert_rules_off_or_empty():
    assert asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"expert": {"on": False, "text": '[X] # [Y]'}}}) == []
    assert asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"expert": {"on": True, "text": "  \n\n"}}}) == []
    assert asm.build_rare_gear_pro_rules(
        {"rare_gear_pro": {"expert": "nonsense"}}) == []


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


def test_build_weighted_sum_rule_min_ilvl():
    rule = asm.build_weighted_sum_rule('[Category] == "Ring"',
                                       [("base_maximum_life", 1)], 100, min_ilvl=65)
    assert rule == (
        '[Category] == "Ring" && [Rarity] == "Rare" '
        '# [ItemLevel] >= "65" && [WeightedSum(base_maximum_life:1)] >= "100" '
        '&& [StashItem] == "true"')


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
