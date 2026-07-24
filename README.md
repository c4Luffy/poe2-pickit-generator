<p align="center">
  <img src="docs/logo.png" width="112" alt="ExileBot 2 Pickit Generator mascot">
</p>

<h1 align="center">ExileBot 2 Pickit Generator</h1>

<p align="center">
  <strong>Build a pickit you can understand.</strong><br>
  Turn live Path of Exile 2 prices into a validated Exiled Bot 2 pickit—or translate an existing <code>.ipd</code> into an in-game loot filter with every unavoidable difference reported.
</p>

<p align="center">
  <a href="https://github.com/c4Luffy/poe2-pickit-generator/releases/download/v4.41.26/ExileBot2PickitGenerator.exe"><img alt="Download v4.41.26 for Windows" src="https://img.shields.io/badge/Download-v4.41.26-c99a4a?style=for-the-badge&labelColor=171411&logo=windows11&logoColor=e8e0d3"></a>
  <a href="https://github.com/c4Luffy/poe2-pickit-generator/releases"><img alt="Total downloads" src="https://img.shields.io/github/downloads/c4Luffy/poe2-pickit-generator/total?style=for-the-badge&label=Downloads&labelColor=171411&color=829d78"></a>
</p>

<p align="center">
  Portable <code>.exe</code> · No installer · No Python · No game-account access
</p>

<p align="center">
  <a href="https://c4luffy.github.io/poe2-pickit-generator/">Website</a> ·
  <a href="https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.41.26">Release notes</a> ·
  <a href="CHANGELOG.md">Changelog</a> ·
  <a href="https://discord.gg/T7DU3Afve6">Discord</a> ·
  <a href="https://github.com/c4Luffy/poe2-pickit-generator/issues">Issues</a>
</p>

![Real ExileBot 2 Pickit Generator v4.38.2 Generate screen](docs/shots/01-generate-v4382.png)

<p align="center"><sub>Real running-app capture · Generate · captured on v4.38.2</sub></p>

