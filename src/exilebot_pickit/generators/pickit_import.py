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

# Label styles come from the shared theme table (generators/filter_themes) so
# an imported pickit's filter looks the same as a generated one. An imported
# pickit carries no prices, so the jackpot tier never applies here.

# Keep the untranslatable list small enough for the UI report.
_MAX_LISTED = 30


# The game's filter parser only knows these rarity words; anything else on a
# Rarity line could make the client reject the WHOLE filter, so unknown values
# are dropped (wider) instead of passed through.
_VALID_RARITIES = {"Normal", "Magic", "Rare", "Unique"}

# Characters a filter string can't carry: '#' starts a comment, '"' ends the
# string, and the syntax has no escaping. No real PoE2 item name contains
# either — a name that does is hand-crafted and simply can't be expressed.
_UNEXPRESSIBLE = ('"', "#")


def _pickup_half(line: str) -> str:
    """Everything before the first '#' OUTSIDE quotes — the pickup conditions.
    A naive split('#') used to cut inside quoted names and silently lose them."""
    in_q = False
    i, n = 0, len(line)
    while i < n:
        c = line[i]
        if in_q and c == "\\" and i + 1 < n:
            i += 2
            continue
        if c == '"':
            in_q = not in_q
        elif c == "#" and not in_q:
            return line[:i]
        i += 1
    return line


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
                        source_name: str = "",
                        theme: str = gen.DEFAULT_FILTER_THEME) -> dict:
    """Parse pickit text and return ``{"ok", "filter_lines", "report"}``.

    Never raises on bad input — unreadable lines are counted and listed, and
    a file with no usable rules returns ``ok=False`` with the report intact.
    ``theme`` picks the label style set; unknown values fall back to the
    default theme inside the lookup.
    """
    named_groups: dict = {}   # (rarity, quality, sockets) -> [names], exact translation
    generic: list = []

    rules = converted = widened = disabled = assumed_pickup = 0
    untranslatable: list = []
    untranslatable_total = 0

    def _flag(no, line, reason):
        nonlocal untranslatable_total
        untranslatable_total += 1
        if len(untranslatable) < _MAX_LISTED:
            untranslatable.append({"line": no, "text": line[:160],
                                   "reason": reason})

    if not isinstance(text, str):
        text = ""
    # The #1 real-world misuse: an in-game .filter renamed to .ipd (players
    # try to convert FilterBlade filters INTO pickits — this page goes the
    # other way). Detect the filter language so the UI can explain direction
    # instead of a generic "nothing converted".
    looks_like_filter = bool(
        re.search(r"^\s*(Show|Hide)\s*(#.*)?$", text, re.M)
        and re.search(r"^\s*(BaseType|Class|SetTextColor|SetFontSize)\b",
                      text, re.M))
    for no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip().lstrip("﻿")   # a BOM is not part of a comment marker
        if not line:
            continue
        if line.startswith("/"):
            disabled += 1
            continue
        rules += 1
        cond_part = _pickup_half(line)
        if not gen._LF_ACTION_RE.search(line):
            # No recognised action — include it anyway. Showing an extra item
            # is harmless; hiding one the bot wanted is not.
            assumed_pickup += 1
        r = _parse_rule(cond_part)
        # "wide": a check was dropped, so the filter shows MORE than the rule.
        # Counted only for rules that actually make it into the filter.
        wide = bool(r["unknown"])
        rarity = r["rarity"]
        if rarity and rarity not in _VALID_RARITIES:
            rarity = None
            wide = True
        bad_names = [n for n in r["names"]
                     if any(ch in n for ch in _UNEXPRESSIBLE)]
        names = [n for n in r["names"] if n and n not in bad_names]

        if bad_names:
            # The lost name can never be expressed — the rule counts as
            # untranslatable (so a Hide gets the loud warning), but any
            # expressible sibling names on the same line still get shown.
            if names:
                key = (rarity, r["quality"], r["sockets"])
                named_groups.setdefault(key, []).extend(names)
            _flag(no, line, "an item name on this line contains '#' or '\"' — "
                            "a filter string can't carry that name")
            continue
        if names:
            key = (rarity, r["quality"], r["sockets"])
            named_groups.setdefault(key, []).extend(names)
            converted += 1
            if wide:
                widened += 1
            continue
        conds = []
        if r["category"]:
            classes = _CATEGORY_CLASS.get(r["category"].lower())
            if classes:
                conds.append("Class == " + " ".join(f'"{c}"' for c in classes))
            else:
                wide = True   # category dropped — whatever remains shows wider
        if rarity:
            conds.append(f"Rarity = {rarity}")
        if r["sockets"] is not None:
            conds.append(f"Sockets >= {r['sockets']}")
        if r["quality"] is not None:
            conds.append(f"Quality >= {r['quality']}")
        if conds:
            generic.append(conds)
            converted += 1
            if wide:
                widened += 1
            continue
        reason = (f"category \"{r['category']}\" has no filter equivalent"
                  if r["category"] else "no conditions a filter can express")
        _flag(no, line, reason)

    # ok = something actually made it into the filter (a partially-translated
    # rule can emit sibling names without counting as converted).
    ok = bool(named_groups or generic)
    # Hide means hide (owner's call): when requested it is always applied.
    # If rules couldn't be translated, their items may be hidden in game even
    # though the bot still picks them up — that risk is surfaced loudly in the
    # report and in the filter itself instead of refusing to hide.
    hide_applied = bool(hide_rest and ok)
    hide_risky = bool(hide_applied and untranslatable_total)

    src = source_name or "pickit"
    out: list = [
        f"# Path of Exile 2 filter — made from {src} by ExileBot 2 Pickit Generator",
        "# Shows every item the pickit could take (pickup conditions only).",
        "# Bot-only checks (mods, tiers, values) can't exist in a filter, so",
        "# those rules are shown a little wider — never narrower.",
        f"# Generated on: {time.strftime('%Y-%m-%dT%H:%M:%S')}",
        "",
    ]
    # Named rules translate EXACTLY: every recognised condition on the line
    # (rarity + quality + sockets, in any combination) rides along with the
    # names — nothing silently dropped.
    def _grp_key(k):
        rar, q, s = k
        return (rar or "", -1 if q is None else q, -1 if s is None else s)
    for key in sorted(named_groups, key=_grp_key):
        rar, q, s = key
        extra = []
        if rar:
            extra.append(f"Rarity = {rar}")
        if q is not None:
            extra.append(f"Quality >= {q}")
        if s is not None:
            extra.append(f"Sockets >= {s}")
        style = gen.filter_theme_style(theme, "unique" if rar == "Unique" else "named")
        out += gen._lf_show_blocks(named_groups[key], extra, style_lines=style)
    gear_style = gen.filter_theme_style(theme, "gear")
    for conds in gen._dedupe_cond_lists(generic):
        out += gen._lf_styled_block(conds, gear_style)

    if hide_applied:
        # Safety: gold must never be hidden — bots grab it regardless of the
        # pickit, and no player wants it invisible. BaseType verified against
        # NeverSink's live SOFT filter.
        out += gen._lf_gold_guard(gen.filter_theme_style(theme, "gold"))
        if hide_risky:
            out += [f"# WARNING: {untranslatable_total} pickit rule(s) couldn't be "
                    "translated — items only those rules match",
                    "# will be HIDDEN in game, even though the bot still picks them up.",
                    ""]
        out += ["# Hide everything else", "Hide", ""]

    return {
        "ok": ok,
        "filter_lines": out if ok else [],
        "report": {
            "looks_like_filter": looks_like_filter and not ok,
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
