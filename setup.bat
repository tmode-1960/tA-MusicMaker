@echo off
setlocal enabledelayedexpansion
title tA MusicMaker - Setup & Installation
chcp 65001 >nul

echo ============================================================
echo         tA MusicMaker - Schnelleinrichtung
echo ============================================================
echo.

rem 1. Python pruefen
echo [1/3] Pruefe Python-Installation...
set "PY_CMD="

where python >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=python"
) else (
    where py >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=py"
    )
)

if defined PY_CMD (
    for /f "tokens=*" %%v in ('%PY_CMD% --version 2^>^&1') do echo       [OK] %%v gefunden!
) else (
    echo.
    echo       [HINWEIS] Python wurde nicht gefunden!
    echo       tA MusicMaker benoetigt Python (kostenlos und Open-Source).
    echo.
    set /p "INSTALL_PY=Moechtest du Python jetzt automatisch installieren (winget)? [J/N]: "
    if /i "!INSTALL_PY!"=="J" (
        echo       Installiere Python ueber den Windows Paketmanager...
        winget install Python.Python.3.12 --accept-package-agreements --accept-source-agreements
        if errorlevel 1 (
            echo.
            echo       Automatischer Download fehlgeschlagen.
            echo       Bitte lade Python manuell herunter: https://www.python.org/downloads/
            echo       (Wichtig: Beim Installieren den Haken bei "Add python.exe to PATH" setzen!)
            pause
            exit /b 1
        )
        echo       Python erfolgreich installiert! Bitte starte das Setup anschliessend erneut.
        pause
        exit /b 0
    ) else (
        echo       Installation abgebrochen. Bitte installiere Python 3.10+ manuell.
        pause
        exit /b 1
    )
)

echo.
echo [2/3] Erstelle Verknuepfung auf dem Windows-Desktop...
set "SCRIPT_DIR=%~dp0"
set "TARGET_BAT=%SCRIPT_DIR%start.bat"

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ws = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $s = $ws.CreateShortcut(\"$desktop\tA MusicMaker.lnk\"); $s.TargetPath = '%TARGET_BAT%'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.IconLocation = 'shell32.dll,116'; $s.Description = 'tA MusicMaker - Lokale KI-Musikproduktion'; $s.Save()" >nul 2>&1

if exist "%USERPROFILE%\Desktop\tA MusicMaker.lnk" (
    echo       [OK] Verknuepfung "tA MusicMaker" erfolgreich auf dem Desktop angelegt!
) else (
    echo       [Info] Verknuepfung konnte nicht automatisch erstellt werden. Du kannst die App direkt ueber "start.bat" starten.
)

echo.
echo [3/3] Einrichtung abgeschlossen!
echo.
echo ============================================================
echo   tA MusicMaker ist einsatzbereit.
echo   ComfyUI sollte gestartet sein (Port 8188).
echo ============================================================
echo.
set /p "START_NOW=Moechtest du tA MusicMaker jetzt direkt starten? [J/N]: "
if /i "!START_NOW!"=="J" (
    start "" "%TARGET_BAT%"
)

exit /b 0
