@echo off
setlocal enabledelayedexpansion
title ExileBot 2 Pickit - EXE Builder

echo ================================================
echo   ExileBot 2 Pickit Generator - EXE Builder
echo ================================================
echo.

:: ── [1/5] Check Python ─────────────────────────────────────────────────────────
echo [1/5] Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python not found in PATH.
    echo Install from https://python.org and tick "Add Python to PATH"
    echo.
    pause & exit /b 1
)

:: ── [2/5] Install dependencies ─────────────────────────────────────────────────
echo.
echo [2/5] Installing packages...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See above.
    pause & exit /b 1
)

:: ── [3/5] Check required files exist ───────────────────────────────────────────
echo.
echo [3/5] Checking files...
if not exist "src\exilebot_pickit\__main__.py" (
    echo ERROR: src\exilebot_pickit\__main__.py not found!
    echo Make sure you're in the project root folder.
    pause & exit /b 1
)
:: appicon.ico gives the EXE its Explorer icon (--icon) and is bundled so the
:: app can set its window/taskbar icon at runtime (--add-data). Without it the
:: EXE builds with the default blank PyInstaller icon. Set outside a parenthesised
:: block so the quotes around the src;dest pair survive cmd parsing.
set "ICON_ARGS="
if exist "src\exilebot_pickit\resources\appicon.ico" set ICON_ARGS=--icon src/exilebot_pickit/resources/appicon.ico --add-data "src/exilebot_pickit/resources/appicon.ico;."
if exist "src\exilebot_pickit\resources\appicon.ico" (echo Files OK ^(app icon found^).) else (echo Files OK ^(WARNING: appicon.ico missing - EXE will have no icon^).)

:: ── [4/5] Clean old build ──────────────────────────────────────────────────────
echo.
echo [4/5] Cleaning old build...
if exist "dist\ExileBot2PickitGenerator.exe" del /f "dist\ExileBot2PickitGenerator.exe"
if exist "build" rmdir /s /q "build"
if exist "ExileBot2PickitGenerator.spec" del /f "ExileBot2PickitGenerator.spec"

:: ── [5/5] Build EXE ────────────────────────────────────────────────────────────
echo.
echo [5/5] Building EXE (takes ~60 seconds, please wait)...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "ExileBot2PickitGenerator" ^
    %ICON_ARGS% ^
    --add-data "src/exilebot_pickit/webui/app.html;." ^
    --add-data "src/exilebot_pickit/resources/appicon.png;." ^
    --collect-all webview ^
    --collect-all clr_loader ^
    --collect-all pythonnet ^
    --collect-all pystray ^
    --collect-data certifi ^
    --hidden-import certifi ^
    --hidden-import charset_normalizer ^
    --hidden-import urllib3 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageDraw ^
    --collect-all exilebot_pickit ^
    --noconfirm ^
    src/exilebot_pickit/__main__.py

if errorlevel 1 (
    echo.
    echo ================================================
    echo   BUILD FAILED - see errors above
    echo ================================================
    echo.
    echo Common fixes:
    echo  - Make sure src/exilebot_pickit/ works (are you in the project root?)
    echo  - Try running as Administrator
    echo  - Check antivirus isn't blocking pyinstaller
    echo.
    pause & exit /b 1
)

:: ── Verify EXE was created ─────────────────────────────────────────────────────
if not exist "dist\ExileBot2PickitGenerator.exe" (
    echo.
    echo ERROR: Build seemed to succeed but EXE not found at dist\ExileBot2PickitGenerator.exe
    pause & exit /b 1
)

:: ── Done ───────────────────────────────────────────────────────────────────────
echo.
echo ================================================
echo   BUILD SUCCESSFUL!
echo ================================================
echo.
echo Your EXE is at:
echo   %CD%\dist\ExileBot2PickitGenerator.exe
echo.
echo You can copy that EXE anywhere and double-click to run.
echo Settings/output live in an ExileBot2PickitGenerator_data folder beside the EXE.
echo.
echo NOTE: Windows Defender may warn about the EXE.
echo This is a false positive - click "More info" then "Run anyway".
echo.
echo Opening output folder...
echo.

:: Open the dist folder and close the window
start "" explorer "%CD%\dist"
exit /b 0
