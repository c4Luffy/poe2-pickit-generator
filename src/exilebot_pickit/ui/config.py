"""Config path bootstrap, defaults, and load/save."""

import sys, os, json, copy, shutil, logging, tempfile, threading
from logging.handlers import RotatingFileHandler

# Serialises savers inside this process (the UI thread and the generate worker
# both write the config). Cross-process safety comes from the per-save temp file
# in save_config — see its docstring.
_SAVE_LOCK = threading.Lock()

# ── Config ────────────────────────────────────────────────────────────────────
# Built EXE: keep everything in ONE tidy data folder next to the .exe instead of
# scattering config/caches/output loose beside it (e.g. all over the Desktop).
if getattr(sys, 'frozen', False):
    _exe_dir = os.path.dirname(sys.executable)
    _cfg_dir = os.path.join(_exe_dir, "ExileBot2PickitGenerator_data")
    try:
        os.makedirs(_cfg_dir, exist_ok=True)
    except OSError:
        # exe lives somewhere unwritable (Program Files, a read-only share) —
        # fall back to %APPDATA% instead of dying with a raw traceback at import.
        _cfg_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                                "exilebot-pickit")
        os.makedirs(_cfg_dir, exist_ok=True)
    # One-time migration: move loose files from older versions into the data folder.
    for _name in ("pickit_gui_config.json", "wiki_icon_cache.json", "pickit_output",
                  "icon_cache", "presets", "price_cache", "latest.ipd"):
        _src = os.path.join(_exe_dir, _name)
        _dst = os.path.join(_cfg_dir, _name)
        if os.path.exists(_src) and not os.path.exists(_dst):
            try:
                shutil.move(_src, _dst)
            except Exception:
                pass
else:
    _cfg_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "exilebot-pickit")
    os.makedirs(_cfg_dir, exist_ok=True)
    # One-time migration from the old package-adjacent location (v2.6.x and earlier).
    _old_cfg = os.path.dirname(os.path.abspath(__file__))
    if _old_cfg != _cfg_dir:
        for _name in ("pickit_gui_config.json", "wiki_icon_cache.json", "pickit_output",
                      "icon_cache", "presets", "price_cache", "latest.ipd"):
            _src = os.path.join(_old_cfg, _name)
            _dst = os.path.join(_cfg_dir, _name)
            if os.path.exists(_src) and not os.path.exists(_dst):
                try:
                    shutil.move(_src, _dst)
                except Exception:
                    pass

CONFIG_PATH      = os.path.join(_cfg_dir, "pickit_gui_config.json")
OUTPUT_DIR       = os.path.join(_cfg_dir, "pickit_output")
ICON_DIR         = os.path.join(_cfg_dir, "icon_cache")
PRICE_CACHE_DIR  = os.path.join(_cfg_dir, "price_cache")
WIKI_CACHE_FILE  = os.path.join(_cfg_dir, "wiki_icon_cache.json")
for _d in (_cfg_dir, OUTPUT_DIR, ICON_DIR):
    os.makedirs(_d, exist_ok=True)


def _default_poe2_filter_dir() -> str:
    """Best-guess location of the PoE2 client loot-filter folder."""
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Documents", "My Games", "Path of Exile 2"),
        os.path.join(home, "OneDrive", "Documents", "My Games", "Path of Exile 2"),
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return candidates[0]


