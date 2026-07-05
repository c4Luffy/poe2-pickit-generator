"""Unit tests for the pure (network-free) functions in poe2_pickit_generator.

Run with:  python -m pytest -q
These cover the loot-filter export, the static validator, and the core
exchange-line builder — the logic most likely to regress silently.
"""
from exilebot_pickit import generator as gen


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
    assert '[ItemLevel] >= "82"' in out


def test_craft_bases_exclude_sword_axe_mace():
    out = "\n".join(gen.build_craft_base_rules())
    assert "Hand Sword" not in out
    assert "Hand Axe" not in out
    assert "Hand Mace" not in out


def test_craft_base_names_are_all_valid():
    # Every curated craft base must exist in the bot's known base list
    for cat, names in gen.craft_base_categories():
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


# ── NEW: ItemLevel placement regression tests ────────────────────────────────
# ExileBot 2 evaluates conditions BEFORE # on the ground (pre-pickup),
# and conditions AFTER # after picking up. [ItemLevel] is only readable
# post-pickup, so it MUST live after the # separator.

def test_craft_base_ilvl_is_after_hash():
    """[ItemLevel] must appear in the action block (after #), not the filter block."""
    rules = [l for l in gen.build_craft_base_rules() if "[StashItem]" in l]
    assert rules, "No craft base rules generated"
    for rule in rules:
        before, after = rule.split("#", 1)
        assert "[ItemLevel]" not in before, (
            f"[ItemLevel] is in the pre-pickup filter (BEFORE #) — bug!\n  {rule}"
        )
        assert "[ItemLevel]" in after, (
            f"[ItemLevel] missing from action block (AFTER #)\n  {rule}"
        )


def test_build_base_rules_ilvl_is_after_hash():
    """Same check for endgame gear bases from build_base_rules()."""
    rules = [l for l in gen.build_base_rules() if "[ItemLevel]" in l]
    assert rules, "No base rules with [ItemLevel] found"
    for rule in rules:
        before, after = rule.split("#", 1)
        assert "[ItemLevel]" not in before, (
            f"[ItemLevel] in pre-pickup filter (BEFORE #) in base rule:\n  {rule}"
        )


def test_craft_base_custom_ilvl_reflected_in_action_block():
    """A custom min_ilvl value must appear after # not before."""
    rules = [l for l in gen.build_craft_base_rules(min_ilvl=75) if "[StashItem]" in l]
    for rule in rules:
        before, after = rule.split("#", 1)
        assert '[ItemLevel] >= "75"' not in before
        assert '[ItemLevel] >= "75"' in after


def test_craft_base_ilvl_overrides_per_base():
    """A user per-base ilvl override wins; other bases keep their own default."""
    out = gen.build_craft_base_rules(min_ilvl=82, ilvl_overrides={"Dueling Wand": 90})
    assert '[ItemLevel] >= "90"' in next(l for l in out if '"Dueling Wand"' in l)
    # non-overridden armour keeps the global default
    assert '[ItemLevel] >= "82"' in next(l for l in out if '"Warlord Cuirass"' in l)
    # built-in accessory default still applies when the user hasn't overridden it
    assert '[ItemLevel] >= "75"' in next(l for l in out if '"Stellar Amulet"' in l)


def test_craft_base_default_ilvl_helper():
    assert gen.craft_base_default_ilvl("Stellar Amulet", 82) == 75   # accessory override
    assert gen.craft_base_default_ilvl("Warlord Cuirass", 82) == 82  # falls back to global
    assert gen.craft_base_default_ilvl("Warlord Cuirass", 70) == 70


def test_validate_pickit_catches_ilvl_before_hash():
    """Validator should warn/error on [ItemLevel] appearing before #."""
    bad = '[Type] == "Glorious Plate" && [Rarity] == "Normal" && [ItemLevel] >= "82" # [StashItem] == "true"'
    result = gen.validate_pickit([bad])
    # After fix the validator should flag this pattern
    flagged = result["errors"] + result["warnings"]
    assert any("ItemLevel" in m for _, m in flagged), (
        "Validator did not flag [ItemLevel] before # — consider adding this check"
    )


