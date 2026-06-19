# PoE2 Pickit Generator

A tool that automatically generates economy-aware loot filter rules for **Exiled Bot 2** in **Path of Exile 2**, powered by live data from [poe.ninja](https://poe.ninja).

---

## What it does

- Pulls live currency and item prices from the poe.ninja PoE2 API
- Auto-detects the current league (or lets you pick one)
- Generates a `.ipd` pickit file with rules for every item category:
  - Currency, Fragments, Essences, Runes, Omens, Soul Cores, Idols
  - Uncut Gems (Skill / Spirit / Support), Lineage Support Gems
  - Expedition, Liquid Emotions, Catalysts, Abyssal Bones
  - Unique Weapons, Armours, Accessories, Flasks, Charms, Jewels
  - All Tablet types (unique + normal/magic/rare)
- Items above your exalted threshold → active pick rule
- Items below threshold → commented out (ignored by bot)
- Optional: scrapes [poe2db.tw](https://poe2db.tw) for high item-level base types

---

## Rule format

```
[Type] == "Divine Orb" # [StashItem] == "true" // 214.800000 exalted | original: 1 divine
```

Unique items include an extra `[UniqueName]` check:

```
[Type] == "Scimitar" && [Rarity] == "Unique" # [UniqueName] == "Widowhail" && [StashItem] == "true" // 850.0 exalted
```

---

## Usage

### GUI (recommended)

Double-click `poe2_pickit_gui.py` or the built `.exe`:

- Select your league and set a minimum exalted threshold
- Enable/disable individual item categories
- Set per-category thresholds if needed
- Click **Generate Pickit** — done
- Optionally enable auto-scheduling to regenerate every N hours

### Command line

```bash
python poe2_pickit_generator.py --league "Runes of Aldur" --min-exalt 5
```

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--league` | auto-detect | Exact league name |
| `--min-exalt` | `10.0` | Min value in exalted to include |
| `--output` | `poe2_pickit.txt` | Output file path |
| `--list-leagues` | — | Print available leagues and exit |
| `--include-bases` | off | Also scrape poe2db.tw for ilvl 75+ bases |
| `--variant` | `all` | `all` / `currency` / `exchange` / `uniques` / `maps` |

---

## Requirements

```bash
pip install requests beautifulsoup4
```

Python 3.8+

---

## Build a standalone EXE (Windows)

Run `BUILD_EXE.bat` — it installs dependencies, compiles with PyInstaller, and drops `PoE2PickitGenerator.exe` in the `dist/` folder.

> Windows Defender may flag the EXE as suspicious. This is a PyInstaller false positive — click **More info → Run anyway**.

---

## Files

| File | Description |
|---|---|
| `poe2_pickit_generator.py` | Core logic — API fetching, rule generation |
| `poe2_pickit_gui.py` | Tkinter dark-mode GUI (v3) |
| `BUILD_EXE.bat` | One-click EXE builder for Windows |

---

## Data sources

- **[poe.ninja PoE2 API](https://poe.ninja)** — live economy prices
- **[poe2db.tw](https://poe2db.tw)** — base item data (optional)

---

## Disclaimer

This tool is not affiliated with Grinding Gear Games or poe.ninja. Use of botting software may violate the Path of Exile Terms of Service.
