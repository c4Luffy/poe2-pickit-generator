# Changelog

All notable changes to **ExileBot 2 Pickit Generator**.
Versions link to their release, where the `ExileBot2PickitGenerator.exe`
download lives.

---

## [v4.21.0] — 2026-07-13 — Every theme gets its own voice, and Item Check grows up

### Themes are no longer just a colour swap
Each of the nine themes now carries its **own body face, heading face and tab style** —
so switching theme changes the *character* of the app, not only its accent:

- **Ossuary** — bookish serif, Marcellus headings, sharp uppercase tabs. An archive.
- **Abyss** — monospace headings, tight uppercase tabs. A deep-sea instrument panel.
- **Void** — Palatino headings, wide-tracked uppercase tabs. Occult.
- **Delirium** — soft Candara throughout, rounded tabs. Dreamlike.
- **Umbral** — stark sans, brutal 2px tabs, hard tracking. Cold and minimal.
- **Blight** — heavy mono headings, hazard-tape tabs.
- **Venom** — friendly humanist face, pill tabs. **Twilight** — warm serif.
- **Relic** stays exactly as it was: the brass workbench.

**Every face is one Windows already ships.** Nothing is downloaded and nothing is
embedded — the lag in the reverted polish pass came from base64-embedding a *variable*
body font, which WebView2 re-interpolated on every glyph under `body{zoom:1.1}`. These
cost nothing.

### Item Check
- **Click the `.ipd` line in a verdict** to jump straight to that rule in Preview, with
  the line flashed. Every preview line now carries its id, not just the validation ones.
- Rules are matched by **identity, not the whole line** — the trailing `// ExValue = …`
  comment holds the price at generate time, so it drifts with the market; matching on it
  missed the rule on any pickit older than today's prices.
- **✨ Try an example** hands back a random **unique, rare or fractured** item, so a few
  presses show all three verdicts. Uniques and their live price come from poe.ninja,
  bases from the game's own base list, and mods are real mod text from our verified
  fracture targets, with the stated range collapsed to a single roll the way a real item
  reads. The rare and fractured examples need no league and no network.
- **Prices now read in exalt, divine and chaos.** A unit is dropped when it would round
  to noise, so a 0.12 ex unique doesn't claim "0.00 div" — and `2483040.00 ex` now
  prints as **2,483,040**.

## [v4.20.0] — 2026-07-13 — Item Check: "why did my bot walk past that?"

Nothing in the app could answer the two questions everybody actually asks — *why did
it leave that behind?* and *why is my stash full of junk?* Preview showed you the
file; History showed you counts. Neither told you what your pickit does to **one
specific item**.

**New 🔍 Item Check tab.** Hover an item in game, press **Ctrl+C**, paste it in. You
get a straight answer — **Picked up**, **Ignored**, or **Depends on the rolls** — the
rule that decided it, and *why*:

> ❌ **Ignored** — worth **6.20 ex**, but your item floor is **8 ex**; it misses by
> **1.80 ex**. 🔧 *Lower the item floor to 6.2 ex or less and it gets taken.*

- **The verdict is not a simulation.** For priced items it runs the *same* assembly
  that writes your `.ipd` and reports whether a rule for that item really comes out
  of it — then shows you **the actual line**. If this tab and the file ever
  disagreed, the file would be the thing that's wrong.
- It tells you *which* reason applies, and they are not the same: cleared your floor,
  **always-take list**, or **a whole category that ignores the floor**. (Currency is
  pick-all — that's why the bot grabs 0.05 ex Scrolls of Wisdom no matter what your
  floor says. Now you can see that instead of guessing.)
- **Rare gear** gives a definitive *no* when no recipe covers the base or the slot is
  off. When the base *is* covered and the slot is on, it says **"depends on the
  rolls"** and shows the scored stats and the threshold — because the bot does that
  maths in-game from the real mods, and inventing a number here would be a lie.
- **Fracture** only speaks up for an actually-fractured item, instead of on every wand.

### Fixed
- **Item level was never parsed.** The old simulator stopped reading at the first
  `--------`, but PoE2 puts `Item Level:` in a *later* block — so every ilvl check
  silently ran against `None`.
- The old **Test Item Simulator** (buried at the bottom of Preview, and unable to
  answer for uniques, currency or rares — the three things people ask about) is gone,
  replaced by this.

## [v4.19.1] — 2026-07-13 — The side panel, cleaned up

The rail was stacking a **fractal-noise SVG, vertical pinstripes, a gold gradient
and inset shadows** — all behind the text. The texture was fighting the labels and
made the whole panel read muddy. It's now one clean surface with a single hairline.

- Nav labels were **Marcellus serif at 14px with 1px letter-spacing and a
  drop-shadow**, which blurs at that size. Now a crisp sans. (Marcellus stays where
  it belongs — the big page headings.)
- A little more air between items.
- **Hover** nudges the item 2px right; the **active tab** gets a soft brass glow so
  the current page reads as *lit*, not just outlined. Both are single-element
  transforms — no repeat of the whole-app transition that made theme switching
  stutter.

## [v4.19.0] — 2026-07-13 — Nine themes, and a theme picker that tells you what they are

### Added — six new themes
The switcher used to be a row of emoji, which told you nothing — nobody can tell what
🌑 or 🌊 means. It's now a **named picker** at the bottom of the sidebar, under a
**THEME** label. It shows the name of the theme you're on plus a dot in its accent
colour, and opens into a list where every theme shows its **colour, name, a one-line
description, and a ✓ on the active one**.

| Theme | | |
|---|---|---|
| 🏺 **Relic** | gold & brass | the default |
| 🧪 **Venom** | emerald | matches the mascot |
| 🔮 **Void** | arcane violet | |
| 🦴 **Ossuary** | bone & ash | **no hue at all** — the warm monochrome |
| 🌸 **Delirium** | pale rose fog | an accent that whispers |
| 🌑 **Umbral** | silver on true black | the cold monochrome |
| 🌊 **Abyss** | bioluminescent teal | a glow, not a colour |
| 🌗 **Twilight** | peach on navy | the only warm accent on a cool ground |
| ☢ **Blight** | toxic chartreuse | the sickly green, vs Venom's clean one |

