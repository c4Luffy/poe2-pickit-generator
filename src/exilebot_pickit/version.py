"""Single source of truth for the app version."""
VERSION = "4.36.0"

# Shown by the in-app "What's new" dialog. Lives HERE so it ships inside the
# exe and works offline / while GitHub is unreachable — the dialog used to
# show only "See the release page for details." whenever the release fetch
# failed. Update together with VERSION on every release.
HIGHLIGHTS = """\
• Label themes — pick once, both filters the app writes wear it (generated + converted), with a live on-the-ground preview.
• Community classic is the default: colors, sizes and minimap icons taken verbatim from NeverSink's live PoE2 filter. Also: Minimal, High contrast, Colorblind safe.
• Jackpot tier: drops worth 50+ exalted (and always Mirror of Kalandra / Divine Orb) get the red screamer with a light beam. No filter sounds, ever.
• Gold is never hidden, now in the generated filter too.
• Chance Bases show the unique you're chancing for with real game art; the list is curated to four bases.
• Prices auto-refresh every 15 minutes — no more nudging a slider for today's divine rate.
• Economy names wrap instead of truncating; the run log wraps paths cleanly and is resizable; the CLI gained --filter-theme."""
