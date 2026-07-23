"""Single source of truth for the app version."""
VERSION = "4.41.22"

# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Preview stopped inventing skipped rules. It read "9 skipped" on a pickit with nothing disabled at all — those 9 were the "// Example:" lines of the syntax guide the app began writing into every .ipd in 4.41.18. They contain [StashItem], so a plain substring test counted them as rules you had switched off. The same miscount fed the Generate tab's "skipped" tile and the command line's "Commented out:" total, so three places reported a number that was never real. All three now count a rule only if it carries the action AND the "#" identify split and isn't a guide example.
• The Chance tab shows what chancing REALLY rolls. Each base now lists every unique that shares it, dearest first, with live prices — so "a Utility Belt is far more often an Ingenuity than a Mageblood" becomes data you can see (Mageblood at 327 div sitting next to the 1 ex outcomes) instead of a warning you take on faith. The jackpot is highlighted, and the list is read-only so reading it can never toggle the base off.
• Chance prices stopped flipping units at random. A ~46 ex unique showed as a useless "0,1 div" while a 13 ex one correctly read "13,5 ex" — divine was used whenever a divine rate existed, however tiny the result. Divine now appears only once something is actually worth a divine or more.
• Diagnostics you paste for help are readable. The report ended with 30 identical "INFO config saved" lines, which pushed the one line explaining the problem off the end. Repeats now collapse to "(x30)", and any ERROR or WARNING is kept even when older than the window, so the useful line survives the noise.

Also in 4.41.21:
• Prices load in the background the moment the app opens, so the wait is gone. Opening Economy used to fetch 24 poe.ninja price lists on the spot — five at a time, with a back-off whenever poe.ninja rate-limited — and you watched "Loading prices…" for it. That same fetch now starts in the background at launch, while you're still on Generate, so the tab is normally ready the instant you click it. Everything that reads prices shares the one cache, so Generate, the Chance tab and Auto-floor all get the same head start. Nothing else changed: prices are just as fresh, and Refresh prices still forces a live re-fetch.

Also in 4.41.20:
• The Economy tab has hover cards now. Hover any item and a card shows its art, live price, 7-day trend, keep/skip status, and the exact pickit rule that catches it — so you can see at a glance what any row actually does. Click a row to PIN the card open; pinned, it gets a Copy button and its own keep/skip toggle, and stays put until you close it with ✕, Esc, or a click anywhere else. Unpinned it is a pass-through tooltip, so it never covers the row's own buttons.
• Right-click any Economy row to copy its pickit rule instantly, without opening anything.
• Value bars sit behind each price — a faint fill, scaled logarithmically, that shows worth at a glance. A one-ex common and a multi-thousand-ex chase item both read now, instead of everything but the top few flattening into identical slivers.
• The Economy sidebar groups collapse. General, Equipment, Atlas and Always pick each fold with a click, so the whole category list fits without scrolling.
• Clicking a row no longer turns its rule off by accident — only the keep/skip button toggles it now. A stray click while reading the table can't silently drop a rule.
• The Economy tab is faster: rule lookups are cached, so repeat hovers and copies are instant instead of hitting the engine every time.
• Generate shows a toast the moment a run starts and again when it finishes (with the rule count and time), so pressing it is never silent — including from the Ctrl+G shortcut.

Also in 4.41.19:
• Regular and unique tablets are priced live now, not hardcoded. poe.ninja added real pricing for both — Precursor Tablets (Overseer, Abyss, Breach, Ritual, Irradiated, Temple, Delirium; priced separately per rarity, Normal/Magic/Rare) and Unique Tablets (all nine) — so generated pickits now respect the normal value floor for tablets like every other market item, instead of force-picking every rarity regardless of what it's actually worth. Some are genuinely valuable (a Normal Ritual Tablet has been worth close to a Divine).
• Both show up as their own Economy categories under Atlas, matching how poe.ninja itself groups them, with live prices, 7-day trend arrows and per-item switches. Precursor Tablets are further grouped by tablet type, with each type's Normal/Magic/Rare rows kept together — the same idea as Exotic Bases grouping by gear slot.
• The Economy sidebar now matches poe.ninja's own layout exactly — section names, order, and item order within each section (General, Equipment, Atlas), checked directly against the live site. Waystones moved out of General into Always pick, since poe.ninja doesn't price it at all and every tier is always kept regardless of value.

