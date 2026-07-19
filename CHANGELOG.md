# Changelog

All notable changes to **ExileBot 2 Pickit Generator**.
Versions link to their release, where the `ExileBot2PickitGenerator.exe`
download lives.

---

## [v4.39.4] — 2026-07-19 — Create your filter stops calling a dropped condition "converted"

- **A condition the converter recognised but couldn't read used to vanish
  silently.** The "shown wider" counter only tracked tokens it didn't recognise,
  so a *known* one that failed to parse was reported as a clean conversion while
  the gate was simply missing from the filter. Every one of these shapes is legal
  in a hand-written `.ipd` and every one was silently dropped:

  | Rule | What went missing |
  | --- | --- |
  | `[ItemLevel] >= 82` (unquoted) | the whole item-level gate |
  | `[WaystoneTier] >= 14` (unquoted) | the tier gate |
  | `[Quality] > "18"` (`>` not `>=`) | the quality gate |
  | `[Sockets] == "3"` (`==` not `>=`) | the socket gate |
  | `[Rarity] != "Normal"` | the rarity gate |
  | `[ItemLevel] >= "70" && [ItemLevel] <= "80"` | the ceiling |

  They now count as **shown wider**, which is what actually happened. The report
  promising "converted / shown wider / untranslatable" is the entire point of
  that tab, so it has to be true.
- **Pickits this app generates are unaffected.** Verified against real generated
  files: the widened count doesn't move by a single rule, because the generator
  writes quoted values with the operators the converter parses. The 528 already
  counted there come from `ItemTier`, a genuine bot-only condition the game's
  filter language cannot express.

---

## [v4.39.3] — 2026-07-19 — Implicits finished, and five that showed the wrong number

- **27 bases showed a blank line** where the game gives them a real implicit —
  52 entries became **79**. Several are facts that change how you use the item:
  **Corona Amulet** grants a *helmet* socket, **Grasping Ring** a *glove*
  socket, **Stalking Belt** a *boot* socket, **Forking / Invoking / Sinew Belt**
  an extra charm slot, and **Grasping Mail** can also roll ring modifiers. The
  nine Lake amulets now show the prefix/suffix trade they make.
- **Five implicits displayed the wrong number.** The game's stat id carries the
  unit and five entries had dropped it: Grand Spear read *"+25 Weapon range"*
  for `local_+%_weapon_range` — a flat 25 instead of +25%. Same for Striking
  Quarterstaff, Flexed Crossbow, Utility Belt (*20% of flask recovery is
  instant*) and Warlord Cuirass. **Thane Mail** rendered the trailing minus of
  `base_self_critical_strike_multiplier_-%` as literal text while keeping a
  leading plus; it is a reduction, so it now reads **-15-25%**.
- **Two-Stone Ring is three different bases** — fire+cold, fire+lightning and
  cold+lightning — and the cold+lightning roll was shown for all three.
- **Guarded by tests** that cross-check every implicit against the GGPK dump: a
  shipped base can no longer render blank, and a percentage stat can no longer
  lose its `%`. Those tests found two of the five wrong numbers on their own.

---

## [v4.39.2] — 2026-07-19 — The bot can buy the Ritual fragment from a Ritual

- **An Audience with the King no longer carries `[IgnoreRitual]`.** That flag
  tells the bot not to spend tribute buying an item back from a Ritual altar —
  but this item *is* the Ritual pinnacle fragment, so a Ritual reward window is
  exactly where you would want it. The flag could only cost: if the item appears
  in the window the bot walked past ~50 ex, and if it only ever drops on the
  ground the flag did nothing at all. Better-or-neutral either way, so it goes.
- **The other two keep the flag.** Expedition Logbook is a genuine ground drop
  (drop level 78), so declining to re-buy a copy with tribute is a real saving.
  Kulemak's Invitation is Abyss content, where the flag never applies.
- **One helper now decides the action for both writers.** These rules are
  emitted by two different builders — the static Special Items section, and the
  economy section when poe.ninja happens to price the item — and in v4.38.4 they
  disagreed, so the same item got contradictory rules depending on whether it
  was priced that day. `special_item_action()` is the single source of truth,
  guarded by a test that runs every Special Item through both paths.

---

## [v4.39.1] — 2026-07-19 — First run picks up everything, and four bases corrected

- **First run now picks up everything.** Both value floors were already 0 on a
  fresh install, but the two exceptional gates defaulted to quality 25 / item
  level 82 — so a brand-new user's very first pickit quietly skipped exceptional
  bases they had never chosen to skip, while the Generate tab said *"Picking up
  everything"*. They now open to **21 / 79**, the loosest legal values (quality
  rolls 21–30, item level 79–82) and the same pair "Turn everything on" sets.
  Anyone already running keeps their own settings — defaults only apply when no
  config file exists.
- **Permafrost Staff and Reflecting Staff removed.** Both exist *only* as
  uniques — The Whispering Ice and Atziri's Rule (an Atziri temple drop). A
  white or rare one never drops, so every non-unique rule naming them was dead.
  Reflecting Staff keeps its ungated rule in the exotic list, which is now the
  only place it appears, so the Exceptional-tab toggle that did nothing is gone.
- **Shrine Sceptre stays.** It was caught by the same sweep and that was wrong:
  it has three ordinary droppable variants (`FourSceptre6a/6b/6c`) alongside one
  unique host, so it drops normally. Restored the same day.
- **The staff slot is back to three bases** — Ravenous (65), Sanctified (56) and
  Paralysing (52) — matching how every other slot keeps its top three even when
  the levels fall off.
- **Crafting on staves never worked.** The only staff in the craft list was
  Permafrost Staff, which cannot drop as a Normal base, so the rule could never
  fire. Ravenous Staff replaces it.
- **The bundled lists and `game_data.json` can no longer drift apart unnoticed.**
  Every other section was checked; base types — the largest at 119 entries —
  was not, and a silently failed edit left the two disagreeing with the whole
  suite still passing. That is exactly how offline and online users end up
  generating different pickits.

