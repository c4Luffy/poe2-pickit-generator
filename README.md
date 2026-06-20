# ExileBot 2 Pickit Generator

A dark-themed GUI tool for **Path of Exile 2** that fetches live economy data from [poe.ninja](https://poe.ninja) and generates `.ipd` pickit rules for **Exiled Bot 2** — with per-item on/off toggles, wiki icons, preset saving, and automatic hourly refresh.

> **Download:** grab the latest `.exe` from the [Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases) — no Python required.

---

## Screenshots

> Categories tab — card grid with wiki icons, per-item toggles, price change arrows, and price display

---

## Features

### Economy & Rules
- **Live poe.ninja data** — fetches current prices for all item categories
- **Per-item toggles** — enable or disable individual items from each category card grid
- **Manually-enabled items bypass threshold** — items you explicitly turn ON are always picked up, regardless of the price threshold
- **Dual thresholds** — separate Exalt floors for currency/exchange items and gear/uniques
- **Per-category threshold** — override the global threshold for any individual category
- **Parallel fetch** — all categories fetched simultaneously for fast generation
- **15-minute cache** — repeated generates within 15 min are instant, no extra API calls
- **Auto-schedule** — regenerates every hour automatically in the background
- **Endgame base types** — 245 endgame bases across 25 categories sourced from game data; instant, no network call

### Categories UI
- **Card grid** — each item shows its wiki icon, name, price (Ex / Chaos / Divine), and ON/OFF dot
- **Price change arrows ▲▼** — green ▲ or red ▼ appears on each card after a Refresh if the price moved more than 3% since the last fetch; arrows persist across app restarts
- **Right-click any card → Copy rule** — instantly copies that item's pickit rule to clipboard; card flashes green to confirm
- **Wiki icons** — fetched from [poe2wiki.net](https://www.poe2wiki.net) with poe.ninja fallback; cached locally
- **Smart icon lookup** — Greater/Perfect currency variants use a two-pass wiki lookup
- **Sectioned display** — Uncut Gems grouped as Support → Spirit → Skill; Expedition shows Thaumaturgic Flux sorted by level
- **Global search** — search bar searches across ALL loaded categories at once
- **Preset system** — Save / Load / Export / Import item selections as JSON presets
- **Enable All / Disable All / Reset** — bulk-toggle all items in the active category
- **↻ Refresh per category** — re-fetch live prices for just the active category; button shows "Refreshing…" while in-flight; count label shows "updated HH:MM" timestamp
- **Disabled-but-valuable highlight** — item cards that are manually turned OFF but priced at or above the active threshold glow **amber**, so you can spot items you may have accidentally left off
- **Per-category enable/disable** — skip entire categories from the generate in the gear panel

### Output
- **Unique pickit ID** — every generated file has a timestamp ID
- **Preview tab** — browse the generated rules with syntax highlighting: active rules in green, commented rules in grey, section headers in gold; filterable, copyable
- **History tab** — log of every generate run with a live sparkline chart showing active rules count over time
- **Backup system** — keeps the last N versions of your `.ipd` file automatically
- **Auto-copy** — optionally deploys the `.ipd` directly to your bot folder after each generate

### App
- **Auto-update checker** — on startup, silently checks GitHub for a newer version; shows a gold banner with a download link if one is found
- **Minimize to system tray** — closing the window hides to tray; app keeps running and auto-refreshing in the background; right-click tray icon to show or quit

---

## Data Sources

**Poe.Ninja** (13 categories): Currency, Fragments, Abyss, Uncut Gems, Lineage Support Gems, Essences, Ultimatum, Talismans, Runes, Ritual, Expedition, Delirium, Breach

**Scout** (6 categories, via [poe2scout.com](https://poe2scout.com)): Accessories, Armour, Jewels, Maps, Weapons, Sanctum — fetched when available, silently skipped if the API is offline for the current league

**Static** (4 categories): Splinters, Waystones, Special Waystones, Tablets — hardcoded always-pick rules, no threshold

---

## Supported Categories

| Category | Source |
|---|---|
| Currency (49 items incl. all Vaal currencies) | Poe.Ninja |
| Essences | Poe.Ninja (sorted by tier: Lesser → Greater → Perfect) |
| Delirium (Liquid Emotions) | Poe.Ninja |
| Breach (Catalysts + Wombgifts) | Poe.Ninja + Static |
| Abyss (Abyssal Bones) | Poe.Ninja |
| Fragments (incl. Simulacrum, all Reliquary Keys) | Poe.Ninja |
| Runes (142 items incl. all 5 Aldur runes) | Poe.Ninja |
| Ritual (Omens) | Poe.Ninja |
| Ultimatum | Poe.Ninja (active when league data available) |
| Talismans | Poe.Ninja (active when league data available) |
| Soul Cores (incl. all Emergent items) | Poe.Ninja |
| Idols | Poe.Ninja |
| Uncut Gems | Poe.Ninja |
| Lineage Support Gems | Poe.Ninja (always picked — no threshold) |
| Expedition (incl. all Sagas and Fluxes) | Poe.Ninja |
| Waystones (all tiers 1–15, all rarities) | Static — always picked |
| Special Waystones (An Audience with the King) | Static — always picked |
| Unique Tablets (7 named) | Static — always picked |
| Regular Tablets (all rarities) | Static — always picked |
| Splinters (Breach + Simulacrum) | Static — always picked |
| Unique Weapons / Armours / Accessories / Flasks / Charms / Jewels / Relics | Poe.Ninja |
| Unique Accessories / Armour / Jewels / Weapons / Sanctum / Maps | Scout (poe2scout.com) |
| Endgame Gear Bases | Game data (245 bases across 25 categories, level 75+, offline) |

---

## Requirements

- **No Python needed** — download the `.exe` from [Releases](https://github.com/c4Luffy/poe2-pickit-generator/releases)
- If running from source: Python 3.9+, `pip install requests Pillow pystray`

---

## Quick Start (EXE)

1. Download `ExileBot2PickitGenerator.exe` from the [Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases)
2. Double-click to run — Windows Defender may show an "unknown publisher" warning, click **More info → Run anyway** (false positive from PyInstaller)
3. Select your league on the **General** tab
4. Open **Categories** — toggle items ON/OFF by clicking their cards
5. Set your Exalt threshold, then click **⚡ Generate**
6. Point Exiled Bot 2 at the generated `.ipd` file in `pickit_output/`

## Quick Start (Python source)

```bash
pip install requests Pillow pystray
python poe2_pickit_gui.py
```

---

## Tabs

| Tab | What it does |
|---|---|
| **General** | Select league, set threshold, run generation, view stats and log |
| **Categories** | Per-item card grid for all exchange categories + gear/base controls |
| **Preview** | Syntax-highlighted view of the last generated `.ipd` — filterable, copyable |
| **History** | Log of all past generate runs with sparkline chart of active rules over time |
| **Settings** | Bot folder path, auto-copy, system tray, backups, overwrite protection |
| **Debug** | Connectivity tests, API endpoint checks, config dump |

---

## Pickit Rule Reference

The generated `.ipd` includes a full syntax guide at the top. Quick reference:

```
// Basic rule
[Type] == "Exalted Orb" # [StashItem] == "true"

// Before # = checked BEFORE identifying | After # = checked AFTER identifying
[Rarity] == "Rare" # [TotalResistances] > "50" && [StashItem] == "true"

// Operators:  == != > >= < <=
// Combine:    && (AND)  || (OR)  () (group)
```

---

## Project Structure

```
poe2-pickit-generator/
├── poe2_pickit_gui.py          # Main GUI — tkinter, 6 tabs (General / Categories /
│                               #   Preview / History / Settings / Debug)
├── poe2_pickit_generator.py    # Economy fetching (poe.ninja + poe2scout.com) and
│                               #   .ipd pickit rule generation
├── version.txt                 # Release version string — fetched by auto-update checker
├── BUILD_EXE.bat               # One-click PyInstaller build → dist/ExileBot2PickitGenerator.exe
├── pickit_output/              # Generated .ipd files land here (auto-created)
├── icon_cache/                 # Item icons downloaded from poe2wiki.net (auto-created)
└── presets/                    # Saved item-selection presets as JSON (auto-created)
```

---

## License

MIT — free to use, modify, and distribute.