Also in 4.41.18:
• A full audit pass — 5 parallel reviews of the rule engine, the bridge, the UI, the data files and config safety, every finding verified by hand before anything shipped. Real fixes: item/unique names with a literal double-quote could corrupt a rule’s syntax (latent — no live item has one today, but the quoting helper existed and 4 call sites weren’t using it); the "always kept regardless of price" guarantee had no way to apply to a name ever priced under a unique-shaped payload (also latent, but the guarantee is supposed to be unconditional); clicking a column header on an Always-pick view (Tablets, Exotic Bases) painted a sort arrow that lied — the rows never actually sorted; and the app’s own embedded syntax guide ([WeightedSum], [IgnoreRitual], WeaponCategory) existed, fully written and tested, but neither writer ever called it — no generated file has ever shipped it until now. Two small data cleanups: an exotic-base slot entry left over from a removed item, and a stronger test so the slot map can’t drift in either direction again.

Also in 4.41.17:
• The strictness controls explain themselves now. Each slot shows a real example — e.g. "a T1 Life + T1 Spirit + T1 Fire res rare scores ≈ 300, clears ≥ 250, kept" — built from that slot’s own stats, and the global dial lists the actual cutoffs (Looser 200 · Balanced 250 · Strict 312 · Very strict 375). The per-slot control no longer had a "Default" button that duplicated whatever the global was set to (two "Looser" side by side); it just highlights the level in effect, with a "↺ Follow the global dial" link when a slot is overridden.

Also in 4.41.16:
• A headless refresh for scheduled tasks: <code>python -m exilebot_pickit --regenerate</code> rebuilds the pickit from your SAVED settings — floors, every switch, rare-gear strictness (global and per-slot), the output folder and auto-copy to the bot — without opening the window. Add <code>--league "Name"</code> to override the league. Point Task Scheduler at it to keep the bot’s loot list fresh on a timer.

Also in 4.41.15:
• Each rare slot can set its own strictness. The dial at the top is still the default for everything, but open a slot (Body Armour, Helmet, …) and there’s a per-slot row: leave it on Default to follow the global dial, or override just that slot — Body Armour Very strict while Helmet stays Looser. Each slot’s cutoff and rules update to match.

Also in 4.41.14:
• The Magic & Rare tab has a strictness dial. Rare gear is kept by a score, and until now that bar was fixed. Pick Looser / Balanced / Strict / Very strict and every slot’s score cutoff scales together — Balanced is the tuned default, stricter keeps fewer but better rares. The recipes (which stats, what weights) don’t change, only the bar they clear, and the numbers shown on the tab are exactly what gets written.

Also in 4.41.13:
• Generate now checks its own poe.ninja coverage. If a whole category comes back empty — the fingerprint of poe.ninja renaming or retiring a type, which silently stops the app pricing that category (exactly how Verisium went unfetched for weeks) — a warning banner tells you right after Generate instead of you noticing loot going unpicked days later. Waystones, which poe.ninja never prices, is allowlisted so it never false-alarms.
• The "What’s new" button is a rounded pill now, and lifts a little on hover — small polish on the button added last version.

Also in 4.41.11:
• Pinnacle keys are always kept now, whatever the price. Reliquary keys, Crisis Fragments, Origin fragments, Simulacrum and Call of the Shadows used to be commented out when they dropped below your value floor — so a cheap key you were collecting got skipped. They now stay in the pickit regardless, like the boss invitations always have.
• A visible "What’s new" button. The version number opened this changelog but nobody knew to click it — there’s a proper button under the title now.
• Resetting settings keeps your theme. Reset still turns every toggle back on and clears your floors, but it no longer repaints the app back to the default look.

