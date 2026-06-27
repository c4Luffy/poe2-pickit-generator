"""In-app auto-updater (ports the old app's mechanism to Qt).

Checks ``version_qt.txt`` on the repo's main branch; if a newer version is
published, downloads the matching release asset and swaps it in via a detached
``.bat`` helper that waits for this process to exit, copies the new ``.exe`` over
the current one (retrying past Windows Defender file locks), relaunches, and self-
deletes. Only meaningful in a frozen build — in dev it just opens the releases page.

The Qt build uses its own tag scheme (``qt-v<version>``) and asset name so it never
collides with the customtkinter app's releases.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

from PySide6.QtCore import QObject, QThread, Signal

from src.core.version import VERSION

GITHUB_REPO = "c4Luffy/poe2-pickit-generator"
ASSET_NAME = "ExileBot2PickitQt.exe"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/version_qt.txt"
RELEASES_URL = f"https://github.com/{GITHUB_REPO}/releases"
_UA = {"User-Agent": f"poe2-pickit-qt/{VERSION}"}


def download_url(remote: str) -> str:
    return (f"https://github.com/{GITHUB_REPO}/releases/download/"
            f"qt-v{remote}/{ASSET_NAME}")


def version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except Exception:  # noqa: BLE001
        return (0,)


def is_newer(remote: str) -> bool:
    return version_tuple(remote) > version_tuple(VERSION)


class UpdateCheckWorker(QObject):
    """Fetches the published version string and reports whether it's newer."""

    result = Signal(str, bool)   # (remote_version, is_newer)
    failed = Signal(str)

    def run(self) -> None:
        try:
            import requests
            r = requests.get(VERSION_URL, timeout=8, headers=_UA)
            if r.status_code != 200:
                self.failed.emit(f"HTTP {r.status_code}")
                return
            remote = r.text.strip()
            self.result.emit(remote, is_newer(remote))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class DownloadWorker(QObject):
    """Streams the release .exe to a temp file, reporting percent progress."""

    progress = Signal(int)
    done = Signal(str)           # path to the downloaded .exe
    failed = Signal(str)

    def __init__(self, remote: str) -> None:
        super().__init__()
        self.remote = remote
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:
        try:
            import requests
            dest = os.path.join(tempfile.gettempdir(), ASSET_NAME)
            with requests.get(download_url(self.remote), stream=True,
                              timeout=(15, 60), headers=_UA) as r:
                if r.status_code != 200:
                    self.failed.emit(
                        f"HTTP {r.status_code} (the release asset may not be "
                        f"published yet)")
                    return
                total = int(r.headers.get("content-length") or 0)
                got = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(65536):
                        if self._cancel:
                            self.failed.emit("Cancelled.")
                            return
                        f.write(chunk)
                        got += len(chunk)
                        if total:
                            self.progress.emit(int(got / total * 100))
            self.done.emit(dest)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


def start_check(parent, on_result, on_failed=None):
    """Run an UpdateCheckWorker on a QThread; returns (thread, worker) — the caller
    MUST keep both refs alive until it finishes."""
    thread = QThread(parent)
    worker = UpdateCheckWorker()
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.result.connect(on_result)
    if on_failed is not None:
        worker.failed.connect(on_failed)
    worker.result.connect(thread.quit)
    worker.failed.connect(thread.quit)
    thread.start()
    return thread, worker


def swap_and_relaunch(new_exe: str) -> None:
    """Spawn a detached helper that waits for us to exit, overwrites the running
    .exe with ``new_exe`` (retrying past AV locks), relaunches, then self-deletes —
    then hard-exit so the file is unlocked. Ported from the old app."""
    cur = sys.executable
    pid = os.getpid()
    bat = os.path.join(tempfile.gettempdir(), "poe2_pickit_qt_update.bat")
    log = os.path.join(tempfile.gettempdir(), "poe2_pickit_qt_update.log")
    script = (
        "@echo off\r\n"
        "setlocal\r\n"
        f'set "LOG={log}"\r\n'
        'echo [update] helper started >> "%LOG%"\r\n'
        ":waitloop\r\n"
        f'tasklist /FI "PID eq {pid}" 2>NUL | find "{pid}" >NUL\r\n'
        "if not errorlevel 1 (\r\n"
        "  ping -n 2 127.0.0.1 >NUL\r\n"
        "  goto waitloop\r\n"
        ")\r\n"
        "ping -n 2 127.0.0.1 >NUL\r\n"
        "set /a tries=0\r\n"
        ":copyloop\r\n"
        f'copy /Y "{new_exe}" "{cur}" >NUL 2>&1\r\n'
        "if not errorlevel 1 goto copied\r\n"
        "set /a tries+=1\r\n"
        'echo [update] copy attempt %tries% failed >> "%LOG%"\r\n'
        "if %tries% GEQ 10 goto giveup\r\n"
        "ping -n 3 127.0.0.1 >NUL\r\n"
        "goto copyloop\r\n"
        ":copied\r\n"
        'echo [update] copy ok - relaunching >> "%LOG%"\r\n'
        f'start "" "{cur}"\r\n'
        "goto done\r\n"
        ":giveup\r\n"
        'echo [update] copy failed - opening releases page >> "%LOG%"\r\n'
        f'start "" "{RELEASES_URL}"\r\n'
        ":done\r\n"
        'del "%~f0"\r\n'
    )
    # OEM codepage = what cmd.exe reads .bat files in, so non-ASCII install paths
    # survive instead of being mangled.
    with open(bat, "w", encoding="oem") as f:
        f.write(script)
    DETACHED = 0x00000008 | 0x00000200   # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen(["cmd", "/c", bat], creationflags=DETACHED, close_fds=True)
    os._exit(0)