---

## [v4.39.0] — 2026-07-19 — The second half of the audit: nine more bugs

v4.38.4 shipped the six most urgent findings. These are the rest, each
reproduced before and verified after against live poe.ninja data.

### Data safety

- **A broken `game_data.json` can no longer strip your base rules.** That file
  self-updates from GitHub, and `_apply` prunes any category the remote copy
  omits — so a truncated or half-edited copy passed validation and silently
  deleted **16 of 17** base categories, stripping almost every base rule from
  every user's pickit with no error anywhere. A remote copy may now add
  categories and change their contents, never remove or empty one. Base names
  carrying a newline are rejected too: they split one rule in two, and the
  second half has no `[Type]`, which Exiled Bot reads as matching *everything*
  on the ground. A cache whose payload fails validation no longer reports a
  fresh timestamp (one bad write used to suppress updates for 6 hours, and a
  future-dated stamp suppressed them forever).

### Fixed

- **Top movers can finally show uniques.** Prices were joined to an items table
  by id, but unique payloads ship `items: []` and carry the name on the row
  itself — so every unique was skipped and all **7 unique categories recorded
  zero prices**. Mageblood could double and the panel stayed empty, permanently,
  because the saved baseline was empty too. A full league now records **438**
  unique prices. A unique priced on several bases keeps its highest price
  instead of letting iteration order decide.
- **Backups stop touching other profiles.** Backups are `<output_base>-<stamp>.ipd`
  matched by prefix, but `-` is a legal output-name character — so with
  `pickit`, every `pickit-strict-*.ipd` matched. Rotation deleted its own
  backups while keeping the other profile's, Clear backups wiped files it didn't
  own, and Restore could put another profile's pickit over yours and copy it to
  the bot. One shared matcher now requires the exact `YYYYMMDD-HHMMSS` stamp.
- **A shared profile can no longer break your app.** Profile fields were copied
  into your config and saved *before* anything could raise, so a bad profile
  persisted, broke Generate for the rest of the session, and could set an
  `output_base` that wrote your `.ipd` outside the output folder permanently.
  Profiles are validated first and rejected with a message.
- **"Saved" now means saved.** `save_config` returned nothing whether it wrote
  the file or not, so ~25 actions answered a hard-coded success: with an
  unwritable config directory the toast said *Saved* while nothing was written
  and the setting vanished at next launch. The atomic-write and corruption
  recovery path is unchanged.
- **The Economy tab can no longer hang forever.** A failed price poll aborted
  before clearing its timer, so the tab pinned on "Loading prices…" and every
  revisit started another timer hammering the bridge every 250 ms — only a
  restart recovered.
- **Auto floor redraws its sliders** instead of leaving the fills frozen at the
  old position beside a changed number.
- **Ctrl+1…0 match the sidebar again.** The shortcut list omitted Create your
  filter, so Ctrl+4 opened History and everything above it was off by one. It is
  derived from the sidebar now, so it cannot drift again. With 14 tabs and 10
  digits, **Magic & Rare no longer has a binding** — it only had one because of
  that off-by-one.
- **"— no profile —" no longer pretends.** It did nothing and silently reverted;
  there is no way to clear the active profile from the bridge, so the option is
  disabled rather than misleading.
- **The command line stops passing off month-old prices as today's.** When
  poe.ninja was unreachable it fell back to the disk copy — kept up to 60 days —
  and printed nothing. It now names the affected categories.

---

## [v4.38.4] — 2026-07-19 — Six bugs found by a full audit of the app

Five parallel audits covered the rule engine, the Python↔JS bridge and config,
the UI, the game-data layer and the filter writers. Every fix below was
reproduced before and verified after, against live poe.ninja data.

