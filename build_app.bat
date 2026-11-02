@echo off
setlocal enabledelayedexpansion
title "tA MusicMaker - Windows App und Installer bauen"
chcp 65001 >nul
cd /d "%~dp0"

set "DO_BUMP=1"
set "NO_PAUSE=0"
for %%a in (%*) do (
    if "%%a"=="--nobump" set "DO_BUMP=0"
    if "%%a"=="--nopause" set "NO_PAUSE=1"
)

echo ============================================================
echo   tA MusicMaker - Erstelle Standalone .exe und Setup.exe
echo ============================================================
echo.

if "!DO_BUMP!"=="1" (
    echo [1/4] Versionsnummer erhoehen...
    python bump_version.py --bump
) else (
    echo [1/4] Synchronisiere bestehende Version...
    python bump_version.py --sync
)
if errorlevel 1 (
    echo [FEHLER] Versions-Update fehlgeschlagen!
    if "!NO_PAUSE!"=="0" pause
    exit /b 1
)

echo [2/4] Pruefe PyInstaller und pywebview...
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo Installiere PyInstaller und pywebview...
    python -m pip install pyinstaller pywebview
)

echo [3/4] Baue Standalone Desktop-App (dist\tA-MusicMaker.exe)...
python -m PyInstaller --noconfirm --clean --onefile --noconsole ^
    --name "tA-MusicMaker" ^
    --icon "app.ico" ^
    --add-data "web;web" ^
    --add-data "YuE2-Song.json;." ^
    --add-data "data\plenio_templates.json;data" ^
    --add-data "app.ico;." ^
    --add-data "version.txt;." ^
    --add-data "Stimmaufnahme-Vorlage-RVC.pdf;." ^
    --collect-all faster_whisper ^
    --collect-all ctranslate2 ^
    --exclude-module PIL ^
    --exclude-module tkinter ^
    --exclude-module cryptography ^
    --exclude-module paramiko ^
    server.py

if errorlevel 1 (
    echo [FEHLER] PyInstaller-Build fehlgeschlagen!
    if "!NO_PAUSE!"=="0" pause
    exit /b 1
)

echo.
echo [4/4] Baue Windows-Installer (dist\tA-MusicMaker-Setup.exe)...
set "ISCC_EXE="
where iscc >nul 2>nul
if not errorlevel 1 set "ISCC_EXE=iscc"
if not defined ISCC_EXE if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC_EXE=C:\Program Files\Inno Setup 6\ISCC.exe"

if not defined ISCC_EXE goto :no_iscc
"%ISCC_EXE%" "installer.iss"
goto :done

:no_iscc
echo [HINWEIS] Inno Setup ISCC.exe nicht gefunden.
echo Die portable Standalone-App liegt trotzdem fertig unter: dist\tA-MusicMaker.exe

:done
if exist "build" rmdir /s /q "build"
echo.
echo ============================================================
echo   FERTIG! Deine fertigen Dateien liegen im Ordner "dist\":
echo   1. dist\tA-MusicMaker.exe        [Portabel - direkt starten]
echo   2. dist\tA-MusicMaker-Setup.exe  [Windows-Installer]
echo ============================================================
echo.
if "!NO_PAUSE!"=="0" pause
