"""Single source of truth for the app version."""
VERSION = "4.38.4"

# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
A five-way audit of the whole app. Six real bugs, found and fixed:
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
