# PoE2 Pickit Generator

A dark-themed GUI tool for **Path of Exile 2** that fetches live economy data from [poe.ninja](https://poe.ninja) and generates `.ipd` pickit rules for **Exiled Bot 2** — with per-item on/off toggles, wiki icons, preset saving, and automatic hourly refresh.

---

## Screenshots

> Categories tab — card grid with wiki icons, per-item toggles, global search, and price display

---

## Features

### Economy & Rules
- **Live poe.ninja data** — fetches current prices for all item categories
- **Per-item toggles** — enable or disable individual items from each category card grid
- **Value threshold** — only items above your set Exalt floor appear as active rules
- **Parallel fetch** — all categories fetched simultaneously for fast generation
- **15-minute cache** — repeated generates within 15 min are instant, no extra API calls
- **Auto-schedule** — regenerates every hour automatically in the background
- **Endgame base types** — scrapes level 75+ gear bases from [poe2db.tw](https://poe2db.tw) with a built-in fallback list

### Categories UI
- **Card grid** — each item shows its wiki icon, name, price (Ex / Chaos / Divine), and ON/OFF dot
- **Wiki icons** — fetched from [poe2wiki.net](https://www.poe2wiki.net) with poe.ninja fallback; cached locally
- **Smart icon lookup** — Greater/Perfect currency variants use a two-pass wiki lookup (own icon first, then base item icon); gem levels share one icon per type
- **Sectioned display** — Uncut Gems grouped as Support → Spirit → Skill sorted by level; Expedition shows Thaumaturgic Flux sorted by level
- **Global search** — search bar searches across ALL loaded categories at once
- **Preset system** — Save / Load / Export / Import item selections as JSON presets
- **Enable All / Disable All / Reset** — bulk-toggle all items in the active category

### Output
- **Unique pickit ID** — every generated file has a timestamp ID
- **Preview tab** — read the generated rules inside the app, filter by keyword, copy to clipboard
- **History tab** — log of every generate run (time, active rules, divine rate, top item, duration)
- **Backup system** — keeps the last N versions of your `.ipd` file automatically
- **Auto-copy** — optionally deploys the `.ipd` directly to your bot folder after each generate

---

## Supported Categories

| Category | Source |
|---|---|
| Currency | poe.ninja |
| Essences | poe.ninja (sorted by tier: Lesser → Greater → Perfect) |
| Delirium (Liquid Emotions) | poe.ninja |
| Breach (Catalysts) | poe.ninja |
| Abyss (Abyssal Bones) | poe.ninja |
| Fragments | poe.ninja |
| Runes | poe.ninja |
| Ritual (Omens) | poe.ninja |
| Soul Cores | poe.ninja |
| Idols | poe.ninja |
| Uncut Gems | poe.ninja |
| Lineage Support Gems | poe.ninja (always picked — no threshold) |
| Expedition | poe.ninja |
| Unique Weapons / Armours / Accessories / Flasks / Charms / Jewels / Relics | poe.ninja |
| Endgame Gear Bases | poe2db.tw (level 75+, quality or socket rules) |

---

## Requirements

- Python 3.9+
- `requests` — `pip install requests`
- `Pillow` (optional but recommended for sharp icon scaling) — `pip install Pillow`

---

## Quick Start

```bash
pip install requests Pillow
python poe2_pickit_gui.py
```

1. Wait for the league list to load, then select your league on the **Generate** tab
2. Open the **Categories** tab — click a category in the sidebar to load its items
3. Toggle individual items ON/OFF by clicking their cards
4. Set your Exalt value floor (items below this threshold are commented out, not deleted)
5. Click **Generate** — the `.ipd` file is written to the `pickit_output/` folder
6. Point Exiled Bot 2 at the generated `.ipd` file

---

## Tabs

| Tab | What it does |
|---|---|
| **Generate** | Select league, set threshold, run generation, view log |
| **Categories** | Per-item card grid for all exchange categories + gear/base controls |
| **Preview** | Read-only view of the last generated `.ipd` — filterable, copyable |
| **History** | Log of all past generate runs |
| **Settings** | Bot folder path, auto-copy, backups, launch minimized, overwrite protection |
| **Debug** | Connectivity tests, API endpoint checks, config dump |

---

## Pickit Rule Reference

The generated `.ipd` includes a full syntax guide at the top. Quick reference:

```
// Basic rule
[Type] == "Exalted Orb" # [StashItem] == "true"

// Before # = checked BEFORE identifying | After # = checked AFTER identifying
[Rarity] == "Rare" # [TotalResistances] > "50" && [StashItem] == "true"

// Computed values
[TotalResistances]          sum of all resistances
[ComputedArmour]            final armour after modifiers
[ComputedEvasion]           final evasion after modifiers
[ComputedEnergyShield]      final ES after modifiers
[DPS] / [PhysicalDPS] / [ElementalDPS]
[TotalFireSpellDamage] / [TotalColdSpellDamage] / [TotalLightningSpellDamage]

// Special flags
[StashItem]    == "true"    pick up and stash
[StashUnid]    == "true"    stash without identifying
[Salvage]      == "true"    mark for salvaging
[IgnoreRitual] == "true"    ignore from ritual rewards

// Operators:  == != > >= < <=
// Combine:    && (AND)  || (OR)  () (group)
```

### Category values

| Group | Values |
|---|---|
| Equipment | `BodyArmour` `Gloves` `Boots` `Belt` `Helmet` `Ring` `Amulet` |
| Weapons | `Weapon` `1Handed` `2Handed` `OffHand` |
| WeaponCategory (1H) | `Wand` `Sceptre` `Spear` `Flail` `OneHandMace` `OneHandAxe` `Dagger` `Claw` |
| WeaponCategory (2H) | `Bow` `Crossbow` `Quarterstaff` `Staff` `TwoHandMace` `TwoHandAxe` |
| WeaponCategory (OH) | `Shield` `Buckler` `Focus` |
| Other | `Flask` `Waystone` `Gem` |

### Example rules

```
// Pick up all Divine Orbs
[Type] == "Divine Orb" # [StashItem] == "true"

// Stash rare helmets with high resistances
[Category] == "Helmet" && [Rarity] == "Rare" # [TotalResistances] > "100" && [StashItem] == "true"

// Pick up bows with high DPS
[WeaponCategory] == "Bow" && [Rarity] == "Rare" # [DPS] > "400" && [StashItem] == "true"

// Stash level 3 support gems
[Type] == "Uncut Support Gem" && [GemLevel] == "3" # [StashItem] == "true"

// Pick up high-tier waystones
[Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"

// Pick a specific unique by name
[Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"
```

---

## Files

| File | Purpose |
|---|---|
| `poe2_pickit_gui.py` | Main GUI application |
| `poe2_pickit_generator.py` | Economy fetching, rule generation logic |
| `BUILD_EXE.bat` | Builds a standalone Windows `.exe` via PyInstaller |
| `pickit_output/` | Generated `.ipd` files land here |
| `icon_cache/` | Downloaded item icons (auto-created, not in repo) |
| `presets/` | Saved item-selection presets |

---

## Building the EXE

Double-click `BUILD_EXE.bat`. Requires Python and an internet connection on first run (downloads PyInstaller). The resulting `dist/PoE2PickitGenerator.exe` is portable.

> Windows Defender may show an "unknown publisher" warning for PyInstaller executables. Click **More info → Run anyway** — it is a false positive.

---

## License

MIT — free to use, modify, and distribute.
