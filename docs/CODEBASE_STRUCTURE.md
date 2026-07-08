# Codebase Structure

Reference for humans and AI coding agents working in this repository. This
document describes the **real** structure of the project. It is Python plus
one single-file vanilla-JS HTML UI — there is no React, no TypeScript, no
bundler, and no `src/app` / `src/features` / `src/components` layout. Do not
introduce that shape here; see `docs/CODEBASE_CLEANUP_REPORT.md` for why.

## What this app is

**ExileBot 2 Pickit Generator** is a Windows desktop app that turns live
[poe.ninja](https://poe.ninja) Path of Exile 2 economy prices into an
Exiled Bot 2 pickit file (`.ipd`). The user picks a league and value floors,
presses Generate, and the app writes ~2,000+ pickit rules covering what is
worth money *today*. It ships as a single PyInstaller `.exe` (no Python
install, no installer) and self-updates its game data from this repo.

Data flow: **poe.ninja prices → user floors & choices → `.ipd` pickit → the bot.**

Architecturally it's one Python engine (fetching, corrections, rule
assembly, config) driven by two front ends: a pywebview/WebView2 window
whose entire UI is a single HTML file, and a headless `--cli` mode. Both
front ends call into the same engine code, so logic added to the engine is
automatically available to both.

The app also emits a matching in-game `.filter` for manual play, but the
`.ipd` is the file the bot actually reads.

## Folder tree (verified against the working tree)

```
src/exilebot_pickit/
  __main__.py            Entry point. `python -m exilebot_pickit` -> WebView2 UI;
                          `--cli` -> headless generator.
  version.py              VERSION = "X.Y.Z" - single source of truth. MUST match
                          the release tag or the Release workflow fails.
  generator.py            (~1000+ lines) The engine: poe.ninja fetching, name
                          corrections, rule builders (build_base_rules,
                          build_craft_base_rules, CHANCE_BASES, etc.), CLI.
                          Re-exports from api/ and data/ submodules for a
                          backward-compatible flat API - much existing code does
                          `import generator as gen` and expects names to live here
                          even when their real definition has moved to a submodule.
  generators/
    __init__.py
    assembly.py            Pure, network-free, Tk-free rule-assembly logic. Takes
                          fetched payloads + a settings *snapshot* dict -> the lines
                          written to the .ipd. This is the unit-testable half of a
                          generate run (see tests/test_assembly.py).
  api/
    __init__.py
    client.py               poe.ninja API client: in-memory + disk cache, retry/
                          backoff (429 / Retry-After), league detection, category
                          fetching.
  data/
    __init__.py
    remote_data.py           Self-updating game data: refreshes base_types + unique
                          categories from game_data.json on GitHub at launch.
                          Best-effort & silent - bad/missing data keeps the
                          bundled copy.
    corrections.py           poe.ninja-name -> in-game-name fixes, skip lists,
                          always-pick currency/runes, tablets, splinters,
                          wombgifts, exotic bases.
    base_types.py            Endgame base types by category (from PoE2
                          baseitemtypes.json).
    icons.py                 STATIC_ICONS (item art as embedded data URIs) +
                          BASE_STATS. Icons ship in the exe so they work offline.
  webui/
    app.html                 THE UI - a single self-contained HTML file (see
                          "Fragility rules" below).
    api.py                   Python<->JS bridge (pywebview). One AppApi class
                          exposed to app.html; reuses the same engine and config
                          as any other front-end. Long work runs on a worker
                          thread; the page polls status().
    poc.py                   WebView2 window launcher + system-tray mode.
  ui/
    config.py                Config path bootstrap, defaults, atomic load/save.
    updater.py               Update check: compares latest GitHub tag to VERSION,
                          surfaces a banner. (No auto-download/swap - that was
                          removed; see the updater-safety skill for what remains
                          load-bearing.)
  resources/                 App icons (appicon.ico / .png / _src.png).

game_data.json               Remote-updatable game data (schema version 2). MUST
                          stay in sync with the code objects in data/ - tests
                          enforce this (tests/test_remote_data.py).
tests/                       pytest suite (network-free; poe.ninja mocked).
.github/workflows/           ci.yml (test+lint+build smoke on push/PR to main),
                          release.yml (build+publish exe on v* tags).
build.exe.bat                Local Windows build script (mirrors the CI build
                          flags).
docs/                         README screenshot/logo/site, plus this document and
                          CODEBASE_CLEANUP_REPORT.md.
```

Runtime data (config, caches, output) lives in an
`ExileBot2PickitGenerator_data` folder next to the exe when frozen, or
`%APPDATA%/exilebot-pickit` in dev. It is **not** in the repo (`.gitignore`d).

