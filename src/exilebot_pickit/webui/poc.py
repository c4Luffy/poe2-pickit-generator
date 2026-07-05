"""Entry point for the modern-UI proof of concept.

Run with:  python -m exilebot_pickit.webui.poc
Renders index.html in a WebView2 window (pywebview) on top of the existing
Python engine. Deliberately separate from the shipped Tkinter app.
"""

import os
import sys

import webview

from exilebot_pickit.webui.api import PocApi


def _html_path() -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "index.html")


def main():
    api = PocApi()
    webview.create_window(
        "ExileBot 2 Pickit — Modern UI (PoC)",
        _html_path(),
        js_api=api,
        width=860, height=940,
        background_color="#0e0f12",
    )
    webview.start()


if __name__ == "__main__":
    main()