- **The bot no longer spends Ritual tribute on Special Items.** When poe.ninja
  prices one of the three (An Audience with the King, Expedition Logbook,
  Kulemak's Invitation), the economy section emits it instead of the Special
  Items builder — and it wrote the rule *without* `[IgnoreRitual]`, the one flag
  those three exist to carry. Forced rules now carry their builder's action.
- **The `.filter` written beside your pickit keeps its item-level gates.** All
  262 `[ItemLevel]` conditions were dropped, so 68 base types showed from act 1
  onward, and that filter disagreed with the one **Create your filter** produces
  from the same pickit. Verified: 0 disagreements across 1,123 base names.
- **Clicking "Turn everything on" twice no longer destroys the undo.** The
  second click overwrote the snapshot with the already-on state, so "Put my
  switches back" restored all-on and your floors were gone. The first snapshot
  is now kept until it is used.
- **The item report no longer lists uniques the pickit doesn't contain.** The
  anvil guard added in 4.38.3 reached the rule builder but not the report, which
  claimed 440 uniques "included" where the file held 227. Excluded rows now say
  why.
- **A hand-edited or ANSI `.ipd` no longer breaks generating forever.** The
  added/removed diff read it as UTF-8; `UnicodeDecodeError` is a `ValueError`,
  not an `OSError`, so it escaped the guard and aborted the run *before* the
  write — leaving the bad file in place so every later run failed identically.
- **A bad saved window size no longer stops the app from opening.** Only the
  outer type was validated, so a non-numeric width raised before the window
  existed: no window, no message, on every launch.

---

## [v4.38.3] — 2026-07-19 — A unique on an anvil-only base no longer makes a dead rule

- **Uniques priced on a Runeforged/Runemastered base are skipped instead of
  rewritten.** Those bases are made at the anvil from dropped items, so they
  never appear as ground loot and Exiled Bot's validator rejects the name. The
  generator handled that by stripping the prefix and targeting the plain base —
  which assumes the plain base exists. It does not always: poe.ninja lists **The
  Prisoner's Manacles** on both `Runemastered Verisium Cuffs` and `Kalguuran
  Cuffs`, and the game has no plain `Verisium Cuffs` at all, so the rewrite
  invented a base type that exists nowhere. The rule could never fire, and it
  failed validation.

  Across current price data this removes exactly three rules, and every affected
  unique keeps a rule on a base that really drops:

  | Unique | Removed | Kept |
  | --- | --- | --- |
  | Rathpith Globe | Plumed Focus | **Sacred Focus** |
  | Voll's Protector | Ironclad Vestments | **Plated Vestments** |
  | The Prisoner's Manacles | Verisium Cuffs | **Kalguuran Cuffs** |

---

## [v4.38.2] — 2026-07-19 — An update announcement that actually says something

- **"What's new" no longer shows a bare link and nothing else.** When a release
  is published before its notes are attached, GitHub fills the body with a lone
  `Full Changelog: <compare url>`. The updater stashes that body at download
  time and the dialog prefers the stash over the highlights bundled in the exe,
  so the announcement was a version heading and one URL. A stashed body now has
  to contain actual prose to be used — strip the changelog line, bare URLs,
  headings and bullets, and if nothing survives, fall back to the bundled
  highlights. Genuinely short notes still win; the test is "is there anything
  at all", not "is there enough".

---

## [v4.38.1] — 2026-07-19 — Exceptional tab uses its full width

- **Shields and Foci no longer render into a third of the page.** Every
  category in the Exceptional tab was pinned to three equal columns so
  Str | Dex | Int would line up. Shields only has Str bases and Foci only Int,
  so a single filled column sat beside two empty ones. Each category now gets
  as many attribute columns as it actually has, and a category with only one
  group flows its cards as a normal grid. Body Armours, Helmets, Gloves and
  Boots keep their aligned Str | Dex | Int columns.

---

## [v4.38.0] — 2026-07-19 — "Everything on" means everything, plus a tab-by-tab cleanup

Every tab in the app was audited this cycle. The headline items are behaviour
fixes — things that were quietly answering wrong:

- **🔓 Turn everything on now really does.** It flipped every switch, but
  Adaptive market floors then recomputed a high floor on the next generate and
  threw away most of what had just been enabled. It now also drops both value
  floors to 0, switches Adaptive floors off, and opens the exceptional gates to
  their loosest legal values (quality 21 / item level 79). **Put my switches
  back** restores all of it, floors included.
- **A floor you set by hand sticks.** Typing or dragging a floor now switches
  Adaptive floors off instead of silently recomputing over your number.
- **Item Check stopped rejecting quality white bases.** Items copy from the game
  as `Superior <Base>` when they have quality, and that prefix was never
  stripped — so the exact bases the Exceptional tab exists to collect were
  reported as "no rule matches". Magic items (whose base is wrapped in affixes)
  now resolve too.
- **Create your filter** translates `ItemLevel` and `WaystoneTier` exactly
  instead of dropping them, so far fewer rules count as "shown wider" and Hide
  mode is safer.

New:

- **Implicits on every base** — Gold Ring `+6-15% Item Rarity`, Visceral Quiver
  `+20-30% Attack Crit Chance` — read from the game's own data files. 52 of the
  bases shipped have one; the rest genuinely have none.
- **Chance cards show what you're chancing for**: the live price of the target
  unique, with art for each possible outcome.
- **Profiles export and import.** Importing previews the profile first and names,
  in amber, everything it turns OFF — a shared profile can't quietly disable
  Divine Orb and cost you loot.
- **Preview**: click a rule to see why it's there and what it's worth, and diff
  the current pickit against any backup.
- **Economy → Top movers**: the 20 biggest 7-day swings across every category.
- **Create your filter**: one click loads the pickit the bot is actually running.
- **Settings**: Clear all saved backups.
- A **weekly automated game-data check** watches for PoE2 patches renaming or
  removing items, so data breaks get caught before they reach anyone's pickit.

Polish:

- **Debug** rebuilt around three plain-language actions instead of eight
  technical buttons, and it no longer alarms you with old, long-fixed errors.
- **Craft** and **Exceptional** lay out properly instead of one long column;
  Exceptional groups bases as Str / Dex / Int columns with hybrids separate.
- Browser popups (`127.0.0.1 says…`) replaced with proper in-app dialogs.
- The **Setup guide** now describes every tab — Create your filter and Item
  Check were never mentioned before.

Data:

- **Revelatory Wombgift removed** — it comes from combining Breach Splinters and
  is spent on the tree, so it never drops on the ground and a pickup rule for it
  could never fire.
- **White Grand Regalia removed** from exceptional bases (owner decision). The
  unique that uses that base is unaffected.

## [v4.37.0] — 2026-07-18 — Filters color by real value: the five-tier ladder

Every filter the app writes — generated next to the pickit or converted from
one — now colors each label by what the item is **actually worth**, read from
the rule's own recorded price and the file's own Divine rate:

- **The value ladder:** mythic (1+ Divine, purple), jackpot (10% of a Divine,
  red screamer), high (10+ ex, orange), useful (1+ ex, gold), quiet. Unpriced
  rules wear their purpose colors instead — chance, craft, fracture (pink),
  exceptional (cyan), curated, uniques.
- **Honest at league start:** when Divine is cheap the tiers keep their own
  bands instead of collapsing into each other — a 12-ex drop labels orange,
  never a false red jackpot; the ladder stays strictly ordered at any Divine
  rate. And if the price feed ever lacks a Divine rate, the generated pickit
  says so instead of writing a bogus 1.0 rate that would paint everything
  purple.
- **Converted pickits keep their tiers:** importing a generated `.ipd` on
  Create your filter reads the same prices, and the report shows exactly what
  got which look — count chips styled in the filter's real colors.
- **One theme, no sounds — owner's call.** The theme picker is gone; every
  filter wears the one community-classic look (the owner's own filter color
  codes). No `PlayAlertSound` anywhere, ever — the bot doesn't listen and
  pings annoy. Beams and minimap icons only where they earn their place.
- **The ground preview is the real thing:** the Create your filter page shows
  the owner's own in-game capture instead of synthetic labels.
- **🔓 All ON + Generate:** one click under the hero button flips every switch
  in the app back on — categories, items, chance/craft/exceptional/fracture,
  rare slots — keeps your floors untouched, and generates.

## [v4.36.0] — 2026-07-17 — Label themes: NeverSink's colors on every filter the app writes

Both filters the app writes — the one generated next to every pickit and the one
converted from any pickit — now share one **label theme**, picked once on the
Create your filter page with a live "how it looks on the ground" preview:

- **Four themes:** Community classic (default — colors, sizes and minimap icons
  taken verbatim from NeverSink's live PoE2 filter), Minimal (the previous quiet
  look), High contrast, and Colorblind safe (blue/orange, no red-vs-green).
- **Jackpot tier:** rules worth 50+ exalted at generate time — plus Mirror of
  Kalandra and Divine Orb always — get the red screamer with sound and beam.
  Sounds exist ONLY on this tier; cheap drops stay quiet on purpose.
- **Gold is never hidden** now also holds for the generated filter, not just
  converted ones.
- **Chance Bases:** every card now shows the unique you're chancing FOR (real
  game art, works offline), and the list was trimmed to the owner's four:
  Utility Belt, Heavy Belt, Gold Ring, Stellar Amulet.
- **Prices refresh themselves** every 15 minutes — no more wiggling a floor
  slider to see today's divine rate.
- **Small comforts:** Economy names wrap instead of vanishing behind "…", the
  run log wraps paths cleanly and is resizable, changing the theme after saving
  a converted filter warns that the saved file still wears the old look, and
  the CLI gained `--filter-theme`.

## [v4.35.2] — 2026-07-16 — Same-day audit: 12 fixes from two code audits + a live sweep

The new tab is hours old, so it got the full treatment the same day: an adversarial
code review, a 37-input attack battery against the converter, and a click-through of
every page in the running app. Everything found was fixed:

- **One divine, everywhere.** The floor slider's reference line and the LIVE bar could
  show two different divine rates (one live, one from your last run). Every fresh rate
  now updates all of them together — what you see is one number, the live one.
- **The Discord button wears the real Discord logo** now.
- **Converter hardening (Create your filter):**
  - a `#` inside an item name could silently drop that name from the filter — the one
    way an item your pickit wants could end up hidden with no warning. Names a filter
    can't express (`#` or `"`) are now excluded *and loudly reported*.
  - named rules translate **all** their conditions exactly — a rule with rarity AND
    quality kept only one before (the filter just showed a bit more than needed).
  - the "shown wider" count is now honest in both directions.
  - an unknown rarity word is dropped (shown wider) instead of being passed through,
    where it could have made the game reject the entire filter.
  - hand-made pickits saved as ANSI (accented item names) now decode correctly.
- **Small but real:** naming your output "latest" no longer collides with the
  duplicate-cleanup (it would have deleted the real pickit at every launch); Save can
  never overwrite a pickit file; two converts can't race each other; drag & drop no
  longer blocks normal text-dragging into inputs; a failed convert can't leave the
  previous file's numbers on screen under the new file's name.

## [v4.35.1] — 2026-07-16 — Create your filter: drag & drop + open folder

Two comforts for the new tab, same day:

- **Drag & drop.** Drop a `.ipd` anywhere on the app window — it jumps to the
  Create your filter tab and converts it on the spot. (If your system blocks
  path access on drop, the app says so and the Choose button still works.)
- **📂 Open folder.** After saving a filter, one click opens the folder it
  landed in — no hunting for where it went.

## [v4.35.0] — 2026-07-16 — Create your filter: any pickit becomes an in-game loot filter

New tab: **📥 Create your filter**. Bring *any* Exiled Bot pickit — hand-made, from a
friend, from another tool, months of manual tuning — pick the file, and the app writes
a loot filter the game understands. What your bot would grab is what you see highlighted
on the ground. The pickit is only read, never changed, and nothing leaves your PC.

- **An honest report, not magic.** After reading your file it tells you exactly what it
  understood: rules read, converted, "shown wider" (rules that check mods or tiers only
  the bot can see — those items still get a label, just without that check), and the
  rare rule a filter genuinely can't express, listed with its line number and why.
- **Hide means hide.** "Hide everything else" is ON by default — your screen shows only
  what your pickit wants (plus gold, which is never hidden: bots grab it regardless of
  any pickit). If a rule couldn't be translated, you get a loud warning instead of a
  silent surprise. Turn it OFF while botting — hidden labels can stall the bot's pickup.
- **Styled like it matters.** Named items get a gold border and a minimap dot; uniques
  show in their orange with a light beam and a minimap star; gear rules stay quiet.
- **It notices drift.** If your pickit changes after the filter was made, the tab warns
  you the next time you open it — one click reloads the file so you can re-save.
- Category rules translate properly (`Ring` → `Class == "Rings"`, flasks, waystones,
  every armour and weapon class) — each class name verified against NeverSink's live
  filter, because a wrong name would silently match nothing.

Also in this release:

- **The output folder no longer has two identical pickits.** `latest.ipd` was a
  leftover duplicate that nothing actually read — users couldn't tell which file their
  bot needed. It's gone (the app cleans up the old copy at launch); the folder is now
  just your pickit, the optional `.filter`, and `backups/`.

## [v4.34.0] — 2026-07-16 — Deep-scan release: 14 fixes from a full-code audit

A multi-angle audit of every file in the project, with every finding verified against
the code before fixing. Nothing about how rules are generated changed — this release is
about the app around them being solid.

Fixes you'll actually notice:

- **The window finally remembers its size and position.** A type mix-up wiped the saved
  geometry on every launch, so the app always opened at the default size. Resize it once
  — it stays.
- **"Reset to defaults" now truly resets.** Toggling items after a reset used to leak
  into the defaults themselves, so the next reset restored your old toggles instead of
  a clean slate.
- **🐛 Report a problem** (Debug tab): one click opens a GitHub issue with your
  diagnostics pre-filled — you review it, you send it. No hidden telemetry, ever.
- **Settings changes can no longer be silently dropped** when a save lands at the same
  instant as another action (the log had recorded 107 such losses in a single day).

Fixes for things that would have bitten later:

- The pickit copied into your bot folder is now written atomically — the generated
  `.ipd` can never be picked up half-written, and a copy error no longer fails the
  whole generate.
- A second config corruption can no longer overwrite the backup of the first — the one
  file that still held your settings.
- Updating the app from a folder with `!` in its path no longer breaks the update swap.
- A rare price-data glitch (NaN) could hang a tab forever; corrupt poe.ninja responses
  are now retried instead of abandoned.
- Release builds now run *every* safety gate (not just the test suite) before an exe
  can publish, and the daily game-data watch fails loudly if it ever breaks instead of
  looking green forever.

## [v4.33.0] — 2026-07-15 — The app tells you when something breaks

Until now, when the app hit an error it wrote it to a log file and said nothing. You'd
only know if you went digging — or if you happened to see a glitch and screenshotted it.

- **A red badge now appears on the Debug tab the moment something goes wrong** — a UI
  error mid-session, or anything the last hour recorded on launch. You see there's a
  problem from anywhere in the app, without hunting for it. Open Debug and it clears.
- **Fixed: the error summary was blind to UI errors.** It counted only Python-side
  failures, so a run of front-end crashes — the kind this app actually hits — showed up
  as "errors: clean." It now counts both, so the count is honest.

This is groundwork, not a feature you'll use daily — but it means a bug reaches *me*
faster, so it gets fixed faster.

## [v4.32.4] — 2026-07-15 — Full-app review: config no longer lost to a BOM

A top-to-bottom scan of every file. Two real fixes:

- **Your settings could be wiped by an invisible character.** If the config file ever
  picked up a UTF-8 BOM — from Notepad's "Save As", PowerShell, or some editors — the app
  failed to read it, quarantined it, and fell back to defaults: league, floors, profiles,
  history, all seemingly gone. (This actually happened once.) The app now reads straight
  past a BOM. Nothing is lost.
- Hardened an Economy edge case that could crash if poe.ninja ever returned an empty
  category list.

Everything else came back clean: the pickit never emits a rule that would match every
item, the headless CLI produces the same sections as the app, the price client backs off
and honours rate-limits correctly, the updater compares versions numerically (so 4.9 <
4.30), and the bundled game data still matches the current patch (0 drift).

## [v4.32.3] — 2026-07-15 — Fixed an Economy crash when switching leagues

A review pass turned up a real error in the logs: changing your league while the Economy
tab was mid-action could throw *"Cannot read properties of null"* and leave the category
list blank. The Economy data is cleared the instant you switch leagues, and three render
functions read it without checking. They now bail cleanly until the new league's data
lands. (The smooth floor dragging from the last build also quietly applies to the quality
and item-level sliders.)

## [v4.32.2] — 2026-07-15 — Smooth floor dragging

The floor slider had a 0.12s width animation, so while you dragged, the fill and handle
lagged behind your cursor — it felt heavy. The animation is now switched off *during* a
drag (the handle tracks the pointer instantly) and kept for click-to-set and presets, so
those still glide. The handle also lifts slightly while held.

## [v4.32.1] — 2026-07-15 — Back to the slider

The quick-pick chips didn't read as an editable control — nothing said "change me". The
drag-slider is back (it has an always-visible handle, so it obviously invites dragging).
It still spans 0 → 1 divine and follows the live divine price, and the reference line
under it keeps chaos + divine.

## [v4.32.0] — 2026-07-15 — Floor quick-pick chips (the slider is gone), div back on the reference

- **The floor drag-slider is replaced by quick-pick chips.** Once the slider spanned a
  whole divine, every common floor was crushed into a 1%-wide sliver on the left — you
  couldn't drag to a small number. Now you tap a chip: **Off · 1 · 5 · 10 · 25 · 50 · 100 ·
  1 div**. The number box still takes any exact value, and "1 div" follows the live divine
  price. The active value is highlighted.
- **The reference line shows divine again**, next to chaos: **≈ 7.28 chaos · 0.99 div**.
  (It only adds divine once the floor is big enough to read in it, ~40 ex+, so a small
  floor stays a clean single chaos figure.)

## [v4.31.3] — 2026-07-15 — The floor slider actually reaches a divine now

v4.31.2 made the slider span 0 → 1 divine, but it was stuck at its 100 ex fallback: the
divine rate only arrived after you opened Economy or generated, so a fresh Generate tab
never had it. The rate is now fetched on load (in the same call that already gets the
chaos rate for the reference line), so the slider spans a real divine — about 424 ex
today — from the moment the tab opens, and tracks the price live.

## [v4.31.2] — 2026-07-15 — Floor slider spans a full divine; reference is chaos-only

- **The floor slider now runs from 0 to one Divine**, and follows the live divine price —
  so its top moves with the market (about 424 ex today). Drag anywhere in that range;
  typing an exact number still works and isn't capped.
- **The reference line under each floor shows chaos only now.** Divine on a small floor
  was a tiny, hard-to-read fraction — one clean chaos number reads better.

## [v4.31.1] — 2026-07-15 — Show the reference (it was hidden), slider to 100 ex

Two quick follow-ups to v4.31.0.

- **The chaos/divine reference line never actually appeared.** It lived inside a
  container (`.dial-extra`) that was set to `display:none` when the under-floor sparkline
  was shelved — so the reference was invisible with it. Pulled it out; it now shows right
  under each floor: **17** ex · ≈ 0.29 chaos. (Its style selector was also dead — it
  targeted a `.floor` ancestor that doesn't exist — so even unhidden it would have been
  unstyled.)
- **The floor slider now runs to 100 ex** (was 50). You can still type any number; this
  is just how far the drag reaches.

## [v4.31.0] — 2026-07-15 — Floors are simply in exalt now

The Chaos/Divine dropdown next to each floor is gone. It was a bug factory — the 58x
preset explosion, the "60.57176 Exalt" display bug, and the convert-vs-reinterpret
confusion all came from it — and it was redundant: the little line under each slider
already shows your floor in every currency.

So the floor is just a number in **exalt** now (a plain "ex" label, like the quality and
item-level dials). No dropdown, no `0.16 chaos` in the box, and that whole family of bugs
is impossible.

You still see chaos and divine — as a **reference**, under the slider, where you read them
instead of typing them:

> **25** ex &nbsp; ≈ 0.43 chaos

Chaos always shows; **divine only appears once the floor is high enough to mean something**
(~40 ex+). A "0.01 div" reference on a 6 ex floor is noise, so it's hidden until it isn't.

## [v4.30.0] — 2026-07-15 — Switching a floor's currency keeps the floor

Change the **unit** next to a floor — Exalt → Chaos, say — and the app used to keep the
*number* and quietly change what it meant. A **9 EXALT** floor became **9 CHAOS**, which
is **~520 ex** — 58× stricter — while the box still innocently read "9". On Divine it was
424× stricter. Your bot would start walking past almost everything and nothing on screen
said why.

Now the unit picker does what a unit picker should: it **converts**. 9 ex shown in chaos
becomes **0.16 chaos** — same floor, written differently, exactly like switching km to
miles. Your bot picks up the identical items.

And it tells you, so there's no guessing:
- *"Same 9 ex floor — just written in chaos. Your bot picks up exactly the same items."*
- When a floor is too small to write in a unit (9 ex is 0.02 divine, which rounds to
  nothing): *"9 ex is too small to write in divine — it stays in exalt."* — instead of the
  dropdown silently snapping back with no explanation.

Two quieter fixes rode along: switching a unit no longer **clears your active preset** (the
floor it set didn't change, so the preset is still true), and no longer **re-saves the
floor**, which had let display rounding creep into the real number on every flick of the
dropdown.

## [v4.29.3] — 2026-07-15 — Two old UI bugs, and 19 KB of dead weight

Both of these were spotted during the UI polish pass that got reverted for being slow.
They cost nothing to fix, so they were worth doing on their own.

- **Your price floors were rendering at the wrong size.** The design asks for big brass
  24px numbers; an inline `font-size:16px` left on the two inputs quietly overruled the
  stylesheet, so they'd always been 16px. They're now the size they were meant to be
  (and the box is wider, so a long value can't clip).
- **19 KB of font was loading on every launch for nothing.** The app embedded the
  **Marcellus** typeface for a single CSS rule — and **no element in the app has that
  class**. It styled nothing, and had been dead weight for a while. Gone, along with
  the last embedded font: every face in the app now ships with Windows.

That also settles the old split where page headings used one serif and "hero" headings
another. There was only ever one heading font actually on screen.

## [v4.29.2] — 2026-07-15 — Presets were silently 58x too strict on a chaos floor

Found while re-checking the wizard, but this one was never about the wizard.

**If your floor unit was Chaos or Divine, applying any preset quietly wrecked it.** The
floor is stored in exalt, and applying a preset dropped that exalt number straight into
the box — while the unit dropdown still said **Chaos**. So "Balanced · uniques from 6 ex"
became **6 chaos ≈ 346 ex**, and on a divine floor **6 div ≈ 2,551 ex**. Your bot then
walked past nearly everything, while the app cheerfully displayed the preset's name.

The value shown is now converted into whatever unit is on screen.

**And a unit is only used if the number survives it.** Two decimals of divine cannot hold
a small exalt floor — 2 ex is 0.0047 div, which displays as **0.00**, i.e. no floor at
all, and the bot would have taken *everything*. Rather than trade one wrong number for
another, each floor is round-tripped: if the unit can't hold it, the box shows **exalt**
and says so.

## [v4.29.1] — 2026-07-15 — The wizard, made honest

Four fixes from walking the beginner's own path through yesterday's wizard.

### It was telling new users their bot was connected when it wasn't
Step 2 said **"✅ Found Exiled Bot — already connected. Nothing to do"** purely because a
folder path existed. Finding the folder is **not** being connected: if the bot's
`pickit.ini` points `active_profile` at another name, it **silently ignores every pickit
you make**. Settings has always worded that state bluntly — *"the bot is IGNORING
everything you generate"* — and the setup guide calls it *the one step everybody misses*.
So the wizard built for people who don't know any better was confidently telling them
the exact opposite. It now runs the real check and offers **✓ Fix it for me**.

### It walked beginners into a stash full of junk
A fresh install has **no floor at all** (0 ex) — the bot stops for anything with a price,
looser than Vacuum. So *Next → Next → Next → Generate* handed a newcomer precisely the
outcome the wizard exists to prevent. Step 3 now lands you on **Balanced** and says so;
any other card is one tap away.

### Also
- **The last step actually generates now.** "Close this and press Generate" was a cop-out;
  the button is **⚡ Generate now** and it does the job.
- **The preset cards overflowed the panel.** They reserve 148px each for the Generate-tab
  row — five of those forced 740px into a 600px box, so *Currency only* fell off the edge.
- Step 3 no longer says *"sets every floor"* to someone who has never heard the word
  **floor**.

## [v4.29.0] — 2026-07-15 — A setup wizard for first-timers

A new user opened the app to **13 tabs and two sliders**, with nothing saying which
three things actually matter. The pieces were all there — auto bot-detection, presets,
the setup guide — but you had to *notice* them.

Now a brand-new install gets walked through it in four steps:

1. **Welcome** — what the app does, in one line, and which league you're farming
2. **Your bot** — it's usually already found and connected, so this just shows you where.
   If not, Search again / Browse are right there (and skipping is fine — generating still
   works, the file just won't travel to the bot on its own)
3. **How much loot?** — pick a preset; it sets every floor and switch at once
4. **That's it** — press Generate. Plus the one thing to check if the bot ignores you.

It only ever appears for someone who has **never generated** — the honest test of a new
user, since your league is saved automatically the moment the app opens and the bot
folder is auto-detected. Skipping counts as done, so nobody gets nagged twice. The
backdrop deliberately doesn't dismiss it: a stray click shouldn't silently mark setup
complete.

**Been here for ages and want it anyway?** The Setup guide has a **▶ Walk me through it**
button. It's the same wizard, and it destroys nothing.

## [v4.28.0] — 2026-07-15 — One typeface, everywhere

Themes each had their **own** body face, heading face and tab style (v4.21.0). Side by
side, one of them was simply better: **Blight's** — plain **Segoe UI**, with uppercase,
bold, letter-spaced tabs. So that is now the whole app, on every theme.

Themes are **colour** again, which is what they were always best at. Two bonuses: the
subtly different `Segoe UI Variable Text` (the old default) is gone, and so are
Candara/Corbel/Constantia — the faces whose old-style figures made every number in the
app look wobbly until v4.24.0 had to force lining digits.

### Fixed — the in-game filter instructions were incomplete
Settings said: *pick "poe2_pickit" in Options → Game → Filters, and it's working.* That
reads like one-time setup. It isn't. **PoE2 only reads a filter at the moment you pick
it** — copying a fresh one over the old file changes nothing in a running game, so you
were playing with a filter from whenever you last selected it.

The setting now says so: after every Generate, re-select the filter in that dropdown
(switch away and back) before the game will use it.

## [v4.27.0] — 2026-07-15 — Price trends, patch tracking, and an honest age pill

### 📈 7-day trends in Economy
Every unique row now draws a **sparkline** of its last 7 days beside the % change, so
you can see at a glance whether something is climbing or bleeding out — not just where
it landed today. poe.ninja has been sending us this curve all along; we were reading
one number off it and throwing the shape away.

### 🧬 The health check now tells you what the *patch* changed
It only ever asked "are your rules still valid?". It now also answers the other half —
**"did the game move?"** — by diffing NeverSink's drop list (1,357 bases) against the
copy it saved last time:

> 🧬 **The game's drop list changed** · last change 2026-07-15
> **started dropping: 3** — Gloam Ring, Dusk Circlet, Penumbra Band

The finding is **kept** until the next real change, so it can't vanish before you look.
The first check just records a baseline — with nothing to compare against, claiming a
change would be a fabrication.

### Fixed
- **The freshness pill was lying.** It said *"prices fetched 35h ago"*, which was never
  true: the price cache lives in memory with a **15-minute** life and is empty at
  launch, so a Generate **always** fetches live prices. It was really showing when you
  last *generated*. It now says what it means — **"pickit built 35h ago"** — and turns
  amber past a day, because that's the thing that actually goes stale: the file on
  disk, while the market moves under it.

## [v4.26.1] — 2026-07-14 — Clear means clear

One bug from a fresh audit of the last two releases: pressing **Clear** in Item Check
didn't reset the auto-paste memory — so after clearing, re-entering the tab refused to
re-paste the very item still on your clipboard ("already handled that copy"). Clear now
forgets too, so the same item pastes again.

Also re-verified in the same pass: the What's-New GitHub fallback fetches real notes
for a hand-downloaded exe, the Fracture search survives toggling a class, and the full
suite (192 tests) is green.

## [v4.26.0] — 2026-07-14 — Search everywhere, copy one section, re-read the notes

### Every item tab has a search box now
**Chance, Exceptional and Fracture** get the same 🔎 filter Craft and Economy already
had — and **Ctrl+F** focuses it on every one of those tabs. The Fracture search goes
one further: it matches **target mod text**, not just class names — type *"skill
level"* and you see exactly which classes fracture for a +skill-level mod.

### Copy one section from Preview
Hover a section in Preview's side list and a small **⧉** appears — click it to copy
just that section's rules (say, only your Currency block) without selecting anything.

### Click the version number to re-read What's New
Closed the update notes too fast? They used to be gone forever. The **version label**
in the sidebar is now clickable and re-opens the notes for the version you're on,
any time.

## [v4.25.0] — 2026-07-14 — Item Check pastes itself, and the league finally saves

### Item Check: Ctrl+C in game, click the tab — done
If your clipboard already holds a PoE2 item when you open **Item Check**, the item
drops straight into the box and the check runs by itself. No Ctrl+V, no button.
It never overwrites something you typed yourself, never re-runs the same copy twice,
and if the clipboard holds anything that isn't an item it stays out of the way.

### Fixed
- **The league was never saved.** The dropdown auto-selects the top league without
  firing a change event, so unless you manually switched leagues at least once, the
  config carried `league=""` forever — and everything that reads it (Item Check, the
  headless CLI, the example builder) got nothing. The selected league is now persisted
  as soon as the list loads. A saved league that no longer exists falls back to the top
  one instead of leaving the box blank.
- **Copy buttons could silently fail — and wipe your clipboard doing it.** The
  clipboard writer let Windows hand it a 64-bit memory handle through a 32-bit
  doorway; whenever the allocation landed above 4 GB the handle got mangled and the
  copy crashed *after* the clipboard had already been emptied. Intermittent by nature —
  it depended on where in memory Windows happened to place the text. Every Copy button
  in the app went through this. Both clipboard directions now use properly-typed calls.

## [v4.24.0] — 2026-07-13 — The app tells you what changed

Updating used to be a black box. The app would show you what was in an update **before**
you installed it — and then, once you were actually running it, never mention it again.
After this week's update crashes, people ended up on a new version with no idea what had
happened to them.

Now the first launch after an update opens a **What's new** panel with that version's
release notes. It appears once, then never again. The notes are saved at download time,
so it works with **no network** — and a brand-new user isn't greeted with a changelog
they have no context for.

### Fixed
- **Numbers looked wobbly.** Candara, Corbel and Constantia — the faces behind Delirium,
  Venom, Twilight and Ossuary — default to **old-style figures**: digits of differing
  heights that dip below the baseline like lowercase letters. Every number in the app
  (floors, prices, item levels) came out uneven on those themes. Lining figures are now
  forced on every theme.
- The release-notes panel rendered markdown badly: raw `*asterisks*` instead of italics,
  and uneven gaps because the source newlines were being printed on top of the
  paragraphs. It now renders properly, on one consistent rhythm.

## [v4.23.0] — 2026-07-13 — Exceptional bases: item level 79 is reachable now

The **Minimum item level** was hard-clamped to **80–82**, so you simply could not ask
for 79 — the box refused it.

That was wrong. An **ilvl-79 base can still roll the extra rune socket**, and those are
the ones worth crafting: a **79 Sacred Focus with two sockets goes for ~34 div**. The
clamp was throwing them on the floor.

The floor now goes down to **79**. (82 is still the default and still the max.)

## [v4.22.1] — 2026-07-13 — The floor "reset itself" to a huge number

Set the unique floor to **Chaos 1**, restart, and it came back as **60.57176 EXALT**,
spilling out of the box.

**Your floor was never wrong.** Floors are stored in exalt, and 1 Chaos really is
~60.57 ex — the bot was picking up exactly what you asked for. What broke was the
*display*: the app saved the number but forgot the **unit**, so it re-showed your chaos
floor as raw, unrounded exalt. It looked like the setting had been thrown away.

The unit is now saved alongside the floor, and the value is rounded. Set **Chaos 1**,
and tomorrow it still says **Chaos 1**.

(This release also carries v4.22.0, whose build failed to publish.)

## [v4.22.0] — 2026-07-13 — Minimize to tray is gone

It broke self-update. With tray mode on, closing the window didn't quit the app — it
hid it, and the process stayed alive **holding the `.exe` open**, so the new version
could never be swapped in and you were quietly relaunched into the old one.

It was also earning nothing. The setting existed "so auto-regenerate keeps running in
the background" — but **there is no auto-regenerate feature**. It was off by default,
yet the tray thread started on every launch regardless.

Closing the window now simply exits.

**The exe got smaller too.** The tray was the only thing using **pystray** and
**Pillow**, and Pillow is a heavy library. Both are gone — fewer moving parts, a
lighter download, and one less thing for antivirus to squint at.

## [v4.21.3] — 2026-07-13 — Update: it kept relaunching the OLD version

The crash is gone, but the update quietly did nothing: it downloaded the new exe,
closed, and then started **the version you updated from**.

**Minimize to tray was eating the exit.** With that setting on, closing the window
doesn't quit the app — it hides it and *cancels* the close, so auto-regenerate can keep
running. That is exactly right for a normal close, and exactly wrong for an update: the
process stayed alive in the tray, still holding the `.exe` open, so the swap could never
land. The helper waited, gave up, and relaunched the only exe there was — the old one.

An update now performs a real exit, whatever the tray setting says.

## [v4.21.2] — 2026-07-13 — Update: wait for the old exe to actually let go

Hardening on top of v4.21.1. A one-file `.exe` is really **two** processes — the
bootloader that unpacks it, and the app itself. The updater only knew the *app's*
process id, but the **bootloader outlives it**, still holding the `.exe` open while it
cleans up its temp folder. The helper could therefore start overwriting the exe inside
that window.

Windows lets you rename a running exe but never overwrite one, so the swap itself is
the only lock test worth trusting: the helper now **retries the swap until it succeeds**
(up to two minutes), and restores your previous version if it never does. You are never
left without a working app.

## [v4.21.1] — 2026-07-13 — Fixed: "Update" crashed the new copy on launch

A user pressed **Install update** and the app came back with an unhandled exception
instead of starting:

> `FileNotFoundError: [Errno 2] No such file or directory:`
> `'C:\Users\...\Temp\_MEI599002\base_library.zip'`

**Our bug, not their machine.** The app ships as a one-file `.exe`, which unpacks
itself into `%TEMP%\_MEIxxxxxx` at launch and advertises that folder in an environment
variable. The update helper we spawned **inherited that variable** — so when it
relaunched the *new* exe, the new copy assumed it was a child of the old one, **skipped
unpacking itself**, and tried to read from a folder the dying old process had already
deleted.

The helper now clears those variables, so the new copy unpacks itself properly.

**If this hit you:** the swap itself worked — your exe is already the new version.
Just **double-click it again** and it will start normally. (A `.bak` of the previous
version sits next to it either way.)

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

[v4.39.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.39.4
[v4.39.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.39.3
[v4.39.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.39.2
[v4.39.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.39.1
[v4.39.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.39.0
[v4.38.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.38.4
[v4.38.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.38.3
[v4.38.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.38.2
[v4.38.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.38.1
[v4.38.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.38.0
[v4.37.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.37.0
[v4.36.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.36.0
[v4.35.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.35.2
[v4.35.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.35.1
[v4.35.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.35.0
[v4.34.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.34.0
[v4.33.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.33.0
[v4.32.4]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.32.4
[v4.32.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.32.3
[v4.32.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.32.2
[v4.32.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.32.1
[v4.32.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.32.0
[v4.31.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.31.3
[v4.31.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.31.2
[v4.31.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.31.1
[v4.31.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.31.0
[v4.30.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.30.0
[v4.29.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.29.3
[v4.29.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.29.2
[v4.29.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.29.1
[v4.29.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.29.0
[v4.28.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.28.0
[v4.27.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.27.0
[v4.26.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.26.1
[v4.26.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.26.0
[v4.25.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.25.0
[v4.24.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.24.0
[v4.23.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.23.0
[v4.22.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.22.1
[v4.22.0]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.22.0
[v4.21.3]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.21.3
[v4.21.2]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.21.2
[v4.21.1]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/v4.21.1
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