Also in 4.41.10:
• The Keys view reads clearer. Its 20 keys now sit under four headings — Crisis Fragments, Origin, Reliquary Keys and Boss Invitations — instead of lumping the crisis and origin sets into one "Pinnacle Keys" block. And an item poe.ninja doesn’t price (Raven’s Reflection) now says "No price · always kept" in the value column instead of just "always picked", so a missing number reads as intended rather than broken.

Also in 4.41.9:
• 15 more dead exotic bases removed — 17 total with the two staves in 4.41.8. Each exists only as a specific unique’s base and never drops as a plain white or rare, so its pickit rule could never fire: Runic Fork (Runeseeker’s Call), Ornate Ringmail (Loreweave), Glacial Fortress (Nightfall), the three Decree armours, and more. You confirmed each on the trade site — every one lists only as its unique, never as a base. The uniques themselves are still picked up from poe.ninja, so no loot is lost; only the never-firing base rule is gone.

Also in 4.41.8:
• Two dead staff bases removed. Reflecting Staff and Perching Staff were in the exotic-bases list, but neither drops as a white or rare — each exists only as the base of a unique (Atziri’s Rule and The Raven’s Flock). The exotic-base rule for them could never fire; the real unique rules are untouched, so you still pick up Atziri’s Rule. Reflecting Staff was confirmed dead back in 4.39.1; Perching Staff is its exact twin.

Also in 4.41.7:
• A "Keys" view gathers every boss key in one place. There are 20 — seven pinnacle keys, nine reliquary keys and four boss invitations — but poe.ninja scatters them across Fragments and Omens, and one (Raven’s Reflection) has no price at all, so you could never see the set. The new Keys entry (top of the sidebar, next to Top movers) reads across those categories and groups them under Pinnacle Keys, Reliquary Keys and Boss Invitations — each with its live price. It is a lens, not a new category: keeping or skipping a key here is the same switch as in Fragments, so nothing is duplicated. The old one-item "Pinnacle Keys" always-pick entry is folded into it. Removed content stays out — poe.ninja does not price the Calamity Fragments, so they are not listed.

Also in 4.41.6:
• Tablets and Exotic Bases are split into sections inside their own category, instead of into separate categories. Tablets reads "Tablets" (7) then "Unique Tablets" (9); Exotic Bases groups its 48 by gear slot — Amulets, Rings, Belts, Body Armours and on through the weapons — so you can find the rings without reading a 48-row alphabetical run. Slots come from the game's own files, because the name does not give it away: "Veridical Chain" is an amulet, "Primal Markings" a body armour, "Runic Fork" a wand. The headings only appear in the unsorted view, so a column sort can never scatter them.

Superseded from 4.41.5:
• Base and unique tablets are separate categories. Sixteen rows read as one undifferentiated list — the seven tablets you juice maps with, then nine uniques mixed in below them. They are "Tablets" (7) and "Unique Tablets" (9) now.

Also in 4.41.4:
• The always-pick section is split into real categories. Tablets, wombgifts, pinnacle keys and exotic bases each get their own sidebar entry, so Raven’s Reflection — a Delirium boss key — is no longer filed under "Fragments" next to splinters and wombgifts, three unrelated things that only ever shared a bucket. Switches you had already turned off in the old bucket stay off.

Also in 4.41.3:
• The Economy grouping added in 4.41.2 is removed. Collapsing families like "Thaumaturgic Flux (Level 8-20)" and the Reliquary Keys into labelled blocks sounded tidy and made the tab worse to use, so it is gone — every category reads exactly as it did before. Raven's Reflection keeps the artwork that shipped alongside it.

Removed from 4.41.2:
• Level families group together in Economy. "Thaumaturgic Flux (Level 8…20)" is thirteen rows that read as one item, and a value sort scattered them all through the table — you could never see the set at a glance or tell which levels you already had. Each family now sits in one block under a labelled rule, positioned where its best-priced member ranked so nothing valuable gets buried. Sort by name and they run 8, 9, 10… in level order; sort by value and they reorder inside the block, so clicking a column still does what you asked.
• Raven's Reflection has its artwork. It has no poe.ninja price row, so the Economy tab's usual fallback to poe.ninja art never fired for it — the icon is embedded from the game's own files instead, and works offline like every other shipped icon.

