# Changelog

All notable changes to **ExileBot 2 Pickit Generator**.
Versions link to their release, where the `ExileBot2PickitGenerator.exe`
download lives.

---

## [v4.11.4] — 2026-07-12 — Rings get fracture targets

Rings were the last big empty slot in the Fracture tab. Researched the full ring
affix pool from the game's mod database — **34 stats can naturally roll on a
ring, and every one of them exists in the bot's ModsList**, so there was never a
technical blocker; nobody had built the targets.

### Added
- **Three ring fracture targets** (36 rules):
  - **Resistance** (S) — resistance is the *highest-level affix a ring can roll*
    (lvl 82), and rings are the game's main resistance slot. Chaos res (lvl 81)
    is the scarcest defence in the game.
  - **Added attack damage** (S) — rings roll a **full tier above gloves**
    (Lightning 60-71 vs the glove cap of 48-59), making ring the best flat
    added-damage slot in the game.
  - **Item Rarity** (A+) — the MF market; rarity is worn twice.
- **Six ring bases**, chosen by implicit rather than item level:
  **Biostatic** (+1% to all *maximum* resistances — the best ring implicit in the
  game), **Gold** (rarity), and the four **modifier-count rings** —
  **Tenebrous** (−2 prefix/+2 suffix), **Penumbra** (+2/−2), **Gloam** (−1/+1),
  **Dusk** (+1/−1). Those four bias which affix *type* the ring can carry, which
  is exactly what you want when fracturing for one specific mod: resistances are
  suffixes, added damage and rarity are prefixes.

### Changed
- **Rare Ring recipe: Amethyst → Biostatic.** Amethyst is an ilvl-20 base whose
  +7-13% chaos-res implicit is strictly worse than the chaos-res *suffix* the
  recipe already scores (24-27%). Biostatic is the highest ring base (ilvl 52)
  and grants max resistances.
- Attributes stay excluded from rings (owner rule); Life, accuracy, cast speed,
  leech and regen are filler in this slot and are not fracture targets.

## [v4.11.3] — 2026-07-12 — Jewels and Charms dropped from Fracture

### Changed
- **Jewels and Charms are gone from the Fracture tab.** They had no fracture
  targets and never will (owner call) — they only sat there as empty rows.
  The tab now lists 19 item classes instead of 21. A test bans them from
  creeping back in.
- Unaffected: **unique Jewels and Charms still price normally** in the Economy
  tab. This only removes them as fracture targets.

## [v4.11.2] — 2026-07-12 — Four dead fracture rules fixed (evasion, elemental)

A new game-data checker (`tools/check_game_data.py`) compares our stat ids,
weights and base names against the game's own mod and item tables. On its first
run it found four Fracture rules that could never match anything.

### Fixed
- **The three Evasion fracture rules** (body, helmet, boots) used the stat id
  `evasion_rating`, which **no craftable affix in the game grants**. Flat Evasion
  is `local_base_evasion_rating` — the mod that rolls the exact 262-300 those
  rules quote. Evasion was always in the game; our id for it was wrong, so the
  rules silently matched nothing. Same renamed-id family as the body-Spirit fix.
- **The elemental-damage fracture rule** used `elemental_damage_+%`; the only
  craftable elemental affix is `elemental_damage_with_attack_skills_+%` (which
  the rare-gear weapon recipes already scored correctly).

### Added
- **`tools/check_game_data.py`** — fetches the live GGPK mod dump and item table
  and flags renamed/removed stat ids, weights that disagree with their documented
  T1 max-roll, and base names that no longer exist. It reports for human review
  and never edits data.

### Verified
- All 67 engine stat ids now exist as craftable affixes; all 188 rare-gear
  weights match their documented rolls; all 53 base names still exist in the game.

## [v4.11.1] — 2026-07-12 — Copy buttons on the Magic & Rare tab

Quality-of-life: get the rare-gear rules out of the app and into your pickit
(or a chat) without hand-selecting text.

### Added
- **Copy stats** on each slot card — copies the scored-stat list (label,
  weight, bot stat id) as tab-separated rows, ready to paste into a sheet.
