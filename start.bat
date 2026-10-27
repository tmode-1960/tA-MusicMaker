@echo off
rem tA MusicMaker - Startskript (Windows)
cd /d "%~dp0"

where python >nul 2>nul
if not errorlevel 1 (
  python server.py %*
  if errorlevel 1 pause
  exit /b 0
)

where py >nul 2>nul
if not errorlevel 1 (
  py server.py %*
  if errorlevel 1 pause
  exit /b 0
)

echo.
echo ============================================================
echo  Python wurde nicht gefunden!
echo  Bitte starte einmal 'setup.bat' zur automatischen Einrichtung
echo  oder installiere Python 3.10+ von https://www.python.org
echo ============================================================
echo.
pause
exit /b 1
