"""Unit tests for the pure (network-free) functions in poe2_pickit_generator.

Run with:  python -m pytest -q
These cover the loot-filter export, the static validator, and the core
exchange-line builder — the logic most likely to regress silently.
"""
import poe2_pickit_generator as gen


# ── Helpers ──────────────────────────────────────────────────────────────────

def _payload(items, rate=1.0):
    """Build a minimal poe.ninja-shaped payload.

    items: list of (id, name, primary_value)
    """
    return {
        "core":  {"rates": {"exalted": rate}},
        "items": [{"id": i, "name": n} for i, n, _ in items],
        "lines": [{"id": i, "primaryValue": v} for i, _, v in items],
    }


# ── build_loot_filter ────────────────────────────────────────────────────────

def test_loot_filter_has_header_and_hide():
    out = gen.build_loot_filter(['[Type] == "Chaos Orb" # [StashItem] == "true"'])
    assert out[0].startswith("# Path of Exile 2 Filter")
    assert "Show" in out
    assert "Hide" in out


def test_loot_filter_uses_exact_basetype_match():
    out = "\n".join(gen.build_loot_filter(['[Type] == "Chaos Orb" # [StashItem] == "true"']))
    assert 'BaseType == "Chaos Orb"' in out


def test_loot_filter_groups_by_condition():
    ipd = [
        '[Type] == "Divine Orb" # [StashItem] == "true"',
        '[Type] == "Sapphire Ring" && [Rarity] == "Unique" # [UniqueName] == "X" && [StashItem] == "true"',
        '[Type] == "Glorious Plate" && [Quality] >= "28" # [StashItem] == "true"',
        '[Type] == "Glorious Plate" && [Sockets] >= "3" # [StashItem] == "true"',
        '[Type] == "Overseer Tablet" && [Rarity] == "Normal" # [StashItem] == "true"',
        '[Category] == "Waystone" && [WaystoneTier] >= "1" # [StashItem] == "true"',
    ]
    out = "\n".join(gen.build_loot_filter(ipd))
    assert "Rarity = Unique" in out
    assert "Rarity = Normal" in out
    assert "Quality >= 28" in out
    assert "Sockets >= 3" in out
    assert 'Class "Waystone"' in out


def test_loot_filter_skips_commented_and_blank():
    ipd = [
        "// a header",
        "",
        '//[Type] == "Worthless Orb" # [StashItem] == "true"',   # disabled
        '[Type] == "Chaos Orb" # [StashItem] == "true"',         # active
    ]
    out = "\n".join(gen.build_loot_filter(ipd))
    assert "Chaos Orb" in out
    assert "Worthless Orb" not in out


def test_loot_filter_chunks_large_groups():
    ipd = [f'[Type] == "Item {i}" # [StashItem] == "true"' for i in range(65)]
    out = "\n".join(gen.build_loot_filter(ipd))
    # 65 names / 30 per chunk -> 3 chunks, so a "# Part 3/3" marker must exist
    assert "# Part 1/3" in out and "# Part 3/3" in out


def test_loot_filter_dedupes_names():
    ipd = [
        '[Type] == "Chaos Orb" # [StashItem] == "true"',
        '[Type] == "Chaos Orb" # [StashItem] == "true"',
    ]
    out = "\n".join(gen.build_loot_filter(ipd))
    assert out.count('"Chaos Orb"') == 1


# ── validate_pickit ──────────────────────────────────────────────────────────

def test_validate_clean_rule_passes():
    res = gen.validate_pickit(['[Type] == "Chaos Orb" # [StashItem] == "true"'])
    assert res["errors"] == []


def test_validate_flags_known_invalid_type():
    # "Refined Necrotic Catalyst" is in KNOWN_INVALID_TYPES
    res = gen.validate_pickit(['[Type] == "Refined Necrotic Catalyst" # [StashItem] == "true"'])
    assert any("Invalid base type" in m for _, m in res["errors"])


def test_validate_flags_unknown_equipment_base():
    line = '[Type] == "Notarealbase" && [Quality] >= "28" # [StashItem] == "true"'
    res = gen.validate_pickit([line])
    assert any("Invalid base type" in m for _, m in res["errors"])


def test_validate_flags_missing_stashitem():
    res = gen.validate_pickit(['[Type] == "Chaos Orb" # [Foo] == "true"'])
    assert any("StashItem" in m for _, m in res["errors"])


# ── build_exchange_lines ─────────────────────────────────────────────────────

def test_exchange_skips_skip_items():
    payload = _payload([(1, "Refined Necrotic Catalyst", 50.0), (2, "Chaos Orb", 1.0)], rate=1.0)
    out = "\n".join(gen.build_exchange_lines(payload, divine_rate_exalts=200.0))
    assert "Refined Necrotic Catalyst" not in out
    assert "Chaos Orb" in out


def test_exchange_comments_below_threshold():
    payload = _payload([(1, "Cheap Thing", 1.0)], rate=1.0)   # 1 ex < MIN_EXALT (10)
    out = gen.build_exchange_lines(payload, divine_rate_exalts=200.0, min_exalt=10.0)
    assert out and out[0].startswith("//")


def test_exchange_pick_all_ignores_threshold():
    payload = _payload([(1, "Cheap Thing", 1.0)], rate=1.0)
    out = gen.build_exchange_lines(payload, divine_rate_exalts=200.0, pick_all=True, min_exalt=10.0)
    assert out and not out[0].startswith("//")


def test_exchange_always_names_prepended():
    payload = _payload([(1, "Chaos Orb", 50.0)], rate=1.0)
    out = gen.build_exchange_lines(payload, divine_rate_exalts=200.0,
                                   always_names=["Exalted Orb"])
    assert any('"Exalted Orb"' in line for line in out)


# ── misc pure helpers ────────────────────────────────────────────────────────

def test_waystone_lines_returns_fallback():
    assert gen.build_waystone_lines() == list(gen.WAYSTONE_FALLBACK_RULES)


# ── build_craft_base_rules ───────────────────────────────────────────────────

def test_craft_bases_are_normal_ilvl_rules():
    out = "\n".join(gen.build_craft_base_rules())
    assert '[Rarity] == "Normal"' in out
    assert '[ItemLevel] >= "81"' in out


def test_craft_bases_exclude_sword_axe_mace():
    out = "\n".join(gen.build_craft_base_rules())
    assert "Hand Sword" not in out
    assert "Hand Axe" not in out
    assert "Hand Mace" not in out


def test_craft_base_names_are_all_valid():
    # Every curated craft base must exist in the bot's known base list
    for cat, names in gen._CRAFT_BEST_BASES.items():
        for n in names:
            assert n in gen.VALID_EQUIPMENT_BASES, f"{cat}: unknown base {n!r}"


def test_craft_bases_respect_disabled():
    full = gen.build_craft_base_rules()
    one  = next(l for l in full if l.startswith("[Type]"))
    name = one.split('"')[1]
    trimmed = "\n".join(gen.build_craft_base_rules(disabled={name}))
    assert f'[Type] == "{name}"' not in trimmed


def test_divine_value_from_exalt():
    assert gen.divine_value_from_exalt(200.0, 100.0) == 2.0
    assert gen.divine_value_from_exalt(5.0, 0.0) == 0.0   # no divide-by-zero