# ── Round 2: CHANCE_BASES, ALWAYS_PICK_RUNES, validator, accessory bases ─────

def test_all_chance_bases_are_valid_equipment_bases():
    """Every base in CHANCE_BASES must be in VALID_EQUIPMENT_BASES."""
    invalid = [(cat, base, tgt) for cat, base, tgt in gen.CHANCE_BASES
               if base not in gen.VALID_EQUIPMENT_BASES]
    assert not invalid, (
        "CHANCE_BASES entries not in VALID_EQUIPMENT_BASES:\n"
        + "\n".join(f"  [{c}] {b!r} -> {t}" for c, b, t in invalid)
    )


def test_accessory_bases_recognised_as_valid():
    """Key accessory bases (rings, amulets) must be valid for the validator."""
    for base in ("Gold Ring", "Solar Amulet", "Heavy Belt", "Utility Belt", "Ornate Belt"):
        assert base in gen.VALID_EQUIPMENT_BASES, f"{base!r} missing from VALID_EQUIPMENT_BASES"


def test_always_pick_runes_not_empty():
    """ALWAYS_PICK_RUNES must cover both Emergent and standard runes."""
    assert len(gen.ALWAYS_PICK_RUNES) >= 9
    assert "Emergent Vigour" in gen.ALWAYS_PICK_RUNES
    assert "Iron Rune" in gen.ALWAYS_PICK_RUNES
    assert "Desert Rune" in gen.ALWAYS_PICK_RUNES
    # dead pre-0.5 names must stay gone (audit 2026-07-05)
    for dead in ("Destined Rune", "Phrecia Rune", "Skullbreaker Rune"):
        assert dead not in gen.ALWAYS_PICK_RUNES


def test_validate_flags_missing_hash_separator():
    """A rule with [StashItem] but no # should be an error."""
    bad = '[Type] == "Chaos Orb" [StashItem] == "true"'
    result = gen.validate_pickit([bad])
    assert any("separator" in m.lower() or "#" in m for _, m in result["errors"]), (
        f"Validator did not flag missing # separator. errors={result['errors']}"
    )


def test_item_name_corrections_no_redundant_none_entries():
    """Items in ITEM_NAME_SKIP should not also have None in ITEM_NAME_CORRECTIONS."""
    redundant = [k for k, v in gen.ITEM_NAME_CORRECTIONS.items()
                 if v is None and k in gen.ITEM_NAME_SKIP]
    assert not redundant, f"Redundant None corrections (already in ITEM_NAME_SKIP): {redundant}"


def test_loot_filter_header_documents_unique_name_limitation():
    """The generated .filter must warn about [UniqueName] not being replicable."""
    out = "\n".join(gen.build_loot_filter(['[Type] == "Chaos Orb" # [StashItem] == "true"']))
    assert "UniqueName" in out, "Loot filter missing [UniqueName] limitation comment"


def test_chance_bases_no_duplicates():
    """CHANCE_BASES must not list the same base type twice."""
    bases = [b for _, b, _ in gen.CHANCE_BASES]
    duplicates = {b for b in bases if bases.count(b) > 1}
    assert not duplicates, f"Duplicate entries in CHANCE_BASES: {duplicates}"


def test_new_bases_generate_gear_rules():
    """Newly added bases (Tattered Robe, Cultist Crown, etc.) must appear in build_base_rules."""
    new_bases = ["Tattered Robe", "Cultist Crown", "Fine Bracers", "Spiral Wraps",
                 "Braced Sabatons", "Heavy Belt", "Utility Belt", "Ornate Belt", "Omen Sceptre"]
    rules_text = "\n".join(gen.build_base_rules())
    for base in new_bases:
        assert f'"{base}"' in rules_text, f"{base!r} missing from build_base_rules output"


# ── Round 3: version sync, requirements, craft base loot filter ───────────────

