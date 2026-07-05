"""Run the ExileBot 2 Pickit Generator GUI.

Usage:
    python -m exilebot_pickit           # Launch the GUI
    python -m exilebot_pickit --cli     # Run the CLI generator
"""
import sys as _sys

if "--cli" in _sys.argv:
    _sys.argv.remove("--cli")
    from exilebot_pickit.generator import main
    _sys.exit(main())

from exilebot_pickit.webui.poc import main
_sys.exit(main())
