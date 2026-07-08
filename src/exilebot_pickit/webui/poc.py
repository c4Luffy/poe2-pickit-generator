"""Entry point for the modern (WebView2) UI.

Run with:  python -m exilebot_pickit.webui.poc
Renders app.html in a WebView2 window (pywebview) on top of the existing
Python engine. Lives alongside the shipped Tkinter app; shares its config.

Tray mode: with the "minimize to tray" setting on, closing the window hides
it to the system tray instead of exiting. The tray menu offers
Show / Generate now / Exit.
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
    _start_freeze_watchdog()
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
    _fix_taskbar_restore(window, api)
    _run_webview(window, api, tray)


def _fix_taskbar_restore(window, api):
    """Work around a WinForms quirk: a FormBorderStyle.None ("frameless") form
    minimized via WindowState=Minimized often does not visually reappear or
    regain focus when Windows sends the restore command from a taskbar click.
    Borderless forms skip the non-client handling a bordered form gets for
    free, so pywebview's own state tracking (events.restored fires correctly)
    isn't enough — the form has to be explicitly re-shown/activated.

    Runs on the pywebview UI thread inside the `restored` event, so it must
    stay fast and never raise (mirrors the try/except-everywhere convention
    used for native-interop calls throughout this file and api.py).
    """
    def _on_restored():
        try:
            form = window.native
            from System.Drawing import Point
            from System.Windows.Forms import FormWindowState, Screen
            # Restore to whatever state the window was actually in (api._maxed
            # is kept accurate by win_max_toggle/win_snap) — forcing Normal
            # unconditionally left a window that was maximized on a SECONDARY
            # monitor before minimizing snapping back to a stale/never-
            # initialized Normal position, often entirely off every monitor.
            # The taskbar keeps showing a cached DWM thumbnail (looks "alive")
            # but the real window is invisible and unclickable.
            form.WindowState = (FormWindowState.Maximized if getattr(api, "_maxed", False)
                                 else FormWindowState.Normal)
            form.Show()
            # Safety net: if the restored bounds don't intersect ANY current
            # monitor's working area (stale position, or a monitor that was
            # unplugged/rearranged since), recenter on the primary screen
            # instead of leaving the window permanently invisible.
            try:
                on_screen = any(scr.WorkingArea.IntersectsWith(form.Bounds)
                                 for scr in Screen.AllScreens)
            except Exception:
                on_screen = True
            if not on_screen:
                prim = Screen.PrimaryScreen.WorkingArea
                form.WindowState = FormWindowState.Normal
                form.Location = Point(prim.X + (prim.Width - form.Width) // 2,
                                       prim.Y + (prim.Height - form.Height) // 2)
            # Nudge Windows into actually repainting/bringing the borderless
            # form to front — a plain Activate() alone is sometimes ignored
            # right after a taskbar-driven restore.
            form.TopMost = True
            form.TopMost = False
            form.Activate()
        except Exception:
            pass
    try:
        window.events.restored += _on_restored
    except Exception:
        pass


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
