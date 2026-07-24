"""Run the ExileBot 2 Pickit Generator GUI.

Usage:
    python -m exilebot_pickit                     # Launch the GUI
    python -m exilebot_pickit --cli               # CLI generator (defaults)
    python -m exilebot_pickit --regenerate        # rebuild from SAVED settings, no window
    python -m exilebot_pickit --regenerate --league "Fate of the Vaal"
"""
import sys as _sys


def _set_dpi_awareness() -> None:
    """Declare Per-Monitor-V2 DPI awareness BEFORE any window is created.

    WebView2 requires the host process to be per-monitor DPI aware; without it
    the render host can hang on a monitor whose scaling differs from the
    primary — the multi-monitor freeze users hit on secondary screens. Must run
    before the first HWND exists (i.e. before importing/starting the GUI), and
    is a no-op on non-Windows / older Windows. Never fatal."""
    if not _sys.platform.startswith("win"):
        return
    import ctypes
    # PER_MONITOR_AWARE_V2 context handle (-4). Falls back for older Windows.
    for attempt in (
        lambda: ctypes.windll.user32.SetProcessDpiAwarenessContext(-4),
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(2),   # PER_MONITOR
        lambda: ctypes.windll.user32.SetProcessDPIAware(),        # system-aware
    ):
        try:
            attempt()
            return
        except Exception:
            continue


def _tune_webview2() -> None:
    """Disable Chromium's native window-occlusion detection in WebView2.

    Chromium (which WebView2 embeds) throttles rendering to ~zero when it thinks
    a window is occluded. On multi-monitor setups that detection misfires — the
    window on a secondary screen (or the main one after a while) is wrongly
    judged hidden, so WebView2 stops painting and the UI *looks* frozen while the
    process is actually fine. Electron/VS Code/Discord all ship this same switch.

    The flag is read from WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS at environment
    creation, so it must be set before the GUI (and thus WebView2) starts. We
    append to any value the user already set rather than clobbering it."""
    import os
    key = "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"
    flags = "--disable-features=CalculateNativeWinOcclusion"
    existing = os.environ.get(key, "")
    if "CalculateNativeWinOcclusion" not in existing:
        os.environ[key] = (existing + " " + flags).strip()


def _console_utf8() -> None:
    """Make the console-mode output UTF-8 safe.

    Both headless modes print progress with '✓' and '·'. On Windows a console
    that isn't UTF-8 (cp1252 — which is exactly what Task Scheduler and a
    redirected pipe give you) raises UnicodeEncodeError on the FIRST ticked
    category, aborting the run before a single file is written. ``--regenerate``
    is documented for Task Scheduler, so its intended environment was the one
    that broke it. Same wrapper tools/check_game_data.py already uses;
    errors='replace' means an exotic console degrades a glyph instead of
    killing the run."""
    import io
    for _name in ("stdout", "stderr"):
        _s = getattr(_sys, _name, None)
        if _s is None or not hasattr(_s, "buffer"):
            continue                      # already wrapped, or no real stream
        try:
            if (getattr(_s, "encoding", "") or "").lower().replace("-", "") != "utf8":
                setattr(_sys, _name, io.TextIOWrapper(
                    _s.buffer, encoding="utf-8", errors="replace", line_buffering=True))
        except Exception:
            pass                          # never let logging setup kill the app


if "--regenerate" in _sys.argv:
    _sys.argv.remove("--regenerate")
    _console_utf8()
    _league = None
    if "--league" in _sys.argv:
        _i = _sys.argv.index("--league")
        _league = _sys.argv[_i + 1] if _i + 1 < len(_sys.argv) else None
    from exilebot_pickit.webui.api import headless_regenerate
    _sys.exit(headless_regenerate(_league))

if "--cli" in _sys.argv:
    _sys.argv.remove("--cli")
    _console_utf8()
    from exilebot_pickit.generator import main
    _sys.exit(main())

_set_dpi_awareness()
_tune_webview2()
from exilebot_pickit.webui.poc import main
_sys.exit(main())
