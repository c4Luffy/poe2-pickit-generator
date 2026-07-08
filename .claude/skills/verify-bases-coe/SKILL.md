---
name: verify-bases-coe
description: Rank/verify craft & exceptional gear bases against live Craft of Exile 2 data (defence per attribute, phys-DPS for weapons). Use before changing _CRAFT_BEST_BASES or the exceptional base lists.
---

# Verify bases vs Craft of Exile 2 (this repo)

For choosing/verifying the BEST gear bases per slot — `generator._CRAFT_BEST_BASES`
(craft bases) and `data/base_types._BASE_TYPES_BY_CATEGORY` (exceptional bases).
This is about *which base is strongest*, not whether it exists — for existence in
the current patch use `verify-game-data` (NeverSink). Do both: rank here, confirm
the winner drops there.

## The data source — ALWAYS fetch fresh, never reuse a local dump

Craft of Exile 2 is a JS SPA (unscrapeable), but exposes raw JSON at
`https://www.craftofexile.com/json/poe2/main/poec_data.json` (served as
`poecd={...}` — strip the `poecd=` prefix and trailing `;`, then `json.loads`).
Download it to the scratchpad with a python script (urllib + a browser
User-Agent), don't WebFetch it (too big).

**Never use a data file the user has sitting on disk as a source, even if it
looks like the same shape** (e.g. an old `mods/*.json` export, a prior
`coe.json` in the scratchpad from an earlier session). PoE2 patches change mod
tiers/values, and a several-months-old dump WILL be wrong — this bit once: a
stale local mod-tier folder produced wrong skill-level values for half the
weapon classes (Crossbow +7 instead of the real +5, etc.), caught only because
the user spot-checked one number. If the user shares a folder of game data,
treat it as a hint about *what to verify*, not an answer — always re-fetch
`poec_data.json` live before writing any tier/value into code, every session,
even if a fetch was already done earlier that same session for a different
class (data doesn't go stale in-session, but starting a fresh check on old
in-memory data from hours/days ago is the same mistake — re-fetch if unsure).

Structure:
- `d["bgroups"]["seq"]` — `{id_bgroup, name_bgroup}` (Body Armours, Helmets, …).
- `d["bases"]["seq"]` — `{id_base, id_bgroup, name_base}` (base group).
- `d["bitems"]["seq"]` — the actual bases: `{id_base, name_bitem, drop_level,
  properties (JSON string), imgurl, is_legacy}`.
- `properties` (parse the string): armour / evasion / energy_shield for armour;
  physical_damage_min/max, attack_time, critical_strike_chance for weapons.

Map `bitem -> base(id_base) -> bgroup(id_bgroup) -> name`. Weapon *type*
(Bows/Spears/Quarterstaves/Crossbows) is NOT a bgroup — read it from the
`imgurl` path (`/OneHandSpears/`, `/Bows/`, or filename contains `Quarterstaff`).

## Ranking rules

- **Attribute subcategory** = which of armour/evasion/ES are nonzero:
  STR=armour, DEX=evasion, INT=ES, and the hybrids (STR/DEX, STR/INT, DEX/INT).
  Rank within a subcategory by the relevant sum.
- **Armour: rank by highest defence *within the top item-level tier*, not raw
  defence.** The single biggest trap: the highest raw-defence base is often a
  LOWER-ilvl base (e.g. lv65) — useless for crafting. Filter to the top
  `drop_level` (lv80 for most armour slots) first, THEN pick the highest defence.
- **Weapons: rank by base phys DPS** = `((min+max)/2) * (1000/attack_time)`.
  Consider crit% and attack speed on close calls (a high-crit base can beat a
  higher-DPS one for crit builds — flag it as a build-dependent choice).
- **Exclude** `is_legacy=="1"` and special variants whose names contain
  "Runemastered" / "Runeforged" — they are not normal craftable bases.

## Process

1. Download + parse the JSON to scratchpad.
2. Print, per slot + subcategory, the current pick vs. the top candidate(s) with
   their stats, so the diff is obvious.
3. For any change: confirm the new base drops in the current patch
   (`verify-game-data`), confirm it has an entry in `data/icons.py`
   (STATIC_ICONS + BASE_STATS) or the tab renders blank, then update the code.
   Craft bases are NOT in `game_data.json` (code-only) — no JSON re-sync needed.
4. Surface build-dependent or ilvl-vs-DPS tradeoffs to the user rather than
   silently swapping — it changes what the bot picks up.
5. `pytest -q` + `ruff` after (tests guard craft-base validity and ilvl gates).
