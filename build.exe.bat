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
if not exist "poe2_pickit_gui.py" (
    echo ERROR: poe2_pickit_gui.py not found in this folder!
    echo Make sure all files are in the same folder as this .bat
    pause & exit /b 1
)
if not exist "poe2_pickit_generator.py" (
    echo ERROR: poe2_pickit_generator.py not found in this folder!
    pause & exit /b 1
)
echo Files OK.

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
    --collect-data certifi ^
    --hidden-import certifi ^
    --hidden-import charset_normalizer ^
    --hidden-import urllib3 ^
    --hidden-import PIL ^
    --hidden-import PIL.Image ^
    --hidden-import PIL.ImageTk ^
    --hidden-import PIL.ImageDraw ^
    --collect-all customtkinter ^
    --noconfirm ^
    poe2_pickit_gui.py

if errorlevel 1 (
    echo.
    echo ================================================
    echo   BUILD FAILED - see errors above
    echo ================================================
    echo.
    echo Common fixes:
    echo  - Make sure poe2_pickit_generator.py is in this folder
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
