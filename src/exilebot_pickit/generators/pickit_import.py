"""Convert ANY Exiled Bot 2 pickit (.ipd) into a PoE2 in-game loot filter.

The engine already turns the pickits *we* generate into a matching `.filter`
(``generator.build_loot_filter``). This module is the user-facing sibling: it
takes a pickit from anywhere — hand-written, another tool, months of manual
tuning — and produces a filter from it, plus a plain-language report of what
it understood.

The guiding rule: **the filter shows everything the pickit could take — equal
or more, never less.** A pickit can check things the game filter cannot see
(mods, tiers, resistances); those checks are dropped from the filter side so
the item still gets a label. The one exception is deliberate: when the user
turns on "hide everything else", hide is honored even if some rules couldn't
be translated — the risk is surfaced loudly (report + a warning inside the
filter) instead of refusing, because the owner decided hide must mean hide.
(A hiding filter is still a bad idea while botting — see
``copy_filter_to_game`` in ui/config.py.)

Pure module: no network, no UI, no file I/O — mirrors generators/assembly.py.
"""
from __future__ import annotations

import re
import time

from exilebot_pickit import generator as gen

# Pickup-side conditions the converter can express in a loot filter. Anything
# else found before the `#` (ItemTier, GemLevel, TotalResistances, …) is a
# bot-only check: it gets dropped and the rule is counted as "widened".
_KNOWN_TOKENS = {"Type", "Rarity", "Quality", "Sockets", "Category"}

_TOKEN_RE = re.compile(r"\[(\w+)\]")

# Exiled Bot [Category] value → PoE2 filter Class name(s), keyed lowercase.
# Every Class string is verified against NeverSink's live SOFT filter (the
# game's real vocabulary) — a wrong string silently matches nothing, which
# with Hide on would hide items the pickit wants. Add new entries only after
# checking that filter again (see .claude/skills/verify-game-data).
_CATEGORY_CLASS = {
    "helmet": ["Helmets"], "bodyarmour": ["Body Armours"],
    "gloves": ["Gloves"], "boots": ["Boots"],
    "ring": ["Rings"], "amulet": ["Amulets"], "belt": ["Belts"],
    "flask": ["Life Flasks", "Mana Flasks"],
    "lifeflask": ["Life Flasks"], "manaflask": ["Mana Flasks"],
    "charm": ["Charms"], "jewel": ["Jewels"], "quiver": ["Quivers"],
    "shield": ["Shields"], "buckler": ["Bucklers"], "focus": ["Foci"],
    "wand": ["Wands"], "staff": ["Staves"], "bow": ["Bows"],
    "crossbow": ["Crossbows"], "sceptre": ["Sceptres"], "spear": ["Spears"],
    "talisman": ["Talismans"], "quarterstaff": ["Quarterstaves"],
    "onehandmace": ["One Hand Maces"], "twohandmace": ["Two Hand Maces"],
    "mace": ["One Hand Maces", "Two Hand Maces"],
    "waystone": ["Waystones"], "tablet": ["Tablet"],
    "currency": ["Stackable Currency"],
}

# Label styles, kept close to the game's own visual language (unique orange,
# currency gold). Command syntax verified against NeverSink's live filter.
# Beams/minimap stars only on uniques — a beam on every cheap currency drop
# would turn a juiced map into a light show.
_STYLE_NAMED = ["SetFontSize 38", "SetBorderColor 255 207 92",
                "MinimapIcon 2 Yellow Circle"]
_STYLE_UNIQUE = ["SetFontSize 40", "SetTextColor 175 96 37",
                 "SetBorderColor 175 96 37", "PlayEffect Brown",
                 "MinimapIcon 1 Brown Star"]
_STYLE_GEAR = ["SetFontSize 32"]
_STYLE_GOLD = ["SetFontSize 35"]

# Keep the untranslatable list small enough for the UI report.
_MAX_LISTED = 30


def _parse_rule(cond_part: str):
    """Extract the filter-expressible pieces of one rule's pickup half."""
    names = [n.replace('\\"', '"') for n in gen._LF_TYPE_RE.findall(cond_part)]
    mr = gen._LF_RARITY_RE.search(cond_part)
    mq = gen._LF_QUALITY_RE.search(cond_part)
    ms = gen._LF_SOCKETS_RE.search(cond_part)
    msg = gen._LF_SOCKETS_GT_RE.search(cond_part)
    mc = gen._LF_CATEGORY_RE.search(cond_part)
    sockets = None
    if ms:
        sockets = int(ms.group(1))
    elif msg:
        sockets = int(msg.group(1)) + 1
    return {
        "names": names,
        "rarity": mr.group(1) if mr else None,
        "quality": int(mq.group(1)) if mq else None,
        "sockets": sockets,
        "category": mc.group(1) if mc else None,
        "unknown": sorted(set(_TOKEN_RE.findall(cond_part)) - _KNOWN_TOKENS),
    }


