"""Entry point for the modern (WebView2) UI.

Run with:  python -m exilebot_pickit.webui.poc
Renders app.html in a WebView2 window (pywebview) on top of the existing
Python engine. Lives alongside the shipped Tkinter app; shares its config.
"""

import os
import sys

import webview

from exilebot_pickit.webui.api import AppApi


def _html_path() -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "app.html")


def _single_instance() -> bool:
    """Windows mutex so a second launch doesn't spawn a second window
    (same guard the Tk app uses, separate mutex name)."""
    if not sys.platform.startswith("win"):
        return True
    try:
        import ctypes
        ctypes.windll.kernel32.CreateMutexW(None, False,
                                            "POE2PickitModernUISingleInstance")
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def main():
    if not _single_instance():
        return
    api = AppApi()
    # Restore last window size (saved on close below)
    geo = api.cfg.get("window_geometry_web") or {}
    w = int(geo.get("w", 1120)) if isinstance(geo, dict) else 1120
    h = int(geo.get("h", 860)) if isinstance(geo, dict) else 860
    window = webview.create_window(
        "ExileBot 2 Pickit Generator",
        _html_path(),
        js_api=api,
        width=max(760, w), height=max(560, h),
        background_color="#0e0f12",
    )

    def _save_geometry():
        try:
            from exilebot_pickit.ui.config import save_config
            api.cfg["window_geometry_web"] = {"w": window.width, "h": window.height}
            save_config(api.cfg)
        except Exception:
            pass
    window.events.closing += _save_geometry
    webview.start()


if __name__ == "__main__":
    main()
