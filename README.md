<div align="center">

# ⚔️ ExileBot 2 Pickit Generator

Turns live [poe.ninja](https://poe.ninja) prices into a ready-to-use Exiled Bot 2 pickit —
so your bot grabs what sells **today**.

[![Release](https://img.shields.io/github/v/release/c4Luffy/poe2-pickit-generator?label=latest&color=2ea043)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=blue)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#license)

<br>

## &rarr; [🌐 &nbsp;Visit the website](https://c4luffy.github.io/poe2-pickit-generator/) &nbsp;·&nbsp; [⬇️ Download for Windows](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)

**[💬 Discord](https://discord.gg/T7DU3Afve6)** · **[🤖 Exiled Bot](https://exiled-bot.net/)**

<sub>One `.exe` · no Python · no installer</sub>

</div>

<br>

Everything — features, quick start and FAQ — lives on the
**[website](https://c4luffy.github.io/poe2-pickit-generator/)**. In short: pick your league,
press **⚡ Generate**, point Exiled Bot 2 at the `.ipd`. Live prices in, a complete pickit out.

> ### ⚒️ What's new in v4.5.0 — "Exile's Workbench" + smarter ground filtering
> **The bot now skips junk on the ground**: base rules filter `[ItemLevel]`
> *before* pickup, fracture rules gate on item tier, and ten broken thresholds
> were fixed after live bot testing. Plus a warmer brass-and-bone redesign with
> drag-slider value floors, real item icons, and prices in ex / div / chaos.
>
> **[→ Full changelog](CHANGELOG.md)**

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

---

<div align="center">
<a name="license"></a>

**[🌐 Website](https://c4luffy.github.io/poe2-pickit-generator/)** · **[⬇️ Download](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)** · **[💬 Discord](https://discord.gg/T7DU3Afve6)** · **[🐛 Issues](https://github.com/c4Luffy/poe2-pickit-generator/issues)** · MIT

<sub>Built for the Exiled Bot 2 community · prices by poe.ninja · not affiliated with GGG</sub>

</div>
