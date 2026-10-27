# Project Rules & Guidelines for tA-MusicMaker

## File Backup Policy
- Vor JEDER Änderung an bestehenden Quellcode-Dateien (z. B. `.py`, `.js`, `.html`, `.css`, `.iss`, `.bat`) MUSS eine Sicherungskopie der Datei vor der Modifikation angelegt werden.
- Speicherort für Backups: Im Ordner `_backups/` unter Beibehaltung der relativen Verzeichnisstruktur (z. B. `_backups/server-20261024-061000.py` oder `_backups/web/app-20261024-061000.js`).
- Namenskonvention: `[Dateiname]-[YYYYMMDD-HHmmss].[Dateiendung]`.
- Vor dem Überschreiben oder Bearbeiten von Dateien stets sicherstellen, dass das Backup erfolgreich geschrieben wurde.

## Version Bump Policy
- Beim Erstellen der Desktop-App und des Installers über `build_app.bat` MUSS die Versionsnummer jedes Mal automatisch hochgezählt werden (Aufruf standardmäßig ohne `--nobump`, also `.\build_app.bat --nopause`).