DEFAULT_CONFIG = {
    "league": "",
    "min_exalt": 0.0,
    "min_exalt_gear": 0.0,
    "min_exalt_unique": 0.0,
    # What's-new: the version whose notes the user has already seen, plus the notes
    # stashed at download time so the panel still works with no network.
    # First-run wizard: set once it is finished OR skipped, so it never nags twice.
    "setup_done": False,
    "last_seen_version": "",
    "pending_version": "",
    "pending_notes": "",
    "output_base": "poe2_pickit",
    "bot_folder": "",
    "auto_copy": False,
    "backup_count": 5,
    "category_enabled": {},
    "history": [],

    "theme": "dark",
    "magic_rare_flasks": True,
    # Master switch for the rare-gear WeightedSum recipes (17 slots).
    "rare_gear_enabled": True,
    # League names already seen in the dropdown — one NOT in this list
    # triggers the "new league detected" banner on the Generate tab.
    "known_leagues": [],
    # dict {w,h,x,y} — poc.py saves one on close. Was "" (a string), which made
    # _coerce_types see dict-vs-str on every load and wipe the saved geometry:
    # the window opened at the default size/position forever.
    "window_geometry_web": {},
    "include_bases": True,
    # Auto floor: recompute both value floors from live prices on every
    # generate ("keep top N%" percentile).
    "auto_floor": False,
    "auto_floor_pct": 40,
    "base_quality": 25,
    "base_min_level": 82,
    "item_states":  {},
    "last_gen_prices": {},
    # App version that produced the current .ipd — Preview warns when it no
    # longer matches, because the shown pickit predates the rules you now have.
    "last_gen_version": "",
    "profiles": {},
    "active_profile": "",
    # Which ready-made preset (see PRESETS) the current floors came from. Cleared
    # the moment the user hand-edits a floor, so the UI never claims a preset is
    # active when the numbers no longer match it.
    "active_preset": "",

    # OFF by default: an in-game loot filter that HIDES items can make Exiled Bot
    # get stuck (it still detects hidden items and paths to them, but the pickup
    # stalls on the un-rendered label). The .filter is still written next to the
    # .ipd for anyone who wants it; this only controls copying it into the PoE2
    # client folder. Bot users should leave it off.
    "copy_filter_to_game": False,
    "poe2_filter_dir": "",
    # Create-your-filter tab: the last pickit→filter conversion, so the app can
    # warn when the source pickit changed after the filter was saved.
    # {"src": pickit path, "out": filter path, "at": unix time saved}
    "filter_from_pickit": {},
    # Label theme for BOTH loot filters the app writes (generated + converted).
    # Keys live in generators/filter_themes.THEMES; unknown values fall back to
    # the default theme at use time, so a stale config can't strip styling.
    "filter_theme": "classic",
}


# ── Ready-made presets ────────────────────────────────────────────────────────
# A preset is just a bundle of settings with a plain-language explanation of what
# it actually picks up and what it costs you. `strict` (1-4) drives the strictness
# meter in the UI; `cfg` is applied verbatim over the user's config.
#
# Floors are in Exalted. Calibrated against a ~500 ex Divine: "Chase" only stops
# for roughly a Divine and up, "Vacuum" stops for anything with a price tag.
PRESETS = [
    {
        "key": "vacuum", "name": "Vacuum", "icon": "🧲", "strict": 1,
        "tag": "League start",
        "picks": "Anything with a price tag — every unique, all currency, rare gear and bases.",
        "floors": "Currency & items from 1 ex · uniques from 1 ex",
        "cost": "Fills your stash fast and slows clears. Best in the first days of a league, when even cheap drops still sell.",
        "cfg": {"min_exalt_gear": 1.0, "min_exalt_unique": 1.0, "auto_floor": False,
                "rare_gear_enabled": True, "include_bases": True},
    },
    {
        "key": "balanced", "name": "Balanced", "icon": "⚖️", "strict": 2,
        "tag": "Everyday farming",
        "picks": "Skips the true junk, keeps anything worth selling. Rare gear and bases stay on.",
        "floors": "Currency & items from 2 ex · uniques from 6 ex",
        "cost": "The sane default. Still generous — you'll grab plenty, just not literal vendor trash.",
        "cfg": {"min_exalt_gear": 2.0, "min_exalt_unique": 6.0, "auto_floor": False,
                "rare_gear_enabled": True, "include_bases": True},
    },
    {
        "key": "strict", "name": "Strict", "icon": "💎", "strict": 3,
        "tag": "High value only",
        "picks": "Only drops worth the walk. Fewer items, better ones.",
        "floors": "Currency & items from 8 ex · uniques from 25 ex",
        "cost": "Noticeably less stash traffic — the bot starts walking past the cheap uniques.",
        "cfg": {"min_exalt_gear": 8.0, "min_exalt_unique": 25.0, "auto_floor": False,
                "rare_gear_enabled": True, "include_bases": True},
    },
    {
        "key": "chase", "name": "Chase", "icon": "👑", "strict": 4,
        "tag": "Big hits only",
        "picks": "Only the money drops — the stuff you'd actually stop a map for.",
        "floors": "Currency & items from 20 ex · uniques from 50 ex",
        "cost": "The strictest preset, but not silly — it still keeps anything genuinely valuable. Exceptional bases are off.",
        "cfg": {"min_exalt_gear": 20.0, "min_exalt_unique": 50.0, "auto_floor": False,
                "rare_gear_enabled": True, "include_bases": False},
    },
    {
        "key": "currency", "name": "Currency only", "icon": "💰", "strict": 2,
        "tag": "No gear at all",
        "picks": "Currency, runes, essences and fragments. Nothing else.",
        "floors": "Currency & items from 1 ex · no uniques, no rare gear, no bases",
        "cost": "Pure currency farming. Unique pricing, rare-gear scoring and base rules are all turned off.",
        "cfg": {"min_exalt_gear": 1.0, "min_exalt_unique": 0.0, "auto_floor": False,
                "rare_gear_enabled": False, "include_bases": False},
        "uniques_off": True,     # also switches every unique_* economy category off
    },
]

