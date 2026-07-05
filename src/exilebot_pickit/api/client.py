"""poe.ninja API client with in-memory + disk caching."""

import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import requests

BASE_URL = "https://poe.ninja/poe2/api/economy"
INDEX_STATE_URL = "https://poe.ninja/poe2/api/data/index-state"
USER_AGENT = "poe2-pickit-generator/1.0 (+local)"
MIN_EXALT = 10.0


EXCHANGE_CATEGORIES = [
    # Order matches the in-game stash-tab list
    ("currency",            "Currency",           "Currency",             False),
    ("essences",            "Essences",           "Essences",             False),
    ("liquid_emotions",     "Delirium",           "Delirium",             False),
    ("catalysts",           "Breach",             "Catalysts",            False),
    ("abyssal_bones",       "Abyss",              "Abyss",                False),
    ("fragments",           "Fragments",          "Fragments",            False),
    ("runes",               "Runes",              "Runes",                False),
    ("omens",               "Ritual",             "Omens",                False),
    ("soul_cores",          "SoulCores",          "Soul Cores",           False),
    ("idols",               "Idols",              "Idols",                False),
    ("uncut_gems",          "UncutGems",          "Uncut Gems",           False),
    ("lineage_support_gems","LineageSupportGems", "Support Gems",         False),
    ("expedition",          "Expedition",         "Expedition",           False),
    ("waystones",           "Waystones",          "Waystones",            False),
]

UNIQUE_CATEGORIES = [
    ("unique_weapons",    "UniqueWeapons",      "Unique Weapons",     True),
    ("unique_armours",    "UniqueArmours",      "Unique Armours",     True),
    ("unique_accessories","UniqueAccessories",  "Unique Accessories", True),
    ("unique_flasks",     "UniqueFlasks",       "Unique Flasks",      True),
    ("unique_charms",     "UniqueCharms",       "Unique Charms",      True),
    ("unique_jewels",     "UniqueJewels",       "Unique Jewels",      True),
    ("unique_relics",     "UniqueSanctumRelics","Unique Relics",      True),
]

ALL_CATEGORIES = EXCHANGE_CATEGORIES + UNIQUE_CATEGORIES

# Categories where EVERY item is picked regardless of price threshold —
# inclusion is driven purely by the per-item selections (the Items-tab
# checkboxes), not by value.
#   • Lineage Support Gems: too rare to skip any.
#   • Currency: picked by selection, never value-filtered.
PICK_ALL_CATEGORIES = {"lineage_support_gems", "currency"}



# ─────────────────────────────────────────────────────────────────────────────
#  API helpers
# ─────────────────────────────────────────────────────────────────────────────

_JSON_MAX_BYTES = 25 * 1024 * 1024  # sanity cap — real payloads are a few MB


def fetch_json(url: str, params: dict) -> dict:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    r = requests.get(url, params=params, headers=headers, timeout=20, stream=True)
    r.raise_for_status()
    # Read with a hard cap so a hostile/misbehaving endpoint can't buffer
    # arbitrary amounts of (decompressed) data into RAM.
    buf, total = [], 0
    for chunk in r.iter_content(262144):
        total += len(chunk)
        if total > _JSON_MAX_BYTES:
            raise ValueError(f"response exceeded {_JSON_MAX_BYTES} bytes: {url}")
        buf.append(chunk)
    return json.loads(b"".join(buf))


# ── Retry with exponential backoff ───────────────────────────────────────────

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_MAX_RETRY_AFTER = 30.0   # don't stall the UI longer than this on a 429


def _retry_after_secs(resp) -> float | None:
    """Server-requested wait from a Retry-After header, or None."""
    try:
        v = (resp.headers.get("Retry-After") or "").strip()
        return float(v) if v else None
    except (ValueError, AttributeError):
        return None


def _request_with_retry(url: str, params: dict, *, retries: int = 3, backoff: float = 1.5) -> dict:
    """fetch_json with backoff retry on 429/5xx and transient network errors.

    A 429 honors the server's Retry-After (poe.ninja's budget is a shared
    ~12 req/5 min window — blind fast retries just dig the hole deeper). If the
    server asks for more than _MAX_RETRY_AFTER we give up immediately so the
    caller falls back to the disk cache instead of hanging the run."""
    last_exc: Exception = RuntimeError("no attempts made")
    for attempt in range(retries):
        try:
            return fetch_json(url, params)
        except requests.HTTPError as e:
            resp = e.response
            if resp is not None and resp.status_code not in _RETRYABLE_STATUS:
                raise
            last_exc = e
            if resp is not None and resp.status_code == 429:
                wait = _retry_after_secs(resp)
                if wait is not None:
                    if wait > _MAX_RETRY_AFTER:
                        raise           # rate window too long — use cached data
                    if attempt < retries - 1:
                        time.sleep(wait)
                    continue
        except (requests.ConnectionError, requests.Timeout) as e:
            last_exc = e
        except ValueError as e:          # oversized response — do not retry
            raise e
        if attempt < retries - 1:
            time.sleep(backoff * (2 ** attempt))  # 1.5 s, 3 s
    raise last_exc


# ── In-memory payload cache (per session) ────────────────────────────────────

_PAYLOAD_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()
_CACHE_TTL: float = 900.0  # 15 minutes


def _cache_get(league: str, key: str):
    with _CACHE_LOCK:
        entry = _PAYLOAD_CACHE.get((league, key))
        if entry and (time.time() - entry[0]) < _CACHE_TTL:
            return entry[1]
    return None


def _cache_set(league: str, key: str, payload: dict):
    with _CACHE_LOCK:
        _PAYLOAD_CACHE[(league, key)] = (time.time(), payload)
    save_payload_to_disk(league, key, payload)


