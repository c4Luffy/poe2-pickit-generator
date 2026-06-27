<div align="center">

# ⚔️ ExileBot 2 Pickit Generator

**Live Path of Exile 2 economy prices → ready-to-use Exiled Bot 2 pickit rules, in one click.**

Builds an `.ipd` pickit **and** a matching in-game `.filter` on every run, using real-time prices from [poe.ninja](https://poe.ninja).

[![CI](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/c4Luffy/poe2-pickit-generator?label=release&color=c8a96e)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=2ea043)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue)](#-license)

### [⬇️ Download the latest .exe →](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)

*No Python, no install — a single self-contained Windows app.*

</div>

---

## ✨ Highlights

- 🪙 **Live pricing** — pulls real PoE2 economy data from poe.ninja on every run
- 🎯 **Pick by value** — set Exalt floors for uniques and exchange/gear; everything else is auto-included
- 🧰 **Two outputs, every run** — the bot `.ipd` *and* a matching in-game `.filter`
- 🖱️ **Click to exclude** — toggle any item on/off from a searchable card grid
- 💎 **Chance & Craft bases** — curated Orb-of-Chance targets and the best blank ilvl-82 craft bases
- 👤 **Profiles** — save setups like *Farmer* / *Boss runner* and switch instantly
- 🔄 **Auto-everything** — hourly background regen, auto-copy to bot/game folders, and self-updating
- 📦 **Offline-safe** — caches prices so it still works when poe.ninja is down

---

## 🚀 Quick Start

### 1 · Download & open
1. Go to the **[Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)**
2. Download **`ExileBot2PickitGenerator.exe`**
3. Run it — if Windows SmartScreen appears, click **More info → Run anyway**

> [!NOTE]
> It's a single self-contained `.exe`. No Python or install needed.

### 2 · Select your league
- On the **Generate** tab, pick your current league from the dropdown.
- *(Optional)* Choose a **Profile** (e.g. `Farmer`, `Boss runner`) to load a saved setup.

### 3 · Choose what *not* to pick *(optional)*
- Open the **Items** tab — every item is **ON by default** (the bot picks everything).
- Click a card to turn it **gray ✗** (excluded); click again to re-enable.
- Use the **search** box to jump to any item instantly.

### 4 · Generate
- Back on the **Generate** tab, click **⚡ Generate Pickit**.
- The `.ipd` is written to the `pickit_output/` folder.

### 5 · Point your bot at the file
- In Exiled Bot 2 settings, set the pickit path to the generated `.ipd`, **or**
- Enable **Auto-copy** in **Settings** to deploy it automatically after each run.

---

## 🎯 In-Game Loot Filter

Every generate also writes a **PoE2 client loot filter** (`.filter`) next to the `.ipd`, mirroring
what the bot picks up — currency, uniques (by base), tablets, and gear bases (by quality/sockets) —
and hides everything else.

- In **Settings → Loot Filter (PoE2 client)**, set your Path of Exile 2 folder and toggle
  **"Also copy loot filter to PoE2 folder after generate"** (on by default). The folder is
  auto-detected at `Documents\My Games\Path of Exile 2`.
- Select it in-game under **Options → Game → Loot Filter**.

> [!NOTE]
> A game filter can only match by BaseType / Rarity / Quality / Sockets — it can't replicate
> `[UniqueName]` or value thresholds. Per-item value filtering stays in the bot's `.ipd`.

---

## 🗂️ Tabs

| Tab | What it does |
|---|---|
| **Generate** | Pick league & profile, set **Unique** and **Exchange & Gear** value floors (in Exalt), run generation, and view stats, price moves & log |
| **Items** | Turn individual items ON/OFF — click a card to exclude it; sorted by price High → Low |
| **Chance Bases** | Toggle Normal-rarity bases to Orb-of-Chance into target uniques |
| **Craft Bases** | Toggle the best blank (Normal) bases for crafting at item level 82 — armour slots cover all 6 defence types, each tagged STR/DEX/INT or a hybrid |
| **Preview** | Syntax-highlighted view of the generated `.ipd` |
| **History** | Log of all past generate runs |
| **Settings** | Bot folder, auto-copy, loot-filter export, backups |
| **Debug** | API connectivity tests and config dump |

---

## 📦 What Gets Picked

Everything is picked by default — use the **Items** tab to exclude what you don't want.

| Category | Items |
|---|---|
| **Currency** | All currency (Chaos, Exalted, Divine, …) |
| **Essences** | All essences |
| **Delirium** | Distilled emotions |
| **Catalysts** | Breach catalysts + Wombgifts |
| **Abyss** | Abyssal Bones |
| **Fragments** | Boss fragments, Simulacrum, Reliquary Keys |
| **Runes** | All runes |
| **Omens** | All ritual omens |
| **Soul Cores** | All soul cores |
| **Idols** | All idols |
| **Uncut Gems** | Skill / Support / Spirit gems |
| **Support Gems** | Lineage support gems |
| **Expedition** | Logbooks and expedition currency |
| **Waystones** | All tiers and rarities (always picked) |
| **Uniques** | Weapons / Armours / Accessories / Flasks / Charms / Jewels / Relics — via poe.ninja |
| **Gear Base Types** | Exceptional gear bases from game data (item level 82), all categories — kept separate from Craft Bases |
| **Craft Bases** | Best Normal (blank) base at ilvl 82 for **all 6 defence types** per armour slot (STR / DEX / INT + STR-DEX, STR-INT, DEX-INT hybrids) plus one top base per weapon type — 31 bases, managed in the **Craft Bases** tab |

---

## 💡 Tips & Tricks

- **Right-click** any item card → copies its pickit rule to the clipboard
- **↻ Refresh** in the Items tab → fetches fresh prices for the current category
- **Enable All / Disable All** toggle every item in the active category at once
- Cards are always sorted by price **High → Low**, so the most valuable items sit on top
- Price arrows **▲▼** appear after a refresh when a price moved more than **3%**
- **Price alerts** flag items that moved more than **20%** since the last run (▲/▼ with old → new price)
- **Open .ipd / Open .filter** buttons open the last generated files instantly
- The app **auto-generates every hour** in the background

---

## 🩺 Troubleshooting

<details>
<summary><b>No prices loading?</b></summary>

<br>Open the **Debug** tab and run the API connectivity test. poe.ninja may be temporarily
down — the app falls back to its offline price cache when that happens.
</details>

<details>
<summary><b>Bot isn't picking items?</b></summary>

<br>Confirm the pickit path in Exiled Bot 2 points to your generated `.ipd`, or enable
**Auto-copy** in **Settings** so the file deploys automatically after each run.
</details>

<details>
<summary><b>Windows blocked the .exe?</b></summary>

<br>Click **More info → Run anyway**. The build is unsigned, not malicious — the source is
right here in this repo.
</details>

---

## 🛠️ For Developers

**Run from source**

```bash
pip install requests Pillow customtkinter
python poe2_pickit_gui.py
```

**Run the tests**

```bash
pip install pytest requests
python -m pytest test_generator.py -v
```

Tests cover rule generation, loot-filter export, static validation, craft bases, chance bases,
and data integrity (48 tests, Python 3.10–3.12). CI runs automatically on every push, and tagged
releases (`vX.Y.Z`) auto-build the `.exe` and publish a GitHub Release.

**Contributing**

Found a bad item name or a poe.ninja mismatch? Add it to `ITEM_NAME_CORRECTIONS` in
`poe2_pickit_generator.py`. New base types go in `_BASE_TYPES_BY_CATEGORY`.

---

## 📄 License

**MIT** — free to use, modify, and distribute.
