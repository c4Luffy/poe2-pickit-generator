"""Deploy generated files to the bot / game folders after a generation.

Mirrors the old app: copy the ``.ipd`` into the Exiled Bot pickit folder and the
``.filter`` into the PoE2 client folder, each under a *stable* name (the output
base) so repeated/auto runs overwrite a single file instead of leaving a trail of
copies the bot never reads. Driven entirely by ``settings`` and called on the GUI
thread once the worker reports the written paths.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from src.core.settings import settings


def _copy(src: str, dest_dir: str, ext: str, stable: str) -> tuple[str, str]:
    if not (dest_dir and os.path.isdir(dest_dir)):
        return ("warn", f"folder not set or missing: {dest_dir or '(empty)'}")
    try:
        dest = os.path.join(dest_dir, stable + ext)
        shutil.copy2(src, dest)
        return ("ok", dest)
    except Exception as exc:  # noqa: BLE001
        return ("err", str(exc))


def deploy_outputs(ipd_path: str, filter_path: str) -> list[tuple[str, str]]:
    """Copy outputs per settings. Returns ``[(level, message), ...]`` where level
    is one of ``ok`` / ``warn`` / ``err``; empty if nothing was requested."""
    results: list[tuple[str, str]] = []
    stable = Path(ipd_path).stem or "poe2_pickit"

    if settings.get("auto_copy_ipd"):
        level, info = _copy(ipd_path, (settings.get("bot_folder") or "").strip(),
                            ".ipd", stable)
        results.append((level, f"Bot folder: {info}" if level != "ok"
                        else f"Copied .ipd to bot folder → {info}"))

    if settings.get("copy_filter_to_game"):
        level, info = _copy(filter_path, (settings.get("poe2_filter_dir") or "").strip(),
                            ".filter", stable)
        results.append((level, f"PoE2 folder: {info}" if level != "ok"
                        else f"Copied .filter to PoE2 folder → {info}"))

    return results