def clear_cache():
    """Discard all cached poe.ninja payloads."""
    with _CACHE_LOCK:
        _PAYLOAD_CACHE.clear()

def prune_disk_cache(max_age_days: int = 60) -> int:
    """Delete disk-cache files older than *max_age_days*. Returns count deleted.

    Call on startup to stop stale league files accumulating across seasons.
    """
    if not _DISK_CACHE_DIR:
        return 0
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    try:
        for fname in os.listdir(_DISK_CACHE_DIR):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(_DISK_CACHE_DIR, fname)
            try:
                if os.path.getmtime(fpath) < cutoff:
                    os.remove(fpath)
                    removed += 1
            except OSError:
                pass
    except OSError:
        pass
    return removed


# ── Disk cache (survives restarts → powers offline mode) ─────────────────────

_DISK_CACHE_DIR: str = ""


def set_disk_cache_dir(path: str):
    """Point the offline cache at a directory. Called once by the GUI on startup."""
    global _DISK_CACHE_DIR
    _DISK_CACHE_DIR = path
    if path:
        try:
            os.makedirs(path, exist_ok=True)
        except OSError:
            pass


def _disk_cache_file(league: str, key: str) -> str:
    safe = re.sub(r'[^\w\-]', '_', f"{league}__{key}")
    return os.path.join(_DISK_CACHE_DIR, safe + ".json")


def save_payload_to_disk(league: str, key: str, payload: dict):
    """Persist one payload so it can be reused when poe.ninja is unreachable."""
    if not _DISK_CACHE_DIR or not isinstance(payload, dict):
        return
    try:
        fname = _disk_cache_file(league, key)
        tmp   = fname + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "payload": payload}, f)
        os.replace(tmp, fname)   # atomic on Windows + POSIX
    except (OSError, TypeError, ValueError):
        pass


def load_payload_from_disk(league: str, key: str):
    """Return a previously saved payload (and its age in seconds), or (None, None)."""
    if not _DISK_CACHE_DIR:
        return None, None
    try:
        with open(_disk_cache_file(league, key), encoding="utf-8") as f:
            data = json.load(f)
        return data.get("payload"), time.time() - float(data.get("ts", 0))
    except (OSError, ValueError):
        return None, None


def cache_info() -> dict:
    """Return counts and age info about the current cache."""
    now = time.time()
    with _CACHE_LOCK:
        entries = [(k, now - v[0]) for k, v in _PAYLOAD_CACHE.items()]
    return {
        "count": len(entries),
        "oldest_secs": max((a for _, a in entries), default=0),
        "ttl_secs": _CACHE_TTL,
    }


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_live_leagues() -> list:
    data = _request_with_retry(INDEX_STATE_URL, {})
    leagues = []
    for item in data.get("economyLeagues", []):
        leagues.append((item.get("name", ""), item.get("url", ""), item.get("displayName", item.get("name", ""))))
    for item in data.get("oldEconomyLeagues", []):
        leagues.append((item.get("name", ""), item.get("url", ""), item.get("displayName", item.get("name", "")) + " (old)"))
    return [l for l in leagues if l[0] and l[1]]


def detect_current_league() -> str:
    try:
        data = _request_with_retry(INDEX_STATE_URL, {})
        active = data.get("economyLeagues", [])
        for item in active:
            name = item.get("name", "")
            if name.lower() not in ("standard", "hardcore"):
                return name
        if active:
            return active[0].get("name", "Mercenaries")
    except (requests.RequestException, ValueError, KeyError) as e:
        print(f"Warning: could not auto-detect league ({e}); falling back to 'Mercenaries'")
    return "Mercenaries"


def fetch_category(league: str, key: str, ninja_type: str, is_unique: bool) -> dict:
    endpoint = "stash/current/item/overview" if is_unique else "exchange/current/overview"
    return _request_with_retry(f"{BASE_URL}/{endpoint}", {"league": league, "type": ninja_type})


def fetch_all_payloads(league: str, categories: list, *, max_workers: int = 5,
                       use_cache: bool = True, offline_fallback: bool = True,
                       stale_out: set | None = None) -> dict:
    """Fetch all category payloads in parallel.

    Returns {key: payload} for successes and {key: Exception} for failures.
    Results are returned in the same order as `categories`.

    If a live fetch fails and `offline_fallback` is on, the last payload saved to
    disk is used instead and its key is added to `stale_out` (so callers can warn
    the user that prices may be out of date).
    """
    results: dict = {}
    to_fetch = []

    for key, ninja_type, label, is_unique in categories:
        if use_cache:
            cached = _cache_get(league, key)
            if cached is not None:
                results[key] = cached
                continue
        to_fetch.append((key, ninja_type, label, is_unique))

    if not to_fetch:
        return results

    def _fetch_one(item):
        k, ninja_type, _label, is_unique = item
        return k, fetch_category(league, k, ninja_type, is_unique)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [(item[0], executor.submit(_fetch_one, item)) for item in to_fetch]
        for key, future in futures:
            try:
                _, payload = future.result()
                if use_cache:
                    _cache_set(league, key, payload)
                results[key] = payload
            except Exception as e:
                disk, _age = load_payload_from_disk(league, key) if offline_fallback else (None, None)
                if disk is not None:
                    results[key] = disk
                    if stale_out is not None:
                        stale_out.add(key)
                else:
                    results[key] = e

    return results


def exalted_rate(payload: dict) -> float:
    return float(payload.get("core", {}).get("rates", {}).get("exalted") or 0.0)


def divine_value_from_exalt(exalt_value: float, divine_rate_exalts: float) -> float:
    return exalt_value / divine_rate_exalts if divine_rate_exalts else 0.0