- **Copy rules** on each slot card — copies that slot's exact `.ipd` rule lines.
- **Copy all rules** in the tab header — grabs all 51 rare-gear rules at once,
  each slot under its own header, in the same order the pickit writes them.

## [v4.11.0] — 2026-07-12 — Rare gear goes LIVE: all 17 slots, in every pickit

The rare-gear WeightedSum recipes are done and **written into every generated
pickit**. All 17 gear slots — armour, jewellery, off-hand and every weapon —
now score rare drops by what actually sells, so the bot keeps the rares worth
picking up and leaves the vendor trash on the floor.

### Added
- **Rare gear in generated pickits.** The full 17-slot recipe set (Body Armour,
  Helmet, Gloves, Boots, Amulet, Ring, Belt, Focus, Quiver, Bow, Crossbow,
  Quarterstaff, Spear, Mace, Sceptre, Wand, Staff) is written into every `.ipd` —
  51 rules, three bases a slot. Each rule keeps a rare only if it clears a
  **WeightedSum** of the stats that matter for that slot (threshold 250 ≈ 2.5
  perfect rolls).
- **Master on/off switch** at the top of the Magic & Rare tab — turn the whole
  rare-gear set off and regenerate to get a pickit without it.
- **Headless `--cli` mode** now writes the rare-gear section too.
- **LIVE badges** on every slot card, replacing the draft marker.

### Recipes
- Every slot was built from its own poe.ninja ladder meta and the game's mod
  database (2026-07-12), not cloned from a template. Weapons score weapon-local
  **crit chance** (percent scale) alongside crit multiplier, added damage, skill
  levels and the "Surpassing" +1-projectile chase; the wand's **+4 to all spell
  skills** and the staff's **+5–6** are in. All 63 scored stat ids are verified
  present in the bot's ModsList.

### Fixed
- Five renamed fracture stat ids that silently never matched — projectile skill
  levels on bows/crossbows, +bolts, quiver bow-damage, and body flat-Spirit —
  now use the engine's real current ids.
- Amethyst Ring added to the base-type validator whitelist.

## [v4.10.0] — 2026-07-12 — Rare gear recipes: the armour set, in draft

The Magic & Rare tab starts showing its real content: per-slot **WeightedSum
recipes** for rare gear, built stat by stat and audited against the game's
own mod database and the live poe.ninja ladder meta.

### Added
- **Recipe cards in Magic & Rare.** Body Armour, Helmet, Gloves and Boots now
  show their full draft recipe: the WeightedSum threshold, minimum item tier,
  the exact bases (one rule per base), every scored stat with its weight and
  bot stat id, and the exact rule lines — ready to copy. Slots still being
  designed say so. Sidebar counts show which slots are drafted.
