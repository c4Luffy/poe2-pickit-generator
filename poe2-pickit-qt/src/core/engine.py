"""Bridge to the existing pickit engine.

Locates `poe2_pickit_generator.py` by walking up the directory tree (so the Qt app
can live anywhere under the repo), puts its folder on sys.path, imports it
unchanged, and points its offline price cache at a local folder. Everything else
in the Qt app imports `gen` from here.
"""
from __future__ import annotations

import sys
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)


def _find_engine_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "poe2_pickit_generator.py").exists():
            return parent
    raise ImportError("poe2_pickit_generator.py not found in any parent directory")


if FROZEN:
    # PyInstaller build: the engine module is bundled (importable directly via the
    # frozen importer), and persistent user data must live NEXT TO the .exe — not
    # in the temporary _MEIPASS extraction dir, which is wiped on exit.
    ENGINE_ROOT = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    APP_DIR = Path(sys.executable).resolve().parent
else:
    ENGINE_ROOT = _find_engine_root()
    APP_DIR = Path(__file__).resolve().parents[2]          # poe2-pickit-qt/

if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

import poe2_pickit_generator as gen  # noqa: E402  (path set up above)

# App-local folders (kept out of the repo via .gitignore patterns; sit beside the
# .exe in a frozen build).
OUTPUT_DIR = APP_DIR / "output"
CACHE_DIR = APP_DIR / "price_cache"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Survive-restarts price cache → enables offline generation when poe.ninja is down.
gen.set_disk_cache_dir(str(CACHE_DIR))

__all__ = ["gen", "OUTPUT_DIR", "CACHE_DIR", "ENGINE_ROOT", "APP_DIR", "FROZEN"]
