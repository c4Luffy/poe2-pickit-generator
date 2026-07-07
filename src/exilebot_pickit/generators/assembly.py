"""Pure pickit-assembly logic — the rule-building half of a generate run.

Everything here is network-free, Tk-free, and I/O-free: it takes already-fetched
poe.ninja payloads plus a settings *snapshot* (a plain dict of the user's choices)
and returns the lines that get written to the ``.ipd``. The GUI's ``_generate``
keeps the fetching, threading, file writing and progress UI; it just delegates the
actual rule assembly to the functions below.

Splitting this out has two payoffs:
  • the generate pipeline becomes unit-testable without a display or the network
    (see test_assembly.py), and
  • the 550-line ``_generate`` god-method shrinks to orchestration.

Behaviour is intentionally identical to the old inline code — these functions were
lifted out of ``_generate`` statement-for-statement.
"""
from __future__ import annotations

import datetime
import re

from exilebot_pickit import generator as gen

_EXVALUE_RE = re.compile(r"ExValue = ([\d.]+)")
_UNIQUE_NAME_RE = re.compile(r'\[UniqueName\] == "([^"]+)"')
_FIRST_QUOTED_RE = re.compile(r'"([^"]+)"')


# ── Rule identity helpers (for diffing one pickit against another) ─────────────

def extract_rule_name(line: str) -> str | None:
    """The item identity a rule targets: its [UniqueName] if present, else the
    first quoted token (the [Type] / base name)."""
    um = _UNIQUE_NAME_RE.search(line)
    if um:
        return um.group(1)
    nm = _FIRST_QUOTED_RE.search(line)
    return nm.group(1) if nm else None


def active_rule_ids(lines) -> set[str]:
    """Identities of active (non-commented) rules — used to diff pickits."""
    ids: set[str] = set()
    for l in lines:
        if not l or l.startswith("//") or "[StashItem]" not in l:
            continue
        n = extract_rule_name(l)
        if n:
            ids.add(n)
    return ids


# ── File header (banner + the Exiled Bot 2 syntax guide) ──────────────────────

