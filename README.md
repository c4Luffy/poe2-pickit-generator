# PoE2 Pickit Generator

Auto-generates Exiled Bot 2 pickit rules (`.ipd`) from live [poe.ninja](https://poe.ninja) economy data for **Path of Exile 2 only**.

---

## Files

| File | Purpose |
|---|---|
| `poe2_pickit_generator.py` | Core engine — fetches poe.ninja data and writes the `.ipd` |
| `poe2_pickit_gui.py` | Dark-mode GUI (v4) wrapping the generator |
| `BUILD_EXE.bat` | Builds a standalone `PoE2PickitGenerator.exe` via PyInstaller |

---

## Requirements

- Python 3.8+
- `pip install requests`
- (Optional) `pip install win10toast` — Windows toast notifications

---

## Quick Start

### Run from source

Place all three files in the same folder, then:

```
python poe2_pickit_gui.py
```

### Build a standalone EXE (Windows)

Double-click `BUILD_EXE.bat`. It will:

1. Check Python is in PATH
2. Install `requests` and `pyinstaller`
3. Bundle everything into `dist\PoE2PickitGenerator.exe`

Windows Defender may flag the EXE as a false positive. Click **More info → Run anyway**.

### Command-line (no GUI)

```
python poe2_pickit_generator.py
python poe2_pickit_generator.py --league "Fate of the Vaal"
python poe2_pickit_generator.py --min-exalt 20
python poe2_pickit_generator.py --list-leagues
python poe2_pickit_generator.py --check-endpoints
python poe2_pickit_generator.py --variant currency
```

| Argument | Default | Description |
|---|---|---|
| `--league` | auto-detect | Exact league name from poe.ninja |
| `--min-exalt` | `10` | Items below this value are commented out |
| `--output` | `poe2_pickit.txt` | Output file path |
| `--list-leagues` | — | Print all live leagues and exit |
| `--check-endpoints` | — | Test every poe.ninja category endpoint |
| `--variant` | `all` | `all` / `currency` / `exchange` / `uniques` / `maps` |

---

## Output Files

All files are written to a `pickit_output\` subfolder next to the EXE/script.

| File | Description |
|---|---|
| `poe2_pickit.ipd` | Main pickit file — point Exiled Bot 2 at this |
| `latest.ipd` | Always-overwritten copy of the last run |
| `poe2_pickit_items.csv` | Full item report: name, value, threshold, included/excluded |
| `poe2_pickit_backup_YYYYMMDD_HHMMSS.ipd` | Timestamped backups (configurable count) |
| `pickit_gui_config.json` | GUI settings (auto-saved next to the EXE) |

---

## Item Categories

### Exchange (non-unique)

Currency, Fragments, Abyssal Bones, Uncut Gems, Lineage Support Gems, Essences, Soul Cores, Idols, Runes, Omens, Expedition, Liquid Emotions, Catalysts, Waystones

### Unique

Unique Weapons, Armours, Accessories, Flasks, Charms, Jewels, Maps, Relics

### Static (always included)

All tablet types (Irradiated, Abyss, Breach, Ritual, Overseer, Delirium, Temple) at all rarities, plus hardcoded high-value unique tablets.

---

## Rule Format

```
[Type] == "Exalted Orb" # [StashItem] == "true" // 1.000000 exalted | original: 1.0000 divine
[Type] == "Rare Waystone" && [Rarity] == "Rare" # [StashItem] == "true"
[Type] == "Unique Bow" && [Rarity] == "Unique" # [UniqueName] == "Widowhail" && [StashItem] == "true" // 420.000000 exalted
```

Items below the threshold are commented out (`//`) rather than deleted, so you can see exactly what was skipped and why.

---

## GUI — Tab Reference

### Generate

The main tab. Set your league, global threshold, and output filename here.

- **⚡ Generate Pickit** — fetch live prices and write the `.ipd` (`Ctrl+G`)
- **↺ Regenerate** — re-run immediately with the same settings
- **Open .ipd** — open the generated file in your default text editor
- **Open output folder** — open the `pickit_output\` folder in Explorer
- **Per-category progress bar** — shows `Fetching 3/14: Essences` while running
- **ETA** — estimated seconds remaining, updated after each category
- **Summary cards** — active rules, commented-out rules, Divine rate, top item, run duration
- **Log** — timestamped fetch log with Copy and Clear buttons

If you try to regenerate within 2 minutes of the last run, a confirmation dialog appears to prevent accidental overwrites.

### Categories

Enable or disable individual item categories, and set per-category price thresholds that override the global setting.

- **Threshold `−1`** — use the global threshold
- **Threshold `0`** — pick everything in this category regardless of value
- **Exchange rows** — normal color
- **Unique rows** — blue tint for quick visual distinction

**Presets:**

| Button | Effect |
|---|---|
| All | Enable every category |
| None | Disable every category |
| Currency only | Enable Currency only |
| Uniques only | Enable all Unique categories |
| Maps + Currency | Enable Currency + Waystones + Unique Maps |

### Preview

Read-only view of the generated pickit with syntax highlighting:

| Color | Meaning |
|---|---|
| Green | Active rule |
| Blue | Unique item rule |
| Grey | Commented-out (below threshold) |
| Gold | Section headers |
| Green highlight | Rule whose value went **up** since last run |
| Amber highlight | Rule whose value went **down** since last run |

Use the **Filter** box to search by item name. **Copy all** copies the full preview to clipboard.

### Price Alerts

Set per-item value thresholds. A popup fires on the next generate run if an item crosses your threshold.

### History

Table and line chart of every generate run: timestamp, active rules, Divine rate, top item, duration.

### Settings

| Setting | Description |
|---|---|
| Exiled Bot pickit folder | Path to your bot's pickit folder |
| Auto-copy | Automatically copy `.ipd` to the bot folder after every generate |
| Scheduled generation | Auto-regenerate every N hours |
| Keep N backup files | How many timestamped backups to keep (0 = disabled) |
| Sound on complete | Play two soft beeps when generation finishes (Windows, built-in) |
| Toast notification | Show a Windows toast when done (requires `pip install win10toast`) |
| Start minimized | Launch the window minimized to the taskbar |
| Config file | Path to `pickit_gui_config.json` with an Open button |
| Reset to defaults | Delete config and restart with factory settings |

Window size and position are saved automatically when you close the app.

### 🔧 Debug

Runs full diagnostics: Python version, installed modules, network connectivity, poe.ninja API health, output path writability, and config state. Useful for bug reports.

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+G` | Generate pickit |
| `Ctrl+R` | Refresh league list |

---

## Pricing Logic

1. Fetches the Currency endpoint first to establish the **Exalted Orb rate**
2. Finds the **Divine Orb** price in Exalted to use as a conversion reference
3. All item values are converted to Exalted for comparison against the threshold
4. Items at or above the threshold → active rule
5. Items below the threshold → commented-out rule (prefixed with `//`)
6. **Lineage Support Gems** are always picked regardless of value (too rare to skip)
7. **Waystones** fall back to static tier-based rules if poe.ninja returns no data

---

## Known Item Corrections

Some poe.ninja names don't match in-game base types. These are corrected automatically:

| poe.ninja name | In-game name |
|---|---|
| Refined Necrotic Catalyst | Refined Neural Catalyst |

Items with deprecated or invalid base types (e.g. `Aldur's Legacy`) are skipped entirely.

---

## Changelog

### v4 (GUI)
- Per-category progress + ETA during generation
- ↺ Regenerate button
- Category preset buttons (All / None / Currency only / Uniques only / Maps + Currency)
- Exchange vs Unique category rows color-coded
- Preview inline highlights for price changes vs previous run (no separate Diff tab)
- Windows toast notification on generate complete
- Mild two-beep sound alert on complete
- Window size and position saved between sessions
- `Ctrl+G` / `Ctrl+R` keyboard shortcuts
- Tooltips on all major controls
- Confirm dialog before overwriting a pickit less than 2 minutes old
- Settings: Reset to Defaults button
- Settings: Config file path shown with Open button
- Settings: Start minimized option

### v3 (GUI)
- Dark mode only
- Debug/Diagnostics tab
- Log timestamps, Copy log, Clear log
- Editable league combobox (type custom league name)
- Live threshold label
- Status bar with last-run duration

### v2 (Generator)
- Full poe.ninja PoE2 API integration
- Exalted-based pricing with Divine conversion rate
- Uncut Gem sub-grouping by type and level
- Waystone fallback rules
- CSV item report
- Item name corrections and skip list
- Removed `chaosValue` fallback (PoE1 field — not used in PoE2)
