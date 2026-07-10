# Changelog

All notable changes to **ExileBot 2 Pickit Generator**.
Versions link to their release, where the `ExileBot2PickitGenerator.exe`
download lives.

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

[v4.4.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.4.0
[v4.3.6]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.6
[v4.3.5]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.5
[v4.3.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.4
[v4.3.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.3
[v4.3.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.2
[v4.3.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.1
[v4.3.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.0
[v4.2.9]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.2.9