These aren't nine tints of the same idea — Ossuary and Umbral are the *same* colourless
concept done warm and cold, and Twilight is the only one that puts a warm accent on a
cool ground.

### Fixed — theme switching stuttered the whole app
Switching a theme applied a transition to **every element on the page** (`html.theming *`)
for 350ms. With nine themes you'll be flicking through them, and that rule made the whole
UI stutter each time. Removed — switches are now instant.

### Removed
**Ember**, **Sanguine** and **Vellum** (a light theme) were tried and cut. If you're
saved on any removed theme, the app puts you back on **Relic** rather than leaving you
on a theme with no colours.

## [v4.18.3] — 2026-07-13 — Ember theme dropped

The molten-orange **Ember** theme didn't look good next to the others and has been
removed. Three themes remain: 🏺 **Relic** (gold, default) · 🧪 **Venom** (emerald,
matches the mascot) · 🔮 **Void** (arcane violet).

If you were using Ember, the app puts you back on **Relic** rather than leaving you
on a theme that no longer has any colours.

## [v4.18.2] — 2026-07-13 — Chase loosened again (owner field feedback)

**Chase** still wanted 120 ex for a unique, which was more than it needed to be. It
now stops for **20 ex currency & items / 50 ex uniques** — strict enough to skip the
noise, loose enough to actually catch the money drops.

Final ladder:

| Preset | Currency & items | Uniques |
|---|---|---|
| 🧲 **Vacuum** | 1 ex | 1 ex |
| ⚖️ **Balanced** | 2 ex | 6 ex |
| 💎 **Strict** | 8 ex | 25 ex |
| 👑 **Chase** | 20 ex | 50 ex |
| 💰 **Currency only** | 1 ex | — |

## [v4.18.1] — 2026-07-13 — Preset floors loosened

The v4.18.0 presets were too stingy — **Chase** demanded a full Divine (500 ex) for a
unique, so it barely picked anything up. Every floor is now roughly **3–4× more
generous**, so each preset keeps what it claims to keep.

| Preset | Currency & items | Uniques | was |
|---|---|---|---|
| 🧲 **Vacuum** | 1 ex | 1 ex | unchanged |
| ⚖️ **Balanced** | **2 ex** | **6 ex** | 5 / 15 |
| 💎 **Strict** | **8 ex** | **25 ex** | 25 / 75 |
| 👑 **Chase** | **30 ex** | **120 ex** | 100 / 500 |
| 💰 **Currency only** | 1 ex | — | unchanged |

Balanced now only skips actual vendor trash, and Chase (~¼ Divine on uniques) still
catches the genuinely valuable drops instead of almost nothing.

The tests no longer hardcode these numbers — they read them from the preset
definitions — plus a new guard that a stricter preset can never end up with a
*lower* floor than a looser one, so the strictness meter can't start lying.

## [v4.18.0] — 2026-07-13 — Presets: pick how greedy the bot should be

### Added — ready-made presets
The Generate tab opens with a **Quick start** row. Five presets, each with a
strictness meter and a plain-language explanation of *what it picks up and what it
costs you*. Hover to read it, click to apply — it sets every floor and switch at once.

| Preset | Currency & items | Uniques | |
|---|---|---|---|
| 🧲 **Vacuum** | 1 ex | 1 ex | Anything with a price. League start. |
| ⚖️ **Balanced** | 5 ex | 15 ex | Skips junk, keeps what sells. |
| 💎 **Strict** | 25 ex | 75 ex | Only drops worth the walk. |
| 👑 **Chase** | 100 ex | 500 ex | Roughly a Divine and up. Bases off. |
| 💰 **Currency only** | 1 ex | — | No uniques, no rare gear, no bases. |

Floors are calibrated against a ~500 ex Divine, so "Chase" genuinely means *a divine
and up* — a real answer to the adaptive floor handing you `≥ 1 ex` at "keep top 80%".

Hand-edit any floor and the preset highlight clears itself: the app never claims a
preset is active once its numbers no longer match.

### Added — four themes
🏺 **Relic** (gold, default) · 🧪 **Venom** (emerald — matches the mascot) ·
🔮 **Void** (arcane violet) · 🔥 **Ember** (molten orange). The old Frost/Blood are
retired. Switching now **cross-fades** instead of hard-flipping, and buttons press
down when clicked.

### Changed
- **Top picks now lead with Divine**, then Chaos, then Exalt (was Exalt first).
- **Sidebar is clean** — the rule-count badges (`1,126`, `18`) are gone.
- **Settings → In-game filter** is expanded by default instead of collapsed.
- Generate tab reordered: league → preset → fine-tune → generate.

## [v4.17.3] — 2026-07-12 — The mascot is in the app itself

### Changed
- The sidebar now shows the **mascot logo** instead of a plain gold "E" tile. The
  transparent cutout is embedded straight into the single-file UI (so it still
  works offline), and the gold gradient box is gone — the character sits clean.

## [v4.17.2] — 2026-07-12 — Transparent logo, no black box

### Changed
- **The app logo no longer sits on a black background.** The mascot is now on a
  transparent background everywhere it appears — the website logo, the app icon
  `.png`, and the `.ico` used for the window and taskbar. Cut with an ML matting
  pass, so the character's own dark armour and cape are kept, not keyed out with
  the background.

## [v4.17.1] — 2026-07-12 — Item icons sit clean

### Fixed
- **Item icons no longer sit on a dark box.** The Economy list and the
  top-valued-items table painted a `--bg3` background + border behind every icon;
  the transparent art now sits directly on the page.
- **Website FAQ:** fixed a missing space in the *".ipd vs .filter"* question — mono
  chips inside a flex `<summary>` had collapsed the whitespace, so it read
  *".ipdvs"*.

