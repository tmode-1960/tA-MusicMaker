@echo off
setlocal
title tA MusicMaker - Release-Paket schnueren
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================================
echo      tA MusicMaker - Erstelle weitergabefaehiges ZIP
echo ============================================================
echo.

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import shutil, os, zipfile; zip_path = 'tA-MusicMaker-Release.zip'; [os.remove(zip_path) if os.path.exists(zip_path) else None]; z = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED); include_files = ['server.py', 'workflow_converter.py', 'voice_swap.py', 'srt_translate.py', 'comfy_client.py', 'YuE2-Song.json', 'start.bat', 'setup.bat', 'README.md', 'Stimmaufnahme-Vorlage-RVC.pdf']; [z.write(f, os.path.join('tA-MusicMaker', f)) for f in include_files if os.path.exists(f)]; [z.write(os.path.join(root, file), os.path.join('tA-MusicMaker', os.path.relpath(os.path.join(root, file)))) for root, _, files in os.walk('web') for file in files if not file.endswith('.tmp')]; z.close(); print(f'Erfolgreich gepackt: {zip_path} ({os.path.getsize(zip_path)//1024} KB)')"
) else (
    echo Python wird benoetigt, um das ZIP zu packen.
)

echo.
echo ============================================================
echo   Fertig! Du kannst 'tA-MusicMaker-Release.zip' nun an
echo   Freunde oder Bekannte weitergeben (z.B. per Drive, USB etc.)
echo.
echo   Der Empfaenger muss die ZIP nur entpacken und einmal
echo   'setup.bat' doppelklicken!
echo ============================================================
echo.
pause
