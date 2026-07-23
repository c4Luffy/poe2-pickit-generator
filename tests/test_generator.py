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
    # "Dustbloom" is in KNOWN_INVALID_TYPES. The two Necrotic Catalysts left that
    # set on 2026-07-20 — they are real released currency, and the bot-validator
    # complaint they were blocked for turned out to be cosmetic.
    res = gen.validate_pickit(['[Type] == "Dustbloom" # [StashItem] == "true"'])
    assert any("Invalid base type" in m for _, m in res["errors"])


def test_the_necrotic_catalysts_are_no_longer_suppressed():
    """They were skipped AND flagged invalid, costing a ~145 ex pickup every time
    one dropped. Both are released StackableCurrency (drop levels 30 and 50); the
    shipped pickit already carries five names that same bot validator flags
    without the bot minding; and the app already picks up Refined Sibilant
    Catalyst at ~2374 ex — the identical family and naming pattern."""
    for name in ("Necrotic Catalyst", "Refined Necrotic Catalyst"):
        assert name not in gen.ITEM_NAME_SKIP
        assert name not in gen.KNOWN_INVALID_TYPES
        rule = f'[Type] == "{name}" # [StashItem] == "true"'
        assert gen.validate_pickit([rule])["errors"] == []


def test_validate_flags_unknown_equipment_base():
    line = '[Type] == "Notarealbase" && [Quality] >= "28" # [StashItem] == "true"'
    res = gen.validate_pickit([line])
    assert any("Invalid base type" in m for _, m in res["errors"])


def test_validate_flags_missing_stashitem():
    res = gen.validate_pickit(['[Type] == "Chaos Orb" # [Foo] == "true"'])
    assert any("StashItem" in m for _, m in res["errors"])


# ── build_exchange_lines ─────────────────────────────────────────────────────

def test_exchange_skips_skip_items(monkeypatch):
    """ITEM_NAME_SKIP is empty today — see
    test_the_necrotic_catalysts_are_no_longer_suppressed — so this pins the
    MECHANISM with a stand-in name rather than a real one."""
    monkeypatch.setattr(gen, "ITEM_NAME_SKIP", {"Bogus Skipped Item"})
    payload = _payload([(1, "Bogus Skipped Item", 50.0), (2, "Chaos Orb", 1.0)], rate=1.0)
    out = "\n".join(gen.build_exchange_lines(payload, divine_rate_exalts=200.0))
    assert "Bogus Skipped Item" not in out
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

# NOTE (2026-07-11): [ItemLevel] moved BEFORE the # across all base rules —
# the bot reads game memory, so ilvl is known pre-pickup (its own editor lists
# Item Level under BEFORE IDENTIFY). Pre-# filtering means low-level bases are
# never picked up at all, instead of hauled home and vendored after identify.

def test_craft_base_ilvl_is_before_hash():
    """[ItemLevel] must be a pre-pickup filter (before #) — owner format."""
    rules = [l for l in gen.build_craft_base_rules() if "[StashItem]" in l]
    assert rules, "No craft base rules generated"
    for rule in rules:
        before, after = rule.split("#", 1)
        assert "[ItemLevel]" in before, (
            f"[ItemLevel] missing from the pre-pickup filter (BEFORE #)\n  {rule}"
        )
        assert "[ItemLevel]" not in after, (
            f"[ItemLevel] duplicated in the action block (AFTER #)\n  {rule}"
        )


def test_build_base_rules_ilvl_is_before_hash():
    """Same check for endgame gear bases from build_base_rules()."""
    rules = [l for l in gen.build_base_rules() if "[ItemLevel]" in l]
    assert rules, "No base rules with [ItemLevel] found"
    for rule in rules:
        before, after = rule.split("#", 1)
        assert "[ItemLevel]" in before, (
            f"[ItemLevel] missing from pre-pickup filter (BEFORE #) in base rule:\n  {rule}"
        )


def test_craft_base_custom_ilvl_reflected_in_filter_block():
    """A custom min_ilvl value must appear before # (ground filter)."""
    rules = [l for l in gen.build_craft_base_rules(min_ilvl=75) if "[StashItem]" in l]
    for rule in rules:
        before, after = rule.split("#", 1)
        assert '[ItemLevel] >= "75"' in before
        assert '[ItemLevel] >= "75"' not in after


