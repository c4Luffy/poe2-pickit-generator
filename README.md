<div align="center">

# ExileBot 2 Pickit Generator

**Live Path of Exile 2 economy prices, converted into an Exiled Bot 2 pickit.**

Build a fresh `.ipd` from poe.ninja prices, tune your own value floors, exclude
anything you do not want, and keep your bot following the market instead of a
stale static list.

[![CI](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/c4Luffy/poe2-pickit-generator?label=latest%20release&color=2ea043)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=0969da)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![Windows](https://img.shields.io/badge/Windows-single%20.exe-0078D6)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

<br>

<a href="https://github.com/c4Luffy/poe2-pickit-generator/releases/latest">
  <img src="https://img.shields.io/badge/Download%20the%20Windows%20app-2ea043?style=for-the-badge" alt="Download the Windows app">
</a>

<br><br>

`poe.ninja prices` -> `your floors and exclusions` -> `.ipd pickit` -> `Exiled Bot 2`

</div>

---

## Quick Start

1. Download `ExileBot2PickitGenerator.exe` from the [latest release](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest).
2. Open the app and choose your league.
3. Set your value floors, or use **Auto floor** to calculate them from the current market.
4. Review the Economy, Chance Bases, Craft Bases, and Exceptional tabs.
5. Click **Generate Pickit**.
6. Point Exiled Bot 2 at the generated `.ipd`, or enable auto-copy to your bot folder.

The app also writes a matching `.filter` for manual play. Use the `.ipd` for the
bot. A loot filter that hides items can make bot pickup behavior unreliable.

## What It Generates

| File | Purpose |
| --- | --- |
| `.ipd` | The Exiled Bot 2 pickit. This is the main output. |
| `latest.ipd` | A stable copy of the newest generated pickit. |
| `.filter` | A Path of Exile 2 client loot filter for manual play. |
| `*_items.csv` | A price and inclusion report for auditing your rules. |
| `backups/*.ipd` | Rotating backups before each new generate. |

By default, generated files live in:

```text
ExileBot2PickitGenerator_data/pickit_output
```

When running from source, the data folder is stored under your user app-data
directory as `exilebot-pickit`.

## Why This Exists

Static pickits age badly. League prices move, patch data changes, new bases get
added, and yesterday's valuable drops can become tomorrow's stash clutter.

This tool keeps the boring part automated:

| Area | What it does |
| --- | --- |
| Live economy | Fetches current Path of Exile 2 prices from poe.ninja. |
| Value floors | Lets you set separate floors for unique gear and everything else. |
| Auto floor | Suggests floors based on the current league's price distribution. |
| Per-item toggles | Lets you disable individual items, categories, bases, and static picks. |
| Safety net | Warns and blocks auto-copy when a generated pickit looks collapsed or broken. |
| Offline fallback | Uses cached price payloads when poe.ninja is unavailable. |
| Self-updating data | Refreshes game-data lists from this repo without requiring a new `.exe`. |
| Bot-friendly output | Writes IPD rules with validation checks before deployment. |

## App Areas

| Tab | What you control |
| --- | --- |
| Generate | League, floors, auto floor, generate status, recent results. |
| Economy | Priced items, uniques, always-pick groups, search, sorting, exclusions. |
| Chance Bases | White bases worth chancing into valuable uniques. |
| Craft Bases | High-item-level Normal bases worth saving as crafting canvases. |
| Exceptional | Extra-socket-capable bases, quality gates, item level gates, unique-on-base pickup. |
| Preview | The exact generated `.ipd`, with sections and validation output. |
| History | Recent runs, rule counts, top values, and market movement context. |
| Settings | Bot folder, auto-copy, backups, tray mode, output names, update checks. |
| Debug | API checks, cache tools, logs, config access, and troubleshooting helpers. |

## Pickit Rules Covered

The generator combines live market data with curated static rules:

- Currency, essences, catalysts, runes, fragments, omens, soul cores, idols, gems, waystones, expedition items, and other exchange categories.
- Unique weapons, armours, accessories, flasks, charms, jewels, relics, and any remote-added unique categories.
- Always-pick groups such as tablets, splinters, wombgifts, boss keys, exotic bases, and key special items.
- Chance Orb bases for targets such as Headhunter, Mageblood, and other valuable uniques.
- Craft bases at configurable item level thresholds.
- Exceptional bases with quality and socket rules.
- Optional rules for any unique that drops on an exceptional base.

## Safety Features

The app is designed to avoid silently deploying a bad pickit:

- Generated rules are validated before they are shown in Preview.
- Backups rotate before overwriting the previous `.ipd`.
- Auto-copy is blocked if the new rule count collapses compared with the last run.
- Core currency rules are checked before deployment.
- Price data is cached to disk for offline fallback.
- Remote game-data updates are schema-validated before they are applied.

## Build From Source

Requires Python 3.10 or newer.

```bash
pip install -e .
python -m exilebot_pickit
```

Run the CLI generator instead of the GUI:

```bash
python -m exilebot_pickit --cli --league "Fate of the Vaal"
python -m exilebot_pickit --cli --list-leagues
```

Run tests and lint:

```bash
pip install pytest ruff
python -m pytest -q
python -m ruff check .
```

Build the Windows executable locally:

```bat
build.exe.bat
```

## Project Layout

```text
src/exilebot_pickit/
  api/client.py              poe.ninja API client, retries, memory and disk cache
  generator.py               legacy-compatible rule builders, CLI, validation
  generators/assembly.py     pure generate pipeline helpers used by the UI
  webui/api.py               Python bridge exposed to the WebView UI
  webui/app.html             single-file modern UI
  webui/poc.py               WebView2 entry point and tray integration
  ui/config.py               config paths, defaults, atomic save/load, logging
  ui/updater.py              GitHub release update checks
  data/remote_data.py        self-updating game-data loader
  data/base_types.py         bundled base-type data
  data/corrections.py        bundled name fixes and always-pick lists
```

## Releases

CI runs tests, lint, byte-compilation, and a Windows PyInstaller smoke build.

To ship a release:

1. Update `src/exilebot_pickit/version.py`.
2. Push a matching `vX.Y.Z` tag.
3. GitHub Actions builds `ExileBot2PickitGenerator.exe`.
4. The release includes the `.exe` and `SHA256SUMS.txt`.

## Troubleshooting

| Problem | Try this |
| --- | --- |
| Prices do not load | Open Debug, run the API test, then retry with Force refresh. |
| poe.ninja is rate-limiting | Wait a little, or generate from cached prices if available. |
| Bot ignores the pickit | Check the bot's configured `.ipd` path or enable auto-copy. |
| Windows blocks the `.exe` | Use "More info" -> "Run anyway" for the unsigned release build. |
| Settings reset | Check Debug -> open config. Corrupt configs are backed up before defaults load. |
| Want the last good file | Open the output folder and check `backups/`. |

## Current Version

`v3.4.0`

Highlights:

- Redesigned Economy tab with grouped categories and item icons.
- Per-item toggles for uniques, waystones, always-pick groups, craft bases, chance bases, and exceptional bases.
- Exceptional base cards with level and stat metadata.
- Smarter search across names and base types.
- New light theme, larger layout, cleaner settings/debug pages.
- Auto floor workflow for current-league price-based thresholds.

## Credits

Prices are provided by [poe.ninja](https://poe.ninja). This project is built for
the Exiled Bot 2 community and is not affiliated with Grinding Gear Games.

Released under the [MIT License](LICENSE).
