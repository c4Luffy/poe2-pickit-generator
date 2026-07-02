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
- 💎 **Chance & Craft bases** — curated Orb-of-Chance targets, plus the best blank craft bases with a **per-base item level** you set yourself
- 🛡️ **Rare Gear by mods** — keep rares scored by the bot's **WeightedSum**, with one-click **strictness presets** and junk gates (min item level / min base tier) so your stash only gets the good stuff
- 🧬 **Per-base Rare Gear (Pro)** — hand-written-pickit quality, generated: one rule **per base type**, split by slot × defence type × Low/Mid/High base bracket, with auto prefix/suffix rules and jewel build archetypes — 765 bases across 18 gear families
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
| **Craft Bases** | Toggle the best blank (Normal) bases for crafting and **set the item level per base** — what you set on a card is exactly what the bot requires. Armour slots cover all 6 defence types, each tagged STR/DEX/INT or a hybrid |
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
| **Craft Bases** | Best Normal (blank) base for **all 6 defence types** per armour slot (STR / DEX / INT + STR-DEX, STR-INT, DEX-INT hybrids) plus top bases per weapon type — 39 bases with a **per-base item level** (default 82; 75 for accessories), managed in the **Craft Bases** tab |

---

## 🆕 What's New

**v2.6.18**
- 🧬 **New Per-base mode on the Rare Gear tab** — a *Simple / Per-base* switch at the top:
  - **Per-base** generates one rule per base type (like a hand-tuned community pickit): every slot splits by **defence type** (Armour / Evasion / ES / hybrids) and by base bracket — **Low** (campaign), **Mid** (cruel), **High** (endgame) — 764 bases across 18 gear families, including **all weapons** (bows, crossbows, quarterstaffs, maces, spears, flails, wands, sceptres, staves, foci, quivers, shields, bucklers).
  - Tick a bracket and tune **one number**; **P/S** also emits prefix-only and suffix-only rules at 60% / 55% of it (catches items with one great half). Optional single-mod **Magic** pickups (movement-speed boots, high phys% bows…).
  - **Jewellery too**: Amulets get five build archetypes (ES caster, stat stacker, blood magic, life caster, projectile) over all 16 bases; Belts get per-base prefix/suffix rules; Rings get **ten build archetypes, each with its own tunable threshold**.
  - **Bulk controls** — *Enable all High (endgame)* ticks every slot's endgame bracket in one click (the usual map-farming setup); *Disable all* resets the whole mode. The counter shows the **exact number of rules** your current selection will generate.
  - **Shields & bucklers** use the community pickit's block-gated scoring — a rule only keeps a shield that actually rolled **% block chance**, then scores block / phys reduction / hybrid defences / life / resists / max-res in one weighted sum.
  - **Jewels**: ten build archetypes (ES/caster in cold, fire, lightning and chaos flavours, bow + endgame bow, quarterstaff + endgame quarterstaff, minions/curses — both-halves scoring, most matched at Rare *and* Magic) plus always-keep movement-speed / quiver-effect jewels.
  - **Magic tier everywhere** — every section has a Magic toggle: transcribed single-mod rules where known (movement-speed boots, phys% bows, gem-level amulets), otherwise the section's mods scored at 40% of your threshold.
  - **Expert rules** — paste (or *Import .ipd file…*) your own hand-written rules and they're appended to the pickit **exactly as written**. Perfect for things no generator can express: graduated threshold ladders, `ComputedArmour`/`ComputedEvasion`/`ComputedEnergyShield` rules, `PhysicalDPS`/`ElementalDPS` weapon rules, per-base Magic jewellery…
  - Base lists are extracted from game data (`build_rare_gear_catalog.py`) — a new league is one script run away.
  - **Simple** mode (the 13-slot list) stays the default; your existing settings are untouched.
