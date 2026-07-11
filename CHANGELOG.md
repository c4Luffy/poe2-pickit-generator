# Changelog

All notable changes to **ExileBot 2 Pickit Generator**.
Versions link to their release, where the `ExileBot2PickitGenerator.exe`
download lives.

---

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