## [v4.17.0] — 2026-07-12 — The app finds your bot folder for you

### Added — auto-detect the Exiled Bot pickit folder
New users had to browse to `...\ExiledBot2\Configuration\default\Pickit` by hand
before any loot reached the bot. Now the app looks for it.

- **On first launch** (no bot folder set yet), the app scans the usual install
  spots — Desktop, Downloads, Documents, your home folder, Program Files, and the
  drive roots — for an Exiled Bot install, and if it finds one it **sets the folder
  and turns Auto-copy on automatically.** The setup banner turns into
  *"Found your Exiled Bot and connected it."*
- **Settings → Auto-detect** button runs the same search any time.
- A folder only counts as a real bot install when a **`pickit.ini` sits beside the
  `Pickit` folder** — the signature of an actual Exiled Bot — so it won't latch
  onto a random lookalike directory.

It does **not** touch `active_profile` — connecting the file is automatic, but which
file the bot reads is still yours to confirm (Settings shows it and offers **Fix it**).

## [v4.16.0] — 2026-07-12 — Headless `--cli` generate now writes the full pickit

### Fixed — the `--cli` path was silently thinner than the app
A pre-ship audit found the headless `python -m exilebot_pickit --cli` generate
emitted rare-gear recipes but **none of the other endgame sections the GUI writes**:
Fracture bases, Craft bases, Exotic bases, and the Magic & Rare flask rules were
all missing. Anyone scripting a pickit off the CLI got a partial file with no
warning.

The CLI now emits the exact same sections, in the same order, a default GUI
generate does — everything on (the headless path has no per-item/per-slot config).
That's ~600 extra rules per run. Two regression tests now assert every section
builder stays wired into `main()` and that each produces content at its defaults,
so the headless path can't silently lose a section again.

The GUI generate was never affected.

## [v4.15.0] — 2026-07-12 — Per-slot rare-gear switches (and the master switch was invisible)

### Fixed — the rare-gear master switch never rendered
`class="sw"` was **not a CSS class**. It has no rules. Every working switch in the
app uses `.switch`. So the master *"Rare-gear rules in your pickit"* toggle was an
unstyled, zero-height div: **present in the DOM, invisible on screen, impossible
to click — in every release since v4.11.0.**

Nobody could turn rare gear off. Caught by the owner in a screenshot, not by any
of the automated gates, because those checked that the *code path* worked and
never checked that a human could *see* the control.

**New gate:** the pre-ship audit now flags any class used in the markup that has
no CSS rule — the exact signature of an invisible control.

### Added — per-slot on/off
Every rare-gear slot now has its own switch (*"Include Sceptre in your pickit"*),
so you can drop the slots you don't care about and keep the rest. The sidebar
shows `off` against a disabled slot, and the card greys out. Toggling is instant
and persists; regenerate to apply.

Magic & Rare was the **only** section with no per-item control — Economy has
per-item, Fracture per-class, Chance/Craft/Exceptional per-base. Now it has
per-slot, plus the master switch above it.

## [v4.14.0] — 2026-07-12 — Settings and Debug redesigned: the app checks, instead of implying

Both tabs used to *imply* things were fine. Now they go and look.

### Settings — verifies the bot connection instead of assuming it
- **The bot-connection card now reads the bot's own `pickit.ini`** and tells you
  the truth:
  - ✓ *"Connected — your bot reads poe2_pickit.ipd, and every Generate deploys
    it there."*
  - ⚠ *"The bot is IGNORING everything you generate — it's reading
    'poe-ninja-20260711-131901.ipd', but you generate 'poe2_pickit.ipd'."*

  The old card showed a folder and a toggle and let you believe you were done.
  It had no idea whether the bot would actually read your file. **It didn't for
  the owner — for a day.**
- **A "Fix it for me" button** rewrites the bot's `active_profile` (backing the
  file up first) when they don't match.
- **Renaming your output file re-checks immediately** — that's the same trap by
  another door, and the app now catches it the second you do it.
- **Redesigned around the app's own sidebar rail** (as used by Craft / Fracture /
  Magic & Rare): sections instead of a wall of cards, and **the rail carries live
  status** — a broken bot connection is visible the instant you open Settings,
  without clicking anything. Advanced settings (the in-game loot filter, which
  bot users are told to leave off) get their own group instead of prime position.

### Debug — health first, tools second
- **Four tiles populate on open**: errors logged, poe.ninja, cached payloads,
  game data. The errors tile is **coloured by recency** — red if any happened in
  the last hour (live), amber if they're historical, green if clean.
- **Errors are counted and grouped**, not dumped as raw text:
  `43 save_config (last 16:14) · 41 load_config (last 16:31)`, with a plain-words
  verdict on whether to worry.

  This is not academic: **318 config errors sat in that log for a day** and were
  only found by grepping the file, because nothing counted them. This tab would
  have opened with a red tile.
- All ten tools unchanged.

## [v4.13.0] — 2026-07-12 — In-app setup guide (and the trap it exists to prevent)

New **📖 Setup guide** tab. Four steps to go from a fresh download to a bot that's
actually reading your pickit — plus the one thing nobody guesses.

### The trap
Connecting the bot takes **three** actions, not two. Everybody does the first two:

1. Settings → point at the bot's Pickit folder
2. Settings → Auto-copy → ON
3. **Open the bot's `Configuration\default\pickit.ini` and set
   `active_profile=poe2_pickit`** ← this one

Skip step 3 and the bot only ever loads the single `.ipd` named by
`active_profile`. Auto-copy still reports success, the file really does land in
the folder — and **the bot carries on reading whatever old pickit it was already
on.** Nothing looks broken and nothing you generate is ever used. The owner's own
bot had been running a pickit from the previous day.

### Added
- **Setup guide tab** (System group): the four steps, with step 3 broken out and
  explained; what the two value floors actually gate (and that rare gear is
  *scored*, not priced, so no floor touches it); what every tab is for; and a
  "the bot seems to be ignoring good loot" checklist — regenerate → check
  `active_profile` → run the Game data health check → check your floors.
