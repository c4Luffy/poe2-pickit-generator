"""Entry point for the modern (WebView2) UI.

Run with:  python -m exilebot_pickit.webui.poc
Renders app.html in a WebView2 window (pywebview) on top of the existing
Python engine. Lives alongside the shipped Tkinter app; shares its config.

Tray mode: with the "minimize to tray" setting on, closing the window hides
it to the system tray instead of exiting — the page (and its auto-regenerate
timer) keeps running. The tray menu offers Show / Generate now / Exit.
"""

import os
import sys
import threading

import webview

from exilebot_pickit.webui.api import AppApi


def _res_path(name: str) -> str:
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return os.path.join(base, name)
    here = os.path.dirname(os.path.abspath(__file__))
    local = os.path.join(here, name)
    if os.path.isfile(local):
        return local
    return os.path.join(here, "..", "resources", name)


def _single_instance() -> bool:
    """Windows mutex so a second launch doesn't spawn a second window."""
    if not sys.platform.startswith("win"):
        return True
    try:
        import ctypes
        ctypes.windll.kernel32.CreateMutexW(None, False,
                                            "POE2PickitModernUISingleInstance")
        return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS
    except Exception:
        return True


def _start_tray(window, api):
    """System-tray icon (pystray) running on its own thread."""
    try:
        import pystray
        from PIL import Image
        img = Image.open(_res_path("appicon.png"))
    except Exception:
        return None

    def _show(icon, item):
        window.show()
        window.restore()

    def _gen(icon, item):
        c = api.cfg
        api.generate(c.get("league") or "", c.get("min_exalt_gear", 0),
                     c.get("min_exalt_unique", 0))

    def _exit(icon, item):
        icon.stop()
        api.cfg["window_geometry_web"] = {"w": window.width, "h": window.height}
        from exilebot_pickit.ui.config import save_config
        save_config(api.cfg)
        window.destroy()

    icon = pystray.Icon("poe2pickit", img, "ExileBot 2 Pickit Generator",
                        menu=pystray.Menu(
                            pystray.MenuItem("Show", _show, default=True),
                            pystray.MenuItem("Generate now", _gen),
                            pystray.MenuItem("Exit", _exit)))
    threading.Thread(target=icon.run, daemon=True).start()
    return icon


def main():
    if not _single_instance():
        return
    api = AppApi()
    geo = api.cfg.get("window_geometry_web") or {}
    w = int(geo.get("w", 1120)) if isinstance(geo, dict) else 1120
    h = int(geo.get("h", 860)) if isinstance(geo, dict) else 860
    # Clamp to the primary screen so the window never opens taller/wider than
    # the desktop (default 860px is too tall for a 1366x768 laptop).
    try:
        scr = webview.screens[0]
        w = min(w, scr.width - 40)
        h = min(h, scr.height - 90)     # leave room for the taskbar
    except Exception:
        pass
    window = webview.create_window(
        "ExileBot 2 Pickit Generator",
        _res_path("app.html") if getattr(sys, "_MEIPASS", None)
        else os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.html"),
        js_api=api,
        width=max(760, w), height=max(560, h),
        background_color="#0e0f12",
        # Frameless: the page draws its own title bar (drag region + min/max/
        # close buttons wired through AppApi.win_*). Alt+F4 still fires the
        # normal closing handler below.
        frameless=True, easy_drag=False,
    )
    tray = _start_tray(window, api)
    api._tray = tray            # win_close() needs it to stop/hide correctly
    _run_webview(window, api, tray)


def _run_webview(window, api, tray):

    def _on_closing():
        # Tray mode on → hide instead of exit so auto-regenerate keeps running.
        if tray is not None and api.cfg.get("minimize_to_tray"):
            window.hide()
            return False        # cancel the close
        try:
            from exilebot_pickit.ui.config import save_config
            api.cfg["window_geometry_web"] = {"w": window.width, "h": window.height}
            save_config(api.cfg)
        except Exception:
            pass
        if tray is not None:
            tray.stop()
        return True
    window.events.closing += _on_closing
    try:
        webview.start()
    except Exception:
        # Almost always a missing WebView2 runtime (rare on updated Windows).
        # With the Tk UI removed there is no fallback, so say exactly what to do.
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                "The app couldn't start its window.\n\n"
                "This usually means the Microsoft WebView2 runtime is missing.\n"
                "Install it (free, one minute) from:\n"
                "https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
                "then start the app again.",
                "ExileBot 2 Pickit Generator", 0x10)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
