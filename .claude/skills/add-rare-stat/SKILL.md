---
name: add-rare-stat
description: Add or change a stat in a rare-gear WeightedSum recipe or a Fracture Bases target - the wrong or renamed stat id / weight is this project's most repeated bug.
---

# Adding a rare-gear or fracture stat (this repo)

This is the single most repeated bug class in this project's history: a stat id
that was renamed or never existed as a craftable affix, or a weight that
doesn't match the real max roll. It has happened to body Spirit, evasion,
elemental damage, crossbow bolts, crit-damage family ids, and more — each time
because a display name looked plausible but the ENGINE id was different, or
because a weight was computed from a wrong or stale roll. Don't guess; verify
every step below.

Relevant files: `src/exilebot_pickit/data/rare/rules.py` (RARE_GEAR weights),
`src/exilebot_pickit/data/fracture_bases/fracture_bases.py` (FRACTURE_TARGETS +
`_FRACTURE_VERIFIED_STAT_IDS`), `src/exilebot_pickit/data/bot_stat_ids/` (the
bot's own valid-id set).

## The trap this guards against

The game's DISPLAY text and its ENGINE stat id are not always the same family.
"Critical Damage Bonus" on gloves/quivers/staves still uses the legacy
`*_critical_strike_multiplier_+` ids, not a newer-looking
`*_critical_hit_damage_bonus` one. Flat evasion is `local_base_evasion_rating`,
not the never-craftable `evasion_rating`. Flat body-armour Spirit is
`base_spirit_from_equipment` (body/amulet only); `local_spirit_+%` is
sceptre-only and would silently match nothing on a body armour. The only way
to catch this is to check the id against real data, every time — never assume
a name that "sounds right" is the real one.

## Steps

1. **Get the real roll from live data**, not memory and not a reference pickit
   (reference files are read-only learning material — never copy a stat id
   from one). Two sources, both already used in this repo:
   - Craft of Exile 2's JSON — see the `verify-bases-coe` skill for the exact
     URL and how to fetch it (kept in ONE place on purpose, so the two skills
     can't quietly drift apart the way a copied URL did once already). Same
     source; it also has mod tiers/rolls, not just base defence numbers.
   - The GGPK mod dump `tools/check_game_data.py` already fetches
     (`repoe-fork mods.min.json`) — the authority on which stat ids exist as a
     normal magic/rare (prefix/suffix) affix, not an implicit/corrupted/essence-only
     one.
2. **Find the T1 (top) roll for that mod on the exact base/class you're scoring.**
   Rolls differ by weapon-speed class (1H vs 2H), by hybrid vs pure defence
   base, and sometimes by slot (rings roll a full tier above gloves on added
   damage, for example). Use the number for the actual base(s) in the recipe.
3. **Compute the weight**: `weight = 100 / T1_max_roll`, rounded to 2 decimals.
   This is why every weight line in `rules.py` carries a `# T1 max N` comment —
   `tools/check_game_data.py` (and the in-app Game Data health check) verify the
   weight against that comment automatically; keep the comment accurate or the
   checker can't catch drift.
4. **Confirm the id is a real bot stat.** It must be in
   `data.bot_stat_ids.BOT_STAT_IDS` (the bot's own `ModsList.html`, decompressed
   at import — 27k+ entries). An id that "looks like" a real one but isn't in
   that set will fail the bot's own validator with "Not found in stats.json".
5. **Multi-tier stats** ("T1 or T2 both count" is the owner's standing rule for
   several slots): use an OR-group of per-stat thresholds gated on the T2
   MINIMUM roll (see `_FRACTURE_OR_GROUP_IDS` in fracture_bases.py for the
   pattern), never a placeholder. Gate on the MAX roll for added-damage ranges
   (min rolls are always tiny, e.g. 1, so gating on the min filters nothing).
6. **Fracture targets only**: a target with no confirmed bot expression must
   stay reference-only — map it to `None`/omit it from
   `_FRACTURE_VERIFIED_STAT_IDS` rather than emitting a guessed rule. Never
   fabricate an expression that hasn't been checked against the bot's real
   files.
7. **Verify, don't trust your own math**: run
   `python tools/check_game_data.py` (checks stat ids, weights vs their
   comments, and base droppability against the live patch) and
   `python -m pytest tests/test_rare.py tests/test_fracture_bases.py -q`
   (checks every id is in `BOT_STAT_IDS`, every rare-gear rule validates with
   zero errors, and every emitted mod id is real).
8. Add a dated comment recording what you verified and against which source —
   every existing weight/target already does this; it's what makes the NEXT
   person's `check_game_data.py` run meaningful instead of a bare number.
