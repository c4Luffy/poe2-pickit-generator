<div align="center">

# ⚔️ ExileBot 2 Pickit Generator

Turns live [poe.ninja](https://poe.ninja) prices into a ready-to-use Exiled Bot 2 pickit —
so your bot grabs what sells **today**.

[![Release](https://img.shields.io/github/v/release/c4Luffy/poe2-pickit-generator?label=latest&color=2ea043)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=blue)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

### [⬇️ Download for Windows](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)

**[🌐 Website](https://c4luffy.github.io/poe2-pickit-generator/)** · **[💬 Discord](https://discord.gg/T7DU3Afve6)** · **[🤖 Exiled Bot](https://exiled-bot.net/)**

<sub>One `.exe` · no Python · no installer</sub>

</div>

<br>

## What it does

- 🪙 **Live prices, every run** — real league economy from poe.ninja, or one-click **Auto floor**
- 🧱 **Knows the good stuff** — currency, uniques, tablets, chance & craft bases, exceptional bases
- 🛡️ **Safe by default** — a broken pickit is never auto-deployed to your bot
- ⏰ **Set and forget** — auto-regenerate on a timer + auto-copy to the bot folder
- 🔄 **Self-updating** — game-data fixes reach every install automatically, no re-download

<br>

## Quick start

1. **[Download the `.exe`](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)** and open it *(Windows warning → More info → Run anyway)*
2. Pick your **league**, press **⚡ Generate**
3. Point Exiled Bot 2 at the `.ipd` — or turn on **Auto-copy** and forget it

Everything valuable is picked by default. Don't want something? One click in the **Economy** tab.

<br>

<details>
<summary><b>The tabs at a glance</b></summary>

<br>

| Tab | What it's for |
|-----|---------------|
| ⚡ Generate | League, value floors, auto floor — the one button |
| 🪙 Economy | Every pickable item with live prices — click to exclude |
| 🎲 Chance / 🛠 Craft | Bases worth chancing or crafting on |
| 🧱 Exceptional | Extra-socket bases, ranked and grouped by attribute |
| 📜 Preview | The exact file the bot reads |
| 🕘 History | Every run charted over the league |
| ⚙ Settings / 🔧 Debug | Bot folder, auto-copy, backups · API test & logs |

</details>

<details>
<summary><b>Tips &amp; troubleshooting</b></summary>

<br>

- **Right-click** a row copies its rule · <kbd>Ctrl</kbd>+<kbd>G</kbd> generates
- Every tab has an **ℹ what is this?** explainer — no wiki needed
- **No prices?** Debug → Run API test (poe.ninja may be down; the cache covers you)
- **Bot ignores items?** Check the pickit path, or enable Auto-copy
- Files live in `ExileBot2PickitGenerator_data` next to the `.exe`
- The bundled `.filter` is for **manual play only** — don't feed it to the bot

</details>

<details>
<summary><b>Build from source</b></summary>

<br>

```bash
pip install -e .            # run:   python -m exilebot_pickit
pip install pytest ruff     # test:  python -m pytest -q && ruff check .
```

`src/exilebot_pickit/` — `generator.py` builds the rules · `webui/` is the WebView2 app · `data/` holds remote-updatable game data. Push a `vX.Y.Z` tag and CI builds + publishes the exe.

</details>

<br>

## What's new — v3.7.1

- 🐛 Fixed the in-app **Discord** and **Exiled Bot** links (were blocked by the URL allowlist)
- ⬆️ **New updater** — a clean update banner with progress bar and one-click **install & restart** (backs up the old exe first, so you never lose a working version)
- 🎨 **App logo** in the sidebar, plus **Discord** and **Exiled Bot** links; clearer "? Help" buttons
- 🧱 Exceptional bases = the 122 best, ranked and grouped by attribute · Chance Bases trimmed to 8

→ [Full changelog](https://github.com/c4Luffy/poe2-pickit-generator/releases)

<br>

---

<div align="center">
<a name="license"></a>

**[🌐 Website](https://c4luffy.github.io/poe2-pickit-generator/)** · **[⬇️ Download](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)** · **[💬 Discord](https://discord.gg/T7DU3Afve6)** · **[🐛 Issues](https://github.com/c4Luffy/poe2-pickit-generator/issues)** · MIT

<sub>Built for the Exiled Bot 2 community · prices by poe.ninja · not affiliated with GGG</sub>

</div>
