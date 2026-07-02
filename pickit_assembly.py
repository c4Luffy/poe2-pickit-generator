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

import poe2_pickit_generator as gen
import rare_gear_catalog as rgc
import rare_gear_templates as rgt

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
                         enabled_names: set[str] | None) -> list[str]:
    """Build the pickit lines for one economy category, dispatching to the right
    builder in poe2_pickit_generator based on the category key."""
    if is_unique:
        return gen.build_unique_lines(payload, divine_rate_exalts, min_exalt=eff_min)
    if key == "uncut_gems":
        return gen.build_uncut_gem_lines(payload, divine_rate_exalts, min_exalt=eff_min,
                                         enabled_names=enabled_names)
    if key == "waystones":
        return gen.build_waystone_lines()
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


# ── Rare gear (pick up rares scored by computed values) ───────────────────────

# Non-negative int setting from the snapshot; bad values → default.
_rare_gear_int = gen.cfg_int


def build_rare_gear_rules(snapshot: dict) -> list[str]:
    """WeightedSum pickup rules for the enabled equipment slots.

    Reads snapshot['rare_gear'] = {token: {enabled, threshold}} and emits one rule
    per enabled slot, using that slot's bot-derived mod-weight preset
    (gen.WEIGHTED_SUM_PRESETS). Returns [] when nothing is enabled — so by default
    this section adds nothing to the .ipd.

    Anti-clutter settings (all from the snapshot):
    - rare_gear_magic (default False): also match Magic items alongside Rare.
    - rare_gear_min_ilvl (default gen.RARE_GEAR_MIN_ILVL_DEFAULT): only stash
      items of at least this item level (post-#; ilvl is read after identify).
      0 disables the check.
    - rare_gear_min_tier (default 0 = off): only pick up bases of at least this
      [ItemTier] (pre-#, so low-tier bases aren't even picked up)."""
    cfg = snapshot.get("rare_gear", {})
    if not isinstance(cfg, dict):
        return []
    include_magic = bool(snapshot.get("rare_gear_magic", False))
    min_ilvl = _rare_gear_int(snapshot, "rare_gear_min_ilvl", gen.RARE_GEAR_MIN_ILVL_DEFAULT)
    min_tier = _rare_gear_int(snapshot, "rare_gear_min_tier", 0)
    lines: list[str] = []
    for token, _disp, _kind in gen.RARE_GEAR_SLOTS:
        slot = cfg.get(token)
        if not isinstance(slot, dict) or not slot.get("enabled"):
            continue
        preset = gen.WEIGHTED_SUM_PRESETS.get(token)
        if not preset or not preset[1]:
            continue
        def_threshold, mods = preset
        try:
            threshold = float(slot.get("threshold", def_threshold))
        except (TypeError, ValueError):
            threshold = def_threshold
        threshold = int(threshold) if float(threshold).is_integer() else threshold
        selector = gen.rare_gear_selector(token)
        if min_tier > 0 and token != "Jewel":   # jewels have no base tier
            selector += f' && [ItemTier] >= "{min_tier}"'
        lines.append(build_weighted_sum_rule(
            selector, mods, threshold,
            include_magic=include_magic, min_ilvl=min_ilvl))
    return lines


# ── Rare gear Per-base mode (one [Type] rule per base, tiered brackets) ───────

_COMBO_LABELS = {
    "armour": "Armour", "evasion": "Evasion", "es": "Energy Shield",
    "armour_evasion": "Armour + Evasion", "armour_es": "Armour + ES",
    "evasion_es": "Evasion + ES", "tri": "Str/Dex/Int", "all": "",
}
_BRACKET_LABELS = {"low": "Low (campaign)", "mid": "Mid (cruel)", "high": "High (endgame)"}


def _round5(x: float) -> int:
    return max(5, int(round(x / 5.0)) * 5)


def _pro_rule(name: str, tier: int, rarity: str, mods, thr, pre: str | None = None) -> str:
    terms = ",".join(weighted_sum_term(*m) for m in mods)
    gate = f"{pre} && " if pre else ""
    return (f'[Type] == "{name}" && [ItemTier] >= "{int(tier)}" && [Rarity] == "{rarity}" '
            f'# {gate}[WeightedSum({terms})] >= "{thr:g}" && [StashItem] == "true"')


