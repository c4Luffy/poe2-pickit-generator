# ExileBot 2 Pickit — Qt prototype (Phase 1)

A modern PySide6 shell being built **in parallel** to the working customtkinter app.
This is the Phase 1 prototype: app shell, JSON theming, animated sidebar, progress
widgets, system monitor, and an in-app console. The pricing/generation **engine is
reused unchanged** and gets wired in from Phase 2 onward.

## Run it

```bash
cd poe2-pickit-qt
pip install -r requirements.txt
python main.py
```

## What's here

| Path | Purpose |
|---|---|
| `main.py` | Entry point — builds the app, theme, and window |
| `src/app.py` | `MainWindow` shell (sidebar + page stack + theme toggle) |
| `src/core/theme_manager.py` | JSON tokens → QSS, live dark/light toggle |
| `src/core/logger.py` | Logging bridged to a Qt signal for the console |
| `src/core/signals.py` | App-wide signal bus |
| `src/ui/widgets/sidebar.py` | Collapsible sidebar (QPropertyAnimation) |
| `src/ui/widgets/circular_progress.py` | QPainter ring, QSS-coloured |
| `src/ui/widgets/linear_progress.py` | Borderless QSS progress bar |
| `src/ui/widgets/system_monitor.py` | CPU/RAM widget (psutil or simulated) |
| `src/components/dashboard.py` | First composed view |
| `src/styles/themes/*.json` | Theme token files |
| `src/styles/app.qss.template` | QSS with `{{token}}` placeholders |

## Try
- Click **☰** (top of the sidebar) to collapse/expand it (animated).
- Click **🌓 Theme** (top bar) to toggle dark/light instantly.
- Click **Run demo task** to animate the circular progress.
