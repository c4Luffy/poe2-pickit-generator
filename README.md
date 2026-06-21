# ExileBot 2 Pickit Generator

Generate `.ipd` pickit rules for **Exiled Bot 2** using live **Path of Exile 2** economy prices from [poe.ninja](https://poe.ninja) — and a matching **in-game loot filter** (`.filter`) on every run.

> **Download:** grab the latest `.exe` from the [Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases) — no Python needed.

---

## How to Use

### 1. Download & open
1. Go to the [**Releases page**](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
2. Download **`ExileBot2PickitGenerator.exe`**
3. Run it — if Windows SmartScreen appears, click **More info → Run anyway**

> [!NOTE]
> It's a single self-contained `.exe`. No Python or install needed.

### 2. Select your league
- On the **Generate** tab, pick your current league from the dropdown.
- *(Optional)* Choose a **Profile** (e.g. `Farmer`, `Boss runner`) to load a saved setup.

### 3. Choose what *not* to pick *(optional)*
- Open the **Items** tab.
- Every item is **ON by default** — the bot picks everything.
- Click a card to turn it **gray (✗)** = excluded. Click it again to re-enable.
- Use **Min `X` c** to bulk-disable everything under a chaos value.
- Use the **search** box to jump to any item instantly.

### 4. Generate
- Return to the **Generate** tab and click **⚡ Generate Pickit**.
- The `.ipd` file is written to the `pickit_output/` folder.

### 5. Point your bot at the file
- In Exiled Bot 2 settings, set the pickit path to the generated `.ipd`, **or**
- Enable **Auto-copy** in **Settings** to deploy it automatically after each generate.

---

## In-Game Loot Filter

Every generate also writes a **PoE2 client loot filter** (`.filter`) next to the `.ipd`, mirroring
what the bot picks up — currency, uniques (by base), tablets, and gear bases (by quality/sockets) —
and hides everything else.

- In **Settings → Loot Filter (PoE2 client)** you can set your Path of Exile 2 folder and toggle
  **"Also copy loot filter to PoE2 folder after generate"** (on by default). The folder is
  auto-detected at `Documents\My Games\Path of Exile 2`.
- Select it in-game under **Options → Game → Loot Filter**.

> [!NOTE]
> A game filter can only match by BaseType / Rarity / Quality / Sockets — it can't replicate
> `[UniqueName]` or value thresholds. Per-item value filtering stays in the bot's `.ipd`.

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
| **Generate** | Select league, pick a profile, run generation, view stats, price moves and log |
| **Items** | Turn individual items ON/OFF — click a card to exclude it; use **Min c** to bulk-disable cheap items |
| **Chance Bases** | Toggle Normal-rarity bases to Orb-of-Chance into target uniques |
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
- **Min X c** filter in the Items toolbar → enter a chaos value and click **Apply** to auto-disable all items below that price across every loaded category
- Price arrows **▲▼** appear on cards after a refresh if the price moved more than 3%
- **Price alerts** in the generate log — items that moved more than 20% since the last run are flagged with ▲/▼ and the old → new price
- The app **auto-generates every hour** in the background automatically

---

## Troubleshooting

<details>
<summary><b>No prices loading?</b></summary>

Open the **Debug** tab and run the API connectivity test. poe.ninja may be temporarily
down — the app falls back to its offline price cache when that happens.
</details>

<details>
<summary><b>Bot isn't picking items?</b></summary>

Confirm the pickit path in Exiled Bot 2 points to your generated `.ipd`, or enable
**Auto-copy** in **Settings** so the file is deployed automatically after each generate.
</details>

<details>
<summary><b>Windows blocked the .exe?</b></summary>

Click **More info → Run anyway**. The build is unsigned, not malicious — the source is
right here in this repo.
</details>

---

## License

MIT — free to use, modify, and distribute.