def test_version_sync():
    """The package VERSION must not be ahead of the GUI VERSION constant.
    (release.yml enforces exact tag == version.py == VERSION at release time.)"""
    from exilebot_pickit.version import VERSION as pkg_ver
    from exilebot_pickit.ui.updater import VERSION as gui_ver

    def vt(v):
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))

    assert vt(pkg_ver) <= vt(gui_ver), (
        f"version.py={pkg_ver!r} is AHEAD of GUI VERSION={gui_ver!r}"
    )


def test_requirements_has_ui_deps():
    """The WebView2 UI needs pywebview + pystray; the Tk stack must be gone."""
    with open("requirements.txt", encoding="utf-8") as f:
        reqs = f.read()
    assert "pywebview" in reqs, "pywebview missing from requirements.txt"
    assert "pystray" in reqs, "pystray missing from requirements.txt"
    assert "customtkinter" not in reqs, "customtkinter should be removed (Tk UI deleted)"


def test_craft_base_rules_appear_in_loot_filter():
    """Normal-rarity craft bases must show up in the generated .filter."""
    craft_lines = gen.build_craft_base_rules()
    lf_text = "\n".join(gen.build_loot_filter(craft_lines))
    assert "Rarity = Normal" in lf_text, "Craft base Normal rules missing from loot filter"


def test_validate_pickit_passes_on_chance_base_rules():
    """build_chance_base_rules output must pass validation with zero errors."""
    result = gen.validate_pickit(gen.build_chance_base_rules())
    assert result["errors"] == [], f"Chance base rules have validation errors: {result['errors']}"


def test_validate_pickit_passes_on_static_tablet_rules():
    """Tablet/wombgift/special builders must pass validation with zero errors."""
    lines = (gen.build_tablet_rules() + gen.build_wombgift_rules()
             + gen.build_special_item_rules())
    result = gen.validate_pickit(lines)
    assert result["errors"] == [], f"Static tablet rules validation errors: {result['errors']}"


# ── Round 4: cache pruning, min_ilvl wiring, craft rules with custom ilvl ─────

def test_prune_disk_cache_exists():
    """prune_disk_cache must be a callable in the generator module."""
    assert callable(gen.prune_disk_cache)


def test_prune_disk_cache_no_dir_returns_zero():
    """prune_disk_cache with no dir set must return 0 without crashing."""
    original = gen._DISK_CACHE_DIR
    gen._DISK_CACHE_DIR = ""
    result = gen.prune_disk_cache()
    gen._DISK_CACHE_DIR = original
    assert result == 0


def test_prune_disk_cache_removes_old_files(tmp_path):
    """prune_disk_cache must delete JSON files older than max_age_days."""
    import os
    gen.set_disk_cache_dir(str(tmp_path))
    # Create a fake stale cache file (mtime set to 90 days ago)
    stale = tmp_path / "old_league__currency.json"
    stale.write_text('{"ts": 0, "payload": {}}')
    os.utime(stale, (0, 0))  # epoch = very old
    removed = gen.prune_disk_cache(max_age_days=60)
    assert removed == 1
    assert not stale.exists()
    gen.set_disk_cache_dir("")  # reset


def test_prune_disk_cache_keeps_recent_files(tmp_path):
    """prune_disk_cache must NOT delete files younger than max_age_days."""
    gen.set_disk_cache_dir(str(tmp_path))
    recent = tmp_path / "new_league__currency.json"
    recent.write_text('{"ts": 0, "payload": {}}')
    # mtime is now (just created) — should survive pruning
    removed = gen.prune_disk_cache(max_age_days=60)
    assert removed == 0
    assert recent.exists()
    gen.set_disk_cache_dir("")


def test_craft_base_rules_custom_ilvl_in_rule():
    """build_craft_base_rules(min_ilvl=75) must emit rules with ilvl 75 after #."""
    rules = [l for l in gen.build_craft_base_rules(min_ilvl=75) if "[StashItem]" in l]
    for rule in rules:
        after = rule.split("#", 1)[1]
        assert '[ItemLevel] >= "75"' in after, f"ilvl 75 missing from action block: {rule}"


# ── Round 6: CLI flags, sort order, base-level default ───────────────────────

