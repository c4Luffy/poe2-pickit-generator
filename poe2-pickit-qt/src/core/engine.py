"""Bridge to the existing pickit engine.

Locates `poe2_pickit_generator.py` by walking up the directory tree (so the Qt app
can live anywhere under the repo), puts its folder on sys.path, imports it
unchanged, and points its offline price cache at a local folder. Everything else
in the Qt app imports `gen` from here.
"""
from __future__ import annotations

import sys
from pathlib import Path


def _find_engine_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "poe2_pickit_generator.py").exists():
            return parent
    raise ImportError("poe2_pickit_generator.py not found in any parent directory")


ENGINE_ROOT = _find_engine_root()
if str(ENGINE_ROOT) not in sys.path:
    sys.path.insert(0, str(ENGINE_ROOT))

import poe2_pickit_generator as gen  # noqa: E402  (path set up above)

# App-local folders (kept out of the repo via .gitignore patterns).
APP_DIR = Path(__file__).resolve().parents[2]          # poe2-pickit-qt/
OUTPUT_DIR = APP_DIR / "output"
CACHE_DIR = APP_DIR / "price_cache"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Survive-restarts price cache → enables offline generation when poe.ninja is down.
gen.set_disk_cache_dir(str(CACHE_DIR))

__all__ = ["gen", "OUTPUT_DIR", "CACHE_DIR", "ENGINE_ROOT"]
