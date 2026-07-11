---
name: release
description: Ship a new version of the pickit generator - bump version, update README changelog, run tests, commit, push, tag, and verify the GitHub release build.
---

# Release checklist (this repo)

1. Ensure the working tree contains only the changes meant to ship; run:
   `python -m pytest -q` and `ruff check src tests` — both must be clean.
2. Extract the `<script>` from `src/exilebot_pickit/webui/app.html` and run
   `node --check` on it. Run the id audit: every `$("id")` in the script must
   match exactly one `id="..."` in the HTML (no missing, no duplicates).
3. Bump `src/exilebot_pickit/version.py` — it MUST match the tag or CI fails.
4. Changelog lives in CHANGELOG.md: add the new version section at the top
   (+ its link ref at the bottom). Update the README "What's new" blockquote
   to the new version (2-4 lines + link to CHANGELOG.md). After tagging,
   attach real release notes with `gh release edit vX.Y.Z --notes-file …`.
   Wording rule: this app is a GENERATOR — write "generated pickits/rules do
   X", never "the bot does X" as if the app were the bot.
5. If any game-data lists changed in code, re-sync `game_data.json` and make
   sure `tests/test_remote_data.py` passes (it diffs JSON vs code).
6. Commit with a message starting `vX.Y.Z: `, push main, then
   `git tag vX.Y.Z && git push origin vX.Y.Z`.
7. The Release workflow (test-gated) builds `ExileBot2PickitGenerator.exe`
   (name must NEVER change — the in-app updater depends on it) + SHA256SUMS.
   Verify with `gh run list` and `gh release view vX.Y.Z --json assets`.
8. Commit as c4Luffy only (git config already set) — no co-author lines.
