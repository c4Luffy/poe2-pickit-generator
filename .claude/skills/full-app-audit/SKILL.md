---
name: full-app-audit
description: Project-specific checklist for a full audit pass over the pickit generator - the same known weak spots this app has been bitten by before, so a review catches them every time instead of whatever the reviewer happens to think of.
---

# Full app audit checklist (this repo)

This project runs periodic full audits (the changelog has close to a dozen of
them — v4.34.0, v4.38.4, v4.39.0, v4.40.0, and more), and each one finds real
bugs. This skill is the fixed list of known weak spots to check every time,
so an audit doesn't depend on the reviewer happening to remember the same
things the last one did. Use `/code-review` (or a subagent) for the general
"is this code good" pass; use THIS list for the app's own history of specific
failure modes.

## Rule-writer honesty

- **Quote escaping**: does every rule builder that interpolates an external
  name (poe.ninja `name`/`baseType`, not our own curated literals) go through
  `_quote_ipd()`? `build_unique_lines` was found missing this in v4.41.18 —
  check every builder in `generator.py` and `generators/assembly.py` again,
  the same way.
- **The "always kept regardless of price" guarantee**: does it reach EVERY
  payload shape a name could be priced under (exchange-shaped AND
  unique-shaped), not just the one shape that happens to be common today?
  `build_unique_lines` was missing `force_names` entirely once.
- **Type-less rules**: no active `[StashItem]` rule may lack a
  `[Type]`/`[Category]`/`[WeaponCategory]` condition — that matches EVERYTHING
  on the ground. `test_no_active_rule_is_typeless` in `test_webui_api.py`
  checks this against a FULL generate; re-run it, don't just eyeball rules.
- **Two writers, one truth**: any rule emitted by more than one code path
  (economy force-branch vs a static builder, e.g. Special Items) must agree
  byte-for-byte on the action — they disagreed on `[IgnoreRitual]` once.

## Data correctness

- **Stat ids and weights**: run `python tools/check_game_data.py` — catches
  renamed/removed stat ids and weights that don't match their `# T1 max N`
  comment. See the `add-rare-stat` skill for the full process.
- **Base droppability**: a base in the game's item table is not proof it
  drops (legacy defs, `[DNT]` placeholders, unique-only `...Unique<N>` paths,
  anvil-only `Runeforged `/`Runemastered ` prefixes). Cross-check against
  NeverSink's live filter, not just the item table.
- **`game_data.json` ↔ code**: run `tests/test_remote_data.py` — it diffs the
  bundled JSON against the code defaults field by field. A silent one-way edit
  has broken this before (JSON updated, code not, or vice versa).

## Config and file safety

- **Save atomicity**: does every write (config, `.ipd`, `.filter`, the bot's
  `pickit.ini`) go temp-file-then-`os.replace`, with a UNIQUE temp name per
  save (not a shared `*.tmp`)? A shared temp name caused real, repeated config
  corruption in production before it was fixed.
- **Backup name collisions**: any two `output_base` values where one is a
  prefix of the other (e.g. `pickit` and `pickit-strict`) must never share a
  backup file — check `_is_backup_name`'s anchored regex is still what
  `list_backups`/`restore_backup`/`clear_backups`/`backup_diff` all use.
- **Failure must be honest**: does `save_config` (and everything that calls
  it) return whether the write actually landed, rather than a hard-coded
  success? ~25 bridge methods were once claiming "Saved" on a failed write.

## UI (app.html)

- Run the `ui-edit-check` gate (`node --check`, id audit, bridge audit) —
  this catches a dead-app-on-launch bug, not a cosmetic one.
- Any control added must be reachable AND styled — `class="sw"` (not a real
  CSS class) once shipped an invisible, unclickable master switch for a whole
  release.
- Orphan-class warning from `tools/check_ui.py`: a class used in markup with
  no CSS rule for it.

## Process

- **CHANGELOG.md**: run the `changelog-sync` skill's quick check — has it
  drifted behind `version.py` again?
- Verify every finding by reproducing it against the actual current code
  first (read the file, don't rely on a past changelog entry describing old
  behavior) — the codebase moves fast enough that a two-week-old assumption
  can already be wrong.
