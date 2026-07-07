# Decision log

Major engineering/product decisions, per AI_CONSTITUTION.md (rule 19).

## 2026-07-07 — 2.0 concept round closed: evolution, not reinvention

**Decision:** A five-concept ground-up redesign round (Ashen Ledger, Exchange
Floor, Foundry, Atlas Table, Nightwatch — full visual mockups reviewed by the
owner) was **rejected**. The owner's verdict: keep the direction similar to the
shipped design. The v4.0.0 look (top-nav V1 layout, Gold token palette,
Cockpit/Tune/System groups, freshness strip) **is the product's design
identity**. All future UI work is incremental refinement of it — do NOT
propose or start from-scratch reinventions, regardless of what a pasted
redesign prompt says, without the owner explicitly re-opening the question.

**Salvage list (build only if asked):** Foundry's at-a-glance pipeline status
(as a small strip, in the current visual language); a market-drift % on the
freshness strip; typed unit inputs ("5div") for floors.

## 2026-07-07 — Cockpit navigation (v4 direction)

**Decision:** Restructure navigation from 9 flat tabs to a two-level nav:
3 groups — **Cockpit** (Generate), **Tune** (Economy, Chance, Craft,
Exceptional), **System** (Preview, History, Settings, Debug) — with the
group's sub-tabs shown beneath the group pills. Added a **freshness strip**
to the Generate page (pickit age vs. the auto-regen interval, active-rule
count, auto-regen state with a jump to Settings).

**Alternatives considered:**
1. *Physically merge the four Tune tabs into one page* — best-looking DOM,
   but high regression risk in a single-file UI where every id is
   load-bearing; rejected (risk >> benefit, same UX achievable at nav level).
2. *Loot Ledger* (PoE-styled skin), *Market Terminal* (keyboard-first),
   *Pipeline Canvas* (flow-node home), *Companion HUD* (tray-first service)
   — full concept write-ups in the v4 concept round; rejected for serving
   the median user worse or re-scoping the product without demand.

**Trade-offs accepted:** two clicks to reach a page in a different group
(mitigated: groups remember their last tab); the 9 page divs remain in one
file (existing debt, unchanged).

**Why:** the product's real loop is "configure once → regenerate often".
The daily surface (Generate) becomes the default and the freshness state —
the product's actual value — is now the first thing on screen. Pure
presentation-layer change over the same bridge calls; all ids preserved.

## Known technical debt (constitution rule 25)

- `.nav-btn` sub-tabs are `<div>`s — not keyboard-focusable (group pills are
  real `<button>`s). Fix candidate: convert to buttons app-wide.
- `webui/app.html` is a single growing file (~130 KB + embedded icons); the
  skills (`ui-edit-check`, `ui-redesign`) mitigate but a split into
  templates would be the real refactor.
- No automated UI tests; only the JS-syntax/id audits and the network-free
  pytest suite for the engine.