- **The four armour recipes themselves.** Each slot got its own recipe from
  what actually sells (poe.ninja Runes of Aldur ladder, 124k characters):
  - *Body Armour* — Life (the game's biggest roll, T1 214) + flat Spirit +
    4 resistances + the body-exclusive %ES tier.
  - *Helmet* — +2 Minion Skills (helmet-exclusive), Rarity, global crit,
    Life/res backbone.
  - *Gloves* — Attack Speed, +2 Melee Skills, Crit Damage Bonus, Rarity,
    Life/res backbone.
  - *Boots* — Movement Speed (30/35 dominate by design), Life, Rarity,
    full res + ES package.
  Every weight = 100 ÷ the stat's live T1 max-roll; every stat id verified in
  the bot's ModsList.

### Important
- **These recipes are DRAFT — they are NOT in generated pickits yet.** The
  jewellery, off-hand and weapon slots are still being built; the whole set
  ships into real pickit output together after a final review. Generated
  `.ipd` files are unchanged by this release.

## [v4.9.3] — 2026-07-12
### Fixed
- **Fracture "spirit body" rules could never match.** The "+57-61 to Spirit"
  body-armour target was mapped to `local_spirit_+%` — a SCEPTRE-only percent
  stat. Bodies roll FLAT Spirit (`base_spirit_from_equipment`, body/amulet
  only — confirmed in the game's mod database). The six emitted body-Spirit
  rules now use the right id and actually fire.

## [v4.9.2] — 2026-07-12 — Every Fracture target now emits real rules

### Fixed
- **The five remaining "unverified" Fracture targets are verified and wired.**
  PoE2 renamed the display text to "Critical Damage Bonus", but the engine
  kept the legacy stat ids — confirmed in the game's own mod database (GGPK
  dump, tier rolls match each target exactly) and re-checked against the
  bot's ModsList:
  - Staff *Critical Spell Damage Bonus* → `base_spell_critical_strike_multiplier_+` ≥ 53
  - Gloves *Critical Damage Bonus* → `base_critical_strike_multiplier_+` ≥ 30
  - Quiver *Critical Damage Bonus for Attack Damage* → `attack_critical_strike_multiplier_+` ≥ 30
  - Gloves *Adds Phys/Fire/Cold/Lightning to Attacks* → one rule with an
    OR-group of max-roll gates (≥ 18 / 33 / 25 / 48 — T2 minimums)
  - Belt *single-element Resistance* → one rule with an OR-group
    (elemental ≥ 36, chaos ≥ 20)
- The Fracture section now emits **441 rules, zero validation errors, zero
  placeholders** (was 411 rules plus 30 `UNVERIFIED_STAT_ID` example lines).

## [v4.9.1] — 2026-07-11
- **Floor sliders now drag up to 50** in every unit (Exalt / Chaos / Divine) —
  they were capped at 5, which made higher value floors impossible to reach by
  dragging. Typing a value still works exactly as before.

## [v4.9.0] — 2026-07-11 — History gets the Workbench treatment

The run-history page was rebuilt into a proper market-history view. Pure UI —
no engine changes, generated pickits are byte-identical.

### Redesigned
- **The run chart is a real chart now.** Gradient area fill, a dotted
  average line, the peak run marked with a diamond, and the latest value
  labeled right on the chart — no hover needed to know where you stand.
  Hovering snaps a crosshair to the nearest run with a richer tooltip:
  rules, ▲/▼ change vs the previous run, skipped, divine rate, top item.
- **Divine-rate sparkline** under the run chart — same timeline, its own
  scale. Watch "1 Div = X ex" drift across the league at a glance.
- **Tiles learned deltas.** "Last run rules" shows ▲ +58 / ▼ 12 vs the
  previous run in green/red; "peak rules" shows the date it happened.
- **The table tells you what moved.** New **Δ column** — a green `+335` /
  red `-5` pill per run vs the run before it — and friendly dates
  ("7 h ago"; the exact timestamp is on hover).

### Unchanged on purpose
- ↻ Re-run with these floors, Clear history, and the 50-run log all work
  exactly as before.

## [v4.8.0] — 2026-07-11 — Shortcuts, settings backup, one-click diagnostics

### Added
- **Keyboard shortcuts.** `Ctrl+1–9` switches tabs (Generate → Magic & Rare),
  `Ctrl+F` focuses the current tab's search box, `Ctrl+G` still generates.
- **Export / import settings (Settings).** Your whole setup — floors, toggles,
  profiles, exclusions — saved to one JSON file and restorable on any PC.
  Imports only accept known settings keys and apply instantly, no restart.
- **Copy diagnostics (Debug).** One click copies version, settings summary,
  cache state and the recent log — paste it when reporting a problem.

## [v4.7.0] — 2026-07-11 — Backup restore + new-league detection

### Added
- **Restore a backup (Settings).** The app already keeps rotating `.ipd`
  backups on every generate — now there's a list (date · size) with a
  one-click **Restore**. The pickit being replaced is itself backed up first,
  so a restore can never lose anything; `latest.ipd`, Preview, and (if
  auto-copy is on) your bot folder are all updated.
- **New-league banner (Generate).** When poe.ninja starts listing a league
  the app has never seen — league launch day — a banner offers a one-click
  **Switch**. Dismiss it and it stays dismissed.

---

## [v4.6.0] — 2026-07-11 — See what changed, redo what worked

Three quality-of-life features for the daily generate loop.

### Added
- **"🆕 Changed" filter in Preview.** After a generate, rules the run added are
  tinted green, a new filter chip shows only them, and items that dropped out
  of the pickit are listed struck-through — so you can see exactly how the
  market moved your pickit instead of reading a one-line summary.
- **"Re-run with these floors" in History.** Expand any past run and one click
  restores that run's exact value floors (switching Adaptive floors off so
  they stick) and generates again.
