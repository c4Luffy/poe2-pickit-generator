---
name: release
description: Ship a new version of the pickit generator - bump version, update README changelog, run tests, commit, push, tag, and verify the GitHub release build.
---

# Release checklist (this repo)

`tools/release.py` automates steps 1-3 and 6-7 below: it runs every gate
(pytest, ruff, the app.html UI gate, the UI logic tests), writes
`version.py` from the version you pass, commits, pushes, tags, and (with `gh`
authenticated) waits for the build and can set the release notes. Prefer it:

    python tools/release.py X.Y.Z -m "subject line" --notes NOTES.md
    python tools/release.py X.Y.Z -m "subject" --notes NOTES.md --dry-run   # gates only

It does NOT touch CHANGELOG.md or the README for you — do step 4 by hand,
FIRST, before running it. Its own CHANGELOG check is a soft warning, not a
blocker, which is exactly how CHANGELOG.md has silently fallen many
releases behind the shipped version before — do not rely on the warning
alone; actually write the entry.

1. Ensure the working tree contains only the changes meant to ship; run:
   `python -m pytest -q` and `ruff check src tests` — both must be clean.
   (covered by `tools/release.py`'s gates)
2. Extract the `<script>` from `src/exilebot_pickit/webui/app.html` and run
   `node --check` on it. Run the id audit: every `$("id")` in the script must
   match exactly one `id="..."` in the HTML (no missing, no duplicates).
   (covered by `tools/release.py`'s gates, via `tools/check_ui.py`)
3. Bump `src/exilebot_pickit/version.py` — it MUST match the tag or CI fails.
   (`tools/release.py` writes this for you from the version you pass it)
4. Changelog lives in CHANGELOG.md: add the new version section at the top
   (+ its link ref at the bottom) — do this BEFORE running `tools/release.py`.
   Update the README "What's new" blockquote to the new version (2-4 lines +
   link to CHANGELOG.md). After tagging, attach real release notes with
   `gh release edit vX.Y.Z --notes-file …` (or pass `--notes` to
   `tools/release.py` and let it do this once the build is green).
   Wording rule: this app is a GENERATOR — write "generated pickits/rules do
   X", never "the bot does X" as if the app were the bot.
5. If any game-data lists changed in code, re-sync `game_data.json` and make
   sure `tests/test_remote_data.py` passes (it diffs JSON vs code).
6. Commit with a message starting `vX.Y.Z: `, push main, then
   `git tag vX.Y.Z && git push origin vX.Y.Z`.
   (`tools/release.py` does this for you, after the gates pass)
7. The Release workflow (test-gated) builds `ExileBot2PickitGenerator.exe`
   (name must NEVER change — the in-app updater depends on it) + SHA256SUMS.
   Verify with `gh run list` and `gh release view vX.Y.Z --json assets`.
   (`tools/release.py` watches the run and checks the assets for you if `gh`
   is authenticated)
8. Commit as c4Luffy only (git config already set) — no co-author lines.
