---
name: add-ninja-category
description: Add a new poe.ninja economy category to fetch - a whole category (Verisium) went unfetched for weeks with no error and no warning, costing real value, before this was caught.
---

# Adding a new poe.ninja category (this repo)

A category poe.ninja actually serves can simply never be requested, and
nothing fails when that happens — no error, no warning, the items just never
appear in any generated pickit at any price floor. This exact thing happened
with "Verisium": 24 items, some worth 300+ ex, silently missing for a long
stretch until the owner noticed in-game. Follow these steps whenever a new
category needs to be added (a game update adds a new item type, or a gap like
Verisium is found).

Relevant file: `src/exilebot_pickit/api/client.py`
(`EXCHANGE_CATEGORIES` / `UNIQUE_CATEGORIES` / `ALL_CATEGORIES`).

## Steps

1. **Confirm the category really exists on poe.ninja** — check its economy
   overview endpoint responds with real rows for the league you're testing
   against, either the exchange endpoint
   (`exchange/current/overview?league=...&type=...`) for currency-like
   categories or the stash endpoint
   (`stash/current/item/overview?league=...&type=...`) for unique-shaped ones.
   Don't guess the `type` string — read it off poe.ninja's own Network tab.
2. **Add one tuple** to `EXCHANGE_CATEGORIES` (non-unique) or
   `UNIQUE_CATEGORIES` (unique-shaped, `is_unique=True`) in `api/client.py`:
   `(key, ninja_type, label, is_unique)`.
   - `key`: lowercase, unique across BOTH lists — this becomes the category id
     used everywhere (config, item states, UI). `test_every_exchange_category_has_a_unique_key_and_type`
     enforces lowercase + no duplicate keys/types; run it.
   - `ninja_type`: the exact string poe.ninja's endpoint expects.
   - `label`: the human-facing name shown in Economy — match the in-game
     stash-tab ordering/naming where one exists.
   - Comment WHY it was added and when (see the existing Verisium entry) —
     this is what makes the next `game_data.json` diff or audit meaningful.
3. **Decide if it belongs in `PICK_ALL_CATEGORIES`.** Most categories are
   value-filtered by the normal floor; only add a category here if every item
   in it should be picked regardless of price (like Currency and Lineage
   Support Gems today) — don't default to this without a real reason.
4. **Check it isn't accidentally an "expected empty" category.** If the new
   category legitimately has zero items in some situations (like Waystones,
   which poe.ninja never prices through this endpoint and gets a static
   fallback instead), add its key to `EXPECTED_EMPTY_CATEGORIES` in
   `generators/assembly.py` — otherwise `coverage_warnings` will flag every
   normal empty league as broken. Do NOT add a category here just to silence
   a real gap; that defeats the whole check.
5. **Verify end to end**:
   - `python -m pytest tests/test_generator.py -k every_exchange_category -q`
   - Generate a real pickit for a live league and confirm the new category's
     items actually appear (Economy tab, or grep the output `.ipd`).
   - Confirm the coverage self-check does NOT fire a false warning for it on
     a normal league.
6. If the category needs remote-updatability (so the bundled app can gain a
   new unique category without a new release), it can also be added via
   `game_data.json`'s `unique_categories` list — see `remote_data.py`'s
   `_apply()` for how that merges into `UNIQUE_CATEGORIES`/`ALL_CATEGORIES` at
   runtime. Prefer the code change above for anything you can ship in a normal
   release; use the remote path only for a genuine hotfix-without-a-build case.