def build_header_lines(league: str, gen_ts: datetime.datetime, gen_id: str,
                       min_exalt: float, min_exalt_unique: float) -> list[str]:
    """The comment banner and embedded configuration guide that opens every .ipd."""
    return [
        "/" * gen._W,
        "//" + f"  EXILEBOT 2  |  PICKIT  |  ID: {gen_id}".center(gen._W - 4) + "//",
        "/" * gen._W,
        f"// League    : {league}",
        f"// Generated : {gen_ts.strftime('%Y-%m-%d %H:%M:%S')}",
        f"// Pickit ID : {gen_id}",
        f"// Threshold : {min_exalt:.0f} ex  (currency/items)  |  {min_exalt_unique:.0f} ex  (unique gear)",
        "/" * gen._W, "",
        # ── Configuration guide ───────────────────────────────────────
        "//",
        "// Exiled Bot 2 Pickit - Configuration Guide for Path of Exile 2",
        "//",
        "// This file defines which items your bot should pick up, identify, keep, or salvage.",
        "//",
        "// Important File:",
        "// - ModsList.html in the main bot folder contains all available mods",
        "//   (Use expressions from the right column, like local_minimum_added_physical_damage)",
        "//",
        "// Special Computed Values:",
        "// ----------------------",
        "// [TotalResistances] - Sums all resistance values on an item",
        '//   Example: [Category] == "Helmet" # [TotalResistances] > "50" && [StashItem] == "true"',
        "//",
        "// Defensive Calculations:",
        "// ---------------------",
        "// [ComputedArmour]       - Final armour value after all modifiers",
        "// [ComputedEvasion]      - Final evasion value after all modifiers",
        "// [ComputedEnergyShield] - Final ES value after all modifiers",
        "//",
        "// Damage Calculations:",
        "// ------------------",
        "// [DPS]         - Total weapon DPS (physical + elemental)",
        "// [ElementalDPS]  - Only elemental portion of weapon DPS",
        "// [PhysicalDPS]   - Only physical portion of weapon DPS",
        "//",
        "// Spell Damage Totals:",
        "// ------------------",
        "// [TotalSpellElementalDamage]  - Combined spell + elemental damage (%)",
        "// [TotalFireSpellDamage]       - Fire spell damage including general spell damage (%)",
        "// [TotalColdSpellDamage]       - Cold spell damage including general spell damage (%)",
        "// [TotalLightningSpellDamage]  - Lightning spell damage including general spell damage (%)",
        "//",
        "// Gems:",
        "// ----",
        "// [GemLevel] - Current level of the gem",
        '// Example: [Type] == "Uncut Support Gem" && [GemLevel] == "3" # [StashItem] == "true"',
        "//",
        "// UniqueName:",
        "// ----------",
        "// Matches specific unique items by their exact name",
        '// Example: [Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"',
        "//",
        "// ItemTier:",
        "// --------",
        "// Represents the tier of the item base type (higher is better)",
        '// Example: [Category] == "Ring" && [ItemTier] >= "2" # [StashItem] == "true"',
        "//",
        "// Quality:",
        "// -------",
        "// The quality percentage of an item (0-20 for most items)",
        '// Example: [Quality] >= "15" # [StashItem] == "true"',
        "//",
        "// WaystoneTier:",
        "// ------------",
        "// The tier of a waystone (1-16 at the moment)",
        '// Example: [Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"',
        "//",
        "// Basic Syntax:",
        "// -----------",
        "// Each line: [What to Check] Operator \"Value\"",
        "//",
        "// Operators: == != > >= < <=",
        "// Combine:   && (AND)  || (OR)  () (group)",
        "//",
        "// Available Categories:",
        '// Equipment : "BodyArmour", "Gloves", "Boots", "Belt", "Helmet", "Ring", "Amulet"',
        '// Weapons   : "Weapon", "1Handed", "2Handed", "OffHand"',
        '// Others    : "Flask", "Waystone", "Gem"',
        "//",
        "// WeaponCategory:",
        '// 1H : "Claw","Dagger","Wand","OneHandSword","OneHandAxe","OneHandMace","Sceptre","Spear","Flail"',
        '// 2H : "Bow","Staff","TwoHandSword","TwoHandAxe","TwoHandMace","Quarterstaff","Crossbow","Trap"',
        '// OH : "Quiver","Shield","Focus"',
        "//",
        "// Rarity Values:  \"Normal\", \"Magic\", \"Rare\", \"Unique\"",
        "//",
        "// Special Flags:",
        '// [StashItem]    == "true"  - Put item in stash',
        '// [StashUnid]    == "true"  - Stash without identifying',
        '// [Salvage]      == "true"  - Mark for salvaging',
        '// [IgnoreRitual] == "true"  - Ignore item from ritual rewards',
        "//",
        "// Rule split with #:",
        "// Before # = checked BEFORE identifying",
        "// After  # = checked AFTER  identifying",
        '// Example: [Rarity] == "Rare" # [TotalResistances] > "50" && [StashItem] == "true"',
        "//",
        "// Local vs Global Modifiers:",
        "// local_* mods (local_attack_speed_+%) affect only the item itself",
        "// regular mods (attack_speed_+%)       affect your entire character",
        "//",
        "/" * gen._W, "",
    ]


# ── Currency → Divine conversion rate ─────────────────────────────────────────

def compute_divine_rate(currency_payload: dict) -> tuple[float, bool, float]:
    """Return ``(divine_rate_exalts, divine_found, exalted_rate)`` from the
    currency payload — the exalt value of one Divine Orb."""
    items_by_id = {i["id"]: i for i in currency_payload.get("items", [])}
    rate = gen.exalted_rate(currency_payload)
    divine_rate_exalts = 1.0
    found = False
    for line in currency_payload.get("lines", []):
        item = items_by_id.get(line.get("id"))
        if item and item.get("name") == "Divine Orb":
            pv = float(line.get("primaryValue") or 0.0)
            divine_rate_exalts = pv * rate if rate else pv
            found = True
            break
    return divine_rate_exalts, found, rate


