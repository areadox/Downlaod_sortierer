@echo off
REM Baut Download-Sortierer.exe (Ergebnis liegt danach im Ordner "dist")
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller -r requirements.txt || goto fehler
python make_icon.py || goto fehler
python -m PyInstaller --onefile --noconsole --name Download-Sortierer --icon icon.ico --hidden-import pystray._win32 --clean app.py || goto fehler
echo.
echo Fertig: dist\Download-Sortierer.exe
pause
exit /b 0
:fehler
echo.
echo Fehler beim Bauen. Ist Python installiert und beim Setup "Add Python to PATH" angehakt?
pause
exit /b 1