Also in 4.41.1:
• Refined Necrotic Catalyst (~136 ex) is picked up again. Both Necrotic Catalysts were suppressed on the grounds that "Exiled Bot's validator rejects these base types" — but that is a claim about the validator, not about whether the item drops, and it was costing a real pickup. Your pickit already carries five names that same validator flags and the bot loads it fine, and the app already picks up Refined Sibilant Catalyst — the identical family.

Also in 4.41.0:
• A whole poe.ninja category was never being fetched. "Verisium" has always been served and this app never asked for it, so all 24 of its items had NO rule at any floor — your bot was walking past Celestial Alloy at ~308 ex, Warding Starlit Ore at ~143 ex, and 14 more worth over 1 ex. Now fetched like every other category, so it prices and updates itself.
• Raven's Reflection is picked up. The Delirium pinnacle key, dropped from Simulacrum, had no rule at all: poe.ninja prices it in no category, and almost every rule this app writes comes from a price — so an unpriced valuable is invisible unless it's named in the always-pick list. It is now.

Also in 4.40.1:
• "Hide everything else" now remembers your choice, and starts OFF. It was hardcoded ON in the markup and never saved — so anyone who turned it off, which the warning directly beneath it tells botters to do, got it back at every launch.
• Restoring a backup no longer claims "nothing is lost". It swaps the FILE only; your settings are untouched, so the next Generate overwrites it. The dialog says that now instead of implying otherwise.
• Item Check warns when your floors have changed since the pickit was built. It answers with your CURRENT settings, but the tab reads as answering about the pickit your bot is running — exactly the sequence you hit after tightening a floor to stop the bot grabbing junk.
• "Disable all" in Economy asks first. It flipped up to ~1900 items with no undo and no confirmation.
• An empty search says so, instead of leaving a blank table that looks like a failed load.
• Craft: set the item level on every base at once instead of 27 steppers one click at a time. Respects the current search.
• Create your filter scrolls to the result, which used to render below a full-width screenshot so the conversion looked like it did nothing.
• Fracture grades finally say what they mean: S+ best in slot, S excellent, A+ strong, A worth keeping.

Also in 4.40.0:
• Item Check stops telling you the bot will walk past things it actually takes. Paste a Waystone and it said "ignored" — while your pickit grabs every waystone. An Uncut Skill Gem got "nothing targets this" against 20 active rules, because in-game it's just "Uncut Skill Gem" while the rules name "Uncut Skill Gem (Level N)". A Magic flask got the same, because only Rare gear had a branch. All three answer correctly now.
• Item Check's error messages were invisible. They were rendered into a box the stylesheet keeps hidden, so a paste it couldn't read made the Check button look completely dead — no result, no error, nothing.
• The setup wizard no longer overwrites your floors behind your back. It applied "Balanced" the moment you ARRIVED at the loot step, so a new user's floors went 0/0 to 2/6 just by pressing Next — quietly undoing the "first run picks up everything" default — and re-running setup did the same to hand-tuned floors. Balanced is still marked Recommended; now it waits for your click.
• Clicking "Turn everything on" twice no longer hides the way back. The second click flips nothing, and the button was keyed to that — so it vanished while your original settings were still safely held.
• The command line stopped writing five duplicate rules (the three Special Items and both splinters), and now validates the file it writes, like the GUI always has.

Also in 4.39.5:
• Two more honesty fixes in Create your filter. The report counted every comment line as a "disabled rule", so a normal pickit claimed 202 rules were switched off when the real answer was zero — section headers and the banner were being counted. And an imported pickit whose value read "1e3" was styled as barely useful: only the "1" was matched, so a 1000 ex item got a 1 ex label. A negative value found no number at all and fell through to section colouring instead of quiet.

