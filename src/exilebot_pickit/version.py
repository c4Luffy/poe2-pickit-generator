"""Single source of truth for the app version."""
VERSION = "4.41.5"

# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
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