**Drift check:** the tree above was cross-checked against a live directory
listing of `src/exilebot_pickit`. Every file CLAUDE.md's "Repository layout"
lists is present; nothing extra of note was found beyond `__pycache__`
directories (expected, gitignored) and the `resources/` icon files (present
but not individually enumerated in CLAUDE.md — a minor omission, not a
contradiction). CLAUDE.md is accurate as of this writing.

## Where a new file of each kind goes

| Adding... | Goes in... |
|---|---|
| A new poe.ninja API endpoint / fetch call | `api/client.py` |
| New game data, name corrections, skip lists, always-pick items | a module under `data/` (new or existing) |
| New rule-building / pickit-assembly logic | `generators/assembly.py` (pure/testable) or `generator.py` (if it needs the fetch/CLI machinery already there) |
| A new UI page/tab | `webui/app.html` (it's the only UI file — add the page's HTML block in the existing page order, see Fragility rules) **and** a corresponding new method on `AppApi` in `webui/api.py` if the page needs to call into Python |
| A new config option | `ui/config.py` (defaults + load/save) |
| A new self-updating game-data list | add the code object under `data/`, then re-sync `game_data.json` (see "game_data.json ↔ code must not drift" below) |

## Naming rules actually used in this repo

- Python modules are `snake_case.py`: `client.py`, `assembly.py`,
  `base_types.py`, `remote_data.py`, `config.py`, `updater.py`, `poc.py`.
- No vague/placeholder module names exist anywhere in the repo — no
  `helper.py`, `utils.py`, `utils2.py`, `misc.py`, `final.py`. Every module
  name describes what it contains. **Preserve this** when adding new
  modules; don't introduce a generic dumping-ground file.
- The one HTML/JS file is `app.html` — vanilla JS inline in a `<script>`
  block, no component files, because there is no build step to assemble them.

## The "generator.py is the compatibility surface" pattern

`generator.py` used to hold nearly everything: fetching, corrections, base
data, and rule builders in one ~1900-line file. As pieces were extracted
into `api/` and `data/` submodules, **`generator.py` kept re-exporting the
moved names** so that all the existing call sites (`import generator as gen`
then `gen.SOME_NAME`) keep working unchanged. The submodule is the real home
and owns the definition; `generator.py` just imports and re-exports it.

Reference example of this pattern: the Fracture Bases data and logic
(`FRACTURE_CLASS_GROUPS`, `FRACTURE_TARGETS`, `FRACTURE_TIERS`,
`FRACTURE_EXCLUDED_UNVERIFIED`, `build_fracture_pickit_rules`,
`classify_fracture_item`, etc.) live in `src/exilebot_pickit/data/
fracture_bases.py`, and `generator.py` re-exports them so `gen.
FRACTURE_TARGETS` and friends keep working exactly as before the move. Use
this as the template when extracting the next data block: move the
definitions to a focused module under `data/` (or `api/`), then add the
re-export lines in `generator.py` rather than updating every call site.

## Critical fragility rules (see the matching skill before touching these)

- **`webui/app.html` is one file.** A single missing element id or JS syntax
  error kills the entire app (symptom: league dropdown stuck on "Loading…",
  empty version label). After ANY edit: extract the `<script>` body and
  `node --check` it, and audit that every `$("id")` matches exactly one
  `id="..."` (zero missing, zero duplicate). See skill `ui-edit-check`.
- **PoE2 game-data names must be verified before being added anywhere**
  (`game_data.json`, `data/corrections.py`, `data/base_types.py`,
  `generator.CHANCE_BASES`, or any new `data/` module). PoE2 renames/removes
  items every patch and wikis list unreleased datamined items — verify
  against NeverSink's live SOFT filter before adding a name. See skill
  `verify-game-data`.
- **`game_data.json` ↔ code must not drift.** When any game-data list
  changes in code, re-sync `game_data.json` and confirm
  `python -m pytest tests/test_remote_data.py -q` passes — it diffs JSON
  against code.

## What should NOT go directly in `src/exilebot_pickit/` root or the repo root

- New engine logic: it belongs in `generators/`, `api/`, or `data/`, not
  loose in the package root next to `generator.py` and `version.py`.
- New UI code: it belongs in `webui/` (either inside `app.html` or as a new
  method on `AppApi` in `webui/api.py`), not as a new top-level `.py` or
  `.html` file.
- New config/update logic: it belongs in `ui/`.
- Generated/runtime artifacts (config, caches, output `.ipd`/`.filter`
  files): never committed to the repo at all — they live in the
  `ExileBot2PickitGenerator_data` folder outside the repo.
- Ad-hoc or one-off scripts: don't add these to the repo root; use a
  scratch/temp location outside version control.