# Settings a preset owns. Hand-editing any of these means the config no longer
# matches the preset, so `active_preset` is cleared.
PRESET_KEYS = ("min_exalt_gear", "min_exalt_unique", "auto_floor",
               "rare_gear_enabled", "include_bases")


# Set when load_config had to fall back — the UI shows a one-time warning
# instead of silently resetting the user's settings.
CONFIG_LOAD_ERROR = ""


def _coerce_types(cfg):
    """Drop config values whose type disagrees with DEFAULT_CONFIG.

    Guards startup against hand-edited or cross-version configs — a list where
    a dict is expected (e.g. ``"category_enabled": []``) used to crash Tk var
    construction on every launch. Numbers are interchangeable (int/float/bool),
    everything else must match the default's type exactly. An explicit JSON
    ``null`` is a mismatch too — defaults are merged before this runs, so a None
    here can only come from the file, and letting it through persisted a config
    that crashed dict/list consumers on every launch."""
    for key, default in DEFAULT_CONFIG.items():
        v = cfg.get(key)
        if v is not None and (isinstance(default, type(v)) or isinstance(v, type(default))):
            continue
        if isinstance(default, (int, float)) and isinstance(v, (int, float)) \
                and not isinstance(v, bool):
            continue
        cfg[key] = default if not isinstance(default, (dict, list)) else type(default)()
    return cfg


def load_config():
    """Read the config, falling back to defaults only when it is really unreadable.

    A read is retried once before declaring corruption: a save landing at the
    same instant used to make this raise, and *every* such failure silently
    dropped the user onto DEFAULT_CONFIG — league, profiles, history and item
    toggles all gone if anything saved afterwards. save_config no longer creates
    that window (see its docstring), and this retry is the belt to that braces.
    """
    global CONFIG_LOAD_ERROR
    import time as _time
    for attempt in (0, 1):
        try:
            # utf-8-sig, not utf-8: a UTF-8 BOM (added by Notepad "Save As", PowerShell's
            # Set-Content -Encoding UTF8, or some editors) makes plain json.load raise, and
            # the app would then wipe to .corrupt.bak and lose every setting. -sig strips a
            # leading BOM if present and reads BOM-less files identically.
            with open(CONFIG_PATH, encoding="utf-8-sig") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("config root is not an object")
            break
        except FileNotFoundError:
            # deepcopy, not dict(): a shallow copy shares the nested dicts/lists
            # with DEFAULT_CONFIG, so later in-place mutation (set_item etc.)
            # silently polluted the defaults — "Reset to defaults" stopped resetting.
            return copy.deepcopy(DEFAULT_CONFIG)   # first run — nothing to recover
        except Exception:
            if attempt == 0:
                _time.sleep(0.15)            # maybe a save was mid-flight
                continue
            return _config_load_failed()
    try:
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg.update(data)
        _coerce_types(cfg)
        if cfg.get("base_min_level") == 75:
            cfg["base_min_level"] = 82
        # old default 28 -> owner picked 25 (between NeverSink's 27+ top tier
        # and 24 mid tier); user-set values other than 28 are left alone.
        if cfg.get("base_quality") == 28:
            cfg["base_quality"] = 25
        return cfg
    except Exception:
        return _config_load_failed()


