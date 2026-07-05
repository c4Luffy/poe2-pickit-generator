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


def main():
    api = AppApi()
    webview.create_window(
        "ExileBot 2 Pickit Generator — Modern UI",
        _html_path(),
        js_api=api,
        width=1120, height=860,
        background_color="#0e0f12",
    )
    webview.start()


if __name__ == "__main__":
    main()