- **Auto-floor preview.** With Adaptive market floors OFF, changing "Keep top
  N%" now shows what the floors *would* be ("uniques ≥ 2.4 ex · everything
  else ≥ 0.8 ex") without applying anything — no more enabling it blind.

### Housekeeping
- Removed ~350 lines of dead code left from the frameless-window era (hidden
  title bar, resize handles, their JS and API endpoints) plus stale docs and
  an obsolete project skill. No behavior change.
- Website now shows the actual app (Generate-console screenshot) and the
  v4.5.0 ground-filtering feature.

---

## [v4.5.0] — 2026-07-11 — "Exile's Workbench" + smarter ground filtering

The look was rebuilt to the warmer **Workbench** design (aged brass & bone,
serif headings), and — more importantly — the pickit engine got real fixes
found by running the generated file in the actual bot.

### Pickit engine (the important part)
- **Item level now filters on the ground.** Base rules moved `[ItemLevel]`
  before the `#` — the bot reads game memory, so it knows a ground item's
  level before pickup (its own editor lists Item Level under BEFORE
  IDENTIFY). Low-level craft/exceptional bases are simply never picked up,
  instead of being hauled home, identified, and vendored.
  `[Type] == "Gold Ring" && [Rarity] == "Normal" && [ItemLevel] >= "75" # [StashItem] == "true"`
- **Fracture rules gate `[ItemTier] >= "4"`** before the `#`, so low-tier
  magic/rare bases stay on the ground too.
- **Fixed useless `>= "1"` thresholds** on ten fracture targets — the parser
  was reading the "1" out of tier tags like "T1 35–38%". Quiver crit is now
  ≥ 30, bow damage ≥ 43, sceptre spirit ≥ 56, and so on.
- **Added-lightning targets now gate on the maximum roll** (the minimum is 1
  on every tier, so it filtered nothing): quivers ≥ 48, one-hand weapons
  ≥ 157, two-hand ≥ 239 — verified live from Craft of Exile.
- **Duplicate rules deduped** (the sceptre skill-level pair emitted both
  ≥ 4 and ≥ 3 versions of the same rule).
- **"Aldur's Legacy" un-flagged** — it's a live Runes of Aldur league unique
  the pickit should (and does) grab; the old "deprecated" warning was bogus.
  Validation is now 100% clean.

### Redesigned — "Exile's Workbench"
- Aged **brass & bone palette** with Georgia serif headings (the approved
  Codex mockup), now the default and Relic theme; Frost/Blood retuned to
  match. Active nav tab is a thin brass left-border.
- **Generate is a "pickit recipe"**: each threshold is a labeled row with a
  plain-English description ("Exceptional base roll, 21–30%"), a big brass
  value, and a **drag-slider track** — the −/+ steppers are gone.
- **Last-run panel** with a status seal (◷ → ✓/✗ live), checklist and run
  stats; **market strip** (live league · divine rate · last-run moves ·
  refresh) under the console.
- **Top picks show real poe.ninja item art** instead of emoji, and each value
  reads in **exalt + divine + chaos**.
- Currency unit picker is a proper dark brass pill (no more white OS popup).

---

## [v4.4.0] — 2026-07-10 — "Exile's Ledger" UI overhaul

A complete visual redesign, built from an approved mockup. Every control and
element id was preserved — **no feature was removed**.

### Redesigned
- **Left rail navigation.** The old top tab-bar is now a 238px rail: brand
  sigil + version, three sections (Operate / Loot Rules / System) with all 11
  tabs always visible, live count badges (Preview / Economy / Fracture), a
  segmented theme switcher, and the Discord / Exiled Bot links pinned to the
  bottom.
- **Generate is now a console.** League + profile row, a "Build today's pickit"
  hero with a full-width Generate action, four **dial tiles** with −/+ steppers
  and fill tracks, and an output row.
