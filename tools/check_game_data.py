#!/usr/bin/env python
"""Game-data drift checker for the ExileBot 2 Pickit Generator.

Fetches two authoritative, machine-readable sources for the CURRENT patch and
diffs them against the data this app ships, so a game patch that renames a stat
id or removes a base type is *caught* instead of silently shipping dead rules
(the exact failure that killed five fracture rules before this tool existed).

Sources
  * repoe-fork PoE2 ``mods.min.json`` — the GGPK mod dump: every craftable
    affix, its engine stat ids, tiers and roll ranges.
  * repoe-fork PoE2 ``base_items.min.json`` — the GGPK item table: THE authority
    on whether a base name still exists.
  * NeverSink's PoE2 SOFT filter — secondary signal only. It names the bases it
    *styles*, which is not the same as the bases that *drop*; treating it as a
    drop list falsely reported Hallowed Sceptre and Dark Staff as removed when
    both are real ilvl-65 bases. Never fail a base on NeverSink alone.

What it checks
  [1] STAT-ID EXISTENCE  — every engine stat id our rare-gear recipes and
      fracture targets use must still be granted by a real craftable affix.
      A missing id == a renamed/removed stat == a rule that matches nothing.
  [2] WEIGHT CONSISTENCY — each rare-gear weight must equal 100 / its own
      "# T1 max N" comment (a self-check that catches arithmetic slips like
      the old %ES weight bug). No network needed for this one.
  [3] BASE NAMES        — every base our rare-gear + chance rules name must
      still exist in the game's item table.
  [4] ROLL DRIFT (advisory) — our "# T1 max N" comment vs the game's current
      top craftable roll for that stat. Coarse (ignores per-slot caps) so it
      only flags, never fails.

Exit code is non-zero if any check in [1]-[3] finds drift, so this can gate CI.

Usage:  python tools/check_game_data.py [--offline]
"""
from __future__ import annotations
import argparse
import io
import os
import re
import sys

# Make the app importable when run from the repo root.
_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

MODS_URL = "https://repoe-fork.github.io/poe2/mods.min.json"
BASE_ITEMS_URL = "https://repoe-fork.github.io/poe2/base_items.min.json"
NEVERSINK_URL = (
    "https://raw.githubusercontent.com/NeverSinkDev/NeverSink-PoE2litefilter/"
    "master/NeverSink's%20filter%202%20-%200-SOFT.filter"
)
_CACHE = os.path.join(_HERE, ".gamedata_cache")

# Weight is defined as 100 / (T1 max roll); allow for 2-decimal rounding.
_WEIGHT_TOL = 0.10


# ── source fetching ────────────────────────────────────────────────────────
def _fetch(url: str, cache_name: str, offline: bool) -> bytes:
    path = os.path.join(_CACHE, cache_name)
    if offline:
        with open(path, "rb") as f:
            return f.read()
    import requests
    r = requests.get(url, timeout=60, headers={"Accept-Encoding": "identity"})
    r.raise_for_status()
    os.makedirs(_CACHE, exist_ok=True)
    with open(path, "wb") as f:
        f.write(r.content)
    return r.content


def load_sources(offline: bool):
    import json
    mods = json.loads(_fetch(MODS_URL, "mods.min.json", offline).decode("utf-8"))
    bases = json.loads(_fetch(BASE_ITEMS_URL, "base_items.min.json", offline).decode("utf-8"))
    ns = _fetch(NEVERSINK_URL, "neversink_soft.filter", offline).decode("utf-8", "replace")
    return mods, bases, ns


def game_base_names(base_items: dict) -> set[str]:
    """Every real base-item name in the game's own item table.

    This is the authority for 'does this base exist'. NeverSink is NOT — it only
    *names* the bases it styles, so plenty of real bases (Pious Sceptre, Dark
    Staff, ...) never appear in it. Checking names against NeverSink alone
    produces false 'removed base' reports.
    """
    return {v["name"] for v in base_items.values()
            if v.get("domain") == "item" and v.get("name")}