def _config_load_failed():
    """Genuinely unreadable config: keep the file for recovery, warn, use defaults."""
    global CONFIG_LOAD_ERROR
    log_exc("load_config")
    # Preserve the corrupt file for recovery instead of silently wiping
    # every setting/profile/exclusion, and tell the UI to say so.
    try:
        bak = CONFIG_PATH + ".corrupt.bak"
        if os.path.exists(bak):
            # NEVER overwrite an earlier quarantine — it may be the only surviving
            # copy of the user's real settings (often hand-recoverable). A second
            # corruption event gets its own timestamped name instead.
            import time as _time
            bak = CONFIG_PATH + _time.strftime(".corrupt-%Y%m%d-%H%M%S.bak")
        shutil.copyfile(CONFIG_PATH, bak)
        CONFIG_LOAD_ERROR = (
            "Your settings file couldn't be read, so defaults were loaded.\n"
            f"The unreadable file was kept at:\n{bak}")
    except Exception:
        CONFIG_LOAD_ERROR = ("Your settings file couldn't be read, "
                             "so defaults were loaded.")
    return copy.deepcopy(DEFAULT_CONFIG)


def save_config(cfg) -> bool:
    """Atomic write — a crash or a concurrent save can no longer truncate the
    config and wipe profiles/history/item selections.

    Returns True when the new config is on disk, False when the save failed
    (the previous file is then untouched — see below). It still NEVER raises:
    a failed save must not crash the app. But returning nothing was its own
    bug: ~25 bridge methods answered the UI with a hard-coded {"ok": True},
    so with an unwritable config directory the toast said "Saved" while
    nothing had been written and the setting vanished at the next launch.

    Every save gets its OWN temp file. A shared ``config.json.tmp`` used to be
    the cause of a steady drip of corruption (318 load_config JSONDecodeErrors
    in one day, 2026-07-12): two savers — the UI thread and the generate worker,
    or a second app process — opened the *same* temp path, the second truncated
    the first's half-written JSON, and whichever finished first atomically moved
    that garbage into place. ``os.replace`` being atomic never helped: the file
    it moved was already corrupt. Readers then fell back to DEFAULT_CONFIG, so a
    save landing at the wrong moment could have wiped every setting.

    The lock serialises savers inside this process; the unique temp name is what
    protects against a second process. The final os.replace is retried because on
    Windows it fails with WinError 32 while another process holds the file open
    (an antivirus scan, the other UI saving at the same instant).
    """
    import time as _time
    with _SAVE_LOCK:
        # Serialize FIRST, into a string, with a retry: pywebview runs every JS
        # call on its own thread, so another bridge call can mutate cfg while we
        # iterate it — json.dump then raises "dictionary changed size during
        # iteration" and the whole save is silently dropped (the log showed 107
        # such losses in one day). The race is transient; a re-read attempt wins.
        fd, tmp = None, None
        try:
            payload = None
            for attempt in range(4):
                try:
                    payload = json.dumps(cfg, indent=2)
                    break
                except RuntimeError:
                    if attempt == 3:
                        raise               # → logged below; save_config never raises
                    _time.sleep(0.02 * (attempt + 1))
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(CONFIG_PATH) or ".",
                                       prefix=".pickit_cfg-", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                fd = None                      # fdopen owns it now
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())           # don't replace with a buffered file
            for attempt in range(4):
                try:
                    os.replace(tmp, CONFIG_PATH)
                    tmp = None
                    break
                except PermissionError:
                    if attempt == 3:
                        raise
                    _time.sleep(0.1 * (attempt + 1))
            log_info("config saved")
            return True
        except Exception:
            log_exc("save_config")
            return False
        finally:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            if tmp and os.path.exists(tmp):     # never leave temp files behind
                try:
                    os.remove(tmp)
                except OSError:
                    pass


# ── Debug log ─────────────────────────────────────────────────────────────────
LOG_PATH = os.path.join(_cfg_dir, "debug.log")
logger = logging.getLogger("pickit")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    try:
        _lh = RotatingFileHandler(LOG_PATH, maxBytes=512 * 1024, backupCount=2, encoding="utf-8")
        _lh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(_lh)
    except Exception:
        logger.addHandler(logging.NullHandler())


def log_exc(context: str = ""):
    """Log the currently-handled exception (call from inside an `except`)."""
    try:
        logger.exception("EXC %s", context)
    except Exception:
        import traceback
        traceback.print_exc()


def log_info(msg: str):
    try:
        logger.info(msg)
    except Exception:
        import traceback
        traceback.print_exc()
