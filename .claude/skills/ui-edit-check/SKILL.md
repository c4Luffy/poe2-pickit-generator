---
name: ui-edit-check
description: Mandatory safety checks after ANY edit to webui/app.html - the single-file UI dies completely from one bad id or JS error.
---

# UI edit safety (this repo)

`src/exilebot_pickit/webui/app.html` is a single file: one missing element or
one JS syntax error kills the ENTIRE app (league dropdown stuck on
"Loading…", version label empty = the script died). After every edit:

1. **JS syntax**: extract the `<script>` body and `node --check` it.
2. **Id audit** (python): every `$("id")` reference must match exactly one
   `id="..."` — zero missing, zero duplicates.
3. **Page blocks**: the pages live in ONE file in this order — p-gen, p-eco,
   p-chance, p-craft, p-exc, p-hist, p-prev, p-set, p-dbg. When slicing a
   block by index, anchor on that page's opening div AND the next page's
   comment — a bad end anchor once deleted two whole pages.
4. **Escapes**: never build replacement JS through `re.sub` replacement
   strings (they eat `\n`); use lambdas or plain string slicing. Never pipe
   emoji/✓/→ through bash heredocs — write a python script to the scratchpad
   and run it.
5. **Layout**: body has `zoom:1.1`, so every viewport height is written as
   `90.9vh` (NOT 100vh) — keep doing that or the bottom of the window gets
   cut off.
6. **Preview**: relaunch the app (kill python first — single-instance mutex),
   then verify visually via PrintWindow screenshot (flags=2) — it works even
   when the window is covered. Toggle-worthy: check the league dropdown
   filled and the version label shows.