- **Live "prices fetched X ago" indicator** in the top bar, so you can see at a
  glance how stale the economy data is.
- **LAST RUN checklist** (fetched → assembled → validated → written) with live
  values, plus KPI tiles (active / skipped / valid) that survive a restart by
  restoring from your newest history entry.
- **"Economy — top picks right now"** table under the console: the five most
  valuable items the run picked up, with their type.
- **New palette — obsidian ground, gold for value, steel for active state** —
  now the default theme. Frost and Blood were retuned to the same family; all
  three themes still work everywhere.
- The same design language was extended to **every remaining tab** — panels,
  section headers, and data tables (rounded item thumbs, monospace tabular
  values with a gold unit suffix, green `keep` / muted `skip` pills).

### Changed
- **Exceptional-base gates now state their real ranges.** Base quality is
  21–30% and base item level is 80–82 (that's what those bases actually roll).
  The dials clamp to those ranges, their fill tracks map across each dial's own
  range, and the Generate dials stay two-way synced with the Settings inputs.
  Configs holding an out-of-range legacy value are clamped on load.

### Fixed
- **History table columns never lined up with their headers.** A duplicate
  `.hrow` rule applied `display:flex` to a `<tr>`, breaking it out of table
  layout. (Pre-existing bug, not introduced by the redesign.)
- **The History chart used a hard-coded gold**, so its fill was the wrong colour
  under the Frost and Blood themes. It now follows the palette.
- Panels on Preview / Economy / Debug reclaim the ~65px of height the old top
  nav used to occupy.

---

## [v4.3.6] — 2026-07-10
- The window now **remembers its position** as well as its size, and reopens
  there — unless that spot is on a monitor you've since unplugged, in which
  case it re-centers.
- **Click any single rule line in Preview to copy just that rule** (text
  selection still works normally).
- New **"Bot folder"** button in Preview opens your configured Exiled Bot folder.

## [v4.3.5] — 2026-07-10
- Validation errors in Preview are now a **clickable list — click one to jump
  straight to that line** and flash it.
- New **"Open folder"** and **"Copy path"** buttons for the generated `.ipd`.

## [v4.3.4] — 2026-07-10
- **Fixed the multi-monitor freeze.** The window used a frameless custom title
  bar, which borderless WinForms windows mishandle — it would freeze or get
  stuck in the taskbar on secondary screens. It now uses a native OS window
  frame, so Windows owns minimize/restore/focus/multi-monitor behaviour.

## [v4.3.3] — 2026-07-10
- **Verified 33 Fracture stat ids** against the bot's own ModsList, taking the
  Fracture section from 94 to **417 emitted rules**. Five targets that have no
  clean single stat id remain honest placeholders rather than guesses.
- Set Per-Monitor-V2 DPI awareness (correct hygiene; it was not the cause of
  the freeze — see v4.3.4).

## [v4.3.2] — 2026-07-10
- Restructured `data/` so every module lives in its own folder (import paths
  unchanged).
- Added the `data/rare` package: the verified Rare stat menu as code, one file
  per section, every id validated against the bot's ModsList.

## [v4.3.1] — 2026-07-09
- Fracture examples now show the **real emitted rule** with its concrete
  threshold, instead of a `<value: …>` placeholder that the bot's validator
  rejected when pasted.

## [v4.3.0] — 2026-07-09
- **The loot filter now shows every item the bot acts on.** Items that were
  salvaged or stashed unidentified were previously hidden.

## [v4.2.9] — 2026-07-09
- Flasks moved from Fracture to the new **Magic & Rare** tab.

---

[v4.11.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.4
[v4.11.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.3
[v4.11.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.2
[v4.11.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.1
[v4.11.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.0
[v4.10.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.10.0
[v4.9.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.3
[v4.9.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.2
[v4.9.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.1
[v4.9.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.0
[v4.8.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.8.0
[v4.7.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.7.0
[v4.6.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.6.0
[v4.5.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.5.0
[v4.4.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.4.0
[v4.3.6]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.6
[v4.3.5]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.5
[v4.3.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.4
[v4.3.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.3
[v4.3.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.2
[v4.3.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.1
[v4.3.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.0
[v4.2.9]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.2.9