def test_cli_version_flag():
    """python -m exilebot_pickit.generator --version must print version and exit 0."""
    import subprocess
    r = subprocess.run(
        ["python", "-m", "exilebot_pickit.generator", "--version"],
        capture_output=True, text=True
    )
    assert r.returncode == 0
    from exilebot_pickit.version import VERSION as ver
    assert ver in (r.stdout + r.stderr), f"Version {ver!r} not in --version output"


def test_base_min_level_cli_default_matches_constant():
    """CRAFT_BASE_MIN_ILVL constant is 82 and used by the CLI."""
    from exilebot_pickit import generator as gen
    assert gen.CRAFT_BASE_MIN_ILVL == 82


# ── Round 6: hardcoded constants, GUI consistency ─────────────────────────────

def test_webui_uses_min_level_constant():
    """The web API snapshot must fall back to base_min_level 82 (the constant's
    value) and expose it via app_info — guards against silent drift."""
    from exilebot_pickit import generator as gen
    assert gen.CRAFT_BASE_MIN_ILVL == 82
    with open("src/exilebot_pickit/webui/api.py", encoding="utf-8") as f:
        api_src = f.read()
    assert '"base_min_level", 82' in api_src


def test_requirements_has_pillow():
    """Pillow is required for icon loading — must be in requirements.txt."""
    with open("requirements.txt", encoding="utf-8") as f:
        reqs = f.read()
    assert "Pillow" in reqs, "Pillow missing from requirements.txt"


def test_build_unique_lines_sorted_high_to_low():
    """Unique rules must be written most-valuable first, like every other category.
    Regression test for the `key=-r[0]` + reverse=True double-negative that listed
    uniques cheapest-first."""
    import re
    payload = {
        "core": {"rates": {"exalted": 1.0}},
        "lines": [
            {"name": "Cheap Unique",  "baseType": "Coral Amulet", "primaryValue": 5.0},
            {"name": "Pricey Unique", "baseType": "Gold Ring",    "primaryValue": 500.0},
            {"name": "Mid Unique",    "baseType": "Jade Amulet",  "primaryValue": 50.0},
        ],
    }
    out  = gen.build_unique_lines(payload, 100.0, min_exalt=0.0)
    vals = [float(re.search(r"ExValue = ([\d.]+)", l).group(1)) for l in out]
    assert vals == sorted(vals, reverse=True), f"uniques not sorted high→low: {vals}"


def test_webui_entry_and_api_import():
    """The packaged entry point routes to the web UI and the bridge imports
    cleanly (no Tk dependency left)."""
    with open("src/exilebot_pickit/__main__.py", encoding="utf-8") as f:
        assert "webui.poc" in f.read()
    from exilebot_pickit.webui.api import AppApi
    for m in ("generate", "economy", "suggest_floors", "league_start_preset"):
        assert hasattr(AppApi, m)


def test_all_new_bases_have_correct_ilvl_placement():
    """All newly added bases must have [ItemLevel] after # in build_base_rules."""
    new_bases = ["Fine Bracers", "Spiral Wraps", "Braced Sabatons", "Cultist Crown",
                 "Tattered Robe", "Omen Sceptre", "Ancient Leggings", "Voltfang Talisman"]
    rules = gen.build_base_rules()
    for base in new_bases:
        base_rules = [r for r in rules if f'"{base}"' in r and "[StashItem]" in r]
        assert base_rules, f"No rules generated for {base!r}"
        for rule in base_rules:
            before = rule.split("#", 1)[0]
            assert "[ItemLevel]" not in before, f"[ItemLevel] before # for {base}: {rule}"


def test_talismans_weapon_category_generates_rules():
    """Talismans — the Druid's weapon (PoE2 0.4, Dec 2025) — a whole base category
    that was missing from the stale data. Every base must produce a pickup rule."""
    from exilebot_pickit.data import base_types as bt
    tals = [n for n, _ in bt._BASE_TYPES_BY_CATEGORY.get("Talismans", ())]
    assert len(tals) == 25, f"expected 25 talisman bases, got {len(tals)}"
    rules = gen.build_base_rules()
    for name in tals:
        assert any(f'"{name}"' in r for r in rules), f"no rule generated for {name!r}"
