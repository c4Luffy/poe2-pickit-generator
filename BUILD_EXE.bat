@echo off
setlocal enabledelayedexpansion
title PoE2 Pickit - EXE Builder

echo ================================================
echo   PoE2 Pickit Generator - EXE Builder
echo ================================================
echo.

:: ── Check Python ──────────────────────────────────────────────────────────────
echo Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python not found in PATH.
    echo Install from https://python.org and tick "Add Python to PATH"
    echo.
    pause & exit /b 1
)

:: ── Install dependencies ──────────────────────────────────────────────────────
echo.
echo [1/4] Installing packages...
python -m pip install --upgrade pip --quiet
python -m pip install requests pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed. See above.
    pause & exit /b 1
)

:: ── Check required files exist ────────────────────────────────────────────────
echo.
echo [2/4] Checking files...
if not exist "poe2_pickit_gui.py" (
    echo ERROR: poe2_pickit_gui.py not found in this folder!
    echo Make sure all 3 files are in the same folder as this .bat
    pause & exit /b 1
)
if not exist "poe2_pickit_generator.py" (
    echo ERROR: poe2_pickit_generator.py not found in this folder!
    pause & exit /b 1
)
echo Files OK.

:: ── Clean old build ───────────────────────────────────────────────────────────
echo.
echo [3/4] Cleaning old build...
if exist "dist\PoE2PickitGenerator.exe" del /f "dist\PoE2PickitGenerator.exe"
if exist "build" rmdir /s /q "build"
if exist "PoE2PickitGenerator.spec" del /f "PoE2PickitGenerator.spec"

:: ── Build EXE ─────────────────────────────────────────────────────────────────
echo.
echo [4/4] Building EXE (takes ~60 seconds, please wait)...
echo.

python -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name "PoE2PickitGenerator" ^
    --add-data "poe2_pickit_generator.py;." ^
    --hidden-import "requests" ^
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

:: ── Verify EXE was created ────────────────────────────────────────────────────
if not exist "dist\PoE2PickitGenerator.exe" (
    echo.
    echo ERROR: Build seemed to succeed but EXE not found at dist\PoE2PickitGenerator.exe
    pause & exit /b 1
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ================================================
echo   BUILD SUCCESSFUL!
echo ================================================
echo.
echo Your EXE is at:
echo   %CD%\dist\PoE2PickitGenerator.exe
echo.
echo You can copy that EXE anywhere and double-click to run.
echo Settings are saved next to the EXE automatically.
echo.
echo NOTE: Windows Defender may warn about the EXE.
echo This is a false positive - click "More info" then "Run anyway".
echo.
echo Opening output folder...
echo.

:: Open the dist folder and close the window
start "" explorer "%CD%\dist"
exit /b 0