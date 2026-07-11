"""Config path bootstrap, defaults, and load/save."""

import sys, os, json, shutil, logging
from logging.handlers import RotatingFileHandler

# ── Config ────────────────────────────────────────────────────────────────────
# Built EXE: keep everything in ONE tidy data folder next to the .exe instead of
# scattering config/caches/output loose beside it (e.g. all over the Desktop).
if getattr(sys, 'frozen', False):
    _exe_dir = os.path.dirname(sys.executable)
    _cfg_dir = os.path.join(_exe_dir, "ExileBot2PickitGenerator_data")
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
    "output_base": "poe2_pickit",
    "bot_folder": "",
    "auto_copy": False,
    "backup_count": 5,
    "category_enabled": {},
    "history": [],

    "theme": "dark",
    "minimize_to_tray": False,
    "magic_rare_flasks": True,
    # League names already seen in the dropdown — one NOT in this list
    # triggers the "new league detected" banner on the Generate tab.
    "known_leagues": [],
    "window_geometry_web": "",
    "confirm_overwrite_secs": 120,
    "include_bases": True,
    # Auto floor: recompute both value floors from live prices on every
    # generate ("keep top N%" percentile).
    "auto_floor": False,
    "auto_floor_pct": 40,
    "base_quality": 25,
    "base_min_level": 82,
    "item_states":  {},
    "last_gen_prices": {},
    "profiles": {},
    "active_profile": "",

    # OFF by default: an in-game loot filter that HIDES items can make Exiled Bot
    # get stuck (it still detects hidden items and paths to them, but the pickup
    # stalls on the un-rendered label). The .filter is still written next to the
    # .ipd for anyone who wants it; this only controls copying it into the PoE2
    # client folder. Bot users should leave it off.
    "copy_filter_to_game": False,
    "poe2_filter_dir": "",
}


# Set when load_config had to fall back — the UI shows a one-time warning
# instead of silently resetting the user's settings.
CONFIG_LOAD_ERROR = ""


def _coerce_types(cfg):
    """Drop config values whose type disagrees with DEFAULT_CONFIG.

    Guards startup against hand-edited or cross-version configs — a list where
    a dict is expected (e.g. ``"category_enabled": []``) used to crash Tk var
    construction on every launch. Numbers are interchangeable (int/float/bool),
    everything else must match the default's type exactly."""
    for key, default in DEFAULT_CONFIG.items():
        v = cfg.get(key)
        if v is None or isinstance(default, type(v)) or isinstance(v, type(default)):
            continue
        if isinstance(default, (int, float)) and isinstance(v, (int, float)) \
                and not isinstance(v, bool):
            continue
        cfg[key] = default if not isinstance(default, (dict, list)) else type(default)()
    return cfg


def load_config():
    global CONFIG_LOAD_ERROR
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("config root is not an object")
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(data)
        _coerce_types(cfg)
        if cfg.get("base_min_level") == 75:
            cfg["base_min_level"] = 82
        # old default 28 -> owner picked 25 (between NeverSink's 27+ top tier
        # and 24 mid tier); user-set values other than 28 are left alone.
        if cfg.get("base_quality") == 28:
            cfg["base_quality"] = 25
        return cfg
    except FileNotFoundError:
        return dict(DEFAULT_CONFIG)          # first run — nothing to recover
    except Exception:
        log_exc("load_config")
        # Preserve the corrupt file for recovery instead of silently wiping
        # every setting/profile/exclusion, and tell the UI to say so.
        try:
            bak = CONFIG_PATH + ".corrupt.bak"
            shutil.copyfile(CONFIG_PATH, bak)
            CONFIG_LOAD_ERROR = (
                "Your settings file couldn't be read, so defaults were loaded.\n"
                f"The unreadable file was kept at:\n{bak}")
        except Exception:
            CONFIG_LOAD_ERROR = ("Your settings file couldn't be read, "
                                 "so defaults were loaded.")
        return dict(DEFAULT_CONFIG)


def save_config(cfg):
    """Atomic write (tmp + os.replace) — a crash mid-write can no longer
    truncate the config and wipe profiles/history/item selections.

    The final os.replace is retried: on Windows it fails with WinError 32 if
    another process momentarily holds the file open (the other UI saving at
    the same instant, or an antivirus scan). One lost save used to be the
    result; a few short retries almost always win the race instead."""
    import time as _time
    try:
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        for attempt in range(4):
            try:
                os.replace(tmp, CONFIG_PATH)
                break
            except PermissionError:
                if attempt == 3:
                    raise
                _time.sleep(0.1 * (attempt + 1))
        log_info("config saved")
    except Exception:
        log_exc("save_config")


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
