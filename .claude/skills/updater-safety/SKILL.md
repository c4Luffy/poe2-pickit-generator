---
name: updater-safety
description: Load-bearing invariants for the in-app self-updater (download + swap-in-place). Breaking these bricks users' installs - it already happened once.
---

# Updater safety (this repo)

The self-updater lives in `src/exilebot_pickit/webui/api.py`
(`download_update` / `_download_update_worker` / `install_update`) and the
banner/state-machine in `webui/app.html`. A running `.exe` is locked by Windows,
so the swap happens via a detached helper `.bat` that runs AFTER the app exits.
Getting this wrong ships a corrupt exe that fails with
`Failed to load python3xx.dll` — a full brick. It happened once (fixed in
v3.8.1). Do not regress these.

## Non-negotiable invariants

1. **Verify the download before it is ever eligible to install.** After the
   stream completes, reject a truncated file (`done != Content-Length`) AND
   verify SHA256 against the release's `SHA256SUMS.txt` asset. Only on a match
   does `os.replace(dest + ".part", dest)` promote it. On any mismatch: raise,
   delete the `.part`, leave the old version untouched. Never install an
   unverified binary.
2. **Never delete the old exe before the new one is confirmed running.** The
   helper `.bat` copies `cur -> cur.bak`, moves `new -> cur`, and on `errorlevel`
   restores `cur.bak` and relaunches. It keeps `.bak` (a working fallback) rather
   than deleting it on success — only ever one copy, overwritten next update.
3. **The exe filename `ExileBot2PickitGenerator.exe` MUST NEVER CHANGE.** The
   updater's download URL and the swap depend on it, and `release.yml` publishes
   exactly that name. Renaming it breaks every existing user's updater.
4. **Frozen-only.** Self-install only runs under `sys.frozen`; in dev it just
   drops the file in Downloads. The helper `.bat` waits on the PID
   (`tasklist /FI "PID eq ..."`), runs detached (`CREATE_NO_WINDOW` = 0x08000000),
   and the app closes via `webview.windows[0].destroy()` so the swap can proceed.

## Recovery / diagnosis when a user reports a bad update

- The **released binary is almost always fine** — prove it: `gh release download`
  the exe + `SHA256SUMS.txt`, compare hashes, and RUN it locally. If it launches,
  the release is good and the fault was the download/swap (or AV), not the build.
- Hand the user a **verified copy** (hash-checked) to unbrick immediately; the
  `.bak` beside their exe is the previous working version if it's still there.
- The permanent guard is invariant #1 (checksum gate) — but it only protects
  downloads made by the fixed version onward. Users already on a broken build
  must re-download by hand (the Settings "Re-download manually" link).

## When you touch updater code

- Re-verify the whole flow end-to-end, not just tests (there are none for the
  helper `.bat`). Confirm: checksum gate rejects a bad file, `.bak` is retained,
  the exe name is unchanged, and the old version survives a failed swap.
