<div align="center">

<img src="docs/logo.png" width="112" alt="PoE 2 Pickit Generator logo">

# PoE 2 Pickit Generator

### for Exiled Bot 2

**Live PoE2 prices in. A validated, bot-ready pickit out.**

Choose your league and how greedy the bot should be. The app turns today's
[poe.ninja](https://poe.ninja) economy into a complete pickit, validates it,
deploys it, and confirms Exiled Bot 2 is listening to the same profile.

<br>

[![Download for Windows](https://img.shields.io/badge/Download_for_Windows-d2a24f?style=for-the-badge&logo=windows&logoColor=181104)](https://github.com/c4Luffy/poe2-pickit-generator/releases/download/v4.21.0/ExileBot2PickitGenerator.exe)
[![Open website](https://img.shields.io/badge/Open_website-79bd62?style=for-the-badge&logo=githubpages&logoColor=10200c)](https://c4luffy.github.io/poe2-pickit-generator/)

[![Release v4.21.0](https://img.shields.io/badge/release-v4.21.0-c99a4a?labelColor=171411)](https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.21.0)
[![Total downloads](https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?color=829d78&labelColor=171411)](https://github.com/c4Luffy/poe2-pickit-generator/releases)
[![Windows 10/11](https://img.shields.io/badge/Windows-10%20%2F%2011-6e6255?logo=windows&logoColor=white)](https://github.com/c4Luffy/poe2-pickit-generator/releases/latest)
[![MIT license](https://img.shields.io/badge/license-MIT-6e6255)](LICENSE)

<br>

<a href="docs/shots/03-item-check.png">
  <img src="docs/shots/03-item-check.png" width="1000" alt="Item Check showing Try an example and a depends-on-the-rolls verdict for a pasted rare item">
</a>

<sub>Real running-app capture · Item Check</sub>

</div>

## What it does

| Live market intelligence | Explainable, validated rules | Reliable bot handoff |
|---|---|---|
| Reads current league prices instead of shipping a frozen price list. | Checks stat IDs before deploy; Item Check then applies those same generated rules to one pasted item. | Copies the output, reads <code>pickit.ini</code>, and confirms the active profile. |
| Five presets plus editable floors and Auto-floor. | Reports Picked up, Ignored, or Depends on the rolls, with the deciding rule and an actionable explanation. | Offers one-click profile repair, rotating backups, and restore. |

The generated pickit covers currency, uniques, bases, runes, essences,
fragments, tablets, maps, waystones, rare gear, and more. An optional matching
in-game loot filter can be generated alongside it.

## Quick start

1. **[Download the v4.21.0 portable Windows app](https://github.com/c4Luffy/poe2-pickit-generator/releases/download/v4.21.0/ExileBot2PickitGenerator.exe).**
2. Open it, choose your league, and start with the **Balanced** preset.
3. Confirm or choose the Exiled Bot 2 folder and enable auto-copy.
4. Press **Generate**. Prices are fetched, the pickit is built and validated,
   and the output is deployed.
5. Run the **connection check**. If <code>active_profile</code> points at another
   file, use **Fix it for me**.

Need to explain a specific drop? Hover it in game, press **Ctrl+C**, paste it
into **Item Check**, and press **Check this item**.

The first setup takes about two minutes. After that, one Generate refreshes the
pickit whenever the market moves.

> [!NOTE]
> Exiled Bot only loads the <code>.ipd</code> named by <code>active_profile</code>.
> A copied file can exist while the bot keeps reading an older profile. The
> connection check catches that silent mismatch.

## Built for real runs

- **Live poe.ninja pricing** across the current trade league.
- **Item Check** explains one pasted item using the emitted rule, opens that
  rule in Preview, and includes ready-made unique, rare, and fractured examples.
- **Five quick-start presets:** Vacuum, Balanced, Strict, Chase, and Currency.
- **27,000-mod validation** before rules reach the bot.
- **Rare-gear scoring** with weighted recipes for all 17 equipment slots.
- **Changed filter and run history** so market-driven differences are visible.
- **Best-effort bot-folder detection** with manual selection when needed.
- **Backups before replacement** with restore support.
- **Nine distinct themes** with their own body type, headings, and tab treatment.
- **Multi-unit pricing** that reads exalt, divine, and chaos values.
- **Portable single-file app:** no installer and no Python required.

## Latest release: [v4.21.0](https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.21.0)

### Themes got a voice. Item Check grew up.

Each of the nine themes now changes the app's typography and tabs as well as its
colour. Ossuary feels archival, Abyss uses instrument-panel mono headings, Void
leans occult, Delirium is soft and rounded, and Umbral is cold and minimal.
Relic remains the familiar brass Workbench. Every font already ships with
Windows, so there is nothing extra to download.

- Click the matched <code>.ipd</code> line in an Item Check verdict to open
  Preview at that exact rule.
- Use **Try an example** to load a random unique, rare, or fractured item.
- Read prices expressed in exalt, divine, and chaos.

> [!IMPORTANT]
> **Item Check is not a simulation.** It uses the same pickit-generation code
> that writes the <code>.ipd</code> file and shows the exact line emitted for the
> pasted item. For the same current settings, the tab and the generated file
> cannot disagree.

**[Read the full changelog →](CHANGELOG.md)**

## Download safety

This is a free community tool. Windows SmartScreen may ask for confirmation
because the executable is not code-signed.

- The complete source and release workflow are public.
- Every release includes a
  **[SHA-256 checksum](https://github.com/c4Luffy/poe2-pickit-generator/releases/download/v4.21.0/SHA256SUMS.txt)**.
- The app reads public price data from poe.ninja and update data from GitHub.
- It never asks for your Path of Exile account.

## Build from source

<details>
<summary><b>Developer setup and checks</b></summary>

<br>

<pre><code>python -m pip install -e .
python -m exilebot_pickit</code></pre>

<pre><code>python -m pip install pytest ruff
python -m pytest -q
ruff check .</code></pre>

The application code lives in <code>src/exilebot_pickit/</code>. Push a
<code>vX.Y.Z</code> tag and the release workflow builds the Windows executable
and publishes its checksum.

</details>

## Help and community

- **[Website](https://c4luffy.github.io/poe2-pickit-generator/)** — complete
  product tour, setup flow, and FAQ.
- **[Discord](https://discord.gg/T7DU3Afve6)** — community help.
- **[Issues](https://github.com/c4Luffy/poe2-pickit-generator/issues)** — bugs
  and feature requests.
- **[Releases](https://github.com/c4Luffy/poe2-pickit-generator/releases)** —
  downloads and version history.

---

<div align="center">

MIT licensed · built for the Exiled Bot 2 community · prices by
[poe.ninja](https://poe.ninja)

<sub>Not affiliated with Grinding Gear Games or Exiled Bot.</sub>

</div>