def pro_section_key(family: str, combo: str, bracket: str) -> str:
    return f"{family}|{combo}|{bracket}"


def build_rare_gear_pro_rules(snapshot: dict) -> list[str]:
    """Per-base WeightedSum rules — the Rare Gear tab's Per-base (Pro) mode.

    Reads snapshot['rare_gear_pro'] = {
        'sections': {'Family|combo|bracket': {'on', 'thr', 'tier', 'ps', 'magic'}},
        'jewels':   {'<archetype>': {'on', 'thr'}, '<single>': {'on'}},
        'expert':   {'on', 'text'},   # hand-written rules appended verbatim
    } and emits, per enabled section: one full rule per base in the bracket,
    plus auto-derived prefix-only (~60%) / suffix-only (~55%) rules when the
    family supports the split ('ps', default on), plus a single-mod Magic rule
    when 'magic' is set and the family has one. Everything defaults to off."""
    cfg = snapshot.get("rare_gear_pro")
    if not isinstance(cfg, dict):
        return []
    sections = cfg.get("sections", {}) if isinstance(cfg.get("sections"), dict) else {}
    lines: list[str] = []

    for family, groups in rgc.CATALOG.items():
        for combo, brackets in groups.items():
            tmpl = rgt.get_template(family, combo)
            if not tmpl:
                continue
            for bracket in ("low", "mid", "high"):
                s = sections.get(pro_section_key(family, combo, bracket))
                if not isinstance(s, dict) or not s.get("on"):
                    continue
                bases = brackets.get(bracket) or []
                if not bases:
                    continue
                try:
                    thr = float(s.get("thr", tmpl["thr"]))
                except (TypeError, ValueError):
                    thr = float(tmpl["thr"])
                thr = int(thr) if thr.is_integer() else thr
                try:
                    tier = int(s.get("tier", tmpl["tier"][bracket]))
                except (TypeError, ValueError):
                    tier = tmpl["tier"][bracket]

                label = " — ".join(x for x in (
                    rgc.FAMILY_LABELS.get(family, family),
                    _COMBO_LABELS.get(combo, combo),
                    _BRACKET_LABELS[bracket]) if x)
                pre = tmpl.get("pre")
                lines += ["", gen.header_minor(label)]
                for name in bases:
                    lines.append(_pro_rule(name, tier, "Rare", tmpl["full"], thr, pre))
                if s.get("ps", True) and tmpl.get("prefix") and tmpl.get("suffix"):
                    lines.append("//PREFIXES")
                    p_thr = _round5(thr * tmpl.get("p_pct", rgt.PREFIX_PCT))
                    for name in bases:
                        lines.append(_pro_rule(name, tier, "Rare", tmpl["prefix"], p_thr, pre))
                    lines.append("//SUFFIXES")
                    s_thr = _round5(thr * tmpl.get("s_pct", rgt.SUFFIX_PCT))
                    for name in bases:
                        lines.append(_pro_rule(name, tier, "Rare", tmpl["suffix"], s_thr, pre))
                if s.get("magic"):
                    lines.append("//MAGIC")
                    if tmpl.get("magic"):
                        stat, weight, m_thr = tmpl["magic"]
                        m_mods = [(stat, weight)]
                    else:
                        # no transcribed single-mod rule → score the full mod set
                        # at a fraction of the threshold (Magic has ≤ 2 mods)
                        m_mods, m_thr = tmpl["full"], _round5(thr * rgt.MAGIC_FALLBACK_PCT)
                    for name in bases:
                        lines.append(_pro_rule(name, tier, "Magic", m_mods, m_thr, pre))

    jewels = cfg.get("jewels", {}) if isinstance(cfg.get("jewels"), dict) else {}
    jewel_lines: list[str] = []
    for arch in rgt.JEWEL_ARCHETYPES:
        key, label, def_thr, body = arch[:4]
        rarities = arch[4] if len(arch) > 4 else ("Magic",)
        j = jewels.get(key)
        if not isinstance(j, dict) or not j.get("on"):
            continue
        try:
            thr = int(float(j.get("thr", def_thr)))
        except (TypeError, ValueError):
            thr = def_thr
        jewel_lines.append(f"// {label}")
        for rarity in rarities:
            jewel_lines.append(f'[Category] == "Jewel" && [Rarity] == "{rarity}" '
                               f'# {body.format(thr=thr)} && [StashItem] == "true"')
    for key, label, stat in rgt.JEWEL_SINGLES:
        j = jewels.get(key)
        if not isinstance(j, dict) or not j.get("on"):
            continue
        jewel_lines.append(f"// {label}")
        for rarity in ("Magic", "Rare"):
            jewel_lines.append(f'[Category] == "Jewel" && [Rarity] == "{rarity}" '
                               f'# [{stat}] >= "1" && [StashItem] == "true"')
    if jewel_lines:
        lines += ["", gen.header_minor("Jewels")] + jewel_lines

    # Amulets: build archetypes over every amulet base (+ Magic amulet rules).
    amulets = cfg.get("amulets", {}) if isinstance(cfg.get("amulets"), dict) else {}
    amu_lines: list[str] = []
    for arch in rgt.AMULET_ARCHETYPES:
        a = amulets.get(arch["key"])
        if not isinstance(a, dict) or not a.get("on"):
            continue
        try:
            thr = float(a.get("thr", arch["thr"]))
        except (TypeError, ValueError):
            thr = float(arch["thr"])
        thr = int(thr) if thr.is_integer() else thr
        amu_lines.append(f"// {arch['label']}")
        for name in rgc.AMULET_BASES:
            amu_lines.append(_pro_rule(name, 1, "Rare", arch["full"], thr))
        if a.get("ps", True) and arch.get("prefix"):
            amu_lines.append("//PREFIXES")
            p_thr = _round5(thr * arch.get("p_thr", arch["thr"] * 0.6) / arch["thr"])
            for name in rgc.AMULET_BASES:
                amu_lines.append(_pro_rule(name, 1, "Rare", arch["prefix"], p_thr))
        if a.get("ps", True) and arch.get("suffix"):
            amu_lines.append("//SUFFIXES")
            s_thr = _round5(thr * arch.get("s_thr", arch["thr"] * 0.55) / arch["thr"])
            for name in rgc.AMULET_BASES:
                amu_lines.append(_pro_rule(name, 1, "Rare", arch["suffix"], s_thr))
    m = amulets.get("magic")
    if isinstance(m, dict) and m.get("on"):
        gems, g_thr = rgt.AMULET_MAGIC_GEMS
        amu_lines.append("// Magic amulets (skill gem levels / rarity)")
        for name in rgc.AMULET_BASES:
            amu_lines.append(_pro_rule(name, 1, "Magic", gems, g_thr))
        stat, r_thr = rgt.AMULET_MAGIC_RARITY
        amu_lines.append(f'[Category] == "Amulet" && [Rarity] == "Magic" '
                         f'# [{stat}] >= "{r_thr}" && [StashItem] == "true"')
    if amu_lines:
        lines += ["", gen.header_minor("Amulets")] + amu_lines

    # Belts: one prefix rule + one suffix rule per base (+ optional Magic rule).
    belts = cfg.get("belts", {}) if isinstance(cfg.get("belts"), dict) else {}
    if belts.get("on"):
        bt = rgt.BELT_TEMPLATE
        try:
            thr = int(float(belts.get("thr", bt["thr"])))
        except (TypeError, ValueError):
            thr = bt["thr"]
        lines += ["", gen.header_minor("Belts"), "//PREFIXES"]
        for name in rgc.BELT_BASES:
            lines.append(_pro_rule(name, bt["tier"], "Rare", bt["prefix"], thr))
        lines.append("//SUFFIXES")
        s_thr = _round5(thr * bt["s_pct"])
        for name in rgc.BELT_BASES:
            lines.append(_pro_rule(name, bt["tier"], "Rare", bt["suffix"], s_thr))
        if belts.get("magic"):
            m_mods, m_thr, m_tier = bt["magic"]
            lines.append("//MAGIC")
            for name in rgc.BELT_BASES:
                lines.append(_pro_rule(name, m_tier, "Magic", m_mods, m_thr))

    # Rings: build archetypes over every ring base (from the user's pickit).
    # New configs carry rings['archetypes'] = {key: {'on', 'thr'}}; legacy
    # configs only have the single 'on' switch, which means "all, preset thr".
    rings = cfg.get("rings", {}) if isinstance(cfg.get("rings"), dict) else {}
    arch_cfg = rings.get("archetypes") if isinstance(rings.get("archetypes"), dict) else None
    if arch_cfg is None:
        enabled = list(rgt.RING_ARCHETYPES) if rings.get("on") else []
        thr_of = {a["key"]: a["thr"] for a in rgt.RING_ARCHETYPES}
        ring_magic = bool(rings.get("on") and rings.get("magic"))
    else:
        enabled, thr_of = [], {}
        for a in rgt.RING_ARCHETYPES:
            s = arch_cfg.get(a["key"])
            if not (isinstance(s, dict) and s.get("on")):
                continue
            enabled.append(a)
            try:
                t = float(s.get("thr", a["thr"]))
            except (TypeError, ValueError):
                t = float(a["thr"])
            thr_of[a["key"]] = int(t) if t.is_integer() else t
        ring_magic = bool(rings.get("magic"))
    if enabled or ring_magic:
        lines += ["", gen.header_minor("Rings")]
        for arch in enabled:
            lines.append(f"// {arch['label']}")
            for name in rgc.RING_BASES:
                lines.append(_pro_rule(name, 1, "Rare", arch["full"], thr_of[arch["key"]]))
        if ring_magic:
            m_mods, m_thr = rgt.RING_MAGIC
            lines.append("//MAGIC")
            for name in rgc.RING_BASES:
                lines.append(_pro_rule(name, 1, "Magic", m_mods, m_thr))
            stat, r_thr = rgt.RING_RARITY
            for rarity in ("Rare", "Magic"):
                lines.append(f'[Category] == "Ring" && [Rarity] == "{rarity}" '
                             f'# [{stat}] >= "{r_thr}" && [StashItem] == "true"')

    # Expert rules: hand-written .ipd lines the templates can't express
    # (threshold ladders, Computed* defences, DPS rules…) — appended VERBATIM.
    expert = cfg.get("expert", {}) if isinstance(cfg.get("expert"), dict) else {}
    if expert.get("on"):
        body = [ln.rstrip() for ln in str(expert.get("text", "")).splitlines()]
        while body and not body[0]:
            body.pop(0)
        while body and not body[-1]:
            body.pop()
        if body:
            lines += ["", gen.header_minor("Expert rules (verbatim)")] + body
    return lines


