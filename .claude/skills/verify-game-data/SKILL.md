---
name: verify-game-data
description: Verify every item name the app ships against the live game before a data change - PoE2 removes/renames items every patch and wikis lie.
---

# Game-data verification (this repo)

PoE2 removes and renames items every patch. Before adding ANY item name to
`game_data.json`, `data/corrections.py`, `data/base_types.py` or
`generator.CHANCE_BASES`, verify it actually DROPS in the current patch:

1. **Primary source — NeverSink's live filter** (the FilterBlade data):
   download `https://raw.githubusercontent.com/NeverSinkDev/NeverSink-PoE2litefilter/master/NeverSink's%20filter%202%20-%200-SOFT.filter`
   (this is the exact URL `tools/check_game_data.py`'s `NEVERSINK_URL` uses —
   keep this skill's link in sync with that constant, they drifted apart once
   already) and grep for the exact name. If it's not in the SOFT filter, it
   does not drop — do not add it (poe2db lists datamined UNRELEASED items, e.g.
   "Expedition Tablet" and "Tempered Rune" were traps).
2. **Secondary — poe2db.tw** for stats/icons: page URL is the name with
   spaces→underscores, apostrophes kept ("Kulemaks_Invitation" style when
   the encoded form 404s). Item art regex:
   `https://cdn\.poe2db\.tw/image/Art/2DItems[^"']+\.(?:png|webp)` — the CDN
   requires a `Referer: https://poe2db.tw/` header; icons are embedded as
   data URIs in `data/icons.py` (STATIC_ICONS) with stats in BASE_STATS.
3. After changing lists: re-sync `game_data.json` from the code objects and
   run `python -m pytest tests/test_remote_data.py -q` — it fails on drift.
4. Never add rules without a `[Type]`/`[Category]` condition: Exiled Bot
   treats a type-less rule as matching EVERYTHING on the ground.
5. Chance bases: the list is owner-curated (4 since 2026-07-17: Utility Belt,
   Heavy Belt, Gold Ring, Stellar Amulet — the low-value chase targets were
   removed on the owner's order). Never add or remove entries without an
   explicit owner decision.