# ── source indexing ────────────────────────────────────────────────────────
def index_mods(mods: dict):
    """Return (affix_stat_ids, any_item_stat_ids, max_roll_by_id).

    affix_stat_ids   — ids granted by a normal prefix/suffix on an item.
    any_item_stat_ids — ids granted by any item-domain mod (implicit/corrupted
                        included) — a softer 'exists at all' signal.
    max_roll_by_id   — best craftable |max| across item prefix/suffix mods.
    """
    affix: set[str] = set()
    any_item: set[str] = set()
    max_roll: dict[str, float] = {}
    for m in mods.values():
        if m.get("domain") != "item":
            continue
        gtype = m.get("generation_type")
        is_affix = gtype in ("prefix", "suffix")
        for s in m.get("stats", []):
            sid = s.get("id")
            if not sid:
                continue
            any_item.add(sid)
            if is_affix and not m.get("is_essence_only"):
                affix.add(sid)
                vals = [abs(v) for v in (s.get("min"), s.get("max")) if isinstance(v, (int, float))]
                if vals:
                    hi = max(vals)
                    # ignore the obvious 99999 test/placeholder tiers
                    if hi < 5000:
                        max_roll[sid] = max(max_roll.get(sid, 0), hi)
    return affix, any_item, max_roll


def neversink_bases(ns_text: str) -> set[str]:
    bases: set[str] = set()
    for line in ns_text.splitlines():
        s = line.strip()
        if s.startswith("#") or "BaseType" not in s:
            continue
        for m in re.findall(r'"([^"]+)"', s):
            bases.add(m)
    return bases


# ── our data ───────────────────────────────────────────────────────────────
def our_stat_ids():
    """Every engine stat id our rare-gear recipes and fracture targets rely on,
    mapped to a short human location for the report."""
    from exilebot_pickit.data.rare import rules as rare
    from exilebot_pickit.data.fracture_bases import fracture_bases as fb
    used: dict[str, list[str]] = {}

    def add(sid, where):
        used.setdefault(sid, [])
        if where not in used[sid]:
            used[sid].append(where)

    for slot, spec in rare.RARE_GEAR.items():
        for sid in spec["weights"]:
            add(sid, f"rare:{slot}")
    for tid, sid in getattr(fb, "_FRACTURE_VERIFIED_STAT_IDS", {}).items():
        if sid:
            add(sid, f"fracture:{tid}")
    for tid, group in getattr(fb, "_FRACTURE_OR_GROUP_IDS", {}).items():
        for sid, _thr in group:
            add(sid, f"fracture:{tid}")
    for sid in getattr(fb, "_AMULET_SKILL_IDS", []):
        add(sid, "fracture:amulet_skill_level")
    return used


def our_bases():
    """Base names our rare-gear and chance rules name, mapped to a location."""
    from exilebot_pickit.data.rare import rules as rare
    from exilebot_pickit import generator as gen
    used: dict[str, list[str]] = {}

    def add(name, where):
        used.setdefault(name, [])
        if where not in used[name]:
            used[name].append(where)

    for slot, spec in rare.RARE_GEAR.items():
        for b in spec["bases"]:
            add(b, f"rare:{slot}")
    for entry in getattr(gen, "CHANCE_BASES", []):
        # CHANCE_BASES rows are (category, base_name, chase_uniques) tuples.
        name = entry[1] if isinstance(entry, (tuple, list)) else entry
        add(name, "chance")
    return used


_WEIGHT_LINE = re.compile(
    r'"(?P<id>[^"]+)":\s*(?P<w>[0-9.]+),\s*#\s*T1 max\s*\+?(?P<n>[0-9]+)'
)


def our_weight_comments():
    """Parse rules.py for (stat_id, weight, T1-max-from-comment) triples so the
    weight can be checked against its own documented roll."""
    from exilebot_pickit.data.rare import rules as rare
    src = open(rare.__file__, encoding="utf-8").read()
    out = []
    for m in _WEIGHT_LINE.finditer(src):
        out.append((m.group("id"), float(m.group("w")), int(m.group("n"))))
    return out


