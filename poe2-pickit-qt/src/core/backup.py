"""Timestamped backups of the generated pickit, with rotation.

Before a generation overwrites an existing ``.ipd``, the old file is copied to
``<base>_backup_<timestamp>.ipd`` and only the newest ``keep`` backups are kept.
The ``*_backup_*.ipd`` pattern is gitignored. Pure + side-effect-local so it's easy
to unit test.
"""
from __future__ import annotations

import datetime
import glob
import os
import shutil


def rotate_backup(path: str, keep: int) -> str | None:
    """Back up ``path`` (if it exists) and prune to the newest ``keep`` backups.

    Returns the backup path created, or None if nothing was backed up.
    """
    if keep <= 0 or not os.path.exists(path):
        return None
    base, ext = os.path.splitext(path)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = f"{base}_backup_{ts}{ext}"
    try:
        shutil.copy2(path, dst)
    except Exception:  # noqa: BLE001  (a failed backup must not block generation)
        return None
    backups = sorted(glob.glob(f"{base}_backup_*{ext}"))
    for old in backups[:-keep]:
        try:
            os.remove(old)
        except OSError:
            pass
    return dst