Also in 4.39.4:
• Create your filter stops calling a dropped condition "converted". That report's honesty is the whole point of the tab, and a condition it RECOGNISED but could not read simply vanished — an [ItemLevel] written without quotes, a [Quality] using > instead of >=, or an ItemLevel floor AND ceiling where only the floor was taken. Those rules were counted as cleanly converted while the gate was gone from the filter. They now count as "shown wider", which is what actually happened. Pickits this app generates are unaffected — their numbers don't move by a single rule.

Also in 4.39.3:
• Implicits are finished. 27 bases showed a blank line where the game gives them a real implicit — including ones that change how you use the item: Corona Amulet grants a HELMET socket, Grasping Ring a GLOVE socket, Stalking Belt a BOOT socket, Forking/Invoking/Sinew Belt an extra charm slot, and Grasping Mail can also roll ring modifiers. 52 entries became 79.
• Five implicits were showing the wrong number. Grand Spear read "+25 Weapon range" when the game stat is a PERCENTAGE — +25%, not a flat 25. Same for Striking Quarterstaff, Flexed Crossbow, Utility Belt (20% of flask recovery is instant) and Warlord Cuirass. Thane Mail showed "+15-25% ... -" with the stat id's trailing minus rendered as text; it is a REDUCTION, so it now reads -15-25%.
• Two-Stone Ring is three different bases — fire+cold, fire+lightning and cold+lightning — and we displayed the cold+lightning roll for all three. It now says which pairs exist.
• A test now cross-checks every implicit against the game's own files, so a base can't ship blank and a percentage can't lose its % sign again.

Also in 4.39.2:
• The bot can now buy An Audience with the King back from a Ritual altar. Its rule carried [IgnoreRitual], which tells the bot not to spend tribute on it — but that item IS the Ritual pinnacle fragment, so a Ritual reward window is exactly where you want it. The flag could only cost you: if the item shows up in the window the bot walked past ~50 ex, and if it only ever drops on the ground the flag did nothing at all. Expedition Logbook and Kulemak's Invitation keep the flag — the Logbook is a real ground drop, so not re-buying a copy with tribute is a genuine saving, and the Invitation is Abyss content where the flag never applies.

Also in 4.39.1:
• First run now picks up EVERYTHING. Both value floors were already 0, but the two exceptional gates defaulted to quality 25 / item level 82 — so a brand-new user's first pickit quietly skipped exceptional bases while the screen said "Picking up everything". They now open to 21 / 79, the loosest legal values. Anyone already running keeps their own settings.
• Three staves and a sceptre corrected. Permafrost Staff and Reflecting Staff exist ONLY as The Whispering Ice and Atziri's Rule — a white or rare one never drops, so every non-unique rule naming them was dead. Removed. Shrine Sceptre was caught by the same sweep, wrongly: it has three ordinary variants as well as a unique host, so it drops fine and stays. Sanctified Staff and Paralysing Staff fill the staff slot back to three.
• Crafting on staves never actually worked — the only staff in the craft list was one of the two that cannot drop. Ravenous Staff replaces it.
• The bundled item lists and game_data.json can no longer drift apart unnoticed; a stale copy of one is exactly how offline and online users end up with different pickits.

Also in 4.39.0:
The second half of the audit — nine more real bugs:
• Top movers can finally show uniques. Prices were joined to an items table by id, but unique data carries the name on the row itself, so every unique was skipped and all 7 unique categories recorded ZERO prices. Mageblood could double and the panel stayed empty. It now records 438 unique prices for a full league.
• A broken game_data.json can no longer strip your base rules. That file self-updates from GitHub, and a truncated copy passed validation and silently deleted 16 of 17 base categories. A remote copy may now add bases but never delete a category, and a name that would produce a rule matching EVERYTHING on the ground is rejected outright.
• Backups stop touching other profiles. Any two output names where one is a prefix of the other collided, so rotation deleted its own backups while keeping the other profile's — and Restore could put the wrong pickit on your bot.
• A shared profile can no longer break your app. Its values were saved BEFORE they were checked, so a bad one killed Generate for the rest of the session and could write your .ipd outside the output folder permanently.
• "Saved" now means saved. If the config file can't be written you are told, instead of seeing a green toast and losing the setting at next launch.
• The Economy tab can no longer hang forever. A failed price poll left a timer running and pinned the tab on "Loading prices…" until you restarted — and every revisit started another one.
• Auto floor redraws its sliders instead of leaving them frozen at the old position.
• Ctrl+1…0 match the sidebar exactly again (Ctrl+4 was opening History). With 14 tabs and 10 digits, Magic & Rare no longer has a binding — it only ever had one because of that off-by-one.
• The command line stops passing off month-old cached prices as today's.

