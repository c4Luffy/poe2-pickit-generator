"""Single source of truth for the app version."""
VERSION = "4.36.0"

# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Filters now color by REAL value: mythic (1+ Divine, purple), jackpot (10% of a Divine, red), high (10+ ex, orange), useful (1+ ex), quiet — read from each rule's own recorded price. Chance, craft, fracture (pink) and exceptional (cyan) bases wear their purpose colors.
• Converting a generated pickit keeps every tier — and the report now shows what got which look, in the exact colors.
• One clean community look, a live on-the-ground preview (with your own capture as the ground), minimap icons and beams included. No filter sounds, ever.
• One-click 🔓 All ON + Generate next to the Generate button: flips every switch back on, keeps your floors, runs the full generate.
• Chance Bases show the unique you're chancing for with real game art; the list is curated to four bases.
• Gold is never hidden, in both filters. Prices auto-refresh every 15 minutes.
• Economy names wrap instead of truncating; the run log wraps paths cleanly and is resizable; the CLI gained --filter-theme."""
