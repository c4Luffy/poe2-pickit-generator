<div align="center">

# ⚔️ ExileBot 2 Pickit Generator

**Live Path of Exile 2 economy prices → ready-to-use Exiled Bot 2 pickit rules, in one click.**

Builds an `.ipd` pickit **and** a matching in-game `.filter` on every run, using real-time prices from [poe.ninja](https://poe.ninja).

<br>

[![CI](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/c4Luffy/poe2-pickit-generator?label=release&color=c8a96e)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=2ea043)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue)](#-license)

<br>

### [⬇️ Download the latest .exe →](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)

*No Python, no install — a single self-contained Windows app.*

</div>

---

## 🚀 Get started in 3 steps

> **1️⃣ Download & open**
> Get **`ExileBot2PickitGenerator.exe`** from the **[latest release](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)** and double-click it.
> *(No install. If Windows shows a warning, click **More info → Run anyway**.)*

> **2️⃣ Pick your league, then click ⚡ Generate**
> On the **Generate** tab, choose your current PoE2 league and hit **⚡ Generate Pickit**. Live prices are fetched and your pickit is saved to the **`pickit_output`** folder.

> **3️⃣ Point your bot at the file**
> In Exiled Bot 2, set the pickit path to the generated `.ipd` — **or** turn on **Auto-copy** in **Settings** so it's deployed for you after every run.

**That's it.** Everything valuable is picked by default. Want to skip something? Open the **Economy** tab and click it to turn it off.

---

## ✨ What it does

- 🪙 **Live prices** — pulls real PoE2 economy data from poe.ninja every run
- 🎯 **Keeps what's worth it** — set a value floor (in Exalts); junk is skipped automatically
- 🧰 **Two files, one click** — the bot `.ipd`, plus a matching `.filter` in the output folder if you ever want one for manual play *(don't feed it to the bot — hidden drops make it get stuck)*
- 🖱️ **Easy to tweak** — click any item to exclude it; search, sort, and see live price-change arrows
- ✨ **Auto value floor** — one click sets your minimum values from the league's real prices
- 🛡️ **Safety net** — a broken or collapsed pickit is never auto-deployed to your bot
- 🖥️ **Modern interface** — instant dark/light themes, system-tray mode, and plain-language explainers on every tab
- 🧱 **Base picking** — dedicated Chance Bases & Craft Bases tabs help you keep the right bases
- 🔄 **Set and forget** — auto-copies the generated pickit straight into your bot folder
- ⬆️ **Update alerts** — tells you when a new version is out and links you straight to the download

---

<details>
<summary><b>💡 Handy tips</b></summary>

<br>

- **Right-click** any item row → copies its pickit rule to the clipboard
- **Refresh** on the Economy tab → gets fresh prices for that category
- **Enable All / Disable All** → toggles a whole category at once
- **Arrows ▲▼** show price moves over 3%; alerts flag moves over 20%
- **Craft Bases** → the item level you set on a card is exactly what the bot uses

</details>

<details>
<summary><b>🛠️ Something not working?</b></summary>

<br>

- **No prices loading?** Open the **Debug** tab → **Run API test**. poe.ninja may be down — the app falls back to its saved price cache.
- **Bot not picking items?** Make sure Exiled Bot 2's pickit path points to your `.ipd`, or turn on **Auto-copy** in Settings.
- **Windows blocked the .exe?** Click **More info → Run anyway**. It's unsigned (it's a free tool), but all the source is right here in this repo.
- **Where are my files?** In an `ExileBot2PickitGenerator_data` folder next to the `.exe` (`pickit_output/` holds the generated files).

</details>

<details>
<summary><b>👩‍💻 Run from source / for developers</b></summary>

<br>

```bash
# run the app
pip install -e .
python -m exilebot_pickit

# run the tests
pip install pytest requests ruff
python -m pytest -q && ruff check .
```

Layout: the app lives in `src/exilebot_pickit/` (`generator.py` + `generators/assembly.py` build the rules, `webui/` is the WebView2 app — `api.py` bridge + `app.html` front-end, `ui/` keeps config/updater plumbing, `data/` holds the item/base data). CI runs tests and lint on every push; pushing a `vX.Y.Z` tag auto-builds the `.exe` and publishes a release.

</details>

---

## 📝 Changelog

Newest first, last 5 releases. Full history is on the **[Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases)** — the current build is always the **[latest release](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)**.

**v3.3.0** — *latest*
- 🧱 **New Exceptional tab** — the best endgame bases explained and managed in one place: white-base pickup (quality/ilvl gates) plus a new option to grab **any unique that drops on an exceptional base**, whatever its price
- 📋 **Always-Pick Items in Economy** — tablets, splinters, wombgifts, special keys, jewels and exotic bases are now visible and individually toggleable like everything else
- 💎 **New pickup sections** — 48 exotic bases (Breach rings, Runic Fork…), valuable jewels (Rare ilvl 81+, Timeless Jewel, Time-Lost Diamond), Kulemak's Invitation
- 🔍 **Game-data audit** — item names verified against the live game (via poe2db + NeverSink's filter data): 7 dead rune names removed and 12 real ones added, chance-orb list corrected to only actually-chanceable targets
- 🐛 Fixes: copy buttons now always work (native clipboard), Preview copies your current selection, long rules wrap instead of being cut off, validation markers point at the right lines, profiles remember the new settings
- The game's loot-filter folder is now detected automatically for the optional .filter copy

**v3.2.1**
- 🐛 **Preview fix** — the section list ("All sections" sidebar) went missing right after generating; it now shows every section immediately, including the big banner sections like Tablets and Chance Orb Bases

**v3.2.0**
- 🔄 **All game data now updates without a new release** — tablets, splinters, wombgifts, always-pick currency & runes, chance-orb bases and item-name fixes moved into the self-updating `game_data.json`; when a PoE2 patch adds or renames items, the app picks up the change automatically within hours
- Bad remote data can't break anything: it's validated first, and the app keeps its built-in copy if the file looks wrong

**v3.1.1**
- Rare Items tab pulled for a redesign — coming back rebuilt step by step

**v3.0.0**
- 🖥️ **Brand-new interface** — the app was rebuilt on a modern WebView2 front-end: same engine, same files, dramatically better UI
- 🌙 **Instant themes** — dark/light switch applies immediately (no restart, no crash)
- ✨ **Auto value floor** — sets both minimum values from the league's live prices ("keep top 40%"), with a preview of how many items each floor keeps
- 💰 **Floors in Exalt, Chaos or Divine** — type the value in whichever currency holds its worth
- 🛡️ **Safety net** — if a run produces a collapsed/broken pickit, auto-copy to the bot is blocked and you're told why
- 🚀 **League-start preset** — one click picks up everything on day 1; one click restores your old setup
- 🖥️ **Tray mode** — close to the system tray and Auto-Regenerate keeps your pickit fresh in the background
- 📈 **Redesigned History & Preview** — trend chart with hover details; section navigator, filter chips and inline validation markers
- Requires the Microsoft WebView2 runtime (preinstalled on up-to-date Windows 10/11)

<!-- 👇 ON EACH UPDATE, add the new version here at the top. Keep only the 5 most recent — drop the oldest as you add the newest:
**vX.Y.Z**
- what changed
- what else changed
-->

---

<div align="center">

**[⬇️ Download](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)** · **[🐛 Report an issue](https://github.com/c4Luffy/poe2-pickit-generator/issues)** · **License: MIT**

</div>