- 🧹 **Rare Gear de-clutter** — the tab no longer stashes half the game:
  - **Strictness presets** — one click (`Loose / Bot default / Strict / Very strict`) sets every slot's threshold to a multiple of the bot's default (Strict = 1.5×, recommended). The numbers update in place so you can still fine-tune per slot.
  - **Min item level** (default **65**) — campaign junk never reaches your stash; only items of at least this ilvl are kept.
  - **Min base tier** (off by default; the bot's own rules use 3) — low-tier bases aren't even picked up, saving inventory trips too.
  - **Magic items are now opt-in** — the "Also keep Magic" box starts unticked (a single big mod let too many Magic items through).
- 🧽 **Polish** — mouse-wheel scrolling is consistent everywhere on the tab (it used to double-speed over some areas); bulk actions write the config once instead of once per row; tooltips can no longer get stuck on screen; the update check now looks at the latest **published release** instead of the source tree, so it can never offer a download that doesn't exist yet.

**v2.6.17**
- 🛡️ **New Rare Gear tab** — automatically keep rares **and** magic items worth picking, scored by their mods (the bot's **WeightedSum**). 13 slots (armour, jewellery, weapons) come pre-loaded with the bot's own mod-weight presets — just tick a slot and tune **one number** (its score threshold). Hover the **ⓘ** on any slot to see exactly what it scores. Everything is **off by default**.
- 📦 **Slightly smaller download** — the build now drops unused modules.

**v2.6.16**
- 🤖 **New app icon** — the ExileBot mascot is now the application icon: the downloaded `.exe`'s icon in Explorer, plus the window's titlebar and taskbar icon.
- ⚡ **Snappier Items tab** — item cards now load in the background in small batches instead of all at once, so opening a big category no longer briefly freezes the app. No visual change.

**v2.6.15**
- 🏷️ The endgame gear-base section is now labelled **"Exceptional Base Types"** in the app, so it's clear what that area is.
- 🖼️ Fixed an icon-loading race that could spam the debug log with harmless `TclError`s when you switched tabs while item icons were still downloading.

**v2.6.14**
- 🛠️ **Craft Bases item level is now exact** — the level shown on each Craft Bases card is precisely what the bot enforces. *(Previously a card could show ilvl 82 while the generated `.ipd` quietly used a lower global value, so the bot picked up lower-level bases.)*
- 🏹 Added **Obliterator Bow** to the curated craft bases.
- 🧪 **Healthier internals** — the rule-assembly pipeline was extracted into a pure, fully-tested module (77 tests + lint in CI). No behaviour change for users; just safer to build on.

See the **[Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases)** for the full history.

---

## 💡 Tips & Tricks

- **Right-click** any item card → copies its pickit rule to the clipboard
- **↻ Refresh** in the Items tab → fetches fresh prices for the current category
- **Enable All / Disable All** toggle every item in the active category at once
- Cards are always sorted by price **High → Low**, so the most valuable items sit on top
- Price arrows **▲▼** appear after a refresh when a price moved more than **3%**
- **Price alerts** flag items that moved more than **20%** since the last run (▲/▼ with old → new price)
- **Open .ipd / Open .filter** buttons open the last generated files instantly
- In **Craft Bases**, the **ilvl** box on each card is what the bot enforces — tune it per base (82 for endgame gear, 75 for accessories, lower if you want more drops)
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
pip install pytest requests ruff
python -m pytest -v
ruff check .
```

Tests cover rule generation, loot-filter export, static validation, craft/chance bases,
data integrity, and the full assembly pipeline (77 tests, Python 3.10–3.12). CI runs tests +
lint on every push, and tagged releases (`vX.Y.Z`) auto-build the `.exe` and publish a GitHub Release.

**Project layout**

| Module | Responsibility |
|---|---|
| `poe2_pickit_generator.py` | Pure rule builders + the poe.ninja API client (also a standalone CLI) |
| `pickit_assembly.py` | Pure pickit-assembly: turns fetched payloads + a settings snapshot into `.ipd` lines (no Tk/network/IO) |
| `poe2_pickit_gui.py` | The Tkinter app — fetching, threading, file output, and UI; delegates rule assembly to the two modules above |
| `ui_common.py`, `tab_*.py` | Shared widget toolkit and the per-tab mixins |

**Contributing**

Found a bad item name or a poe.ninja mismatch? Add it to `ITEM_NAME_CORRECTIONS` in
`poe2_pickit_generator.py`. New base types go in `_BASE_TYPES_BY_CATEGORY`.

---

## 📄 License

**MIT** — free to use, modify, and distribute.
