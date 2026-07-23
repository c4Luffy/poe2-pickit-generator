---
name: changelog-sync
description: Check whether a user-facing change needs a CHANGELOG.md / README entry, right when the change is made - not saved up for release day, which is how CHANGELOG.md fell many versions behind before.
---

# Keeping CHANGELOG.md and the README in sync (this repo)

`CHANGELOG.md` has fallen multiple releases behind the shipped version before
— its newest entry sitting several versions earlier than `version.py`, the
README, and the actual GitHub release. The `release` skill's own gate for this
is a SOFT warning (it prints a message but doesn't block), which is exactly
why the drift wasn't caught at release time. This skill exists to catch it
earlier: at the moment the change is made, not batched up later.

## When to run this

Any time you finish a change a real user would notice — a behavior fix, a new
tab/feature, a data correction that changes what the pickit picks up, a UI
change. Not for pure refactors, internal test-only changes, or dependency
bumps with no visible effect.

## What to do

1. **Add the CHANGELOG.md entry now, not at release time.** New section at the
   top, above the most recent one:
   ```
   ## [vX.Y.Z] — YYYY-MM-DD — Short, plain-language title

   - **What changed, in bold** — why it mattered, in plain language. Follow
     the existing entries' voice: concrete numbers over vague claims ("all 24
     items" not "some items"), the actual symptom before the fix, wording rule
     that this app is a GENERATOR ("generated pickits/rules do X", never "the
     bot does X" as if the app were the bot).
   ```
   Add the matching link reference at the bottom of the file
   (`[vX.Y.Z]: https://github.com/c4Luffy/poe2-pickit-generator/releases/tag/vX.Y.Z`)
   even before the tag exists — the link just won't resolve until release day.
2. **Update the README's "Current release" section** the same way, but keep it
   short: 2-4 lines, not the full CHANGELOG prose. It's a condensed pointer,
   not a duplicate — older entries belong in CHANGELOG.md, only the newest
   handful stay in the README's collapsible.
3. **If you're not sure this version has shipped yet** (no tag cut), that's
   fine — write the entry under whatever the NEXT version will be. It gets
   corrected at release time if the number changes; an undocumented change is
   a bigger problem than a provisional version number.
4. Before actually cutting a release, still follow the `release` skill in
   full — this skill only prevents the entry from being forgotten in the first
   place. It does not replace the release checklist.

## Quick check

`grep -c "^## \[v" CHANGELOG.md` then compare the top entry's version against
`src/exilebot_pickit/version.py`'s `VERSION` — if they don't match and you
just shipped a user-facing change, the entry is missing. Don't wait for the
release skill to catch it later.
