"""Run the ExileBot 2 Pickit Generator GUI.

Usage:
    python -m exilebot_pickit           # Launch the GUI
    python -m exilebot_pickit --cli     # Run the CLI generator
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


if "--cli" in _sys.argv:
    _sys.argv.remove("--cli")
    from exilebot_pickit.generator import main
    _sys.exit(main())

_set_dpi_awareness()
_tune_webview2()
from exilebot_pickit.webui.poc import main
_sys.exit(main())
