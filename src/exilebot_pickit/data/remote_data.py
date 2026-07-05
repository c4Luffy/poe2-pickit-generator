"""Self-updating game data.

Unique ITEMS already keep themselves current: every generate pulls the full
live list (names + prices) from poe.ninja, so a new unique flask/armour/etc.
added in a game patch appears automatically on the next run.

What CAN'T update that way is the bundled game data: the exceptional base-type
lists (data/base_types.py) and the unique category list (api/client.py). This
module refreshes both from a small JSON file hosted in the project's GitHub
repo (game_data.json on the main branch). When a game patch adds new bases or
a whole new unique category, only that file needs updating in the repo — every
installed app picks it up on its next launch, no new .exe required.

Design constraints:
  * Silent, best-effort: no network / bad JSON / weird schema → keep bundled
    data. The app must never be worse off than before this feature existed.
  * The fetched copy is cached on disk so offline launches still use the most
    recent data seen.
  * Data is applied by mutating the existing dict/lists IN PLACE — every other
    module imported them by reference at startup, so identity must not change.
"""

import json
import os
import threading
import time

import requests

from exilebot_pickit.data import base_types as _bt
from exilebot_pickit.data import corrections as _corr
from exilebot_pickit.api import client as _client

REMOTE_DATA_URL = ("https://raw.githubusercontent.com/"
                   "c4Luffy/poe2-pickit-generator/main/game_data.json")
_FETCH_MIN_INTERVAL = 6 * 3600   # don't hammer GitHub on rapid relaunches

_CACHE_BASENAME = "game_data_cache.json"


def _validate(data) -> bool:
    """True if *data* looks like a sane game_data.json."""
    if not isinstance(data, dict):
        return False
    bt = data.get("base_types")
    if bt is not None:
        if not isinstance(bt, dict) or not bt:
            return False
        for cat, entries in bt.items():
            if not isinstance(cat, str) or not isinstance(entries, list):
                return False
            for e in entries:
                if (not isinstance(e, list) or len(e) != 2
                        or not isinstance(e[0], str)
                        or not isinstance(e[1], int)):
                    return False
    uc = data.get("unique_categories")
    if uc is not None:
        if not isinstance(uc, list):
            return False
        for e in uc:
            if (not isinstance(e, list) or len(e) != 3
                    or not all(isinstance(x, str) for x in e)):
                return False

    def _str_list(v):
        return isinstance(v, list) and all(isinstance(x, str) and x for x in v)

    def _pair_list(v, n):
        return (isinstance(v, list)
                and all(isinstance(e, list) and len(e) == n
                        and all(isinstance(x, str) and x for x in e) for e in v))

    for key in ("splinters", "wombgifts", "special_items", "exotic_bases",
                "jewels"):
        v = data.get(key)
        if v is not None and not _str_list(v):
            return False
    ap = data.get("always_pick")
    if ap is not None:
        if not isinstance(ap, dict):
            return False
        for k in ("currency", "runes"):
            v = ap.get(k)
            if v is not None and not _str_list(v):
                return False
    tb = data.get("tablets")
    if tb is not None:
        if not isinstance(tb, dict):
            return False
        if tb.get("types") is not None and not _str_list(tb["types"]):
            return False
        if tb.get("uniques") is not None and not _pair_list(tb["uniques"], 2):
            return False
    nf = data.get("name_fixes")
    if nf is not None:
        if not isinstance(nf, dict):
            return False
        corr = nf.get("corrections")
        if corr is not None:
            if not isinstance(corr, dict) or not all(
                    isinstance(k, str) and isinstance(v, str)
                    for k, v in corr.items()):
                return False
        if nf.get("skip") is not None and not _str_list(nf["skip"]):
            return False
    cb = data.get("chance_bases")
    if cb is not None and not _pair_list(cb, 3):
        return False
    return True


