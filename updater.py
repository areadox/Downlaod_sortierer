"""Update-Funktion: sucht auf GitHub nach einem neueren Release und tauscht die .exe aus."""
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

from version import GITHUB_REPO, __version__

API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
EXE_NAME = "Download-Sortierer.exe"


def _parse(v):
    """'v1.2.10' -> (1, 2, 10)"""
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3]) or (0,)


def is_frozen():
    """True, wenn das Programm als .exe läuft."""
    return getattr(sys, "frozen", False)


def check():
    """Fragt das neueste Release ab.

    Rückgabe: None, wenn kein Update da ist, sonst
    {"version": "1.1.0", "notes": "...", "download_url": "..." | None}
    Wirft eine Exception bei Netzwerkfehlern.
    """
    req = urllib.request.Request(API_URL, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "Download-Sortierer",
    })
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.load(r)
    latest = data.get("tag_name", "")
    if _parse(latest) <= _parse(__version__):
        return None
    url = next((a["browser_download_url"] for a in data.get("assets", [])
                if a.get("name", "").lower().endswith(".exe")), None)
    return {"version": latest.lstrip("v"), "notes": data.get("body") or "", "download_url": url}


def download(url, progress=None):
    """Lädt die neue .exe in einen Temp-Ordner. progress(prozent) wird laufend aufgerufen."""
    target = os.path.join(tempfile.gettempdir(), "Download-Sortierer-update.exe")
    req = urllib.request.Request(url, headers={"User-Agent": "Download-Sortierer"})
    with urllib.request.urlopen(req, timeout=30) as r, open(target, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(64 * 1024)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if progress and total:
                progress(done * 100 // total)
    if os.path.getsize(target) < 100 * 1024:
        raise OSError("Download unvollständig")
    return target


def install_and_restart(new_exe):
    """Ersetzt die laufende .exe durch die neue und startet sie neu.

    Eine laufende .exe kann sich unter Windows nicht selbst überschreiben.
    Deshalb wird ein kleines Batch-Skript gestartet, das wartet, bis das
    Programm beendet ist, die Datei austauscht und das Programm neu startet.
    Danach muss sich das Programm selbst beenden.
    """
    current = os.path.abspath(sys.executable)
    script = os.path.join(tempfile.gettempdir(), "download-sortierer-update.bat")
    with open(script, "w", encoding="utf-8") as f:
        f.write(f"""@echo off
chcp 65001 >nul
set tries=0
:warten
timeout /t 1 /nobreak >nul
set /a tries+=1
move /y "{new_exe}" "{current}" >nul 2>&1
if errorlevel 1 (
    if %tries% lss 30 goto warten
    echo Update fehlgeschlagen. Die neue Version liegt unter "{new_exe}".
    pause
    exit /b 1
)
timeout /t 2 /nobreak >nul
start "" "{current}"
del "%~f0"
""")
    subprocess.Popen(["cmd", "/c", script], env=clean_environment(),
                     creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def clean_environment():
    """Umgebung ohne die Variablen, die PyInstaller für die laufende .exe setzt.

    Sonst erbt die neu gestartete .exe Pfade in den Temp-Ordner (_MEIxxxx) der
    alten .exe. Der wird beim Beenden gelöscht -> Fehler "Failed to load Python DLL".
    """
    env = dict(os.environ)
    mei = getattr(sys, "_MEIPASS", None)
    for key in list(env):
        if key.startswith("_PYI_") or key in ("_MEIPASS", "_MEIPASS2"):
            del env[key]
        elif mei and mei.lower() in env[key].lower():  # z. B. TCL_LIBRARY, TK_LIBRARY
            del env[key]
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env
