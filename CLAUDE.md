# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## What this project is

**ExileBot 2 Pickit Generator** — a Windows desktop app that turns live
[poe.ninja](https://poe.ninja) Path of Exile 2 economy prices into an
Exiled Bot 2 pickit file (`.ipd`). The user picks a league and value floors,
presses Generate, and the app writes ~2,000+ pickit rules covering what is
worth money *today*. It ships as a single PyInstaller `.exe` (no Python, no
installer) and self-updates its game data from this repo.

Data flow: **poe.ninja prices → user floors & choices → `.ipd` pickit → the bot.**

The app also emits a matching in-game `.filter` for manual play, but the `.ipd`
is the file the bot reads.

## Repository layout

```
src/exilebot_pickit/
  __main__.py            Entry point. `python -m exilebot_pickit` → WebView2 UI;
                         `--cli` → headless generator.
  version.py             VERSION = "X.Y.Z" — single source of truth. MUST match
                         the release tag or the Release workflow fails.
  generator.py           (~1100 lines) The engine: poe.ninja fetching, name
                         corrections, rule builders (build_base_rules,
                         build_craft_base_rules, CHANCE_BASES, etc.), CLI.
                         Re-exports from api/ and data/ for a backward-compatible
                         flat API — much code does `import generator as gen`.
  generators/
    assembly.py          Pure, network-free, Tk-free rule-assembly logic. Takes
                         fetched payloads + a settings *snapshot* dict → the lines
                         written to the .ipd. This is the unit-testable half of a
                         generate run (see tests/test_assembly.py).
    filter_classification.py
                         Pure: maps one IPD rule → a visual kind for the loot
                         filter (value ladder from the rule's ExValue + the
                         file's Divine rate; section purpose for unpriced
                         rules). Never touches pickup decisions.
    filter_themes.py     Pure: the style table (kind → filter style lines).
                         ONE theme by owner decision; NO PlayAlertSound ever.
    pickit_import.py     Pure: any .ipd → in-game .filter + honest report
                         (Create your filter). Shares classification/themes
                         with generator.build_loot_filter.
  api/
    client.py            poe.ninja API client: in-memory + disk cache, retry/backoff
                         (429 / Retry-After), league detection, category fetching.
  data/
    remote_data.py       Self-updating game data: refreshes base_types + unique
                         categories from game_data.json on GitHub at launch.
                         Best-effort & silent — bad/missing data keeps the bundled copy.
    corrections.py       poe.ninja-name → in-game-name fixes, skip lists, always-pick
                         currency/runes, tablets, splinters, wombgifts, exotic bases.
    base_types.py        Endgame base types by category (from PoE2 baseitemtypes.json).
    icons.py             STATIC_ICONS (item art as embedded data URIs) + BASE_STATS.
                         Icons ship in the exe so they work offline.
  webui/
    app.html             THE UI — a single self-contained HTML file (see warning below).
    api.py               Python↔JS bridge (pywebview). Reuses the same engine and
                         config as any other front-end. Long work runs on a worker
                         thread; the page polls status().
    poc.py               WebView2 window launcher + system-tray mode.
  ui/
    config.py            Config path bootstrap, defaults, atomic load/save.
    updater.py           Update check: compares latest GitHub tag to VERSION,
                         surfaces a banner. (No auto-download/swap — that was removed.)
  resources/             App icons.

game_data.json           Remote-updatable game data (schema version 2). MUST stay in
                         sync with the code objects in data/ — tests enforce this.
tests/                   pytest suite (network-free; poe.ninja mocked).
.github/workflows/       ci.yml (test+lint+build smoke on push/PR to main),
                         release.yml (build+publish exe on v* tags).
build.exe.bat            Local Windows build script (mirrors the CI build flags).
docs/                    README screenshot.
tools/
  check_game_data.py     Game-data drift checker. Fetches the live GGPK mod dump
                         (repoe-fork mods.min.json) + NeverSink's SOFT filter and
                         diffs them against our stat ids, weights and base names.
                         Flags renamed/removed stat ids, weight-vs-comment
                         mismatches, and bases that may no longer drop. Run before
                         a game-data change: `python tools/check_game_data.py`.
```

Runtime data (config, caches, output) lives in a `ExileBot2PickitGenerator_data`
folder next to the exe when frozen, or `%APPDATA%/exilebot-pickit` in dev. It is
**not** in the repo (`.gitignore`d).

## Development workflow

```bash
pip install -e .                 # install
python -m exilebot_pickit        # run the GUI (needs a display / Windows WebView2)
python -m exilebot_pickit --cli --league "Fate of the Vaal"   # headless generate
python -m exilebot_pickit --cli --list-leagues

pip install pytest "ruff==0.15.20"
python -m pytest -q              # tests (fast, no network — poe.ninja is mocked)
ruff check .                     # lint
```

**Both `pytest` and `ruff check .` must be clean before any commit.** CI runs
them on Python 3.10/3.11/3.12, byte-compiles every module, runs the suite, and
does a Windows `.exe` build smoke test. Lint is deliberately high-signal only
(`E9,F,B,UP`, line-length 120) — do not introduce a broad style reset.

## Critical conventions

These are load-bearing. Violating them ships a broken app. Three project skills
(`.claude/skills/`) encode them in detail — read the relevant one before the
matching kind of change:

### Editing `webui/app.html` → skill `ui-edit-check`
It is **one file**; a single missing element id or JS syntax error kills the
entire app (symptom: league dropdown stuck on "Loading…", empty version label).
After ANY edit:
- Extract the `<script>` body and `node --check` it.
- Id audit: every `$("id")` must match exactly one `id="..."` — zero missing,
  zero duplicate.
- Pages are ordered blocks in this file: p-gen, p-eco, p-chance, p-craft, p-exc,
  p-fracture, p-rare, p-hist, p-dbg, p-prev, p-item, p-mypk, p-guide, p-set
  (re-verify with a regex over `class="page` — this list has gone stale before).
  When slicing by index, anchor on both the page's opening div and the next
  page's comment.
- Never build replacement JS via `re.sub` replacement strings (they eat `\n`);
  never pipe emoji through bash heredocs — write a Python script to scratchpad.
- Body uses `zoom:1.1`, so viewport heights are written as `90.9vh`, not `100vh`.

### Adding/changing game-data item names → skill `verify-game-data`
PoE2 renames/removes items every patch and wikis list unreleased datamined items.
Before adding ANY name to `game_data.json`, `data/corrections.py`,
`data/base_types.py`, or `generator.CHANCE_BASES`:
- Verify it drops in the current patch against **NeverSink's live SOFT filter**
  (the primary source of truth). If it's not there, it doesn't drop — don't add it.
- Use poe2db.tw only for stats/icons.
- Never write a rule without a `[Type]`/`[Category]` condition — Exiled Bot treats
  a type-less rule as matching *everything* on the ground.
- The chance-base list is owner-curated (4 bases since 2026-07-17: Utility
  Belt, Heavy Belt, Gold Ring, Stellar Amulet). Never add or remove entries
  without an explicit owner decision.

### game_data.json ↔ code must not drift
When any game-data list changes in code, re-sync `game_data.json` and confirm
`python -m pytest tests/test_remote_data.py -q` passes — it diffs JSON vs code.

Run `python tools/check_game_data.py` after a patch (or when adding names) to
catch the *other* kind of drift — a stat id the game renamed, or a base that
stopped dropping — against the live GGPK mod dump and NeverSink's SOFT filter.
It flags for human review; it never edits data. Weights stay consistent when
each `# T1 max N` comment equals `100 / weight` (the checker verifies this).

### Releasing → skill `release`
1. Working tree is only the changes to ship; `pytest -q` + `ruff check src tests` clean.
2. Run the app.html JS `node --check` + id audit.
3. Bump `version.py` (must equal the tag).
4. README "What's new": add the new version on top, keep ~5 entries (older drop
   into the collapsible).
5. Re-sync `game_data.json` if code lists changed.
6. Commit `vX.Y.Z: …`, push, `git tag vX.Y.Z && git push origin vX.Y.Z`.
7. The test-gated Release workflow builds `ExileBot2PickitGenerator.exe` — **this
   filename must never change**; the in-app updater's download URL depends on it —
   plus `SHA256SUMS.txt`.

## Design principles baked into the code

- **One engine, swappable front-ends.** `webui/api.py` reuses `api.client`,
  `generators.assembly`, and `ui.config` — the same config/state as any other UI.
  Keep new logic in the shared engine, not the UI layer.
- **Self-updating without a new release.** Unique items refresh every generate
  (live poe.ninja); bundled base/category lists refresh from `game_data.json`.
  Remote-data loading is silent and best-effort — never let it hard-fail the app.
- **Config safety.** `ui/config.py` saves atomically and recovers from corruption;
  a bad write must never wipe a user's settings/profiles/exclusions
  (`tests/test_config.py` guards this).
- **`generator.py` is the compatibility surface.** It re-exports names from `api/`
  and `data/`; prefer importing through `generator as gen` to match existing code.

## Git / PR conventions

- Branch off `main`; open PRs against `main`. A PR template exists
  (`.github/PULL_REQUEST_TEMPLATE.md`) with a checklist (ruff, pytest, GUI-tested,
  README updated) — fill it in.
- Release commits use the `vX.Y.Z: …` subject convention.
