---
name: ui-redesign
description: Safely make LARGE layout changes to webui/app.html (nav restructure, multi-column page reshapes, palette shifts) without breaking the single-file app or the theme system.
---

# UI redesign (this repo)

For big visual changes to `src/exilebot_pickit/webui/app.html` — restructuring
the nav, reshaping a page into columns, moving DOM blocks, shifting the palette.
Small tweaks just need `ui-edit-check`; this is for the risky, structural ones.
Always run `ui-edit-check` after EVERY edit here too.

## Before you touch app.html

1. **Branch first** (`git checkout -b redesign-...`). Main ships to users.
2. **Prototype for sign-off.** For a new look, build a standalone self-contained
   `.html` in the scratchpad and open it in the browser (`cmd //c start ""`),
   so the user approves the design *before* you edit the real file. Extract the
   real logo data-URI from app.html (`data:image/png;base64,...`) so the mockup
   looks right. Iterate on the prototype, not the app.

## Editing gotchas that bite here

3. **Emoji lines won't match.** Retyped emoji bytes (⚡🪙🎲🛠🧱) differ from the
   file's, so an Edit `old_string` containing them fails. Anchor on **emoji-free
   substrings** instead: attributes (`data-p="gen">`), `</div>`, class names.
   To rename a nav label, match `Chance Bases</div>` (the nav uses `</div>`, the
   page title uses `</h1>` — so it's unique and won't hit the heading).
4. **The file has 120 KB data-URIs on single lines.** `Read` blows the token
   budget on those lines — never read the whole `<nav>`/brand region. Use `Grep`
   for structural anchors and `Read` small ranges that skip the data-URI lines.

## Restructuring DOM safely

5. **Move blocks in stages, not one giant edit.** To split a page into columns:
   (a) open the wrapper before the first block, (b) at the split point close the
   old container + close the left col + open the right col + open a new card,
   (c) after the last block add the extra closes. Do each as its own edit.
6. **Verify div balance** after structural edits with a python count over the
   page slice (`seg.count('<div')` vs `seg.count('</div>')`). Note a slice that
   starts at `id="p-xxx"` misses that page's own opening `<div`, so opens =
   closes − 1 is *balanced*.
7. **Preserve every id.** The JS finds controls by `$("id")`. When you move a
   block, keep its ids. When you REMOVE a feature (e.g. Compare), delete the
   button **and** its handler **and** any `$("...")` it referenced (incl. ids
   that only exist inside a `innerHTML` string) together — a dangling `$("id")`
   fails the id-audit.

## Theme discipline (don't break the 3 themes)

8. **Only use CSS variables** (`--bg`, `--bg2`, `--bg3`, `--border`, `--text`,
   `--dim`, `--gold`, `--gold-dim`, `--gold-br`, `--ok`, `--err`, `--warn`,
   `--steel`) — never hardcode a hex. Three themes: `:root` = the default
   Workbench brass (identical to `html[data-theme=relic]`), plus
   `html[data-theme=ocean]` (Frost) and `html[data-theme=nebula]` (Blood).
   Legacy names gold/ember map to relic in setTheme. To shift the palette,
   change `:root` AND relic together; every theme block must define the full
   13-token set (a static audit script exists — parse each block and compare).
   Note the nav is a LEFT RAIL (not a top bar) since v4.4.0.
9. **Reuse the shared component classes** for consistency: `.craft-side` +
   `.cside-btn` (+ `.n` count span) for any left sidebar; `.eco-toolbar` for a
   rounded toolbar panel; `.eco-header` + `.eco-rate` for a slim page header.
   Add these to a new tab instead of inventing one-off styles.

## Layout conventions

10. `.page` defaults to `max-width:900px`; widen a specific tab with an id
    override (`#p-gen,#p-eco{max-width:1180px}`), don't change the global.
11. Body is `zoom:1.1` → viewport heights are `90.9vh`, and the nav is a
    `grid-template-columns:auto 1fr auto` (brand · centered tabs · actions) that
    stacks under a `@media(max-width:940px)` rule. Keep both patterns.

## Finish

12. `ui-edit-check` (node --check + id audit) after every edit, relaunch the app
    (kill python first), and drive a real Generate once before merging. Then
    merge to main and `release` for the version bump + tagged build.
