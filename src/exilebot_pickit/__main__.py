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


if "--cli" in _sys.argv:
    _sys.argv.remove("--cli")
    from exilebot_pickit.generator import main
    _sys.exit(main())

_set_dpi_awareness()
from exilebot_pickit.webui.poc import main
_sys.exit(main())
