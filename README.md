# PoE2 Pickit Generator

Automatically generates `.ipd` pickit rules for **Exiled Bot 2** based on live [poe.ninja](https://poe.ninja) economy data and endgame base types scraped from [poe2db.tw](https://poe2db.tw).

---

## Features

- **Live economy data** — fetches current prices from poe.ninja every hour
- **Endgame base types** — scrapes level 75+ bases across all gear slots from poe2db (weapons, armour, off-hands)
- **Auto-schedule** — regenerates the pickit every hour automatically, no manual steps
- **Unique pickit ID** — every generated file includes a timestamp ID so you always know which one is newest
- **Parallel fetch** — all poe.ninja categories fetched in parallel for fast generation
- **15-minute cache** — repeated generates within 15 min are instant, no extra API calls
- **Backup system** — keeps the last N versions of your pickit file automatically
- **Preview tab** — view the generated rules inside the app before deploying
- **History tab** — browse previous generate runs

---

## Requirements

- Python 3.9+
- `requests` library (`pip install requests`)

Or just run `BUILD_EXE.bat` to create a standalone `.exe` (no Python needed after that).

---

## Quick Start

```bash
pip install requests
python poe2_pickit_gui.py
```

1. Select your league on the **Generate** tab
2. Configure which item categories to pick up on the **Categories** tab
3. Click **Generate** — the `.ipd` file is written to the `output/` folder
4. Point Exiled Bot 2 to the generated `.ipd` file

---

## Tabs Overview

| Tab | What it does |
|---|---|
| **Generate** | Select league, set value threshold, run generation |
| **Categories** | Toggle which item types to include (uniques, currency, bases, etc.) |
| **Preview** | Read-only view of the last generated pickit |
| **History** | Log of all past generate runs in this session |
| **Settings** | Bot folder path, backups, auto-copy, notifications |
| **Debug** | Test API connectivity and file paths |

---

## Base Types

Endgame base types are scraped live from poe2db (level ≥ 75) across all categories:

**Weapons** — One Hand Maces, Spears, Bows, Crossbows, Staves, Quarterstaves, Two Hand Maces  
**Armour** — Body Armours (STR / DEX / INT / hybrid), Helmets, Gloves, Boots  
**Off-hand** — Shields, Bucklers, Foci

If poe2db is unreachable, a built-in fallback list of 154 known endgame bases is used automatically.

---

## Pickit Rule Reference

The generated `.ipd` file includes a full syntax guide at the top. Key concepts:

```
// Basic rule:
[Type] == "Exalted Orb" # [StashItem] == "true"

// Split with # (before = pre-ID, after = post-ID):
[Rarity] == "Rare" # [TotalResistances] > "50" && [StashItem] == "true"

// Computed values:
[TotalResistances]       — sum of all resistances
[ComputedArmour]         — final armour after modifiers
[ComputedEvasion]        — final evasion after modifiers
[ComputedEnergyShield]   — final ES after modifiers
[DPS] / [PhysicalDPS] / [ElementalDPS]
[TotalSpellElementalDamage] / [TotalFireSpellDamage] / ...

// Special flags:
[StashItem]    == "true"   pick up and stash
[StashUnid]    == "true"   stash without identifying
[Salvage]      == "true"   mark for salvage
[IgnoreRitual] == "true"   skip ritual rewards
```

**Operators:** `==`  `!=`  `>`  `>=`  `<`  `<=`  
**Combine:** `&&` (AND)  `||` (OR)  `()` (group)

### Categories

| Group | Values |
|---|---|
| Equipment | `BodyArmour` `Gloves` `Boots` `Belt` `Helmet` `Ring` `Amulet` |
| Weapons | `Weapon` `1Handed` `2Handed` `OffHand` |
| WeaponCategory (1H) | `Wand` `Sceptre` `Spear` `Flail` `OneHandMace` `OneHandAxe` `Dagger` `Claw` |
| WeaponCategory (2H) | `Bow` `Crossbow` `Quarterstaff` `Staff` `TwoHandMace` `TwoHandAxe` |
| WeaponCategory (OH) | `Shield` `Buckler` `Focus` |
| Other | `Flask` `Waystone` `Gem` |

### Rarity

```
[Rarity] == "Normal"
[Rarity] == "Magic"
[Rarity] == "Rare"
[Rarity] == "Unique"
```

### Examples

```
// Pick up all Divine Orbs
[Type] == "Divine Orb" # [StashItem] == "true"

// Stash rare helmets with high total resistances
[Category] == "Helmet" && [Rarity] == "Rare" # [TotalResistances] > "100" && [StashItem] == "true"

// Pick up bows with high DPS
[WeaponCategory] == "Bow" && [Rarity] == "Rare" # [DPS] > "400" && [StashItem] == "true"

// Stash level 3 support gems
[Type] == "Uncut Support Gem" && [GemLevel] == "3" # [StashItem] == "true"

// Pick up waystones tier 10+
[Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"

// Stash any unique by name
[Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"
```

---

## Files

| File | Purpose |
|---|---|
| `poe2_pickit_gui.py` | Main GUI application |
| `poe2_pickit_generator.py` | Economy fetching, rule generation logic |
| `BUILD_EXE.bat` | Builds a standalone Windows `.exe` via PyInstaller |
| `output/` | Generated `.ipd` files land here |

---

## Building the EXE

Double-click `BUILD_EXE.bat`. Requires Python and an internet connection for the first run (installs PyInstaller). The resulting `dist/PoE2PickitGenerator.exe` is portable — copy it anywhere.

> Windows Defender may flag the EXE as unknown. Click **More info → Run anyway** — it is a false positive common with PyInstaller executables.

---

## License

MIT — do whatever you want with it.
