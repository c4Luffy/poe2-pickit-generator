"""Game-data health check — the in-app version.

PoE2 renames stats and removes bases every patch. When that happens our rules
still *look* correct but match nothing, and the bot silently walks past loot with
no error anywhere. Nine rules were dead this way before this check existed (the
three Evasion fracture rules had never worked, not once).

This module answers one question: **do the things our rules hunt for still exist
in the game?** It fetches the game's own data and diffs it against ours.

Sources (in order of authority)
  * repoe-fork ``mods.min.json``       — every craftable affix: engine stat ids,
                                          tiers, roll ranges. THE authority on
                                          "is this stat id real".
  * repoe-fork ``base_items.min.json`` — the game's item table. THE authority on
                                          "does this base exist".
  * NeverSink's SOFT filter            — SECONDARY ONLY. It names the bases it
                                          *styles*, which is not the set of bases
                                          that *drop*; treating it as a drop list
                                          falsely reported Hallowed Sceptre and
                                          Dark Staff as removed when both are
                                          real. Never fail a base on this alone.

Everything here is best-effort and never raises into the app: a failed fetch
falls back to the cached copy, and a total failure returns ``error`` set rather
than blowing up a launch. It reports; it never edits data.
"""
from __future__ import annotations

import json
import os
import re
import time

MODS_URL = "https://repoe-fork.github.io/poe2/mods.min.json"
BASE_ITEMS_URL = "https://repoe-fork.github.io/poe2/base_items.min.json"
NEVERSINK_URL = (
    "https://raw.githubusercontent.com/NeverSinkDev/NeverSink-PoE2litefilter/"
    "master/NeverSink's%20filter%202%20-%200-SOFT.filter"
)

# The sources only move when the game patches; don't re-pull ~9 MB every launch.
CACHE_TTL_SECONDS = 12 * 3600

# weight is defined as 100 / (T1 max roll); allow for 2-decimal rounding.
_WEIGHT_TOL = 0.10

_WEIGHT_LINE = re.compile(
    r'"(?P<id>[^"]+)":\s*(?P<w>[0-9.]+),\s*#\s*T1 max\s*\+?(?P<n>[0-9]+)'
)


def _cache_dir() -> str:
    from exilebot_pickit.ui.config import _cfg_dir
    d = os.path.join(_cfg_dir, "gamedata_cache")
    os.makedirs(d, exist_ok=True)
    return d


def _fetch(url: str, name: str, force: bool) -> bytes:
    """Fetch a source, preferring a fresh cache. A network failure falls back to
    a stale cache — an old answer beats no answer and beats a crash."""
    path = os.path.join(_cache_dir(), name)
    if not force and os.path.exists(path) \
            and (time.time() - os.path.getmtime(path)) < CACHE_TTL_SECONDS:
        with open(path, "rb") as f:
            return f.read()
    try:
        import requests
        r = requests.get(url, timeout=60, headers={"Accept-Encoding": "identity"})
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        return r.content
    except Exception:
        if os.path.exists(path):
            with open(path, "rb") as f:      # stale, but better than nothing
                return f.read()
        raise


# ── indexing the game's data ──────────────────────────────────────────────────
def index_mods(mods: dict):
    """(affix_stat_ids, any_item_stat_ids) — ids granted by a normal item
    prefix/suffix, and the softer 'granted by any item mod at all' set."""
    affix: set[str] = set()
    any_item: set[str] = set()
    for m in mods.values():
        if m.get("domain") != "item":
            continue
        is_affix = m.get("generation_type") in ("prefix", "suffix")
        for s in m.get("stats", []):
            sid = s.get("id")
            if not sid:
                continue
            any_item.add(sid)
            if is_affix and not m.get("is_essence_only"):
                affix.add(sid)
    return affix, any_item


def game_base_names(base_items: dict) -> set[str]:
    """Every real base-item name in the game's own item table."""
    return {v["name"] for v in base_items.values()
            if v.get("domain") == "item" and v.get("name")}


def neversink_bases(ns_text: str) -> set[str]:
    bases: set[str] = set()
    for line in ns_text.splitlines():
        s = line.strip()
        if s.startswith("#") or "BaseType" not in s:
            continue
        bases.update(re.findall(r'"([^"]+)"', s))
    return bases


# ── what WE depend on ─────────────────────────────────────────────────────────
def our_stat_ids() -> dict:
    """Every engine stat id our rare-gear recipes and fracture targets rely on,
    mapped to the human-readable places that use it."""
    from exilebot_pickit.data.rare import rules as rare
    from exilebot_pickit.data.fracture_bases import fracture_bases as fb
    used: dict[str, list[str]] = {}

    def add(sid, where):
        used.setdefault(sid, [])
        if where not in used[sid]:
            used[sid].append(where)

    for slot, spec in rare.RARE_GEAR.items():
        for sid in spec["weights"]:
            add(sid, f"Rare gear · {slot}")
    for tid, sid in getattr(fb, "_FRACTURE_VERIFIED_STAT_IDS", {}).items():
        if sid:
            add(sid, f"Fracture · {tid}")
    for tid, group in getattr(fb, "_FRACTURE_OR_GROUP_IDS", {}).items():
        for sid, _thr in group:
            add(sid, f"Fracture · {tid}")
    for sid in getattr(fb, "_AMULET_SKILL_IDS", []):
        add(sid, "Fracture · amulet_skill_level")
    return used


