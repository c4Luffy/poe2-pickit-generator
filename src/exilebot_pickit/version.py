"""Single source of truth for the app version."""
VERSION = "4.38.2"

# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
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
