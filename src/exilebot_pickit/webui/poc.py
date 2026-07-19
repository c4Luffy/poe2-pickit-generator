"""Entry point for the modern (WebView2) UI.

Run with:  python -m exilebot_pickit.webui.poc
Renders app.html in a WebView2 window (pywebview) on top of the existing
Python engine. Lives alongside the shipped Tkinter app; shares its config.

Closing the window exits. (There used to be a "minimize to tray" mode; it kept the
process alive holding the .exe open, which silently broke self-update, and the
auto-regenerate it existed to serve was never built.)
"""

import os
import sys
import threading

import webview

from exilebot_pickit.webui.api import AppApi


def _start_freeze_watchdog():
    """Dump every thread's exact stack to <config dir>/watchdog.log every 15s,
    overwriting each time. Three rounds of freeze reports (multi-monitor
    restore, pointer-capture leak, drag-listener leak) have each been fixed
    from code review alone with no live capture — if it still happens, this
    file will show what every thread was actually doing in the ~15s before
    the freeze, instead of guessing a fourth theory blind. Runs on its own
    thread so it keeps dumping even if the UI thread itself is the one stuck
    in a blocking native call (that releases the GIL, same as any blocking
    I/O) — only a true GIL deadlock would stop it too, which is itself a
    useful data point."""
    import faulthandler
    import time
    try:
        from exilebot_pickit.ui.config import LOG_PATH
        path = os.path.join(os.path.dirname(LOG_PATH), "watchdog.log")
    except Exception:
        return

    def _loop():
        while True:
            time.sleep(15)
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    faulthandler.dump_traceback(file=f, all_threads=True)
            except Exception:
                pass
    threading.Thread(target=_loop, daemon=True, name="freeze-watchdog").start()


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


def _win_geometry(window):
    """Best-effort {x,y,w,h} of the window for save/restore. Reads the native
    WinForms bounds (position + size); falls back to pywebview width/height."""
    try:
        b = window.native.Bounds
        return {"x": int(b.X), "y": int(b.Y), "w": int(b.Width), "h": int(b.Height)}
    except Exception:
        try:
            return {"w": int(window.width), "h": int(window.height)}
        except Exception:
            return {}


def _saved_position(geo):
    """Restore the saved top-left ONLY if it still lands on a connected screen
    (a monitor may have been unplugged/rearranged since). Returns {} otherwise,
    so create_window centers on the primary screen."""
    if not (isinstance(geo, dict) and "x" in geo and "y" in geo):
        return {}
    try:
        x, y = int(geo["x"]), int(geo["y"])
        for scr in webview.screens:
            sx, sy = int(getattr(scr, "x", 0)), int(getattr(scr, "y", 0))
            if sx - 8 <= x <= sx + scr.width - 40 and sy - 8 <= y <= sy + scr.height - 40:
                return {"x": x, "y": y}
    except Exception:
        pass
    return {}


def main():
    if not _single_instance():
        return
    _start_freeze_watchdog()
    api = AppApi()
    geo = api.cfg.get("window_geometry_web") or {}

    def _dim(key, default):
        """A saved size that isn't a number must not stop the app from opening.

        _coerce_types only checks that window_geometry_web is a dict, so a bad
        INNER value (a string, None) survived a config load and raised here —
        before the window existed, so there was no error dialog and no window,
        on every launch, with no way for the user to see why.
        """
        if not isinstance(geo, dict):
            return default
        try:
            v = int(geo.get(key, default))
        except (TypeError, ValueError):
            return default
        return v if v > 0 else default

    w = _dim("w", 1120)
    h = _dim("h", 860)
    pos = _saved_position(geo)
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
        x=pos.get("x"), y=pos.get("y"),      # restore last position (or center)
        background_color="#0e0f12",
        # Native OS window frame (owner decision 2026-07-10): the frameless
        # custom-title-bar window had unfixable multi-monitor bugs — freezing /
        # "stuck in the taskbar, can't click it" on secondary screens, because
        # borderless WinForms forms mishandle taskbar restore, activation and
        # per-monitor moves. A standard frame lets Windows own all of that. The
        # page's own title bar + resize handles are hidden via CSS (.titlebar /
        # .rz) so there's exactly one title bar.
        frameless=False,
    )
    _run_webview(window, api)


def _run_webview(window, api):

    def _on_closing():
        try:
            from exilebot_pickit.ui.config import save_config
            api.cfg["window_geometry_web"] = _win_geometry(window)
            save_config(api.cfg)
        except Exception:
            pass
        return True
    window.events.closing += _on_closing
    # Pin the WebView2 browser profile to the app's own data folder. Without
    # this, WebView2 creates its profile relative to the exe/current dir --
    # which breaks in two real, user-reported ways on version updates:
    #   1. the exe sits somewhere read-only, so profile creation fails, and
    #   2. an old copy still running (not fully exited after the updater swap)
    #      holds the profile lock, so the new copy can't open.
    # Both used to surface as a misleading "WebView2 runtime is missing"
    # dialog even though the runtime was fine.
    try:
        from exilebot_pickit.ui.config import PRICE_CACHE_DIR
        storage = os.path.join(os.path.dirname(PRICE_CACHE_DIR), "webview_profile")
        os.makedirs(storage, exist_ok=True)
    except Exception:
        storage = None
    try:
        if storage:
            webview.start(storage_path=storage)
        else:
            webview.start()
    except Exception:
        # No fallback UI exists, so diagnose the two known causes honestly
        # instead of always blaming a missing WebView2 runtime.
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                "The app couldn't start its window.\n\n"
                "Most common causes, in order:\n\n"
                "1. An older copy of the app is still running — check the\n"
                "   Task Manager for\n"
                "   ExileBot2PickitGenerator, close it, then start again.\n\n"
                "2. The Microsoft WebView2 runtime is missing (rare on\n"
                "   updated Windows). Install it free from:\n"
                "   https://developer.microsoft.com/microsoft-edge/webview2/\n\n"
                "3. The app folder isn't writable — move the .exe to a\n"
                "   normal folder like Documents and run it from there.",
                "ExileBot 2 Pickit Generator", 0x10)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