# ── Per-category rule building ────────────────────────────────────────────────

def effective_min(snapshot: dict, key: str, is_unique: bool,
                  min_exalt_gear: float, min_exalt_unique: float) -> float:
    """The exalt threshold for a category: its per-category override when set
    (>= 0), otherwise the appropriate global (unique gear vs everything else)."""
    cat_thresh = snapshot.get("cat_thresh", {}).get(key, -1.0)
    if not isinstance(cat_thresh, (int, float)):
        cat_thresh = -1.0
    global_min = min_exalt_unique if is_unique else min_exalt_gear
    return cat_thresh if cat_thresh >= 0 else global_min


def enabled_names_for(key: str, is_unique: bool, payload: dict,
                      cat_states: dict) -> set[str] | None:
    """The set of item names to keep for an exchange category given the Items-tab
    on/off state, or ``None`` to fall back to pure threshold filtering (the default
    when nothing is disabled, and always for uniques)."""
    if cat_states and not is_unique:
        items_in_payload = {
            gen.ITEM_NAME_CORRECTIONS.get(i["name"], i["name"])
            for i in payload.get("items", []) if i.get("name")
        }
        disabled = {n for n, s in cat_states.items() if not s.get("enabled", True)}
        return items_in_payload - disabled
    return None


def build_category_lines(key: str, is_unique: bool, payload: dict,
                         divine_rate_exalts: float, eff_min: float,
                         min_exalt_gear: float,
                         enabled_names: set[str] | None,
                         cat_states: dict | None = None) -> list[str]:
    """Build the pickit lines for one economy category, dispatching to the right
    builder in poe2_pickit_generator based on the category key."""
    if is_unique:
        dis = {n for n, s in (cat_states or {}).items()
               if not s.get("enabled", True)}
        return gen.build_unique_lines(payload, divine_rate_exalts, min_exalt=eff_min,
                                      disabled_names=dis)
    if key == "uncut_gems":
        return gen.build_uncut_gem_lines(payload, divine_rate_exalts, min_exalt=eff_min,
                                         enabled_names=enabled_names)
    if key == "waystones":
        # waystone rows are synthetic (poe.ninja doesn't price them), so the
        # Economy-tab toggles come from cat_states, not the payload names
        dis = {n for n, s in (cat_states or {}).items()
               if not s.get("enabled", True)}
        return gen.build_waystone_lines(disabled=dis)
    pick_all  = key in gen.PICK_ALL_CATEGORIES
    tier_sort = (key == "essences")
    always    = gen.ALWAYS_PICK_CURRENCY if key == "currency" else (
        gen.ALWAYS_PICK_RUNES if key == "runes" else None)
    ritual_th = min_exalt_gear if key == "omens" else None
    return gen.build_exchange_lines(payload, divine_rate_exalts,
                                    pick_all=pick_all,
                                    min_exalt=eff_min,
                                    tier_sort=tier_sort,
                                    enabled_names=enabled_names,
                                    always_names=always,
                                    force_names=gen.always_pick_force_names(),
                                    ritual_threshold=ritual_th)


def top_items_from_lines(lines) -> list[tuple[str, float]]:
    """Pull ``(name, exalt_value)`` pairs out of active rules that carry an
    ``ExValue =`` comment — used to surface the most valuable picks."""
    out: list[tuple[str, float]] = []
    for l in lines:
        if l.startswith("//") or "[StashItem]" not in l:
            continue
        name = extract_rule_name(l)
        vm = _EXVALUE_RE.search(l)
        if name and vm:
            out.append((name, float(vm.group(1))))
    return out


# ── Static / curated sections (tablets, wombgifts, chance, craft bases) ────────

def chance_base_disabled(snapshot: dict) -> set[str]:
    return {
        base for base, st in snapshot.get("item_states", {}).get("_chance", {}).items()
        if not st.get("enabled", True)
    }