- **First-run nudge** on the Generate tab when no bot folder is set: *"Your bot
  isn't connected yet — generating writes a pickit, but nothing will reach Exiled
  Bot until you set it up."* It clears itself as soon as the folder is chosen.

## [v4.12.4] — 2026-07-12 — Concurrent saves were corrupting your settings file

The Debug log told on it: **318 `load_config` failures and 107 `save_config`
failures in a single day**, still happening minutes before this fix.

`save_config` wrote every save to one shared `config.json.tmp`. When two savers
ran at once — the UI thread and the generate worker, or a second copy of the app —
the second **truncated the first's half-written JSON**, and whichever finished
first atomically moved that garbage into place. `os.replace` being atomic never
helped: the file it moved was *already corrupt*.

**Every one of those 318 read failures silently dropped the app onto default
settings.** A save landing in that window would have wiped your league, profiles,
run history and every item toggle. Nothing was lost this time — that was luck.

### Fixed
- **Each save now writes its own temp file** (`tempfile.mkstemp`), so savers can
  no longer clobber each other. An in-process lock serialises the UI thread and
  the generate worker; the unique temp name is what protects against a second
  process. The write is `fsync`'d before the swap, and temp files are always
  cleaned up.
- **`load_config` retries once** before declaring the config corrupt, so a save
  landing at the same instant can never again cost you your settings.
- Regression test: 4 threads × 25 saves against 2 readers must produce **zero**
  corrupt reads. It catches the old code (20 corruptions) and passes the new.

## [v4.12.3] — 2026-07-12 — A stale cache was overriding shipped data fixes

**Shipping a game-data fix did nothing for up to 6 hours.** The remote-data disk
cache was keyed only on a timer, so on launch the app applied the *cached* game
data over its own newer bundled lists — and the cache won.

