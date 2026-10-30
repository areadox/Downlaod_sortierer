"""Kernlogik: Dateien erkennen, Videos als Film/Serie einordnen, verschieben oder kopieren."""
import os
import re
import shutil
import time

# Endungen von Downloads, die noch laufen -> nie anfassen
INCOMPLETE_EXTENSIONS = {"crdownload", "part", "partial", "download", "tmp", "opdownload", "!ut", "aria2"}

# Typische Release-Angaben, ab denen der Rest des Namens abgeschnitten wird
_JUNK = (
    r"2160p|1080p|1080i|720p|576p|480p|4k|uhd|hdr|hdr10|dv|"
    r"web[- ]?dl|webrip|web|bluray|blu[- ]?ray|bdrip|brrip|dvdrip|hdtv|hdrip|remux|"
    r"x264|x265|h264|h265|hevc|avc|xvid|aac|ac3|dts|ddp?5 ?1|dd5 ?1|atmos|"
    r"german|deutsch|english|dl|multi|dubbed|subbed|proper|repack|extended|uncut|unrated|complete"
)
_JUNK_RE = re.compile(rf"(?i)(?:^|\s)(?:{_JUNK})(?=\s|$)")
_INVALID_CHARS = re.compile(r'[<>:"/\\|?*]')

_SXXEXX = re.compile(r"(?i)\bS(\d{1,2})\s*E(\d{1,3})(?:\s*-?\s*E?\d{1,3})?\b")
_NXNN = re.compile(r"(?i)\b(\d{1,2})x(\d{2,3})\b")
_STAFFEL = re.compile(r"(?i)\b(?:Staffel|Season)\s*(\d{1,2})\b")
_EPISODE = re.compile(r"(?i)\b(?:Episode|Folge|Ep)\.?\s*(\d{1,3})\b")
_YEAR = re.compile(r"(?:^|[\s(\[])((?:19|20)\d{2})(?=[\s)\]]|$)")


def clean_title(text):
    """'Der.Herr_der.Ringe [GER]' -> 'Der Herr der Ringe'"""
    text = re.sub(r"\[[^\]]*\]|\{[^}]*\}", " ", text)   # [Gruppe] {xyz} entfernen
    text = re.sub(r"[._]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    m = _JUNK_RE.search(text)
    if m:
        text = text[: m.start()]
    text = re.sub(r"\(\s*\)", "", text)
    text = text.strip(" -–()")
    text = _INVALID_CHARS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    if text.islower():  # "the office" -> "The Office"
        text = text.title()
    return text


def parse_video(name):
    """Analysiert einen Dateinamen (ohne Endung).

    Rückgabe:
      {"kind": "series", "title": ..., "season": int, "episode": int}
      {"kind": "movie",  "title": ..., "year": "2010" | None}
    """
    plain = re.sub(r"[._]+", " ", name)

    # 1) S01E02 / s1e2
    m = _SXXEXX.search(plain)
    if m:
        title = clean_title(plain[: m.start()])
        if title:
            return {"kind": "series", "title": title, "season": int(m.group(1)), "episode": int(m.group(2))}

    # 2) 1x02
    m = _NXNN.search(plain)
    if m:
        title = clean_title(plain[: m.start()])
        if title:
            return {"kind": "series", "title": title, "season": int(m.group(1)), "episode": int(m.group(2))}

    # 3) Deutsches Format: "Episode 3 Staffel 1 von Serienname" oder "Serienname Staffel 1 Folge 3"
    ms, me = _STAFFEL.search(plain), _EPISODE.search(plain)
    if ms and me:
        parts = re.split(r"(?i)\svon\s", plain, maxsplit=1)
        if len(parts) == 2:
            title = parts[1]
        else:
            title = plain[: min(ms.start(), me.start())]
        title = clean_title(title)
        if title:
            return {"kind": "series", "title": title, "season": int(ms.group(1)), "episode": int(me.group(1))}

    # 4) Film, evtl. mit Jahr
    m = _YEAR.search(plain)
    if m and clean_title(plain[: m.start()]):
        return {"kind": "movie", "title": clean_title(plain[: m.start()]), "year": m.group(1)}
    return {"kind": "movie", "title": clean_title(plain) or name, "year": None}


def video_destination(info, ext, cfg):
    """Zielpfad für ein erkanntes Video."""
    if info["kind"] == "series":
        se = f"S{info['season']:02}E{info['episode']:02}"
        folder = os.path.join(cfg["series_folder"], info["title"])
        if cfg.get("season_subfolders", True):
            folder = os.path.join(folder, f"Staffel {info['season']:02}")
        return os.path.join(folder, f"{info['title']} {se}.{ext}")
    label = f"{info['title']} ({info['year']})" if info.get("year") else info["title"]
    return os.path.join(cfg["movies_folder"], label, f"{label}.{ext}")


def unique_path(path):
    """Hängt ' (2)', ' (3)' ... an, falls die Datei schon existiert."""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def plan(file, cfg):
    """Bestimmt das Ziel für eine Datei (nur Name, kein Pfad). Gibt Zielpfad zurück."""
    name, dot, ext = file.rpartition(".")
    if not dot or not name:
        return os.path.join(cfg["target_folder"], cfg["other_name"], file)
    ext = ext.lower()
    if ext in cfg["video_extensions"]:
        if cfg.get("rename_videos", True):
            return video_destination(parse_video(name), ext, cfg)
        return os.path.join(cfg["target_folder"], "Videos", file)
    folder = cfg["file_type_map"].get(ext, cfg["other_name"])
    return os.path.join(cfg["target_folder"], folder, file)


def _is_ready(path, cfg):
    """True, wenn der Download fertig aussieht (Endung ok, länger nicht verändert)."""
    ext = path.rpartition(".")[2].lower()
    if ext in INCOMPLETE_EXTENSIONS:
        return False
    try:
        age = time.time() - os.path.getmtime(path)
    except OSError:
        return False
    return age >= cfg.get("min_age_seconds", 15)


def _protected(path, cfg):
    """Eigene Programmdateien und die Zielordner nie anfassen."""
    app_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.dirname(os.path.abspath(path)) == app_dir


def run_once(cfg, log=print, processed=None):
    """Einmal durch den überwachten Ordner gehen. Gibt Anzahl verarbeiteter Dateien zurück.

    processed: Menge bereits kopierter Dateien (nur im Kopier-Modus nötig,
    damit dieselbe Datei nicht immer wieder kopiert wird).
    """
    src = cfg["watch_folder"]
    if not os.path.isdir(src):
        log(f"Überwachter Ordner existiert nicht: {src}")
        return 0
    copy = cfg.get("mode") == "copy"
    done = 0
    for file in sorted(os.listdir(src)):
        path = os.path.join(src, file)
        if os.path.isdir(path) or file.startswith(".") or file.lower() == "desktop.ini":
            continue
        if _protected(path, cfg) or not _is_ready(path, cfg):
            continue
        if copy and processed is not None:
            key = (path, os.path.getsize(path), os.path.getmtime(path))
            if key in processed:
                continue
        dest = unique_path(plan(file, cfg))
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if copy:
                shutil.copy2(path, dest)
                if processed is not None:
                    processed.add(key)
                log(f"Kopiert: {file}  →  {dest}")
            else:
                shutil.move(path, dest)
                log(f"Verschoben: {file}  →  {dest}")
            done += 1
        except PermissionError:
            log(f"Noch in Benutzung, später nochmal: {file}")
        except OSError as e:
            log(f"Fehler bei {file}: {e}")
    return done
