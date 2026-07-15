#!/usr/bin/env python
"""Game-data drift checker — command-line front-end.

The engine lives in ``exilebot_pickit.data.game_data_check`` so the app can run
the exact same check from its Settings tab (this folder is not bundled into the
.exe). This file is just a printer.

Fetches the game's own mod and item tables and diffs them against the stat ids,
weights and base names our rules ship, so a patch that renames a stat is *caught*
instead of silently shipping rules that match nothing.

Exit code is non-zero when a critical finding turns up, so it can gate CI.

Usage:  python tools/check_game_data.py [--force]
"""
from __future__ import annotations
import argparse
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from exilebot_pickit.data.game_data_check import run_check  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true",
                    help="re-download the sources instead of using the cache")
    ap.add_argument("--json", action="store_true",
                    help="emit the raw result as JSON (for the scheduled patch-watch)")
    args = ap.parse_args()

    r = run_check(force=args.force)
    if args.json:
        import json
        print(json.dumps(r))
        return 2 if r["error"] else (1 if r["critical"] else 0)
    if r["error"]:
        print(f"✗ {r['error']}")
        return 2

    s = r["sources"]
    print("GAME-DATA CHECKER")
    print(f"  mods        : {s['mods']:,} ({s['affix_stats']:,} craftable-affix stat ids)")
    print(f"  base items  : {s['bases']:,} real bases (the authority on 'does it exist')")
    print(f"  NeverSink   : {s['neversink']:,} named bases (a styling list, NOT a drop list)")
    print(f"  checked     : {r.get('checked_stats', 0)} stat ids · "
          f"{r.get('checked_weights', 0)} weights · {r.get('checked_bases', 0)} bases")
    print()

    if not r["findings"]:
        print("  ✓ everything our rules hunt for still exists in the current patch")
    for f in r["findings"]:
        mark = "✗" if f["level"] == "critical" else "⚠"
        print(f"  {mark} [{f['kind']}] {f['title']}")
        print(f"      {f['detail']}")
        print(f"      used by: {', '.join(f['where'])}")
    print()
    print(f"SUMMARY: {r['critical']} critical, {r['advisory']} advisory")
    print("  → game data drifted; verify each ✗ before shipping." if r["critical"]
          else "  → data is in sync with the current patch.")
    return 1 if r["critical"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
