"""Laden und Speichern der Einstellungen (settings.json neben dem Programm)."""
import json
import os
import sys

# Als .exe (PyInstaller) liegt __file__ in einem Temp-Ordner -> Ordner der .exe nehmen
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(APP_DIR, "settings.json")

DEFAULT_FILE_TYPE_MAP = {
    # Bilder
    "jpg": "Bilder", "jpeg": "Bilder", "png": "Bilder", "gif": "Bilder", "bmp": "Bilder",
    "webp": "Bilder", "svg": "Bilder", "heic": "Bilder", "ico": "Bilder",
    # Dokumente
    "pdf": "Dokumente", "doc": "Dokumente", "docx": "Dokumente", "odt": "Dokumente",
    "rtf": "Dokumente", "txt": "Dokumente", "md": "Dokumente",
    # Tabellen
    "xls": "Tabellen", "xlsx": "Tabellen", "ods": "Tabellen", "csv": "Tabellen",
    # Präsentationen
    "ppt": "Praesentationen", "pptx": "Praesentationen", "odp": "Praesentationen",
    # Audio
    "mp3": "Audio", "wav": "Audio", "flac": "Audio", "ogg": "Audio", "m4a": "Audio",
    # Archive
    "zip": "Archive", "rar": "Archive", "7z": "Archive", "tar": "Archive", "gz": "Archive",
    # Programme / Installer
    "exe": "Programme", "msi": "Programme", "dmg": "Programme", "deb": "Programme", "apk": "Programme",
    # Code
    "py": "Code", "js": "Code", "ts": "Code", "html": "Code", "css": "Code", "json": "Code",
    "java": "Code", "c": "Code", "cpp": "Code", "rs": "Code",
}

DEFAULT_VIDEO_EXTENSIONS = ["mp4", "mkv", "avi", "mov", "wmv", "webm", "m4v", "flv"]

DEFAULTS = {
    # Ordner, der überwacht wird
    "watch_folder": os.path.join(os.path.expanduser("~"), "Downloads"),
    # Zielordner für normale Dateien (Bilder, Dokumente, ...)
    "target_folder": os.path.join(os.path.expanduser("~"), "Downloads", "Sortiert"),
    # Zielordner für Filme und Serien
    "movies_folder": os.path.join(os.path.expanduser("~"), "Videos", "Filme"),
    "series_folder": os.path.join(os.path.expanduser("~"), "Videos", "Serien"),
    # Ordner für Dateien ohne bekannte Endung
    "other_name": "Sonstiges",
    # "move" = verschieben (Downloads wird leer), "copy" = kopieren (Original bleibt)
    "mode": "move",
    # Alle wie viele Sekunden der Ordner geprüft wird
    "interval_seconds": 10,
    # Datei erst anfassen, wenn sie so lange nicht mehr verändert wurde (Download fertig)
    "min_age_seconds": 15,
    # Höchstens so viele Dateien am Stück verschieben, dann Pause
    "batch_size": 3,
    "batch_pause_seconds": 5,
    # Videos umbenennen und in Film-/Serienordner einsortieren
    "rename_videos": True,
    # Serien zusätzlich in "Staffel 01"-Unterordner legen
    "season_subfolders": True,
    # Überwachung beim Programmstart sofort starten
    "autostart_watch": False,
    "video_extensions": DEFAULT_VIDEO_EXTENSIONS,
    "file_type_map": DEFAULT_FILE_TYPE_MAP,
}


def load():
    data = dict(DEFAULTS)
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data.update(json.load(f))
        except (OSError, ValueError) as e:
            print(f"settings.json konnte nicht gelesen werden ({e}), nutze Standardwerte")
    return data


def save(data):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