def our_bases() -> dict:
    from exilebot_pickit.data.rare import rules as rare
    from exilebot_pickit.data.fracture_bases import fracture_bases as fb
    from exilebot_pickit import generator as gen
    used: dict[str, list[str]] = {}

    def add(name, where):
        used.setdefault(name, [])
        if where not in used[name]:
            used[name].append(where)

    for slot, spec in rare.RARE_GEAR.items():
        for b in spec["bases"]:
            add(b, f"Rare gear · {slot}")
    for cls, bases in getattr(fb, "_FRACTURE_BASE_OVERRIDES", {}).items():
        for b in bases:
            add(b, f"Fracture · {cls}")
    for entry in getattr(gen, "CHANCE_BASES", []):
        add(entry[1] if isinstance(entry, (tuple, list)) else entry, "Chance bases")
    return used


def our_weight_comments() -> list:
    """(stat_id, weight, documented T1 max) for every rare-gear weight, parsed
    from the recipe source, so a weight can be checked against its own roll."""
    from exilebot_pickit.data.rare import rules as rare
    try:
        with open(rare.__file__, encoding="utf-8") as f:
            src = f.read()
    except OSError:
        return []            # frozen build without source — skip this check
    return [(m.group("id"), float(m.group("w")), int(m.group("n")))
            for m in _WEIGHT_LINE.finditer(src)]


# ── the check ─────────────────────────────────────────────────────────────────
def run_check(force: bool = False) -> dict:
    """Diff our rules against the current patch. Never raises.

    Returns ``{ok, critical, advisory, findings, sources, checked_at, error}``.
    A *critical* finding means some rule is very likely matching nothing.
    """
    result = {"ok": True, "critical": 0, "advisory": 0, "findings": [],
              "sources": {}, "checked_at": time.strftime("%Y-%m-%d %H:%M"),
              "error": ""}
    try:
        mods = json.loads(_fetch(MODS_URL, "mods.min.json", force).decode("utf-8"))
        base_items = json.loads(_fetch(BASE_ITEMS_URL, "base_items.min.json", force).decode("utf-8"))
        ns_text = _fetch(NEVERSINK_URL, "neversink.filter", force).decode("utf-8", "replace")
    except Exception as e:
        result["error"] = f"Couldn't reach the game-data sources ({type(e).__name__})."
        return result

    affix, any_item = index_mods(mods)
    real_bases = game_base_names(base_items)
    ns_bases = neversink_bases(ns_text)
    result["sources"] = {"mods": len(mods), "affix_stats": len(affix),
                         "bases": len(real_bases), "neversink": len(ns_bases)}

    def flag(level, kind, title, detail, where):
        result["findings"].append({"level": level, "kind": kind, "title": title,
                                   "detail": detail, "where": where})
        result[level] += 1

    # 1. stat ids — a missing one means a rule that matches nothing
    used_ids = our_stat_ids()
    for sid, where in sorted(used_ids.items()):
        if sid in affix:
            continue
        if sid not in any_item:
            flag("critical", "stat", sid,
                 "No affix in the game grants this stat any more — rules using it "
                 "match nothing (renamed or removed in a patch).", where)
        else:
            flag("advisory", "stat", sid,
                 "Exists, but not as a normal magic/rare affix (implicit or "
                 "corrupted only) — worth a look.", where)
    result["checked_stats"] = len(used_ids)

    # 2. weights vs their own documented roll (no network needed)
    triples = our_weight_comments()
    for sid, w, n in triples:
        if n <= 0:
            continue
        expected = 100.0 / n
        if abs(w - expected) / expected > _WEIGHT_TOL:
            flag("critical", "weight", sid,
                 f"Weight is {w} but the documented T1 max of {n} implies "
                 f"{expected:.2f} — the stat is being mis-scored.",
                 "Rare gear")
    result["checked_weights"] = len(triples)

    # 3. base names — against the game's item table, NOT NeverSink
    used_bases = our_bases()
    for b, where in sorted(used_bases.items()):
        if b not in real_bases:
            flag("critical", "base", b,
                 "This base no longer exists in the game — rules naming it "
                 "match nothing.", where)
        elif b not in ns_bases:
            flag("advisory", "base", b,
                 "Exists in the game, but NeverSink doesn't name it. Not a bug — "
                 "NeverSink only names bases it styles.", where)
    result["checked_bases"] = len(used_bases)

    result["ok"] = result["critical"] == 0
    return result