Also in 4.38.4:
• The bot no longer spends Ritual tribute on An Audience with the King, Expedition Logbook or Kulemak's Invitation. When poe.ninja prices one of the three Special Items, the economy section emits it — and it was writing the rule WITHOUT [IgnoreRitual], the one flag those three exist to carry.
• The .filter written beside your pickit keeps its item-level gates. All 262 of them were being dropped, so 68 base types lit up from act 1 onward — and that filter disagreed with the one Create your filter produces from the same pickit. They now match exactly.
• Clicking "Turn everything on" twice no longer destroys the undo. The second click overwrote the snapshot with the already-on state, so "Put my switches back" restored all-on and your floors were gone.
• The item report no longer lists uniques the pickit doesn't contain — it claimed 440 included where the file had 227 (my own miss in 4.38.3).
• One hand-edited or ANSI .ipd in the output folder used to break generating forever. It aborted before the write, so the bad file stayed and every later run failed the same way.
• A bad saved window size no longer stops the app from opening at all — no window, no message, every launch.

Also in 4.38.3:
• Uniques priced on an anvil-only base no longer produce a dead rule. Runeforged/Runemastered bases are crafted at the anvil and never drop, so the generator used to strip the prefix and target the plain base instead — but the plain base doesn't always exist. The Prisoner's Manacles was targeted on "Verisium Cuffs", which the game has never had, so the rule could never fire and Exiled Bot's validator rejected the file. Those rows are dropped now: Rathpith Globe, Voll's Protector and The Prisoner's Manacles each keep a rule on the base that really drops.

Also in 4.38.2:
• This dialog no longer announces an update with nothing but a link. When a release is published before its notes are written, GitHub fills the body with a lone "Full Changelog" URL — the updater stashed that and showed it instead of these highlights, which ship inside the exe. A stashed body with no actual prose in it now loses to this list.

Also in 4.38.1:
• Exceptional: Shields and Foci no longer waste two thirds of the width. Every category was pinned to three attribute columns so Str | Dex | Int would line up — but Shields only has Str bases and Foci only Int, leaving one filled column beside two empty ones. Categories now get as many columns as they actually have.

Also in 4.38.0:
• 🔓 Turn everything on now really does: both floors drop to 0, Adaptive floors switch off and exceptional gates open to quality 21 / ilvl 79 — before, Adaptive floors quietly re-filtered everything you just enabled. "Put my switches back" restores it all.
• Setting a floor by hand now turns Adaptive floors OFF instead of ignoring you — your number sticks.
• Item Check no longer answers "no rule matches" for a QUALITY white base. Items copy as "Superior <Base>" when they have quality, and that prefix was never stripped — so the exact bases the Exceptional tab collects were answering wrong. Magic items resolve now too.
• Every base shows its implicit (Gold Ring +6-15% Item Rarity, Visceral Quiver +20-30% Attack Crit Chance), read from the game's own data files.
• Chance cards show the live price of the unique you're chancing FOR, with art for every possible target.
• Profiles export/import to a file — and importing previews what a profile contains, naming in amber anything it turns OFF, so a shared profile can't quietly disable Divine Orb.
• Preview: click any rule to see why it's there and what it's worth; compare against a backup to see exactly which rules changed.
• Economy: "Top movers" — the 20 biggest 7-day price swings across every category.
• Create your filter: one click loads the pickit your bot is actually running; ItemLevel and WaystoneTier now translate exactly.
• Debug rebuilt around three plain-language actions, and it no longer alarms you with old, long-fixed errors.
• Craft and Exceptional lay out properly instead of one long column; Exceptional groups Str / Dex / Int with hybrids separate."""
