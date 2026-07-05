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

<br><br>

<img src="docs/assets/readme-flow.svg" alt="Animated workflow: poe.ninja prices flow through the generator into an IPD pickit for Exiled Bot 2." width="900">

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
