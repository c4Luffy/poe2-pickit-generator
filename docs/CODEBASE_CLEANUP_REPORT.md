# Codebase Cleanup Report

## Context

The owner requested a full codebase cleanup/reorganization, described in
generic React/TypeScript terms: `src/app`, `src/features/*`,
`src/components/ui`, `hooks/`, PascalCase component files, and so on. This
repository is not a React/TypeScript project — it's a Python desktop app
(`src/exilebot_pickit/*.py`, already organized into `api/`, `data/`,
`generators/`, `ui/`, and `webui/` subpackages) plus a single self-contained
vanilla-JS HTML file (`src/exilebot_pickit/webui/app.html`) with no build
step and no bundler. Applying the requested structure verbatim would not
map onto anything real here and would actively fight the app's packaging
model (single-file HTML shipped inside a PyInstaller exe).

We explained this mismatch to the owner and got approval for a scoped,
realistic alternative instead: extract one large, clearly-scoped data block
out of `generator.py` into its own module (matching the pattern already
used for `data/corrections.py` and `data/base_types.py`), and produce the
two reference documents in this `docs/` folder rather than force a
structure that doesn't fit the project.

## What was moved

The Fracture Bases data and logic — `FRACTURE_CLASS_GROUPS`,
`FRACTURE_TARGETS`, `FRACTURE_TIERS`, `FRACTURE_EXCLUDED_UNVERIFIED`, and
the `fracture_*` / `build_fracture_pickit_rules` / `classify_fracture_item`
functions (roughly 495 lines) — moved out of `generator.py` into a new
`src/exilebot_pickit/data/fracture_bases.py` module. `generator.py`
re-exports these names, so existing code that does `gen.FRACTURE_TARGETS`
(or calls the fracture helper functions through the `generator as gen`
compatibility surface) keeps working unchanged. This follows the same
pattern already established for `data/corrections.py` and
`data/base_types.py`: the submodule owns the definition, `generator.py`
re-exports it for backward compatibility.

## What was NOT moved/renamed, and why

- **`webui/api.py` (1,299 lines)** was left alone. It's a single class,
  `AppApi`, exposed as one pywebview bridge object — JS in `app.html` calls
  `api().someMethod()` against that one object. Splitting the class across
  multiple files would fight the framework (pywebview exposes one object)
  for no real benefit; it would just add import indirection without
  reducing coupling.
- **`webui/app.html` (1,792 lines)** was left alone. It is architecturally
  required to be a single file: it ships as one asset inside the exe with
  no build step, no bundler, and no module loader. Splitting it into
  multiple files would require introducing a bundler — a much larger and
  riskier change than a cleanup pass, and out of scope for what was
  approved.
- **No files were renamed.** An audit of the repository found no vague or
  unclear module names (no `helper.py`, `utils.py`, `utils2.py`,
  `final.py`, etc.) anywhere in `src/exilebot_pickit/`. The existing naming
  convention (`snake_case.py`, descriptive names) was already being
  followed consistently, so there was nothing to fix.
- **No files were deleted.** An audit found no dead code, no orphaned
  modules, and no unused imports worth removing as part of this pass.

## Remaining technical debt

These are genuine future considerations, not urgent problems:

- **`webui/api.py` and `webui/app.html` size.** Both are large single
  files by necessity (one bridge class; one no-build-step HTML asset), so
  splitting them isn't a clear win today. If either keeps growing
  significantly, it may be worth revisiting — e.g. introducing a build
  step for `app.html` if it becomes unmanageable, or grouping `AppApi`
  methods into mixins if the bridge class keeps expanding. Not worth doing
  preemptively.
- **No automated UI tests.** Coverage for `app.html` is limited to static
  checks (`node --check` on the extracted `<script>` body, and an id-audit
  that every `$("id")` matches exactly one `id="..."`) plus the
  network-free Python test suite (`pytest`) for the engine. There is no
  automated exercising of the actual UI interactions.
- **Single-file UI review cost.** As `app.html` grows, reviewing changes to
  it gets harder purely because everything — markup, styles, and script —
  lives in one file with no sectioning enforced beyond convention (the
  documented page-block order: p-gen, p-eco, p-chance, p-craft, p-exc,
  p-hist, p-prev, p-set, p-dbg).

## Verification

`pytest`, `ruff check .`, and the `app.html` verification gates (`node
--check` on the extracted script body, plus the element-id audit) were run
as part of this cleanup pass and passed, consistent with the repository's
"both `pytest` and `ruff check .` must be clean before any commit"
requirement.
