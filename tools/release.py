#!/usr/bin/env python3
"""One-command release: gate -> bump version.py -> commit -> tag -> push -> notes.

Cuts the manual 7-step dance down to one command, and closes the two footguns that have
actually bitten this project:
  * version.py != tag  -> the release workflow hard-fails ("Version mismatch").
  * tagging a build that never passed the gates -> a broken exe ships (v4.22.0 did).

The script writes version.py FROM the version you pass and tags v<that>, so they can't
disagree; and it runs every gate BEFORE it touches git, aborting on the first failure.

Usage:
  python tools/release.py 4.34.0 -m "subject line for the commit" --notes NOTES.md
  python tools/release.py 4.34.0 -m "subject" --notes NOTES.md --dry-run   # gates only, no writes

Prerequisites: your code + CHANGELOG changes for this version are already in the working
tree (the script bumps version.py, commits everything, tags, and pushes). `gh` must be
authenticated for the notes/latest step; without it the release still publishes via CI —
you just set notes by hand.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# The Windows console defaults to cp1252, which can't encode the status glyphs below and
# would crash the tool mid-run. Force UTF-8 output where the runtime supports it.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "src" / "exilebot_pickit" / "version.py"
CHANGELOG = ROOT / "CHANGELOG.md"

GATES = [
    ("tests", [sys.executable, "-m", "pytest", "-q"]),
    ("lint", [sys.executable, "-m", "ruff", "check", "."]),
    ("ui gate", [sys.executable, "tools/check_ui.py"]),
    ("ui logic", ["node", "tests/test_ui_logic.mjs"]),
]


def run(cmd, **kw):
    return subprocess.run(cmd, cwd=ROOT, **kw)


def die(msg: str) -> None:
    print(f"\n✗ {msg}")
    sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="One-command release.")
    ap.add_argument("version", help="X.Y.Z (no leading v)")
    ap.add_argument("-m", "--message", required=True, help="commit subject (after 'vX.Y.Z: ')")
    ap.add_argument("--notes", help="path to a markdown file for the release body")
    ap.add_argument("--dry-run", action="store_true",
                    help="run the gates and show the plan; make NO commits/tags/pushes")
    a = ap.parse_args()

    if not re.fullmatch(r"\d+\.\d+\.\d+", a.version):
        die(f"version must be X.Y.Z, got {a.version!r}")
    tag = f"v{a.version}"

    # on main, and the tag doesn't already exist
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"],
                 capture_output=True, text=True).stdout.strip()
    if branch != "main":
        die(f"not on main (on {branch}) — releases cut from main")
    if run(["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
           capture_output=True).returncode == 0:
        die(f"tag {tag} already exists")

    # Sync with the remote BEFORE the gates, so the gates validate exactly the
    # tree that ships. (This used to happen after the commit, exit code ignored:
    # a remote commit pushed mid-release got folded in UNGATED, and a rebase
    # conflict left the repo mid-rebase with the bump already committed.)
    # --autostash: the working tree legitimately carries this release's changes.
    if run(["git", "pull", "--rebase", "--autostash", "-q",
            "origin", "main"]).returncode != 0:
        die("git pull --rebase failed — resolve (or `git rebase --abort`) and rerun")

    # CHANGELOG must mention this version (soft — warn, don't block)
    if CHANGELOG.exists() and f"[{tag}]" not in CHANGELOG.read_text(encoding="utf-8"):
        print(f"⚠ CHANGELOG has no '## [{tag}]' entry — add it before release.")

    # ── gates, before touching anything ─────────────────────────────────────────
    print(f"Releasing {tag}: running gates first\n")
    for name, cmd in GATES:
        print(f"  … {name}")
        if run(cmd, capture_output=True).returncode != 0:
            # re-run visibly so the failure is on screen
            run(cmd)
            die(f"gate '{name}' failed — nothing tagged, nothing pushed")
    print("  ✓ all gates green\n")

    if a.dry_run:
        print("DRY RUN — would now:")
        print(f"  set version.py = {a.version}")
        print(f"  git commit -am '{tag}: {a.message}'")
        print(f"  git tag {tag} && git push origin main && git push origin {tag}")
        print("  wait for the release build, then set notes + --latest")
        return 0

    # ── bump, commit, tag, push ─────────────────────────────────────────────────
    VERSION_FILE.write_text(
        '"""Single source of truth for the app version."""\n'
        f'VERSION = "{a.version}"\n', encoding="utf-8", newline="\n")

    run(["git", "add", "-A"])
    if run(["git", "commit", "-q", "-m", f"{tag}: {a.message}"]).returncode != 0:
        die("git commit failed (nothing to commit?)")
    # No pull here: the sync happened BEFORE the gates. If someone pushed during
    # the gate run, fail loudly rather than tagging code the gates never saw.
    if run(["git", "push", "-q", "origin", "main"]).returncode != 0:
        die("git push failed — remote moved during the release? "
            "rerun (the pre-gate sync will pick the new commits up)")
    run(["git", "tag", tag])
    if run(["git", "push", "-q", "origin", tag]).returncode != 0:
        die(f"pushing tag {tag} failed")
    print(f"✓ pushed {tag} — CI is building the exe")

    # ── wait for the build, set notes + latest ──────────────────────────────────
    if not _have_gh():
        print("gh not available — the release will publish via CI; set notes by hand.")
        return 0
    _wait_and_publish(tag, a.notes)
    return 0


def _have_gh() -> bool:
    try:
        return run(["gh", "auth", "status"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


def _wait_and_publish(tag: str, notes: str | None) -> None:
    import json
    import time
    print("  waiting for the release build …")
    # Match the run to THIS tag (headBranch == the tag name for tag pushes).
    # Grabbing the newest run used to race: seconds after the push, the newest
    # run is often the PREVIOUS release's finished build — watch returned
    # instantly and the asset check then failed with a bogus "no exe" error.
    rid = None
    for _ in range(30):                        # ~5 min for the run to appear
        out = run(["gh", "run", "list", "--workflow=release.yml", "--limit", "5",
                   "--json", "databaseId,headBranch,status"],
                  capture_output=True, text=True).stdout
        try:
            rid = next((r.get("databaseId") for r in json.loads(out) or []
                        if r.get("headBranch") == tag), None)
        except Exception:
            rid = None
        if rid:
            break
        time.sleep(10)
    if rid:
        if run(["gh", "run", "watch", str(rid), "--exit-status"],
               capture_output=True).returncode != 0:
            die(f"release build FAILED — see `gh run view {rid}`")
    else:
        print(f"  ⚠ never saw a run for {tag} — checking release assets anyway")
    assets = run(["gh", "release", "view", tag, "--json", "assets",
                  "--jq", ".assets[].name"], capture_output=True, text=True).stdout
    if "ExileBot2PickitGenerator.exe" not in assets:
        die(f"release build did not produce the exe — check `gh run view {rid}`")
    print("  ✓ exe + checksums built")
    if notes and Path(notes).exists():
        run(["gh", "release", "edit", tag, "--notes-file", notes, "--latest"])
        print("  ✓ notes set, marked latest")
    else:
        run(["gh", "release", "edit", tag, "--latest"])
        print("  ✓ marked latest (no --notes file given; set the body by hand)")
    print(f"\n✓ {tag} released.")


if __name__ == "__main__":
    sys.exit(main())