def craft_base_section(snapshot: dict) -> tuple[list[str], int, int]:
    """Return ``(lines, rule_count, floor_ilvl)`` for the craft-base section.

    Every visible craft base carries an explicit per-base ilvl in the snapshot
    (the GUI bakes the value shown in each Craft Bases card into item_states before
    generating), so the .ipd always matches what the tab displays. ``floor_ilvl`` is
    the lowest level actually emitted among enabled bases, used for the section
    header so it never claims a level the rules don't use.
    """
    cb_states = snapshot.get("item_states", {}).get("_craftbase", {})
    disabled = {name for name, st in cb_states.items() if not st.get("enabled", True)}
    overrides = {name: st["ilvl"] for name, st in cb_states.items() if "ilvl" in st}
    global_min = int(snapshot.get("base_min_level", gen.CRAFT_BASE_MIN_ILVL))
    active_ilvls = [v for n, v in overrides.items() if n not in disabled]
    floor = min(active_ilvls) if active_ilvls else global_min
    lines = gen.build_craft_base_rules(disabled, min_ilvl=floor, ilvl_overrides=overrides)
    count = sum(1 for l in lines if l.startswith("[Type]"))
    return lines, count, floor


def rare_section(snapshot: dict) -> list[str]:
    """Rare-gear rules for the Rare tab.

    The tab is designed one class at a time with the user; a class emits rules
    only once its approved design exists in ``gen.RARE_DESIGNED``. With no
    designs landed yet this always returns ``[]`` — the pipeline hook exists so
    each class only has to plug in here as it goes live.
    """
    if not gen.RARE_DESIGNED:
        return []
    return []


# ── Price-move alerts ─────────────────────────────────────────────────────────

def compute_price_alerts(categories, all_payloads: dict,
                         prev_league_prices: dict, chaos_ex_val: float,
                         threshold: float = 0.20):
    """Compare current vs previous-run prices and flag big movers.

    Returns ``(new_gen_prices, alerts)`` where ``new_gen_prices`` is
    ``{cat_key: {name: exalt_value}}`` (the new baseline to persist) and ``alerts``
    is a list of ``(abs_delta, display_text)`` for moves of at least *threshold*.
    """
    new_gen_prices: dict = {}
    alerts: list[tuple[float, str]] = []

    for key, _t, _label, _is_unique in categories:
        payload = all_payloads.get(key)
        if not payload or isinstance(payload, Exception):
            continue
        rate = gen.exalted_rate(payload)
        items_by_id = {i["id"]: i for i in payload.get("items", [])}
        cur_prices: dict = {}
        for line in payload.get("lines", []):
            item = items_by_id.get(line.get("id"))
            if not item or not item.get("name"):
                continue
            raw_name = item["name"]
            if raw_name in gen.ITEM_NAME_SKIP:
                continue
            name = gen.ITEM_NAME_CORRECTIONS.get(raw_name, raw_name)
            pv = float(line.get("primaryValue") or 0.0)
            ex = pv * rate if rate else pv  # same convention as build_exchange_lines
            cur_prices[name] = ex
        new_gen_prices[key] = cur_prices

        prev_cat = prev_league_prices.get(key, {})
        for name, ex_now in cur_prices.items():
            ex_prev = prev_cat.get(name)
            if ex_prev is None or ex_prev <= 0 or ex_now <= 0:
                continue
            delta = (ex_now - ex_prev) / ex_prev
            if abs(delta) < threshold:
                continue
            chaos_now  = ex_now  / chaos_ex_val if chaos_ex_val else ex_now
            chaos_prev = ex_prev / chaos_ex_val if chaos_ex_val else ex_prev
            # Skip near-worthless items — they round to "0c → 0c" and just spam the
            # panel with meaningless huge percentages.
            if max(chaos_now, chaos_prev) < 1.0:
                continue
            sign  = "+" if delta > 0 else ""
            arrow = "▲" if delta > 0 else "▼"
            text = f"{arrow} {name}: {chaos_prev:.0f}c → {chaos_now:.0f}c  ({sign}{delta*100:.0f}%)"
            alerts.append((abs(delta), text))

    return new_gen_prices, alerts