def convert_pickit_text(text: str, hide_rest: bool = False,
                        source_name: str = "") -> dict:
    """Parse pickit text and return ``{"ok", "filter_lines", "report"}``.

    Never raises on bad input — unreadable lines are counted and listed, and
    a file with no usable rules returns ``ok=False`` with the report intact.
    """
    plain: list = []
    unique: list = []
    by_rarity: dict = {"Normal": [], "Magic": [], "Rare": []}
    by_quality: dict = {}
    by_sockets: dict = {}
    generic: list = []

    rules = converted = widened = disabled = assumed_pickup = 0
    untranslatable: list = []
    untranslatable_total = 0

    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("/"):
            disabled += 1
            continue
        rules += 1
        cond_part = line.split("#", 1)[0]
        if not gen._LF_ACTION_RE.search(line):
            # No recognised action — include it anyway. Showing an extra item
            # is harmless; hiding one the bot wanted is not.
            assumed_pickup += 1
        r = _parse_rule(cond_part)
        if r["unknown"]:
            widened += 1

        if r["names"]:
            if r["rarity"] == "Unique":
                unique.extend(r["names"])
            elif r["rarity"] in by_rarity:
                by_rarity[r["rarity"]].extend(r["names"])
            elif r["quality"] is not None:
                by_quality.setdefault(r["quality"], []).extend(r["names"])
            elif r["sockets"] is not None:
                by_sockets.setdefault(r["sockets"], []).extend(r["names"])
            else:
                plain.extend(r["names"])
            converted += 1
            continue
        conds = []
        if r["category"]:
            classes = _CATEGORY_CLASS.get(r["category"].lower())
            if classes:
                conds.append("Class == " + " ".join(f'"{c}"' for c in classes))
        if r["rarity"]:
            conds.append(f"Rarity = {r['rarity']}")
        if r["sockets"] is not None:
            conds.append(f"Sockets >= {r['sockets']}")
        if r["quality"] is not None:
            conds.append(f"Quality >= {r['quality']}")
        if conds:
            generic.append(conds)
            converted += 1
            continue
        reason = (f"category \"{r['category']}\" has no filter equivalent"
                  if r["category"] else "no conditions a filter can express")
        untranslatable_total += 1
        if len(untranslatable) < _MAX_LISTED:
            untranslatable.append({"line": no, "text": line[:160],
                                   "reason": reason})

    # Hide means hide (owner's call): when requested it is always applied.
    # If rules couldn't be translated, their items may be hidden in game even
    # though the bot still picks them up — that risk is surfaced loudly in the
    # report and in the filter itself instead of refusing to hide.
    hide_applied = bool(hide_rest)
    hide_risky = bool(hide_rest and untranslatable_total)

    src = source_name or "pickit"
    out: list = [
        f"# Path of Exile 2 filter — made from {src} by ExileBot 2 Pickit Generator",
        "# Shows every item the pickit could take (pickup conditions only).",
        "# Bot-only checks (mods, tiers, values) can't exist in a filter, so",
        "# those rules are shown a little wider — never narrower.",
        f"# Generated on: {time.strftime('%Y-%m-%dT%H:%M:%S')}",
        "",
    ]
    out += gen._lf_show_blocks(plain, _STYLE_NAMED)
    out += gen._lf_show_blocks(unique, ["Rarity = Unique"] + _STYLE_UNIQUE)
    for rar in ("Normal", "Magic", "Rare"):
        out += gen._lf_show_blocks(by_rarity[rar], [f"Rarity = {rar}"] + _STYLE_GEAR)
    for q in sorted(by_quality):
        out += gen._lf_show_blocks(by_quality[q], [f"Quality >= {q}"] + _STYLE_GEAR)
    for s in sorted(by_sockets):
        out += gen._lf_show_blocks(by_sockets[s], [f"Sockets >= {s}"] + _STYLE_GEAR)
    for conds in gen._dedupe_cond_lists(generic):
        out += ["Show"] + [f"    {c}" for c in conds + _STYLE_GEAR] + [""]

    if hide_applied:
        # Safety: gold must never be hidden — bots grab it regardless of the
        # pickit, and no player wants it invisible. BaseType verified against
        # NeverSink's live SOFT filter.
        out += (["# Always show gold", "Show", '    BaseType == "Gold"']
                + [f"    {s}" for s in _STYLE_GOLD] + [""])
        if hide_risky:
            out += [f"# WARNING: {untranslatable_total} pickit rule(s) couldn't be "
                    "translated — items only those rules match",
                    "# will be HIDDEN in game, even though the bot still picks them up.",
                    ""]
        out += ["# Hide everything else", "Hide", ""]

    ok = converted > 0
    return {
        "ok": ok,
        "filter_lines": out if ok else [],
        "report": {
            "rules": rules,
            "converted": converted,
            "widened": widened,
            "disabled": disabled,
            "assumed_pickup": assumed_pickup,
            "untranslatable_total": untranslatable_total,
            "untranslatable": untranslatable,
            "hide_applied": hide_applied,
            "hide_risky": hide_risky,
        },
    }