> [!IMPORTANT]
> **Using v4.20.0 or v4.21.0? Update manually once.** Close the old app, [download v4.41.26](https://github.com/c4Luffy/poe2-pickit-generator/releases/download/v4.41.26/ExileBot2PickitGenerator.exe), and open it. Your settings, profiles, and Exiled Bot folder stay in place. Later in-app updates work normally.

## Start here

There are two simple ways to use the app.

### I need a pickit

Choose your league and a loot preset, adjust the price floors you want, then select **Generate**. The app fetches current poe.ninja prices, writes and validates the `.ipd`, and checks that Exiled Bot 2 is reading the same profile.

**Choose a league → Pick a preset → Set your floors → Generate**

### I already have a pickit

Drop any Exiled Bot `.ipd` into the window—a hand-made file, a friend's pickit, or one created by another tool. The app reads it, explains what the game can represent, and saves a translated Path of Exile 2 loot filter.

**Drop the `.ipd` → Review the report → Save the `.filter`**

## Generate in four steps

1. **Pick your league.** Fetch current Path of Exile 2 prices from poe.ninja.
2. **Choose a preset.** Start with Vacuum, Balanced, Strict, Chase, or Currency only.
3. **Set your floors.** Adjust what is worth stopping for, or use Auto-floor.
4. **Generate and check.** Write the files, validate thousands of rules, and confirm the active profile.

## Create your filter

**Create your filter** reads any Exiled Bot pickit and translates its rules into an in-game loot filter. When Path of Exile's filter language cannot represent a bot-only condition, the conversion report says exactly what happened.

- **Converted:** represented directly in the game filter.
- **Shown wider:** a bot-only check was removed, so the item remains visible.
- **Untranslatable:** listed with its source line and the reason.

Your source `.ipd` is **read-only**, is never modified, and is never uploaded. If it changes after the filter was created, the app warns you.

> [!WARNING]
> **Hide everything else starts OFF, and remembers your choice.** Gold is never hidden. Leave it **off while botting** — hidden ground labels can stall pickup. Always review any translation warning before turning it on.

## Item Check

Hover an item in Path of Exile 2, press `Ctrl+C`, then paste it into **Item Check**.

You receive one of three verdicts:

- **Picked up**
- **Ignored**
- **Depends on the rolls**

Each verdict includes the deciding rule and a practical next step.

> [!NOTE]
> **The verdict is not a simulation.** Item Check runs the same generator that writes the `.ipd` and shows the actual emitted line. With the same current settings, Item Check and the generated pickit cannot disagree.

Rare gear stays honest. If no recipe covers the base or its slot is disabled, the answer is a definitive no. When a recipe does cover it, Item Check shows the scored stats and threshold because the final roll check happens inside Exiled Bot. Fractured items show the actual target mods.

## Know which file does what

| Output | Used by | What it controls | Important note |
| --- | --- | --- | --- |
| `.ipd` pickit | Exiled Bot 2 | Which items the generated pickit targets | `pickit.ini` must point to the generated filename |
| `.filter` loot filter | Path of Exile 2 | Which ground labels are visible and how they look | Select it again under **Options → Game → Filters** after every save or regeneration |
| On-screen conversion report | You | What converted, was shown wider, or could not translate | It is a report, not a third output file |

<details>
<summary><strong>See a generated rule sample</strong></summary>

```text
// PoE 2 pickit — generated from live poe.ninja prices
[Type] == "Divine Orb" # [StashItem] == "true"
[Type] == "Stellar Amulet" && [Rarity] == "Normal" && [ItemLevel] >= "82" # [StashItem] == "true"
[Type] == "Heavy Belt" && [Rarity] == "Unique" # [UniqueName] == "Headhunter" && [StashItem] == "true"
[Category] == "Waystone" && [WaystoneTier] >= "10" # [StashItem] == "true"
```

</details>

## Safe, local, and recoverable

- Imported pickits are never modified or uploaded.
- Generated output stays on your PC.
- Rotating backups protect output before replacement.
- Hand-made ANSI pickits decode correctly.
- Unusual item-name characters are excluded and reported instead of disappearing silently.
- The app never asks for your Path of Exile account.

Windows SmartScreen may ask for confirmation because this free community executable is not code-signed. You can verify the release with its [published SHA-256 checksum](https://github.com/c4Luffy/poe2-pickit-generator/releases/download/v4.41.26/SHA256SUMS.txt).

### Three important usage notes

1. **Check `active_profile`.** A mismatch can make Exiled Bot 2 read an older pickit. The connection check verifies it.
2. **Reselect the optional game filter after every save or regeneration.** Choose it again under **Options → Game → Filters**. Exiled Bot reads the `.ipd`, not the `.filter`.
3. **Turn Hide everything else off while botting.** Hidden ground labels can stall pickup.

## Current release: v4.41.28

### Every rule builder now escapes quotes in item names

- **A unique whose name or base type contained a literal `"` would have corrupted its pickit rule.** `build_unique_lines` interpolated the poe.ninja `name` and `baseType` straight into the rule with no escaping — the one builder the v4.41.18 audit fixed for `force_names` but left with raw quoting, and that release admitted quote escaping was "still incomplete elsewhere." A quote in either value would unbalance the rule and Exiled Bot's validator would reject the whole file. Both now go through `_quote_ipd`, matching every other builder. The uncut-gem builder (external names, but regex-gated so a quote can't reach it) is wrapped too, so "every builder escapes external names" is now literally true. No live item has a quote today; this closes the latent case.
- **Regression test added**: a unique whose name and base both contain `"` still produces a rule whose structural quotes stay balanced.

### v4.41.27 — Scheduled and piped runs stop crashing on a non-UTF-8 console

- **A headless `--cli` / `--regenerate` run aborted before writing a single file on a console that wasn't UTF-8.** Both modes print progress with `✓` and `·`, and on a Windows console that isn't UTF-8 — cp1252, which is exactly what Task Scheduler and a redirected pipe (`> log.txt`) hand you — the *first* ticked category raised `UnicodeEncodeError` and killed the run before any output was generated. `--regenerate` is documented for Task Scheduler, so its intended home was the one that broke it.
- Both entry points now wrap `stdout`/`stderr` as UTF-8 with `errors="replace"` (the same wrapper `tools/check_game_data.py` already uses), so an exotic console degrades a glyph instead of aborting the run. Only a stream that isn't already UTF-8 is touched, so a normal terminal is unaffected.

### v4.41.26 — Concurrent writes stop failing, plus a pass of visual polish

- **Two runs writing the same output collided and the write failed.** Every generated file — the `.ipd`, the `.filter`, the item report and the bot's own `pickit.ini` — used a temp file named after its target, so two runs writing the same output shared one temp name. That's an ordinary overlap here, because the app ships `--regenerate` for Task Scheduler: the GUI generating while the timer fires. **Reproduced** with two writers on one path — the old code raised a Windows `PermissionError`, so the write simply failed. Each write now gets its own uniquely named temp file (the protection `config.json` already had), and the same test passes with no errors and nothing left behind.
- **Visual polish, no layout changes.** KPI tiles on Preview, History and Debug gain a hairline accent, a little depth and a lift on hover, so a row of numbers reads as one panel. Section headings inside cards gain a small accent bar, making long pages easier to scan. All driven by the theme's own accent colour, so every theme keeps its voice.
- **The sidebar fits again.** Trimming 3px of padding per nav button reclaimed **~104px** — enough that the theme picker and the Discord / Exiled Bot links no longer fall off shorter windows.
- Considered and **rejected**: zebra striping on the Economy and History tables — both interleave hidden rows, so the banding would have striped rows you never see.

### v4.41.25 — The Exceptional tab explains its own exceptions

- **Belts and quivers looked like they didn't belong.** That tab is explained entirely by the extra rune socket an exceptional base rolls — 3 sockets for body armour and two-handers, 2 for gloves, boots, shields, foci and one-handers. Belts and quivers take **no runes at all**, so seven bases sat in a list whose stated premise didn't apply to them, with nothing saying why.
- They're listed because they're still the **strongest base of their slot to craft on** — the tab's actual subject. The card now says so directly instead of leaving you to assume a mistake.
- Wording only: no base added, removed or re-gated, and no generated rule changes.

### v4.41.24 — A gate you couldn't lower, and two more counts that lied

- **Create your filter reported "11 disabled rules" for a pickit with nothing disabled.** All eleven were the embedded syntax guide's own documentation — its `// Example:` lines and its Special Flags legend — which are comments carrying a real action token, so the counter read them as rules you had switched off. This is the **fourth** place the guide added in v4.41.18 produced a wrong number. The exclusion is narrow: a genuinely commented-out rule still counts, including one using `[Salvage]`/`[StashUnid]` or written without the `#` split. Verified both ways — the real pickit now reports **0**, and three deliberately disabled rules still report **3**.
- **The Craft tab couldn't lower the item-level gate on three jewellery bases.** Solar Amulet, Gold Amulet and Gold Ring had no data row, so the stepper's minimum fell back to a hardcoded `75` — while the control promises to floor at "this base's own drop level". They drop from **30**, **35** and **40**, so everything below 75 was unreachable. Fixed from the game's own base-item table.
- **History under-reported past 30 runs.** The app keeps the last **50** and the tab says so, but only read back 30 — so "runs logged" stuck at 30 and **"peak rules" could miss a real peak** in the oldest 20 kept runs.
- Also checked and healthy: **Item Check** (Waystones, `Superior` bases and Uncut Gems all still answer correctly), **Fracture** (79 targets, 0 unverified stat ids), **Settings** and **Setup guide**.

### v4.41.23 — Two exceptional staff bases stop rendering blank

- **Sanctified Staff and Paralysing Staff showed as empty cards** on the Exceptional tab — an icon and a name and nothing else, while every other one of the 121 bases showed at least an item level.
- **Cause:** both joined the staff slot back in v4.39.1 (replacing two that never drop) but were never given a stats row, so the level fell back to `0` — which renders as nothing. It shipped that way for 13 releases.
- **Fix:** both now carry their real drop level (Sanctified **56**, Paralysing **52**), read from the game's own base-item table — the same authority the rest of the tab uses, and cross-checked against existing rows rather than guessed.
- Also checked the whole tab: the game-data drift checker reports **0 critical, 0 advisory**, and all 121 bases have artwork.

### v4.41.22 — Three UIs stop reporting skipped rules that were never skipped

- **Preview claimed "9 skipped" for a pickit with nothing disabled.** Those nine were the `// Example:` lines of the syntax guide that v4.41.18 began writing into every generated `.ipd` — they contain `[StashItem]` and start with `//`, so a bare substring test counted each as a rule you had switched off. The **"Skipped" filter** listed them as your disabled rules, and the rule total was inflated by nine.
- **The same miscount sat in three places.** It also fed the Generate tab's "skipped" tile and the `--cli` "Commented out:" total. All three now share one helper: a line counts as a rule only if it carries the `[StashItem]` action **and** the `#` identify split, and isn't a guide example.
- **The Chance tab shows the real outcome pool.** Each base lists every unique that shares it, dearest first, with live prices — so the tab's warning ("a Utility Belt is far more often an Ingenuity than a Mageblood") becomes visible data: Mageblood at ~328 div directly above the 5 ex and 1 ex outcomes. Built from data already fetched, so no extra network calls, and read-only so reading it can't toggle the base off.
- **Chance prices no longer flip units at random.** A ~46 ex unique rendered as a useless "0,1 div" while a 13 ex one correctly read "13,5 ex". Divine now appears only at 1 divine or more.
- **Pasted diagnostics are readable.** The report ended with 30 identical `INFO config saved` lines, pushing the one line that explained the problem off the end. Repeats collapse to `(x30)`, and any `ERROR`/`WARNING` survives even when older than the window.

### v4.41.21 — Prices load in the background, so the Economy tab opens instantly

- **The price fetch starts at launch instead of when you open Economy.** Opening the tab used to fetch 24 separate poe.ninja category price lists on the spot — five at a time, each with a back-off wait whenever poe.ninja rate-limited — and you watched "Loading prices…" while it finished. That same fetch now runs in the background shortly after the app opens, while you're still on Generate, so Economy is normally fully populated the moment you click it.
- **One fetch speeds up everything that reads prices.** They all share the same 15-minute cache, so **Generate**, the **Chance** tab and **Auto-floor** get the same head start — not just Economy.
- **Nothing else changes.** It's fire-and-forget: if the pre-fetch fails or you're offline, the tab loads exactly as before. Price freshness is unchanged, and **Refresh prices** still forces a live re-fetch. Tabs that never touched the network (Craft, Exceptional, Fracture, Magic & Rare, Preview, Item Check, History, Debug) were already instant.

### v4.41.20 — Economy tab overhaul: hover cards, value bars, collapsible groups

- **Hover cards on Economy rows.** Hover any item and a card shows its art, live price, 7-day trend, keep/skip status, and the exact pickit rule that catches it — so it's obvious at a glance what any row does. Unpinned, the card is a pass-through tooltip that never covers the row's own buttons; **click a row to pin it** into a stable panel with a Copy button and its own keep/skip toggle, closed by ✕, Esc, or a click away. It flips near the screen edges so it never spills off-screen.
- **Right-click a row to copy its pickit rule** instantly, without opening the card.
- **Value bars behind each price, log-scaled.** A faint fill reads as relative worth at a glance. Prices span huge magnitudes — a one-ex common versus a multi-thousand-ex chase item — so a linear fill flattened everything but the top few into identical slivers; the log scale spreads the low and mid range so every bar means something.
- **Collapsible Economy sidebar groups.** General, Equipment, Atlas and Always pick each fold with a click on their header, so the whole category list fits without scrolling. Headers are bigger and bold, with a caret and count.
- **No more accidental toggles.** Clicking a row no longer flips its keep/skip — only the keep/skip button does, so a stray click while reading the table can't silently drop a rule.
- **The Economy tab is faster.** The pickit-rule lookup behind hovers, right-click copy and the row Copy button is cached per item, so repeat interactions are instant instead of calling into the engine every time.
- **Generate is never silent.** A toast fires the moment a run starts and again when it finishes, with the rule count and time — whether you press Generate on the tab or via Ctrl+G.

### v4.41.19 — Tablets are priced live now, not hardcoded

- **Regular and unique tablets are no longer a hardcoded always-pick list.** poe.ninja added real pricing for both — Precursor Tablets (Overseer, Abyss, Breach, Ritual, Irradiated, Temple, Delirium; priced separately per rarity, Normal/Magic/Rare) and Unique Tablets (all nine) — so generated pickits now respect the normal value floor for tablets like every other market item, instead of force-picking every rarity regardless of what it's actually worth. Some are genuinely valuable — a Normal Ritual Tablet has been worth close to a Divine.
- **Both show up as their own Economy categories under Atlas**, matching how poe.ninja itself groups them, with live prices, 7-day trend arrows and per-item switches. Precursor Tablets are further grouped by tablet type, with each type's Normal/Magic/Rare rows kept together — the same idea as Exotic Bases grouping by gear slot.
- **The Economy sidebar now matches poe.ninja's own layout exactly** — section names, order, and item order within each section (General, Equipment, Atlas), checked directly against the live site. Waystones moved out of General into Always pick, since poe.ninja doesn't price it at all and every tier is always kept regardless of value.

### v4.41.18 — A full audit pass, four real findings

- **Literal quote marks are escaped in more rule builders, but not all of them.** The existing helper now protects standard formatted rules and the exchange pick-all path. No cached item currently triggers this edge case. The unique-rule `[Type]` and `[UniqueName]` fields still interpolate raw values in v4.41.18, so this path is not yet fixed everywhere.
- **The "always kept regardless of price" guarantee had a unique-payload blind spot.** Pinnacle keys and special items are meant to stay in the generated pickit at every price unless you disable them. The app and saved-settings regeneration now apply that protection if poe.ninja ever prices one through a unique-shaped payload; nothing currently triggers the edge case. The separate legacy `--cli` path still does not pass the same always-kept set.
- **A sort arrow claimed two static Economy views had sorted.** Clicking Value or 7-day change on Tablets or Exotic Bases painted an arrow even though those views keep their fixed section order. The arrow no longer appears where sorting does nothing.
- **The built-in syntax guide had never reached a generated file.** Its `[WeightedSum]`, `[IgnoreRitual]`, WeaponCategory and worked-example comments were written and tested, but neither real writer included them. Both writers now add the guide to generated `.ipd` files.

### v4.41.17 — Safer loot rules, rare-gear control, and clearer Economy views

- **Seventeen dead exotic-base rules are gone, and pinnacle keys stay enabled at every price.** Runic Fork, Ornate Ringmail, Glacial Fortress, Reflecting Staff, Perching Staff, the three Decree armours and the other unique-only bases never drop as plain white or rare items, so those rules could never fire. The generator still adds their uniques from poe.ninja. Reliquary keys, Crisis Fragments, Origin fragments, Simulacrum and Call of the Shadows now remain in the generated pickit regardless of price.
- **Economy puts all 20 boss keys in one Keys view.** It groups Crisis Fragments, Origin fragments, nine Reliquary Keys and Boss Invitations with live prices, including Raven's Reflection even though poe.ninja does not price it. The view reuses the same switches as Fragments, so nothing is duplicated; an unpriced item reads "No price · always kept". The old "Fragments & Keys" bucket is also split into Tablets, Wombgifts and Exotic Bases, with unique tablets separated and exotic bases grouped by gear slot from the game's own files.
- **Rare gear has a strictness dial.** Choose **Looser**, **Balanced**, **Strict**, or **Very strict** to scale the score cutoff for all 17 slots, then override any slot on its own. Recipes and stat weights stay the same; only the score a rare must clear changes. Each slot shows a real example built from its own stats, such as a T1 Life + T1 Spirit + T1 Fire resistance rare scoring about 300 and clearing 250.
- **Scheduled refreshes run without opening the window.** `python -m exilebot_pickit --regenerate` rebuilds the generated pickit from your saved floors, every switch, global and per-slot rare strictness, output folder and auto-copy setting. Add `--league "Name"` to override the league and point Task Scheduler at it.
- **Generate warns when poe.ninja returns a whole category empty.** The warning appears immediately instead of leaving that category unpriced without telling you. Waystones are allowlisted because poe.ninja never prices them.
- **What's new is visible, and Reset keeps your app appearance.** A rounded button under the app title opens the changelog. Reset still enables every toggle and clears the floors, but no longer changes the appearance you chose.

### v4.41.3 — Revert the Economy grouping

- **The item grouping added in v4.41.2 is removed.** It sounded tidy and made the tab worse to use. Every Economy category reads exactly as it did before.
- **Raven's Reflection keeps its artwork**, which shipped in the same release and is unrelated.

### v4.41.2 — Level families read as one thing

- **"Thaumaturgic Flux (Level 8…20)" is thirteen rows that read as one item**, and a value sort scattered them through the Economy table. Each family now sits in one block under a labelled rule, positioned where its best-priced member ranked. Sort by name for true level order; sort by value and they reorder inside the block.
- **Raven's Reflection has its artwork**, embedded from the game's own files — it has no poe.ninja price row, so the usual art fallback never fired for it.

<details>
<summary><strong>Older releases</strong></summary>

### v4.41.1 — The Necrotic Catalysts come back

- **Refined Necrotic Catalyst (~136 ex) is picked up again.** Both were suppressed because "Exiled Bot's validator rejects these base types" — a claim about the validator, not about whether the item drops. Your pickit already carries five names that same validator flags and the bot loads it fine, and the app already picks up Refined Sibilant Catalyst, the identical family.

### v4.41.0 — A whole price category was never being fetched

- **poe.ninja serves a "Verisium" category and this app never asked for it** — all 24 of its items had no rule at any floor. The generated pickit therefore had no rule for **Celestial Alloy at ~308 ex**, Warding Starlit Ore at ~143 ex, or 14 more worth over 1 ex. Now fetched like every other category, so they price and update themselves.
- **Raven's Reflection is picked up.** The Delirium pinnacle key, dropped from Simulacrum, had no rule at all — poe.ninja prices it in no category, and an unpriced valuable is invisible unless it's named in the always-pick list.

### v4.40.1 — The quality-of-life pass

- **"Hide everything else" remembers your choice and starts OFF** — it was hardcoded ON and never saved, so anyone who turned it off got it back every launch.
- **Restoring a backup no longer claims "nothing is lost"** — it replaces the file only, and the dialog says so.
- **Item Check warns when your floors changed** since the pickit was built.
- **"Disable all" asks first** (~1,900 items, no undo), and an **empty search says so** instead of showing a blank table.
- **Craft can set every item level at once**, **Create your filter scrolls to the result**, and **Fracture grades explain what S+/S/A+/A mean**.

### v4.40.0 — Item Check tells the truth, and setup stops overwriting your floors

- **Item Check said the bot would walk past items your pickit actually takes** — a Waystone got *"ignored"* while the pickit grabs every waystone; an Uncut Skill Gem got *"nothing targets this"* against 20 active rules; a Magic flask the same. All three answer correctly now.
- **Item Check's error messages were invisible** — an unreadable paste showed nothing at all, so the button looked broken.
- **The setup wizard overwrote your floors on arrival at the loot step**, taking a new user from 0/0 to 2/6 by pressing Next and undoing the "first run picks up everything" default. Balanced is still recommended; it now waits for your click.
- **"Turn everything on" twice hid the undo button**, and **`--cli` wrote five duplicate rules and never validated**.
- **The bot-connection check now looks at the file, not just the name** — it can tell you nothing has been deployed yet, or that the bot's copy is older than yours.

### v4.39.5 — Two more honesty fixes in the conversion report

- **Every comment line was counted as a "disabled rule"** — a normal pickit claimed 202 disabled when the real answer was zero. Only a commented-out *rule* counts now.
- **An imported value written as `1e3` was read as `1`**, so a 1000 ex item got a 1 ex label. A negative value matched nothing at all.

### v4.39.4 — Create your filter stops calling a dropped condition "converted"

- **A condition the converter recognised but couldn't read used to vanish silently** — an `[ItemLevel]` written without quotes, a `[Quality]` using `>` instead of `>=`, an ItemLevel floor *and* ceiling where only the floor was taken. Those rules were reported as cleanly converted while the gate was missing from the filter. They now count as **shown wider**, which is what actually happened.
- **Pickits this app generates are unaffected** — verified against real files, the numbers don't move by a single rule.

### v4.39.3 — Implicits finished, and five that showed the wrong number

- **27 bases showed a blank line** where the game gives them a real implicit — 52 entries became 79. Several change how you use the item: **Corona Amulet** grants a *helmet* socket, **Grasping Ring** a *glove* socket, **Stalking Belt** a *boot* socket, and **Grasping Mail** can also roll ring modifiers.
- **Five implicits displayed the wrong number.** Grand Spear read "+25 Weapon range" when the game stat is a percentage — +25%, not a flat 25. Same for Striking Quarterstaff, Flexed Crossbow, Utility Belt and Warlord Cuirass. Thane Mail showed a reduction as if it were a bonus.
- **Two-Stone Ring is three different bases** (fire+cold, fire+lightning, cold+lightning) and one roll was shown for all three.

### v4.39.2 — The bot can buy the Ritual fragment from a Ritual

- **An Audience with the King no longer carries `[IgnoreRitual]`.** That flag tells the bot not to spend tribute buying an item back from a Ritual altar — but this item *is* the Ritual pinnacle fragment, so a Ritual reward window is exactly where you'd want it. Expedition Logbook and Kulemak's Invitation keep the flag: the Logbook is a real ground drop, so not re-buying a copy is a genuine saving, and the Invitation is Abyss content where the flag never applies.

### v4.39.1 — First run picks up everything, and four bases corrected

- **First run now picks up everything.** The floors were already 0, but the two exceptional gates defaulted to quality 25 / item level 82 — so a new user's first pickit quietly skipped exceptional bases while the screen said "Picking up everything". They now open to 21 / 79. Anyone already running keeps their own settings.
- **Permafrost Staff and Reflecting Staff removed** — both exist only as uniques (The Whispering Ice, Atziri's Rule), so every white/rare rule naming them was dead. **Shrine Sceptre stays**: it was caught by the same sweep and that was wrong — it drops normally.
- **Crafting on staves never worked** — the only staff in the craft list couldn't drop as a Normal base. Ravenous Staff replaces it, and the rare staff slot is back to three bases.

### v4.39.0 — The second half of the audit — nine more bugs

- **A broken `game_data.json` can no longer strip your base rules.** That file self-updates from GitHub, and a truncated copy passed validation and silently deleted 16 of 17 base categories. A remote copy may now add bases, never delete a category.
- **Top movers can finally show uniques.** Every unique was being skipped, so all 7 unique categories recorded zero prices — a full league now records 438.
- **Backups stop touching other profiles**, **a shared profile can no longer break your app**, and **"Saved" now means saved** instead of a green toast over a failed write.
- **The Economy tab can no longer hang forever**, auto floor redraws its sliders, and **Ctrl+1…0 match the sidebar again** (Ctrl+4 was opening History; Magic & Rare loses the binding it only had by mistake).

### v4.38.4 — Six bugs found by a full audit of the app

Five parallel audits covered the rule engine, the bridge and config, the UI, the game data and the filter writers. Every fix was reproduced before and verified after, against live poe.ninja data.

- **The bot no longer spends Ritual tribute on Special Items.** When poe.ninja prices one of the three, the economy section emitted it *without* `[IgnoreRitual]` — the one flag those three exist to carry.
- **The `.filter` written beside your pickit keeps its item-level gates.** All 262 were dropped, so 68 base types showed from act 1 onward and that filter disagreed with the one Create your filter builds from the same pickit. Now: 0 disagreements across 1,123 names.
- **"Turn everything on" twice no longer destroys the undo** — the second click used to overwrite the snapshot, so restoring gave you all-on with your floors gone.
- **The item report no longer lists uniques the pickit doesn't contain** (440 claimed vs 227 real).
- **A hand-edited or ANSI `.ipd` no longer breaks generating forever**, and **a bad saved window size no longer stops the app from opening.**

### v4.38.3 — A unique on an anvil-only base no longer makes a dead rule

- **Uniques priced on a Runeforged/Runemastered base are skipped instead of rewritten.** Those bases are made at the anvil and never drop, so the generator used to strip the prefix and target the plain base — but the plain base doesn't always exist. The Prisoner's Manacles was targeted on `Verisium Cuffs`, a base the game has never had, so the rule could never fire and it failed validation. Rathpith Globe, Voll's Protector and The Prisoner's Manacles each keep a rule on the base that really drops.

### v4.38.2 — An update announcement that actually says something

- **"What's new" no longer shows a bare link and nothing else.** A release published before its notes are attached gets an auto-generated body containing one `Full Changelog` URL, and the dialog showed that instead of the highlights bundled in the exe. A stashed body with no prose in it now loses to those highlights.

### v4.38.1 — Exceptional tab uses its full width

- **Shields and Foci no longer render into a third of the page.** Every category in the Exceptional tab was pinned to three equal columns so Str | Dex | Int would line up — but Shields only has Str bases and Foci only Int, so one filled column sat beside two empty ones. Each category now gets as many columns as it actually has.

### v4.38.0 — "Everything on" means everything, plus a tab-by-tab cleanup

Every tab was audited that cycle. The headline items are behaviour fixes — things that were quietly answering wrong:

- **🔓 Turn everything on now really does.** It flipped every switch, but Adaptive market floors then recomputed a high floor on the next run and threw most of it away. It now also drops both floors to 0, switches Adaptive floors off, and opens exceptional gates to quality 21 / ilvl 79. **Put my switches back** restores all of it.
- **A floor you set by hand sticks** — typing or dragging one now switches Adaptive floors off instead of silently recomputing over your number.
- **Item Check stopped rejecting quality white bases.** It now strips the `Superior` prefix and resolves Magic items whose base is wrapped in affixes, so the bases your generated rules cover are recognized correctly.
- **Create your filter translates `ItemLevel` and `WaystoneTier` exactly** instead of dropping them, so far fewer rules count as "shown wider" and Hide mode is safer.
- **Useful detail across every tab:** bases display their game-data implicits when they have one; Chance cards show live target prices and art; profile imports preview everything they turn OFF; Preview explains and compares rules; Economy shows Top movers.

</details>

[Read the complete v4.41.26 release notes](https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.41.26) · [full changelog](CHANGELOG.md)

<details>
<summary><strong>Everything included</strong></summary>

- Five presets: Vacuum, Balanced, Strict, Chase, and Currency only.
- Editable exalted-orb floors and Auto-floor.
- Current-league pricing and seven-day unique trends.
- Item Check with the actual emitted rule.
- Coverage for 17 rare-gear slots.
- Pickit-to-filter conversion with an honest report.
- Setup guide and connection check.
- Rotating backups and restore tools.
- Portable Windows application with no installer.

</details>

<details>
<summary><strong>Build from source</strong></summary>

Requirements: Windows 10 or 11 and Python 3.10 or newer.

```powershell
git clone https://github.com/c4Luffy/poe2-pickit-generator.git
cd poe2-pickit-generator
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m exilebot_pickit
```

</details>

## Help and community

- [Setup and troubleshooting](https://c4luffy.github.io/poe2-pickit-generator/#faq)
- [Discord community](https://discord.gg/T7DU3Afve6)
- [Report an issue](https://github.com/c4Luffy/poe2-pickit-generator/issues)
- [All releases](https://github.com/c4Luffy/poe2-pickit-generator/releases)

---

Community project; not affiliated with Grinding Gear Games, Path of Exile 2, Exiled Bot 2, or poe.ninja.
