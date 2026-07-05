<div align="center">

# ⚔️ ExileBot 2 Pickit Generator

### Live Path of Exile 2 prices in. Ready-to-use pickit out. One click.

Fetches the **real PoE2 economy** from [poe.ninja](https://poe.ninja) and writes an Exiled Bot 2 `.ipd` pickit
(plus a matching in-game `.filter`) tuned to what's *actually worth picking up today*.

<br>

[![CI](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml/badge.svg)](https://github.com/c4Luffy/poe2-pickit-generator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/c4Luffy/poe2-pickit-generator?label=release&color=c8a96e)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=2ea043)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![Platform](https://img.shields.io/badge/platform-Windows-0078D6)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue)](#license)

<br>

## [⬇️ &nbsp;Download the latest .exe](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)

*No Python. No install. One self-contained Windows app.*

<br>

</div>

---

## 🚀 Up and running in 3 steps

|   | Step | What to do |
|:-:|------|------------|
| 1️⃣ | **Download & open** | Grab `ExileBot2PickitGenerator.exe` from the [latest release](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest) and double-click. *(Windows warning? → More info → Run anyway.)* |
| 2️⃣ | **Generate** | Pick your league, hit **⚡ Generate Pickit**. Live prices in, pickit out — saved to `pickit_output`. |
| 3️⃣ | **Connect the bot** | Point Exiled Bot 2 at the `.ipd` — or flip on **Auto-copy** in Settings and never touch it again. |

> **That's it.** Everything valuable is picked by default. Don't want something? One click in the **Economy** tab turns it off.

---

## ✨ Why it's good

| | |
|---|---|
| 🪙 **Live prices, every run** | Real PoE2 economy from poe.ninja — never a stale price list |
| ✨ **Auto value floor** | One click sets your minimum values from the league's actual prices |
| 🛡️ **Safety net** | A broken or collapsed pickit is **never** auto-deployed to your bot |
| ⏰ **Set & forget** | Auto-regenerate every few hours + tray mode + auto-copy = always fresh, zero clicks |
| 🔄 **Self-updating game data** | New items after a game patch reach every installed app within hours — no new download |
| 💰 **Your currency, your call** | Value floors in Exalt, Chaos or Divine, converted at the live rate |
| 🖥️ **Modern UI** | Instant dark/light themes, price-change arrows, plain-language explainers on every tab |
| ⬆️ **Update alerts** | Tells you when a new version is out, links straight to it |

### 🗺️ The tabs, in one line each

| Tab | What it's for |
|-----|---------------|
| ⚡ **Generate** | The main button — league, value floors, auto floor, league-start preset |
| 🪙 **Economy** | Everything the bot can pick up, with live prices — click to include/exclude |
| 🎲 **Chance Bases** | White bases worth keeping for Orb of Chance (Headhunter, Mageblood…) |
| 🛠 **Craft Bases** | Blank high-ilvl bases worth crafting on, per slot |
| 🧱 **Exceptional** | Top-tier bases with extra rune sockets — white pickups + uniques on them |
| 📜 **Preview** | The exact file the bot reads, with sections, filters and validation |
| 🕘 **History** | Every run logged, with a trend chart |
| ⚙ **Settings / 🔧 Debug** | Bot folder, auto-copy, backups, updates · API test & logs |

---

<details>
<summary><b>💡 Handy tips</b></summary>

<br>

- **Right-click** any item row → copies its pickit rule to the clipboard
- **Refresh** on the Economy tab → fresh prices for that category
- **Enable All / Disable All** → toggles a whole category at once
- **Arrows ▲▼** show price moves over 3%; alerts flag moves over 20%
- **Craft Bases** → the item level you set on a card is exactly what the bot uses

</details>

<details>
<summary><b>🛠️ Something not working?</b></summary>

<br>

- **No prices loading?** Debug tab → **Run API test**. poe.ninja may be down — the app falls back to its saved price cache.
- **Bot not picking items?** Check the pickit path in Exiled Bot 2, or turn on **Auto-copy** in Settings.
- **Windows blocked the .exe?** More info → Run anyway. It's unsigned (free tool) — all the source is right here.
- **Where are my files?** In `ExileBot2PickitGenerator_data` next to the `.exe` (`pickit_output/` holds the generated files).

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

Newest first, last 5 releases. Full history on the **[Releases page](https://github.com/c4Luffy/poe2-pickit-generator/releases)**.

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

**[⬇️ Download](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)** · **[🐛 Report an issue](https://github.com/c4Luffy/poe2-pickit-generator/issues)** · <a name="license"></a>**License: MIT**

</div>
