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
- **Endgame base types** — scrapes level 75+ gear bases from [poe2db.tw](https://poe2db.tw) with a built-in fallback list

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

## Supported Categories

| Category | Source |
|---|---|
| Currency (49 items incl. all Vaal currencies) | poe.ninja |
| Essences | poe.ninja (sorted by tier: Lesser → Greater → Perfect) |
| Delirium (Liquid Emotions) | poe.ninja |
| Breach (Catalysts) | poe.ninja |
| Abyss (Abyssal Bones) | poe.ninja |
| Fragments (incl. Simulacrum, all Reliquary Keys) | poe.ninja |
| Runes (142 items incl. all 5 Aldur runes) | poe.ninja |
| Ritual (Omens) | poe.ninja |
| Soul Cores (incl. Emergent Vigour/Possibility/Protection/Instinct) | poe.ninja |
| Idols | poe.ninja |
| Uncut Gems | poe.ninja |
| Lineage Support Gems | poe.ninja (always picked — no threshold) |
| Expedition (incl. all Sagas and Fluxes) | poe.ninja |
| Waystones | All tiers 1–15, all rarities (always picked) |
| Unique Weapons / Armours / Accessories / Flasks / Charms / Jewels / Relics | poe.ninja |
| Endgame Gear Bases | poe2db.tw (level 75+, quality or socket rules) |
| Unique Tablets (7 named) | Static rules — always picked |
| Regular Tablets (all rarities) | Static rules — always picked |
| Breach Splinter / Simulacrum Splinter | Static rules — always picked |
| Breach Wombgifts (Growing / Lavish / Banded / Signet) | Static rules — always picked |
| Emergent Runes (Vigour / Possibility / Protection / Instinct) | Static rules — always picked |

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

## Files

| File | Purpose |
|---|---|
| `poe2_pickit_gui.py` | Main GUI application |
| `poe2_pickit_generator.py` | Economy fetching, rule generation logic |
| `version.txt` | Current version — bumped on every release |
| `BUILD_EXE.bat` | Builds a standalone Windows `.exe` via PyInstaller |
| `pickit_output/` | Generated `.ipd` files land here |
| `icon_cache/` | Downloaded item icons (auto-created) |
| `presets/` | Saved item-selection presets |

---

## License

MIT — free to use, modify, and distribute.