Caught the hard way: right after v4.12.1 removed Hallowed Sceptre and Dark Staff
(bases that don't drop), a freshly generated pickit **still contained 22 rules
for them**. The cache, written before the fix, put both straight back. The
validator flagged it only because it checks against the bundled data — that
mismatch is the one thing that made this visible at all.

### Fixed
- **The cache is now stamped with the app version, and a cache written by a
  different build is ignored** (forcing an immediate refetch). A new build always
  ships game data at least as new as an older build's cache, so on a version
  change the bundled data is the safe starting point. Offline launches on the
  *same* version still use the cache exactly as before.
- Regression test added.

If you updated and generated in the last few hours, **regenerate** — your pickit
may contain rules for the two dead bases.

## [v4.12.2] — 2026-07-12 — Settings audit: one dead knob removed

Audited every setting against the config, the API allowlist and the UI.
**Everything checks out** — all 28 config keys are accounted for, every
user-facing setting has a working control, and no label lies about what it does
(the "Gear floor" mislabel in v4.11.6 was the last of those).

### Removed
- **`confirm_overwrite_secs`** — a leftover from the deleted Tk UI. It sat in the
  config and was settable through the API, but **nothing read it**: a knob that
  did nothing. Gone from the defaults, the settable allowlist and the info
  payload.

## [v4.12.1] — 2026-07-12 — Two dead bases removed; the checker was too trusting

**Hallowed Sceptre** and **Dark Staff** don't drop. They sit in the game's item
table but no longer appear in the game — the owner searched in-game and found
neither. Every rule naming them was picking up nothing.

### Fixed
- **Removed both bases** from the rare-gear recipes, the base-type lists, and
  `game_data.json` (which the app pulls at launch — leaving it stale would have
  put them straight back). Replacements are the highest bases that actually drop:
  - *Sceptre* — Wrath (49), Shrine (26), **Omen (16)**
  - *Staff* — Permafrost (75), **Reflecting (70)**, Ravenous (65)
- **The health check was too trusting and said this was fine.** It treated "the
  name exists in the game's item table" as proof a base is real. It isn't: the
  table keeps legacy definitions and even `[DNT]` dev placeholders
  (`[DNT] Driftwood Oar`). A base must now pass **both** tests — the name exists
  **and** NeverSink lists it as dropping — and failing the second is a **critical**
  finding, not the shrug it used to be.

  This is exactly the check that would have caught these two, and it excused them
  instead.

## [v4.12.0] — 2026-07-12 — Game-data health check, in the app

PoE2 renames stats and removes bases every patch. When it does, your rules still
*look* correct but match **nothing** — the bot silently walks past loot, with no
error anywhere. Nine rules were dead exactly this way (the three Evasion fracture
rules had never worked, not once). It is the only failure in this app that is
completely invisible.

### Added
- **Game data health** (Settings). Compares every stat id, weight and base name
  your rules depend on against the game's own mod and item tables, and tells you
  in plain words:
  - *"✓ Your rules match the current patch"*, or
  - *"⚠ 3 rules may be picking up nothing"* — naming each one and what uses it.

  It **runs automatically at launch** (in the background, ~9 MB cached for 12
  hours) and puts a **warning banner on the Generate tab** if anything critical
  turns up. It only ever reports — it never edits your data. A failed fetch falls
  back to the cached copy and never blocks a launch.

  The engine moved into the app (`data/game_data_check`) so it ships in the
  `.exe`; `tools/check_game_data.py` is now a thin CLI over the same code.

- **Preview staleness banner.** Preview renders your *last generated* pickit, and
  quietly showing a 14-hour-old file from a previous version reads as a bug — it
  did to the owner, who wrote the spec. It now says so:
  - *"⚠ This preview was generated by v4.11.5 — you're now on v4.12.0. It does
    not include your current rules. Press ⚡ Generate to rebuild it."*
  - or, for an old-but-current-version run, *"Showing your last run from 3 hours
    ago — regenerate to apply any setting changes."*

## [v4.11.7] — 2026-07-12 — One Magic & Rare section, not two

### Fixed
- **The rare-gear rules now live inside the Magic & Rare section** instead of a
  separate one. Both are managed from the same Magic & Rare tab, so the Preview
  sidebar showing a 2-rule "MAGIC & RARE" next to a 51-rule
  "RARE GEAR — WEIGHTED…" looked broken. It's now one **MAGIC & RARE** section
  with all **53** rules (2 flasks + 51 rare-gear), which is what the code
  originally intended. The per-slot sub-headers inside are unchanged.
- The old section title was also long enough to be **truncated** in the sidebar.
- **Long section names now show in full on hover** (title tooltip), so anything
  clipped at 20 characters — e.g. "REGULAR TABLETS (ALL…" — is still readable.

## [v4.11.6] — 2026-07-12 — The "Gear floor" was actually the currency floor

### Fixed
- **Renamed "Gear floor" → "Currency & items floor".** The label was wrong and
  actively misleading. That slider does not gate rare gear at all — it gates
  **currency, essences, runes, fragments, omens, delirium, catalysts, abyss,
  soul cores, idols, uncut gems, support gems, expedition and waystones**
  (everything that is not a unique). Rare-gear rules are *scored* (WeightedSum),
  not priced, so no value floor has ever touched them.

  This wasn't cosmetic: with the slider at 30 Ex — a reasonable number if you
  believe it only affects gear — a real run silently commented out **96 runes,
  70 essences, 24 idols, 23 uncut gems and 21 delirium items**. Core currency
  (Divine/Exalted/Mirror) is always-pick and was never at risk.

  The generated `.ipd` header already described it correctly
  (`Threshold: N ex (currency/items) | N ex (unique gear)`) — the UI was the
  odd one out.
- The **Unique floor** description now names what it covers (unique weapons,
  armours, accessories, flasks, charms, jewels, relics).

## [v4.11.5] — 2026-07-12 — Whitelist the new ring bases (latent gap)

### Fixed
- The five ring bases added in v4.11.4 — **Biostatic**, **Tenebrous**,
  **Penumbra**, **Gloam** and **Dusk** — were missing from
  `VALID_EQUIPMENT_BASES`, the validator's base-name whitelist. Nothing broke
  today, because rare and fracture rules carry no quality/sockets gate and the
  validator skips the base check for those — but the gap would have surfaced the
  moment a gate was added. Now whitelisted.
- **New guard test** (`test_every_base_we_name_is_in_the_validator_whitelist`):
  every base named by a rare-gear recipe or a Fracture base override must be in
  the whitelist, so a typo or a new base can't slip through silently again.

## [v4.11.4] — 2026-07-12 — Rings get fracture targets

Rings were the last big empty slot in the Fracture tab. Researched the full ring
affix pool from the game's mod database — **34 stats can naturally roll on a
ring, and every one of them exists in the bot's ModsList**, so there was never a
technical blocker; nobody had built the targets.

### Added
- **Three ring fracture targets** (36 rules):
  - **Resistance** (S) — resistance is the *highest-level affix a ring can roll*
    (lvl 82), and rings are the game's main resistance slot. Chaos res (lvl 81)
    is the scarcest defence in the game.
  - **Added attack damage** (S) — rings roll a **full tier above gloves**
    (Lightning 60-71 vs the glove cap of 48-59), making ring the best flat
    added-damage slot in the game.
  - **Item Rarity** (A+) — the MF market; rarity is worn twice.
- **Six ring bases**, chosen by implicit rather than item level:
  **Biostatic** (+1% to all *maximum* resistances — the best ring implicit in the
  game), **Gold** (rarity), and the four **modifier-count rings** —
  **Tenebrous** (−2 prefix/+2 suffix), **Penumbra** (+2/−2), **Gloam** (−1/+1),
  **Dusk** (+1/−1). Those four bias which affix *type* the ring can carry, which
  is exactly what you want when fracturing for one specific mod: resistances are
  suffixes, added damage and rarity are prefixes.

### Changed
- **Rare Ring recipe: Amethyst → Biostatic.** Amethyst is an ilvl-20 base whose
  +7-13% chaos-res implicit is strictly worse than the chaos-res *suffix* the
  recipe already scores (24-27%). Biostatic is the highest ring base (ilvl 52)
  and grants max resistances.
- Attributes stay excluded from rings (owner rule); Life, accuracy, cast speed,
  leech and regen are filler in this slot and are not fracture targets.

## [v4.11.3] — 2026-07-12 — Jewels and Charms dropped from Fracture

### Changed
- **Jewels and Charms are gone from the Fracture tab.** They had no fracture
  targets and never will (owner call) — they only sat there as empty rows.
  The tab now lists 19 item classes instead of 21. A test bans them from
  creeping back in.
- Unaffected: **unique Jewels and Charms still price normally** in the Economy
  tab. This only removes them as fracture targets.

## [v4.11.2] — 2026-07-12 — Four dead fracture rules fixed (evasion, elemental)

A new game-data checker (`tools/check_game_data.py`) compares our stat ids,
weights and base names against the game's own mod and item tables. On its first
run it found four Fracture rules that could never match anything.

### Fixed
- **The three Evasion fracture rules** (body, helmet, boots) used the stat id
  `evasion_rating`, which **no craftable affix in the game grants**. Flat Evasion
  is `local_base_evasion_rating` — the mod that rolls the exact 262-300 those
  rules quote. Evasion was always in the game; our id for it was wrong, so the
  rules silently matched nothing. Same renamed-id family as the body-Spirit fix.
- **The elemental-damage fracture rule** used `elemental_damage_+%`; the only
  craftable elemental affix is `elemental_damage_with_attack_skills_+%` (which
  the rare-gear weapon recipes already scored correctly).

### Added
- **`tools/check_game_data.py`** — fetches the live GGPK mod dump and item table
  and flags renamed/removed stat ids, weights that disagree with their documented
  T1 max-roll, and base names that no longer exist. It reports for human review
  and never edits data.

### Verified
- All 67 engine stat ids now exist as craftable affixes; all 188 rare-gear
  weights match their documented rolls; all 53 base names still exist in the game.

## [v4.11.1] — 2026-07-12 — Copy buttons on the Magic & Rare tab

Quality-of-life: get the rare-gear rules out of the app and into your pickit
(or a chat) without hand-selecting text.

### Added
- **Copy stats** on each slot card — copies the scored-stat list (label,
  weight, bot stat id) as tab-separated rows, ready to paste into a sheet.
- **Copy rules** on each slot card — copies that slot's exact `.ipd` rule lines.
- **Copy all rules** in the tab header — grabs all 51 rare-gear rules at once,
  each slot under its own header, in the same order the pickit writes them.

## [v4.11.0] — 2026-07-12 — Rare gear goes LIVE: all 17 slots, in every pickit

The rare-gear WeightedSum recipes are done and **written into every generated
pickit**. All 17 gear slots — armour, jewellery, off-hand and every weapon —
now score rare drops by what actually sells, so the bot keeps the rares worth
picking up and leaves the vendor trash on the floor.

### Added
- **Rare gear in generated pickits.** The full 17-slot recipe set (Body Armour,
  Helmet, Gloves, Boots, Amulet, Ring, Belt, Focus, Quiver, Bow, Crossbow,
  Quarterstaff, Spear, Mace, Sceptre, Wand, Staff) is written into every `.ipd` —
  51 rules, three bases a slot. Each rule keeps a rare only if it clears a
  **WeightedSum** of the stats that matter for that slot (threshold 250 ≈ 2.5
  perfect rolls).
- **Master on/off switch** at the top of the Magic & Rare tab — turn the whole
  rare-gear set off and regenerate to get a pickit without it.
- **Headless `--cli` mode** now writes the rare-gear section too.
- **LIVE badges** on every slot card, replacing the draft marker.

### Recipes
- Every slot was built from its own poe.ninja ladder meta and the game's mod
  database (2026-07-12), not cloned from a template. Weapons score weapon-local
  **crit chance** (percent scale) alongside crit multiplier, added damage, skill
  levels and the "Surpassing" +1-projectile chase; the wand's **+4 to all spell
  skills** and the staff's **+5–6** are in. All 63 scored stat ids are verified
  present in the bot's ModsList.

### Fixed
- Five renamed fracture stat ids that silently never matched — projectile skill
  levels on bows/crossbows, +bolts, quiver bow-damage, and body flat-Spirit —
  now use the engine's real current ids.
- Amethyst Ring added to the base-type validator whitelist.

## [v4.10.0] — 2026-07-12 — Rare gear recipes: the armour set, in draft

The Magic & Rare tab starts showing its real content: per-slot **WeightedSum
recipes** for rare gear, built stat by stat and audited against the game's
own mod database and the live poe.ninja ladder meta.

### Added
- **Recipe cards in Magic & Rare.** Body Armour, Helmet, Gloves and Boots now
  show their full draft recipe: the WeightedSum threshold, minimum item tier,
  the exact bases (one rule per base), every scored stat with its weight and
  bot stat id, and the exact rule lines — ready to copy. Slots still being
  designed say so. Sidebar counts show which slots are drafted.
- **The four armour recipes themselves.** Each slot got its own recipe from
  what actually sells (poe.ninja Runes of Aldur ladder, 124k characters):
  - *Body Armour* — Life (the game's biggest roll, T1 214) + flat Spirit +
    4 resistances + the body-exclusive %ES tier.
  - *Helmet* — +2 Minion Skills (helmet-exclusive), Rarity, global crit,
    Life/res backbone.
  - *Gloves* — Attack Speed, +2 Melee Skills, Crit Damage Bonus, Rarity,
    Life/res backbone.
  - *Boots* — Movement Speed (30/35 dominate by design), Life, Rarity,
    full res + ES package.
  Every weight = 100 ÷ the stat's live T1 max-roll; every stat id verified in
  the bot's ModsList.

### Important
- **These recipes are DRAFT — they are NOT in generated pickits yet.** The
  jewellery, off-hand and weapon slots are still being built; the whole set
  ships into real pickit output together after a final review. Generated
  `.ipd` files are unchanged by this release.

## [v4.9.3] — 2026-07-12
### Fixed
- **Fracture "spirit body" rules could never match.** The "+57-61 to Spirit"
  body-armour target was mapped to `local_spirit_+%` — a SCEPTRE-only percent
  stat. Bodies roll FLAT Spirit (`base_spirit_from_equipment`, body/amulet
  only — confirmed in the game's mod database). The six emitted body-Spirit
  rules now use the right id and actually fire.

## [v4.9.2] — 2026-07-12 — Every Fracture target now emits real rules

### Fixed
- **The five remaining "unverified" Fracture targets are verified and wired.**
  PoE2 renamed the display text to "Critical Damage Bonus", but the engine
  kept the legacy stat ids — confirmed in the game's own mod database (GGPK
  dump, tier rolls match each target exactly) and re-checked against the
  bot's ModsList:
  - Staff *Critical Spell Damage Bonus* → `base_spell_critical_strike_multiplier_+` ≥ 53
  - Gloves *Critical Damage Bonus* → `base_critical_strike_multiplier_+` ≥ 30
  - Quiver *Critical Damage Bonus for Attack Damage* → `attack_critical_strike_multiplier_+` ≥ 30
  - Gloves *Adds Phys/Fire/Cold/Lightning to Attacks* → one rule with an
    OR-group of max-roll gates (≥ 18 / 33 / 25 / 48 — T2 minimums)
  - Belt *single-element Resistance* → one rule with an OR-group
    (elemental ≥ 36, chaos ≥ 20)
- The Fracture section now emits **441 rules, zero validation errors, zero
  placeholders** (was 411 rules plus 30 `UNVERIFIED_STAT_ID` example lines).

## [v4.9.1] — 2026-07-11
- **Floor sliders now drag up to 50** in every unit (Exalt / Chaos / Divine) —
  they were capped at 5, which made higher value floors impossible to reach by
  dragging. Typing a value still works exactly as before.

## [v4.9.0] — 2026-07-11 — History gets the Workbench treatment

The run-history page was rebuilt into a proper market-history view. Pure UI —
no engine changes, generated pickits are byte-identical.

### Redesigned
- **The run chart is a real chart now.** Gradient area fill, a dotted
  average line, the peak run marked with a diamond, and the latest value
  labeled right on the chart — no hover needed to know where you stand.
  Hovering snaps a crosshair to the nearest run with a richer tooltip:
  rules, ▲/▼ change vs the previous run, skipped, divine rate, top item.
- **Divine-rate sparkline** under the run chart — same timeline, its own
  scale. Watch "1 Div = X ex" drift across the league at a glance.
- **Tiles learned deltas.** "Last run rules" shows ▲ +58 / ▼ 12 vs the
  previous run in green/red; "peak rules" shows the date it happened.
- **The table tells you what moved.** New **Δ column** — a green `+335` /
  red `-5` pill per run vs the run before it — and friendly dates
  ("7 h ago"; the exact timestamp is on hover).

### Unchanged on purpose
- ↻ Re-run with these floors, Clear history, and the 50-run log all work
  exactly as before.

## [v4.8.0] — 2026-07-11 — Shortcuts, settings backup, one-click diagnostics

### Added
- **Keyboard shortcuts.** `Ctrl+1–9` switches tabs (Generate → Magic & Rare),
  `Ctrl+F` focuses the current tab's search box, `Ctrl+G` still generates.
- **Export / import settings (Settings).** Your whole setup — floors, toggles,
  profiles, exclusions — saved to one JSON file and restorable on any PC.
  Imports only accept known settings keys and apply instantly, no restart.
- **Copy diagnostics (Debug).** One click copies version, settings summary,
  cache state and the recent log — paste it when reporting a problem.

## [v4.7.0] — 2026-07-11 — Backup restore + new-league detection

### Added
- **Restore a backup (Settings).** The app already keeps rotating `.ipd`
  backups on every generate — now there's a list (date · size) with a
  one-click **Restore**. The pickit being replaced is itself backed up first,
  so a restore can never lose anything; `latest.ipd`, Preview, and (if
  auto-copy is on) your bot folder are all updated.
- **New-league banner (Generate).** When poe.ninja starts listing a league
  the app has never seen — league launch day — a banner offers a one-click
  **Switch**. Dismiss it and it stays dismissed.

---

## [v4.6.0] — 2026-07-11 — See what changed, redo what worked

Three quality-of-life features for the daily generate loop.

### Added
- **"🆕 Changed" filter in Preview.** After a generate, rules the run added are
  tinted green, a new filter chip shows only them, and items that dropped out
  of the pickit are listed struck-through — so you can see exactly how the
  market moved your pickit instead of reading a one-line summary.
- **"Re-run with these floors" in History.** Expand any past run and one click
  restores that run's exact value floors (switching Adaptive floors off so
  they stick) and generates again.
- **Auto-floor preview.** With Adaptive market floors OFF, changing "Keep top
  N%" now shows what the floors *would* be ("uniques ≥ 2.4 ex · everything
  else ≥ 0.8 ex") without applying anything — no more enabling it blind.

### Housekeeping
- Removed ~350 lines of dead code left from the frameless-window era (hidden
  title bar, resize handles, their JS and API endpoints) plus stale docs and
  an obsolete project skill. No behavior change.
- Website now shows the actual app (Generate-console screenshot) and the
  v4.5.0 ground-filtering feature.

---

## [v4.5.0] — 2026-07-11 — "Exile's Workbench" + smarter ground filtering

The look was rebuilt to the warmer **Workbench** design (aged brass & bone,
serif headings), and — more importantly — the pickit engine got real fixes
found by running the generated file in the actual bot.

### Pickit engine (the important part)
- **Item level now filters on the ground.** Base rules moved `[ItemLevel]`
  before the `#` — the bot reads game memory, so it knows a ground item's
  level before pickup (its own editor lists Item Level under BEFORE
  IDENTIFY). Low-level craft/exceptional bases are simply never picked up,
  instead of being hauled home, identified, and vendored.
  `[Type] == "Gold Ring" && [Rarity] == "Normal" && [ItemLevel] >= "75" # [StashItem] == "true"`
- **Fracture rules gate `[ItemTier] >= "4"`** before the `#`, so low-tier
  magic/rare bases stay on the ground too.
- **Fixed useless `>= "1"` thresholds** on ten fracture targets — the parser
  was reading the "1" out of tier tags like "T1 35–38%". Quiver crit is now
  ≥ 30, bow damage ≥ 43, sceptre spirit ≥ 56, and so on.
- **Added-lightning targets now gate on the maximum roll** (the minimum is 1
  on every tier, so it filtered nothing): quivers ≥ 48, one-hand weapons
  ≥ 157, two-hand ≥ 239 — verified live from Craft of Exile.
- **Duplicate rules deduped** (the sceptre skill-level pair emitted both
  ≥ 4 and ≥ 3 versions of the same rule).
- **"Aldur's Legacy" un-flagged** — it's a live Runes of Aldur league unique
  the pickit should (and does) grab; the old "deprecated" warning was bogus.
  Validation is now 100% clean.

### Redesigned — "Exile's Workbench"
- Aged **brass & bone palette** with Georgia serif headings (the approved
  Codex mockup), now the default and Relic theme; Frost/Blood retuned to
  match. Active nav tab is a thin brass left-border.
- **Generate is a "pickit recipe"**: each threshold is a labeled row with a
  plain-English description ("Exceptional base roll, 21–30%"), a big brass
  value, and a **drag-slider track** — the −/+ steppers are gone.
- **Last-run panel** with a status seal (◷ → ✓/✗ live), checklist and run
  stats; **market strip** (live league · divine rate · last-run moves ·
  refresh) under the console.
- **Top picks show real poe.ninja item art** instead of emoji, and each value
  reads in **exalt + divine + chaos**.
- Currency unit picker is a proper dark brass pill (no more white OS popup).

---

## [v4.4.0] — 2026-07-10 — "Exile's Ledger" UI overhaul

A complete visual redesign, built from an approved mockup. Every control and
element id was preserved — **no feature was removed**.

### Redesigned
- **Left rail navigation.** The old top tab-bar is now a 238px rail: brand
  sigil + version, three sections (Operate / Loot Rules / System) with all 11
  tabs always visible, live count badges (Preview / Economy / Fracture), a
  segmented theme switcher, and the Discord / Exiled Bot links pinned to the
  bottom.
- **Generate is now a console.** League + profile row, a "Build today's pickit"
  hero with a full-width Generate action, four **dial tiles** with −/+ steppers
  and fill tracks, and an output row.
- **Live "prices fetched X ago" indicator** in the top bar, so you can see at a
  glance how stale the economy data is.
- **LAST RUN checklist** (fetched → assembled → validated → written) with live
  values, plus KPI tiles (active / skipped / valid) that survive a restart by
  restoring from your newest history entry.
- **"Economy — top picks right now"** table under the console: the five most
  valuable items the run picked up, with their type.
- **New palette — obsidian ground, gold for value, steel for active state** —
  now the default theme. Frost and Blood were retuned to the same family; all
  three themes still work everywhere.
- The same design language was extended to **every remaining tab** — panels,
  section headers, and data tables (rounded item thumbs, monospace tabular
  values with a gold unit suffix, green `keep` / muted `skip` pills).

### Changed
- **Exceptional-base gates now state their real ranges.** Base quality is
  21–30% and base item level is 80–82 (that's what those bases actually roll).
  The dials clamp to those ranges, their fill tracks map across each dial's own
  range, and the Generate dials stay two-way synced with the Settings inputs.
  Configs holding an out-of-range legacy value are clamped on load.

### Fixed
- **History table columns never lined up with their headers.** A duplicate
  `.hrow` rule applied `display:flex` to a `<tr>`, breaking it out of table
  layout. (Pre-existing bug, not introduced by the redesign.)
- **The History chart used a hard-coded gold**, so its fill was the wrong colour
  under the Frost and Blood themes. It now follows the palette.
- Panels on Preview / Economy / Debug reclaim the ~65px of height the old top
  nav used to occupy.

---

## [v4.3.6] — 2026-07-10
- The window now **remembers its position** as well as its size, and reopens
  there — unless that spot is on a monitor you've since unplugged, in which
  case it re-centers.
- **Click any single rule line in Preview to copy just that rule** (text
  selection still works normally).
- New **"Bot folder"** button in Preview opens your configured Exiled Bot folder.

## [v4.3.5] — 2026-07-10
- Validation errors in Preview are now a **clickable list — click one to jump
  straight to that line** and flash it.
- New **"Open folder"** and **"Copy path"** buttons for the generated `.ipd`.

## [v4.3.4] — 2026-07-10
- **Fixed the multi-monitor freeze.** The window used a frameless custom title
  bar, which borderless WinForms windows mishandle — it would freeze or get
  stuck in the taskbar on secondary screens. It now uses a native OS window
  frame, so Windows owns minimize/restore/focus/multi-monitor behaviour.

## [v4.3.3] — 2026-07-10
- **Verified 33 Fracture stat ids** against the bot's own ModsList, taking the
  Fracture section from 94 to **417 emitted rules**. Five targets that have no
  clean single stat id remain honest placeholders rather than guesses.
- Set Per-Monitor-V2 DPI awareness (correct hygiene; it was not the cause of
  the freeze — see v4.3.4).

## [v4.3.2] — 2026-07-10
- Restructured `data/` so every module lives in its own folder (import paths
  unchanged).
- Added the `data/rare` package: the verified Rare stat menu as code, one file
  per section, every id validated against the bot's ModsList.

## [v4.3.1] — 2026-07-09
- Fracture examples now show the **real emitted rule** with its concrete
  threshold, instead of a `<value: …>` placeholder that the bot's validator
  rejected when pasted.

## [v4.3.0] — 2026-07-09
- **The loot filter now shows every item the bot acts on.** Items that were
  salvaged or stashed unidentified were previously hidden.

## [v4.2.9] — 2026-07-09
- Flasks moved from Fracture to the new **Magic & Rare** tab.

---

[v4.21.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.21.0
[v4.20.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.20.0
[v4.19.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.19.1
[v4.19.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.19.0
[v4.18.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.18.3
[v4.18.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.18.2
[v4.18.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.18.1
[v4.18.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.18.0
[v4.17.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.17.3
[v4.17.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.17.2
[v4.17.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.17.1
[v4.17.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.17.0
[v4.16.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.16.0
[v4.15.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.15.0
[v4.14.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.14.0
[v4.13.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.13.0
[v4.12.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.12.4
[v4.12.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.12.3
[v4.12.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.12.2
[v4.12.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.12.1
[v4.12.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.12.0
[v4.11.7]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.7
[v4.11.6]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.6
[v4.11.5]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.5
[v4.11.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.4
[v4.11.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.3
[v4.11.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.2
[v4.11.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.1
[v4.11.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.11.0
[v4.10.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.10.0
[v4.9.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.3
[v4.9.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.2
[v4.9.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.1
[v4.9.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.9.0
[v4.8.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.8.0
[v4.7.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.7.0
[v4.6.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.6.0
[v4.5.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.5.0
[v4.4.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.4.0
[v4.3.6]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.6
[v4.3.5]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.5
[v4.3.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.4
[v4.3.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.3
[v4.3.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.2
[v4.3.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.1
[v4.3.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.3.0
[v4.2.9]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.2.9
