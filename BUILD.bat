@echo off
:: ============================================================
::  BUILD.bat — One-click build for Ravi Instant Photo
::  Run this from the project folder (where bg_remover.py is)
:: ============================================================

title Building Ravi Instant Photo Installer...
color 0A

echo.
echo  ================================================
echo   Ravi Instant Photo — Build Script
echo  ================================================
echo.

:: ── Step 1: Check Python ─────────────────────────────────────
echo [1/4] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Python not found. Install from https://python.org
    pause & exit /b 1
)
echo        OK

:: ── Step 2: Install/upgrade PyInstaller ──────────────────────
echo [2/4] Installing PyInstaller...
python -m pip install pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo  ERROR: pip failed. Check your Python installation.
    pause & exit /b 1
)
echo        OK

:: ── Step 3: Bundle app with PyInstaller ──────────────────────
echo [3/4] Bundling app (this takes 2-5 minutes)...
echo.

:: Use "python -m PyInstaller" instead of "pyinstaller" directly.
:: This avoids PATH issues with Microsoft Store Python installations.
python -m PyInstaller PassportPhotoMaker.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo  ERROR: PyInstaller failed. See output above.
    pause & exit /b 1
)
echo.
echo        Bundling complete! App is in "dist\Ravi Instant Photo\"

:: ── Step 4: Build NSIS installer ─────────────────────────────
echo [4/4] Building NSIS installer...
echo.

set NSIS=""
if exist "C:\Program Files (x86)\NSIS\makensis.exe" set NSIS="C:\Program Files (x86)\NSIS\makensis.exe"
if exist "C:\Program Files\NSIS\makensis.exe"       set NSIS="C:\Program Files\NSIS\makensis.exe"

if %NSIS%=="" (
    echo  WARNING: NSIS not found. Download from: https://nsis.sourceforge.io/Download
    echo  Then re-run this script, or run manually:
    echo     makensis installer.nsi
    echo.
    echo  Your bundled app is ready in: "dist\Ravi Instant Photo\"
    pause & exit /b 0
)

%NSIS% /V3 installer.nsi
if errorlevel 1 (
    echo.
    echo  ERROR: NSIS build failed. See output above.
    pause & exit /b 1
)

echo.
echo  ================================================
echo   BUILD COMPLETE!
echo   Installer: RaviInstantPhoto_Setup.exe
echo  ================================================
echo.
echo  Test it: double-click RaviInstantPhoto_Setup.exe
echo.
pause
