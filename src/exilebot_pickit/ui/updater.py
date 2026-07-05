"""Update-notification mixin for PickitApp.

The whole flow: on startup, ask GitHub whether a newer release exists; if so,
show a clickable banner that opens the Releases page in the browser. The user
downloads the new .exe themselves.

That's deliberate. Earlier versions tried to auto-download the new EXE and
hot-swap it in place via a detached backup/rollback helper — it repeatedly
failed in the field (antivirus locks, permission issues, half-swaps), so the
whole download/swap/rollback machinery was removed. A one-click trip to GitHub
can't brick an install, and grabbing the .exe by hand is trivial.
"""

import threading

import requests

from exilebot_pickit.ui.config import log_exc
from exilebot_pickit.version import VERSION  # single source of truth
GITHUB_REPO   = "c4Luffy/poe2-pickit-generator"
VERSION_URL   = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
# Point straight at the newest release so its .exe asset is one click away.
RELEASES_URL  = f"https://github.com/{GITHUB_REPO}/releases/latest"


class AutoUpdateMixin:
    """Adds a startup update-check + clickable 'update available' banner to a
    tk.Tk app. Expects the host to provide self.after, self.winfo_children(),
    the _update_lbl / _update_bar widgets, and a config dict self.cfg."""

    # ── Version compare (pure, unit-tested) ────────────────────────────────────

    @staticmethod
    def _ver_tuple(v: str):
        try:
            return tuple(int(x) for x in v.lstrip("v").split("."))
        except Exception:
            return (0,)

    @staticmethod
    def _should_offer_update(remote, current) -> bool:
        """True when `remote` is a newer version than `current`. Pure — no Tk,
        no I/O — so it's unit-testable."""
        remote = str(remote or "").lstrip("v").strip()
        if not remote:
            return False
        return AutoUpdateMixin._ver_tuple(remote) > AutoUpdateMixin._ver_tuple(current)

    # ── Check + notify ─────────────────────────────────────────────────────────

    def _check_update_async(self, manual: bool = False):
        """*manual* = the user clicked "Check for updates now" — every outcome
        must produce visible feedback (the silent startup check stays silent)."""
        threading.Thread(target=self._check_update, args=(manual,), daemon=True).start()

    def _notify_update_result(self, msg: str):
        """Show manual-check feedback via the host's Settings status label,
        falling back to the debug log."""
        lbl = getattr(self, "_settings_saved_lbl", None)
        if lbl is not None:
            lbl.configure(text=msg)
            self.after(5000, lambda: lbl.configure(text=""))
        if hasattr(self, "_log"):
            self._log(msg, "info")

    def _check_update(self, manual: bool = False):
        try:
            r = requests.get(VERSION_URL, timeout=8,
                             headers={"User-Agent": f"poe2-pickit/{VERSION}",
                                      "Accept": "application/vnd.github+json"})
            if r.status_code != 200:
                if manual:
                    self.after(0, lambda: self._notify_update_result(
                        f"Update check failed (GitHub said {r.status_code}) — try again later."))
                return
            remote = str((r.json() or {}).get("tag_name") or "").lstrip("v").strip()
            if self._should_offer_update(remote, VERSION):
                self.after(0, lambda rv=remote: self._show_update_banner(rv))
                if manual:
                    self.after(0, lambda rv=remote: self._notify_update_result(
                        f"⬆ v{rv} is available — see the banner at the top."))
            elif manual:
                self.after(0, lambda: self._notify_update_result(
                    f"✓ You're up to date (v{VERSION})."))
        except Exception:
            log_exc("update check")
            if manual:
                self.after(0, lambda: self._notify_update_result(
                    "Update check failed — no connection to GitHub."))

    def _show_update_banner(self, remote: str):
        """Reveal the (clickable) update banner. The banner label's <Button-1>
        binding calls _open_releases — see PickitApp._build_ui."""
        self._update_lbl.configure(
            text=f"⬆  Update available: v{remote}  —  click here to open the download "
                 f"page  (you have v{VERSION})"
        )
        try:
            self._update_bar.pack(fill="x", after=self.winfo_children()[1])
        except Exception:
            self._update_bar.pack(fill="x")

    def _open_releases(self):
        import webbrowser
        webbrowser.open(RELEASES_URL)