def _apply(data: dict) -> None:
    """Merge validated remote data into the live module structures."""
    bt = data.get("base_types")
    if bt:
        _bt._BASE_TYPES_BY_CATEGORY.clear()
        for cat, entries in bt.items():
            _bt._BASE_TYPES_BY_CATEGORY[cat] = tuple((n, s) for n, s in entries)
        # generator snapshots the valid-base set at import — rebuild it so the
        # validator accepts (and suggests) the refreshed bases.
        try:
            from exilebot_pickit import generator as _gen
            _gen.VALID_EQUIPMENT_BASES = (
                frozenset(n for ents in _bt._BASE_TYPES_BY_CATEGORY.values()
                          for n, _ in ents)
                | _gen._ACCESSORY_BASES
            )
        except Exception:
            pass
    uc = data.get("unique_categories")
    if uc:
        known = {c[0] for c in _client.UNIQUE_CATEGORIES}
        for key, ninja_type, label in uc:
            if key not in known:
                entry = (key, ninja_type, label, True)
                _client.UNIQUE_CATEGORIES.append(entry)
                _client.ALL_CATEGORIES.append(entry)

    # Always-pick static sections. All mutations are IN PLACE ([:] / clear+
    # update) — generator.py imported these objects by reference at startup.
    if data.get("splinters"):
        _corr.SPLINTERS[:] = data["splinters"]
    if data.get("wombgifts"):
        _corr.WOMBGIFTS[:] = data["wombgifts"]
    if data.get("special_items"):
        _corr.SPECIAL_ITEMS[:] = data["special_items"]
    if data.get("exotic_bases"):
        _corr.EXOTIC_BASES[:] = data["exotic_bases"]
    if data.get("jewels"):
        _corr.JEWELS[:] = data["jewels"]
    ap = data.get("always_pick") or {}
    if ap.get("currency"):
        _corr.ALWAYS_PICK_CURRENCY[:] = ap["currency"]
    if ap.get("runes"):
        _corr.ALWAYS_PICK_RUNES[:] = ap["runes"]
    tb = data.get("tablets") or {}
    if tb.get("types"):
        _corr.TABLET_TYPES[:] = tb["types"]
    if tb.get("uniques"):
        _corr.TABLET_UNIQUES[:] = [tuple(e) for e in tb["uniques"]]
    nf = data.get("name_fixes") or {}
    if nf.get("corrections") is not None:
        _corr.ITEM_NAME_CORRECTIONS.clear()
        _corr.ITEM_NAME_CORRECTIONS.update(nf["corrections"])
    if nf.get("skip") is not None:
        _corr.ITEM_NAME_SKIP.clear()
        _corr.ITEM_NAME_SKIP.update(nf["skip"])
    if data.get("chance_bases"):
        try:
            from exilebot_pickit import generator as _gen
            _gen.CHANCE_BASES[:] = [tuple(e) for e in data["chance_bases"]]
        except Exception:
            pass


def load_cached_game_data(cache_dir: str) -> tuple:
    """Apply the last remote copy saved on disk (fast, no network).

    Called synchronously at startup — BEFORE the UI builds its category rows —
    so previously-seen new unique categories get their toggle switches.
    Returns (status_string, cache_timestamp)."""
    cache_file = os.path.join(cache_dir, _CACHE_BASENAME)
    status, cached_ts = "bundled data (no remote copy yet)", 0.0
    try:
        with open(cache_file, encoding="utf-8") as f:
            wrapper = json.load(f)
        cached, cached_ts = wrapper.get("data"), float(wrapper.get("ts", 0))
    except (OSError, ValueError, TypeError):
        return status, cached_ts
    if cached is not None and _validate(cached):
        try:
            _apply(cached)
            status = "cached remote data applied"
        except Exception:
            pass
    return status, cached_ts


def refresh_game_data(cache_dir: str) -> str:
    """Load cached remote data, then fetch a fresh copy if the cache is old.

    Returns a short status string for the debug log. Never raises."""
    cache_file = os.path.join(cache_dir, _CACHE_BASENAME)
    status, cached_ts = load_cached_game_data(cache_dir)

    if time.time() - cached_ts < _FETCH_MIN_INTERVAL:
        return status
    try:
        r = requests.get(REMOTE_DATA_URL, timeout=10,
                         headers={"User-Agent": _client.USER_AGENT})
        if r.status_code != 200:
            return status
        data = r.json()
        if not _validate(data):
            return status + " (remote copy failed validation — ignored)"
        _apply(data)
        try:
            tmp = cache_file + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"ts": time.time(), "data": data}, f)
            os.replace(tmp, cache_file)
        except OSError:
            pass
        return "fresh remote data applied"
    except Exception:
        return status + " (remote fetch failed — offline?)"


def refresh_game_data_async(cache_dir: str, done=None) -> None:
    """Background-thread wrapper; calls *done(status)* if given."""
    def _run():
        st = refresh_game_data(cache_dir)
        if done:
            try:
                done(st)
            except Exception:
                pass
    threading.Thread(target=_run, daemon=True).start()