# ── report ─────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--offline", action="store_true",
                    help="use the last cached sources instead of fetching")
    ap.add_argument("--rolls", action="store_true",
                    help="also print the coarse roll-drift appendix (noisy: it "
                         "ignores per-slot caps, so it over-flags)")
    args = ap.parse_args()

    try:
        mods, base_items, ns_text = load_sources(args.offline)
    except Exception as e:
        print(f"✗ could not load sources ({type(e).__name__}: {e})")
        if not args.offline:
            print("  try --offline to use the last cached copy, or check your connection.")
        return 2

    affix, any_item, max_roll = index_mods(mods)
    ns_bases = neversink_bases(ns_text)
    real_bases = game_base_names(base_items)
    print("GAME-DATA CHECKER")
    print(f"  mods.min.json      : {len(mods):,} mods  ({len(affix):,} craftable-affix stat ids)")
    print(f"  base_items.min.json: {len(real_bases):,} real base items (the authority on 'does it exist')")
    print(f"  NeverSink SOFT     : {len(ns_bases):,} bases it explicitly names (a styling list, NOT a drop list)")
    print()

    critical = 0
    advisory = 0

    # [1] stat-id existence
    used_ids = our_stat_ids()
    missing = []
    weird = []
    for sid, where in sorted(used_ids.items(), key=lambda kv: kv[0]):
        if sid not in affix:
            (missing if sid not in any_item else weird).append((sid, where))
    print(f"[1] STAT-ID EXISTENCE — {len(used_ids)} engine ids checked")
    if not missing and not weird:
        print("    ✓ all present in the craftable affix pool")
    for sid, where in missing:
        critical += 1
        print(f"    ✗ REMOVED/RENAMED: {sid}   used by {', '.join(where)}")
    for sid, where in weird:
        advisory += 1
        print(f"    ⚠ not a normal affix (implicit/corrupted only?): {sid}   used by {', '.join(where)}")
    print()

    # [2] weight consistency (self-check, no network)
    triples = our_weight_comments()
    bad_w = []
    for sid, w, n in triples:
        if n <= 0:
            continue
        expected = 100.0 / n
        if abs(w - expected) / expected > _WEIGHT_TOL:
            bad_w.append((sid, w, n, expected))
    print(f"[2] WEIGHT CONSISTENCY — {len(triples)} rare-gear weights checked (weight == 100 / T1-max)")
    if not bad_w:
        print("    ✓ every weight matches its documented T1 max-roll")
    for sid, w, n, expected in bad_w:
        critical += 1
        print(f"    ✗ {sid}: weight {w} but T1 max {n} implies {expected:.2f}")
    print()

    # [3] base names — against the game's own item table (the authority).
    # NeverSink is only a secondary signal: it names the bases it styles, so a
    # real base can legitimately be absent from it (that produced two false
    # "removed base" reports before this check was rewritten).
    used_bases = our_bases()
    items = sorted(used_bases.items(), key=lambda kv: kv[0])
    gone = [(b, w) for b, w in items if b not in real_bases]
    unstyled = [(b, w) for b, w in items if b in real_bases and b not in ns_bases]
    print(f"[3] BASE NAMES — {len(used_bases)} rare-gear + chance bases checked vs the game's item table")
    if not gone:
        print("    ✓ every base still exists in the game")
    for b, where in gone:
        critical += 1
        print(f"    ✗ NOT IN THE GAME: \"{b}\"   used by {', '.join(where)}")
    for b, where in unstyled:
        advisory += 1
        print(f"    ⚠ exists, but NeverSink doesn't name it: \"{b}\"   used by {', '.join(where)}")
    if unstyled:
        print("      (not a bug — NeverSink only names bases it styles. Worth a glance")
        print("       only if you expected it to be a chase base.)")
    print()

    # [4] roll drift (advisory, opt-in — coarse global max, over-flags)
    if args.rolls:
        print("[4] ROLL DRIFT (advisory — coarse global max, ignores per-slot caps; verify before acting)")
        drift = []
        seen = set()
        for sid, _w, n in triples:
            if sid in seen:
                continue
            seen.add(sid)
            game = max_roll.get(sid)
            if game is None:
                continue
            game_i = int(round(game))
            if game_i != n and (abs(game_i - n) / max(n, 1)) > 0.12:
                drift.append((sid, n, game_i))
        if not drift:
            print("    ✓ no notable divergence between our comments and the game's top rolls")
        for sid, n, game_i in drift:
            print(f"    ⚠ {sid}: we note T1 max {n}, game top craftable roll is {game_i}")
        print()
    else:
        print("[4] ROLL DRIFT — skipped (run with --rolls; it is a coarse, noisy appendix)")
        print()

    print(f"SUMMARY: {critical} critical, {advisory} advisory")
    if critical:
        print("  → game data drifted. Verify each ✗ against the game before shipping.")
    else:
        print("  → data is in sync with the current patch.")
    return 1 if critical else 0


if __name__ == "__main__":
    raise SystemExit(main())
