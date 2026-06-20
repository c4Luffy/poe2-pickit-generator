# ExileBot 2 Pickit Generator

Generate `.ipd` pickit rules for **Exiled Bot 2** using live **Path of Exile 2** economy prices from [poe.ninja](https://poe.ninja).

> **Download:** grab the latest `.exe` from the [Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases) — no Python needed.

---

## How to Use

**1. Download & open**
- Download `ExileBot2PickitGenerator.exe` from [Releases](https://github.com/c4Luffy/poe2-pickit-generator/releases)
- Run it — if Windows shows a warning, click **More info → Run anyway**

**2. Select your league**
- On the **Generate** tab, pick your current league from the dropdown

**3. Choose what NOT to pick (optional)**
- Open the **Items** tab
- Every item is **ON by default** — the bot picks everything
- Click any item card to turn it **gray** (excluded) — the bot will skip it
- Click it again to re-enable

**4. Generate**
- Go back to **Generate** and click **⚡ Generate Pickit**
- The `.ipd` file is saved to the `pickit_output/` folder

**5. Point your bot at the file**
- In Exiled Bot 2 settings, point the pickit path to the generated `.ipd` file
- Or enable **Auto-copy** in Settings to deploy it automatically after each generate

---

## Running from Source

```bash
pip install requests Pillow
python poe2_pickit_gui.py
```

---

## Tabs

| Tab | What it does |
|---|---|
| **Generate** | Select league, run generation, view stats and log |
| **Items** | Turn individual items ON/OFF — click a card to exclude it, click again to re-enable |
| **Preview** | Syntax-highlighted view of the generated `.ipd` file |
| **History** | Log of all past generate runs |
| **Settings** | Bot folder, auto-copy, backups |
| **Debug** | API connectivity tests and config dump |

---

## What Gets Picked

Everything is picked by default. Use the **Items** tab to exclude specific items.

| Category | Items |
|---|---|
| Currency | All currency (Chaos, Exalted, Divine, etc.) |
| Essences | All essences |
| Delirium | Distilled emotions |
| Catalysts | Breach catalysts + Wombgifts |
| Abyss | Abyssal Bones |
| Fragments | Boss fragments, Simulacrum, Reliquary Keys |
| Runes | All runes |
| Omens | All ritual omens |
| Soul Cores | All soul cores |
| Idols | All idols |
| Uncut Gems | Skill / Support / Spirit gems |
| Support Gems | Lineage support gems |
| Expedition | Logbooks and expedition currency |
| Waystones | All tiers and rarities (always picked) |
| Unique Weapons / Armours / Accessories / Flasks / Charms / Jewels / Relics | Via poe.ninja |
| Endgame Gear Bases | 245 bases, level 75+, all 25 categories |

---

## Tips

- **Right-click** any item card → copies its pickit rule to clipboard
- **↻ Refresh** in the Items tab → fetches fresh prices for the current category
- **Enable All / Disable All** buttons toggle all items in the active category at once
- **Save Preset** → save your item selections with a name, author and description; **Load Preset** → restore with a metadata preview
- **Export Preset** → save your selections as a shareable `.json` file; **Import Preset** → load one from someone else (shows a preview before applying)
- Price arrows **▲▼** appear on cards after a refresh if the price moved more than 3%
- The app **auto-generates every hour** in the background automatically

---

## License

MIT — free to use, modify, and distribute.