def test_craft_base_ilvl_overrides_per_base():
    """A user per-base ilvl override wins; other bases keep their own default."""
    out = gen.build_craft_base_rules(min_ilvl=82, ilvl_overrides={"Dueling Wand": 90})
    assert '[ItemLevel] >= "90"' in next(l for l in out if '"Dueling Wand"' in l)
    # non-overridden armour keeps the global default
    assert '[ItemLevel] >= "82"' in next(l for l in out if '"Soldier Cuirass"' in l)
    # built-in accessory default still applies when the user hasn't overridden it
    assert '[ItemLevel] >= "75"' in next(l for l in out if '"Solar Amulet"' in l)


def test_craft_base_default_ilvl_helper():
    assert gen.craft_base_default_ilvl("Solar Amulet", 82) == 75   # accessory override
    assert gen.craft_base_default_ilvl("Soldier Cuirass", 82) == 82  # falls back to global
    assert gen.craft_base_default_ilvl("Soldier Cuirass", 70) == 70


def test_validate_pickit_allows_ilvl_before_hash():
    """[ItemLevel] before # is VALID — the bot reads game memory, so it knows a
    ground item's level pre-pickup (confirmed 2026-07-11 from the bot's own
    editor: Item Level is offered under BEFORE IDENTIFY). The validator must
    NOT flag it — pre-# filtering skips low-ilvl drops on the ground."""
    good = '[Type] == "Glorious Plate" && [Rarity] == "Normal" && [ItemLevel] >= "82" # [StashItem] == "true"'
    result = gen.validate_pickit([good])
    flagged = result["errors"] + result["warnings"]
    assert not any("ItemLevel" in m for _, m in flagged), (
        f"Validator wrongly flagged pre-# ItemLevel: {flagged}"
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
    # Wrath Sceptre replaced Hallowed Sceptre 2026-07-12 (Hallowed is in the
    # game's item table but does not drop, so it left the base lists).
    new_bases = ["Soldier Cuirass", "Imperial Greathelm", "Massive Mitts", "Tasalian Greaves",
                 "Heavy Belt", "Utility Belt", "Ornate Belt", "Wrath Sceptre"]
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
    """The WebView2 UI needs pywebview. The Tk stack is gone, and so are pystray and
    Pillow — the system tray was their only user, and it silently broke self-update by
    keeping the process (and its lock on the .exe) alive after the window closed."""
    with open("requirements.txt", encoding="utf-8") as f:
        reqs = f.read()
    assert "pywebview" in reqs, "pywebview missing from requirements.txt"
    assert "customtkinter" not in reqs, "customtkinter should be removed (Tk UI deleted)"
    assert "pystray" not in reqs, "pystray is back — the tray was removed on purpose"
    assert "Pillow" not in reqs, "Pillow is back — only the tray ever needed it"


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
    """build_craft_base_rules(min_ilvl=75) must emit the ilvl gate BEFORE the #
    (owner format — the bot filters on the ground, so low-ilvl bases are never
    picked up at all instead of vendored after identify)."""
    rules = [l for l in gen.build_craft_base_rules(min_ilvl=75) if "[StashItem]" in l]
    for rule in rules:
        before = rule.split("#", 1)[0]
        assert '[ItemLevel] >= "75"' in before, f"ilvl 75 missing from pre-# block: {rule}"


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


# ── CLI ↔ GUI section parity ─────────────────────────────────────────────────

def test_cli_generate_emits_every_pickit_section():
    """The headless --cli generate must write the same sections a default GUI
    generate does. main() is network-heavy, so guard at the source level: every
    section builder the GUI worker calls has to stay wired into main(). Regression
    guard for the CLI silently dropping fracture / craft bases / exotic bases /
    magic-rare flasks — it emitted rare gear but none of those before 2026-07-12."""
    import inspect
    src = inspect.getsource(gen.main)
    for builder in (
        "build_tablet_rules", "build_wombgift_rules", "build_special_item_rules",
        "build_exotic_base_rules", "build_chance_base_rules",
        "build_craft_base_rules", "build_fracture_pickit_rules",
        "build_magic_rare_rules", "rare_gear_body",
    ):
        assert builder in src, f"CLI generate no longer emits {builder}()"


def test_cli_parity_builders_produce_content():
    """The four sections the CLI used to miss must actually have content at their
    config-less defaults — an empty-by-default builder would make the parity guard
    above pass while the CLI still wrote nothing useful."""
    assert gen.build_exotic_base_rules(), "exotic bases empty by default"
    assert gen.build_craft_base_rules(), "craft bases empty by default"
    assert gen.build_fracture_pickit_rules({}), "fracture emits nothing with all classes on"
    assert gen.build_magic_rare_rules(), "magic & rare flask rules empty by default"


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


def test_anvil_only_bases_are_dropped_from_unique_rules():
    """Runeforged/Runemastered bases are made at the anvil from dropped items, so
    they never appear as ground loot and no pickup rule can fire on one. These
    rows used to be kept with the prefix stripped, on the assumption that the
    plain base is what drops — but the plain base does not always exist, and the
    rewrite then invented a base type the game has never had (owner ruling,
    2026-07-19: drop the row instead)."""
    assert gen.is_anvil_only_base("Runeforged Warden Bow")
    assert gen.is_anvil_only_base("Runemastered Verisium Cuffs")
    assert not gen.is_anvil_only_base("Warden Bow")

    payload = {"lines": [{"name": "Some Unique",
                          "baseType": "Runeforged Warden Bow", "primaryValue": 100.0}]}
    out = gen.build_unique_lines(payload, 1.0, min_exalt=0.0)
    assert not any("Runeforged" in ln for ln in out)
    assert not any('"Warden Bow"' in ln for ln in out), "must not invent a plain-base rule"


def test_unique_keeps_its_droppable_base_when_ninja_also_lists_an_anvil_one():
    """The Prisoner's Manacles is priced on both "Runemastered Verisium Cuffs"
    and "Kalguuran Cuffs". The game has no plain "Verisium Cuffs", so stripping
    the prefix emitted a rule that could never fire and that the bot's validator
    rejected. The real base must survive; the anvil one must not."""
    payload = {"lines": [
        {"name": "The Prisoner's Manacles", "baseType": "Runemastered Verisium Cuffs",
         "primaryValue": 100.0},
        {"name": "The Prisoner's Manacles", "baseType": "Kalguuran Cuffs",
         "primaryValue": 100.0},
    ]}
    out = gen.build_unique_lines(payload, 1.0, min_exalt=0.0)
    assert any('[Type] == "Kalguuran Cuffs"' in ln for ln in out)
    assert not any("Verisium" in ln for ln in out)


def test_webui_entry_and_api_import():
    """The packaged entry point routes to the web UI and the bridge imports
    cleanly (no Tk dependency left)."""
    with open("src/exilebot_pickit/__main__.py", encoding="utf-8") as f:
        assert "webui.poc" in f.read()
    from exilebot_pickit.webui.api import AppApi
    for m in ("generate", "economy", "suggest_floors", "exceptional_bases"):
        assert hasattr(AppApi, m)


def test_all_new_bases_have_correct_ilvl_placement():
    """Exceptional-base rules gate [ItemLevel] BEFORE the # (owner format) so
    the bot skips low-level bases on the ground instead of vendoring them."""
    # Wrath Sceptre replaced Hallowed Sceptre here 2026-07-12: Hallowed is still
    # in the game's item table but does not drop, so it was removed from the base
    # lists. The gate-placement behaviour under test is unchanged.
    new_bases = ["Polished Bracers", "Blacksteel Sabatons", "Imperial Greathelm",
                 "Vile Robe", "Wrath Sceptre", "Apostle Leggings"]
    rules = gen.build_base_rules()
    for base in new_bases:
        base_rules = [r for r in rules if f'"{base}"' in r and "[StashItem]" in r]
        assert base_rules, f"No rules generated for {base!r}"
        for rule in base_rules:
            before = rule.split("#", 1)[0]
            assert "[ItemLevel]" in before, f"[ItemLevel] missing from pre-# for {base}: {rule}"




def test_loot_filter_shows_salvage_and_stashunid_not_just_stashitem():
    """The in-game filter must SHOW every item the bot acts on (StashItem,
    StashUnid, Salvage) — else it hides items the bot wants (community bug)."""
    ipd = [
        '[Type] == "Divine Orb" # [StashItem] == "true"',
        '[Rarity] == "Normal" && [Sockets] > "0" # [Salvage] == "true"',
        '[Rarity] == "Magic" && [Sockets] > "0" # [Salvage] == "true"',
        '[Type] == "Some Base" # [StashUnid] == "true"',
    ]
    out = "\n".join(gen.build_loot_filter(ipd))
    # StashUnid item is shown
    assert '"Some Base"' in out
    # salvage rules (no [Type]) become rarity+socket Show blocks, not hidden
    assert "Rarity = Normal" in out and "Rarity = Magic" in out
    assert "Sockets >= 1" in out          # [Sockets] > "0" -> >= 1
    # a commented-out rule is still ignored
    ipd2 = ['//[Rarity] == "Rare" # [Salvage] == "true"']
    out2 = "\n".join(gen.build_loot_filter(ipd2))
    assert "Rarity = Rare" not in out2


# ── Full-scan regression tests (2026-07-15): exclusions at the consumer end ──

def test_disabled_unique_is_actually_excluded_from_output():
    """The set-builder side of exclusions is tested; this pins the CONSUMER —
    a regression here silently ignores every user exclusion."""
    payload = {"core": {"rates": {"exalted": 1.0}},
               "lines": [{"name": "Headhunter", "baseType": "Heavy Belt",
                          "primaryValue": 500.0},
                         {"name": "Kaom's Heart", "baseType": "Glorious Plate",
                          "primaryValue": 400.0}]}
    out = "\n".join(gen.build_unique_lines(payload, 1.0, min_exalt=0.0,
                                            disabled_names={"Headhunter"}))
    active = [l for l in out.splitlines()
              if "Headhunter" in l and not l.lstrip().startswith("//")]
    assert not active, "disabled unique still has an ACTIVE rule"
    assert "Kaom's Heart" in out                    # the enabled one still there


def test_disabled_currency_not_resurrected_by_always_names():
    """always_names must not override an explicit user disable — the subtle
    rule the exclusion pipeline depends on."""
    payload = {"core": {"rates": {"exalted": 1.0}},
               "items": [{"id": "exalted-orb", "name": "Exalted Orb"}],
               "lines": [{"id": "exalted-orb", "primaryValue": 1.0}]}
    out = "\n".join(gen.build_exchange_lines(
        payload, 1.0, min_exalt=0.0,
        enabled_names=set(),                        # user disabled EVERYTHING
        always_names=["Exalted Orb"]))
    active = [l for l in out.splitlines()
              if "Exalted Orb" in l and l.lstrip().startswith("[")]
    assert not active, "always_names resurrected an explicitly disabled item"


def test_special_items_keep_ignore_ritual_when_ninja_prices_them():
    """When poe.ninja also prices a Special Item, the economy force-branch emits
    it instead of build_special_item_rules — and used to write a bare
    [StashItem], so the two writers disagreed about [IgnoreRitual] depending on
    whether the item happened to be priced that day.

    Uses Expedition Logbook, which KEEPS the flag: it is a genuine ground drop
    (drop_level 78), so declining to re-buy a copy with tribute is a real
    saving. An Audience with the King is the deliberate exception — see
    test_the_ritual_pinnacle_fragment_can_be_bought_from_a_ritual.
    """
    name = "Expedition Logbook"
    payload = {"core": {"rates": {"exalted": 1.0}},
               "items": [{"id": "x", "name": name}],
               "lines": [{"id": "x", "primaryValue": 50.0}]}
    out = gen.build_exchange_lines(payload, 1.0, min_exalt=10.0,
                                   force_names=set(gen.always_pick_force_names()))
    rule = next(ln for ln in out if name in ln)
    assert '[IgnoreRitual] == "true"' in rule, rule
    # and it must match what the static builder would have written
    static = next(ln for ln in gen.build_special_item_rules(set()) if name in ln)
    assert rule.split("//")[0].strip() == static.strip()


def test_unique_report_never_claims_a_rule_the_pickit_lacks():
    """The CSV report and the .ipd must agree. The anvil guard was added to
    build_unique_lines but not to the report, so the report claimed hundreds of
    uniques were included that are nowhere in the pickit."""
    payload = {"core": {"rates": {"exalted": 1.0}},
               "lines": [
                   {"name": "Some Unique", "baseType": "Runemastered Silk Robe",
                    "primaryValue": 100.0},
                   {"name": "Some Unique", "baseType": "Silk Robe",
                    "primaryValue": 100.0},
               ]}
    rules = gen.build_unique_lines(payload, 1.0, min_exalt=0.0)
    rows = gen.collect_unique_report_rows("unique_armours", payload, 1.0, 0.0)
    included = [r for r in rows if str(r["included"]).lower() in ("yes", "true", "1")]
    assert len(included) == len(rules) == 1
    assert included[0]["base_type"] == "Silk Robe"
    anvil_row = next(r for r in rows if r["base_type"].startswith("Runemastered"))
    assert str(anvil_row["included"]).lower() in ("no", "false", "0")


def test_loot_filter_keeps_the_item_level_gate():
    """The .filter written beside a pickit dropped every [ItemLevel], so it showed
    low-level bases the pickit ignores — and disagreed with the .filter produced by
    importing that same pickit through Create your filter."""
    rule = ('[Type] == "Soldier Cuirass" && [Rarity] == "Normal" '
            '&& [ItemLevel] >= "82" # [StashItem] == "true"')
    out = "\n".join(gen.build_loot_filter([rule]))
    assert "ItemLevel >= 82" in out
    assert 'BaseType == "Soldier Cuirass"' in out


def test_loot_filter_does_not_merge_different_item_levels():
    """Two bases gated at different ilvls must not land in one block — that would
    hand one of them the other's gate."""
    rules = [
        '[Type] == "A Base" && [Rarity] == "Normal" && [ItemLevel] >= "82" # [StashItem] == "true"',
        '[Type] == "B Base" && [Rarity] == "Normal" && [ItemLevel] >= "79" # [StashItem] == "true"',
    ]
    body = "\n".join(gen.build_loot_filter(rules))
    blocks = [b for b in body.split("Show") if "BaseType" in b]
    for b in blocks:
        if '"A Base"' in b:
            assert "ItemLevel >= 82" in b and '"B Base"' not in b
        if '"B Base"' in b:
            assert "ItemLevel >= 79" in b


def test_cli_does_not_duplicate_a_priced_always_pick_item():
    """A name poe.ninja prices gets a rule in its own economy category, so the
    static builder must skip it or the file carries two rules for one item —
    with conflicting actions, since only one of them has [IgnoreRitual]. The GUI
    deduped these; the CLI did not, and shipped five duplicates."""
    dupes = {"Expedition Logbook", "Breach Splinter"}
    for build in (gen.build_special_item_rules, gen.build_tablet_rules):
        out = "\n".join(build(dupes))
        for name in dupes:
            assert f'[Type] == "{name}"' not in out, (build.__name__, name)
    # and with nothing to skip, they are still emitted
    assert '[Type] == "Expedition Logbook"' in "\n".join(gen.build_special_item_rules(set()))
    assert '[Type] == "Breach Splinter"' in "\n".join(gen.build_tablet_rules(set()))


def test_every_exchange_category_has_a_unique_key_and_type():
    """A whole poe.ninja category was missing for months.

    poe.ninja has always served "Verisium" and the app simply never fetched it,
    so all 24 items had no rule at ANY floor — Celestial Alloy at ~308 ex was
    being walked past. Nothing failed, because a category you don't ask for
    produces no error; it just silently isn't in your pickit.

    This can't detect a category nobody has heard of, but it does pin the list
    against typos and duplicates, which is how one would most likely be lost.
    """
    keys = [k for k, _t, _l, _u in gen.ALL_CATEGORIES]
    types = [t for _k, t, _l, _u in gen.ALL_CATEGORIES]
    assert len(keys) == len(set(keys)), "duplicate category key"
    assert len(types) == len(set(types)), "duplicate poe.ninja type"
    assert "verisium" in keys, "Verisium dropped out of the fetch list again"
    for k, t, label, _u in gen.ALL_CATEGORIES:
        assert k and t and label, (k, t, label)
        assert k == k.lower(), f"category key should be lowercase: {k}"


# ── Tablets: priced live via poe.ninja (added 2026-07-23) ────────────────────

def test_build_tablet_market_lines_sorted_high_to_low_and_gates_on_rarity():
    """poe.ninja's PrecursorTablets category prices each tablet type PER
    RARITY variant — the emitted rule must gate on [Rarity], never
    [UniqueName], and rows sort most-valuable first like every other builder."""
    payload = {
        "core": {"rates": {"exalted": 10.0}},
        "lines": [
            {"name": "Abyss Tablet", "baseType": "Abyss Tablet",
             "variant": "Magic", "primaryValue": 1.0},
            {"name": "Abyss Tablet", "baseType": "Abyss Tablet",
             "variant": "Normal", "primaryValue": 5.0},
        ],
    }
    out = gen.build_tablet_market_lines(payload, 1.0, min_exalt=0.0)
    assert out[0] == ('[Type] == "Abyss Tablet" && [Rarity] == "Normal" '
                      '# [StashItem] == "true" // ExValue = 50.00')
    assert out[1] == ('[Type] == "Abyss Tablet" && [Rarity] == "Magic" '
                      '# [StashItem] == "true" // ExValue = 10.00')
    assert '[UniqueName]' not in "\n".join(out)


def test_build_tablet_market_lines_below_floor_is_commented_not_dropped():
    payload = {"core": {"rates": {"exalted": 1.0}},
               "lines": [{"name": "Temple Tablet", "baseType": "Temple Tablet",
                          "variant": "Rare", "primaryValue": 1.0}]}
    out = gen.build_tablet_market_lines(payload, 1.0, min_exalt=50.0)
    assert out and out[0].startswith("//")
    assert '[Type] == "Temple Tablet" && [Rarity] == "Rare"' in out[0]


def test_build_tablet_market_lines_skips_rows_missing_base_or_variant():
    payload = {"core": {"rates": {"exalted": 1.0}},
               "lines": [{"name": "", "baseType": "", "variant": "Normal", "primaryValue": 5.0},
                         {"name": "Breach Tablet", "baseType": "Breach Tablet",
                          "variant": None, "primaryValue": 5.0}]}
    assert gen.build_tablet_market_lines(payload, 1.0, min_exalt=0.0) == []


def test_tablets_are_no_longer_force_picked_regardless_of_price():
    """Regular tablets used to be force-picked (poe.ninja never priced them),
    so TABLET_TYPES lived in always_pick_force_names(). Now that poe.ninja
    prices them live, they must respect the normal value floor like any other
    market item instead of overriding it."""
    assert not (set(gen.TABLET_TYPES) & gen.always_pick_force_names())


def test_build_unique_lines_honours_force_names():
    """build_unique_lines had no force_names parameter at all, so the
    "always kept regardless of floor" guarantee every other builder gives
    always_pick_force_names() silently did not apply here. Dormant today
    (nothing force-picked is currently priced as a unique), but the
    guarantee must hold if that ever changes (audited 2026-07-21)."""
    payload = {"core": {"rates": {"exalted": 1.0}}, "lines": [{
        "name": "Forced Cheap Unique", "baseType": "Coral Amulet", "primaryValue": 0.1}]}
    below_floor = gen.build_unique_lines(payload, 1.0, min_exalt=50.0)
    assert below_floor[0].startswith("//"), "should be commented: below floor, not forced"

    forced = gen.build_unique_lines(payload, 1.0, min_exalt=50.0,
                                    force_names={"Forced Cheap Unique"})
    assert not forced[0].startswith("//"), "force_names must override the floor"

    # an explicit disable still wins over force_names, same as the exchange builder
    forced_but_disabled = gen.build_unique_lines(payload, 1.0, min_exalt=50.0,
                                                 force_names={"Forced Cheap Unique"},
                                                 disabled_names={"Forced Cheap Unique"})
    assert forced_but_disabled[0].startswith("//")