# ── Weighted-sum mod scoring (Phase 2 — validation slice) ─────────────────────

def weighted_sum_term(stat_id: str, weight) -> str:
    """One WeightedSum term in the bot's real format: ``stat_id:weight``
    (e.g. ``base_maximum_life:1.2``). Verified against the bot's own pickit files."""
    return f"{stat_id}:{float(weight):g}"


def build_weighted_sum_rule(selector: str, mods, threshold,
                            include_magic: bool = False,
                            min_ilvl: int = 0) -> str:
    """Build one WeightedSum pickit rule, matching the bot's exact syntax:

        <selector> && [Rarity] == "Rare" # [WeightedSum(stat:wt,stat:wt,...)] >= "N" && [StashItem] == "true"

    selector: the pre-# selection clause, e.g. '[Category] == "BodyArmour"' or
              '[WeaponCategory] == "Shield" && [ItemTier] >= "3"'.
    mods: iterable of (stat_id, weight) pairs.
    [WeightedSum(...)] reads identified mods, so it lives AFTER the #; the threshold
    is quoted — both verified against the bot's default pickit files.
    min_ilvl > 0 additionally requires [ItemLevel] >= min_ilvl to stash — also
    post-# because item level is only readable after identify."""
    terms = [weighted_sum_term(*m) for m in mods]
    rarity = ('([Rarity] == "Rare" || [Rarity] == "Magic")'
              if include_magic else '[Rarity] == "Rare"')
    th = f"{threshold:g}" if isinstance(threshold, (int, float)) else str(threshold)
    ilvl = f'[ItemLevel] >= "{int(min_ilvl)}" && ' if min_ilvl and min_ilvl > 0 else ""
    return (f'{selector} && {rarity} '
            f'# {ilvl}[WeightedSum({",".join(terms)})] >= "{th}" && [StashItem] == "true"')


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
