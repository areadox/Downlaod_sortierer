# Download-Sortierer

Kleines Python-Programm mit Oberfläche, das den Download-Ordner überwacht und automatisch aufräumt.

- **Normale Dateien** (Bilder, Dokumente, Tabellen, Archive, …) landen nach Endung in Unterordnern des Zielordners.
- **Videos** werden erkannt, umbenannt und einsortiert:
  - Serien → `Serien/Dark/Staffel 01/Dark S01E03.mp4`
  - Filme → `Filme/Inception (2010)/Inception (2010).mkv`
- Unfertige Downloads (`.crdownload`, `.part`, …) und Dateien, die gerade noch geschrieben werden, bleiben liegen.
- Es werden immer nur ein paar Dateien am Stück verschoben (Standard: 3), jede wird erst vollständig
  fertig kopiert und geprüft, dann folgt eine kurze Pause (Standard: 5 Sek.). Beides ist einstellbar.
- Gibt es eine Datei schon, wird ` (2)` angehängt – es wird nie etwas überschrieben.

## Erkannte Video-Namen

| Dateiname | Ergebnis |
|---|---|
| `Episode 3 Staffel 1 von Dark.mp4` | `Dark S01E03.mp4` |
| `Folge 12 Staffel 2 von How I Met Your Mother.mkv` | `How I Met Your Mother S02E12.mkv` |
| `Breaking.Bad.S05E14.German.1080p.WEB.x264.mkv` | `Breaking Bad S05E14.mkv` |
| `the_office_2x05_hdtv.avi` | `The Office S02E05.avi` |
| `Inception.2010.1080p.BluRay.x264.mkv` | Film `Inception (2010)` |

Alles andere mit Video-Endung wird als Film unter seinem bereinigten Namen abgelegt.
Im Programm gibt es eine **Vorschau**, in die man einen Dateinamen tippen kann, um das Ziel zu sehen.

## Starten

Benötigt nur Python 3.8+ (tkinter ist unter Windows dabei, unter Linux ggf. `sudo apt install python3-tk`).

```
python app.py          # mit Fenster
python app.py --once   # einmal aufräumen, ohne Fenster (z. B. für die Aufgabenplanung)
```

Unter Windows startet `pythonw app.py` ohne schwarzes Konsolenfenster. Für den Autostart eine Verknüpfung
darauf in `shell:startup` legen und im Programm „Überwachung beim Programmstart automatisch starten“ anhaken.

## Als .exe

**Fertige .exe herunterladen:** unter [Releases](https://github.com/areadox/downlaod_sortierer/releases/latest)
`Download-Sortierer.exe` laden. Sie läuft ohne Python; `settings.json` wird neben der .exe gespeichert.

Die .exe wird automatisch von GitHub Actions gebaut (`.github/workflows/build.yml`):
- jeder Push auf `main` baut die .exe (Test-Build unter *Actions* → Lauf → *Artifacts*)
- gibt es für die Nummer in `version.py` noch kein Release, wird automatisch eines erstellt (z. B. `v1.1.0`)

**Neue Version veröffentlichen:** in `version.py` die Nummer erhöhen (z. B. `"1.1.0"`), committen, pushen – fertig.
Alle installierten Programme bieten das Update dann beim nächsten Start an.

Selbst bauen geht weiterhin mit `build_exe.bat`.

## Updates

Das Programm sucht beim Start (abschaltbar) und über den Knopf „Nach Updates suchen“ nach einem neueren
Release auf GitHub. Als .exe lädt es die neue Version auf Wunsch herunter, tauscht sich selbst aus und startet neu.
Die Einstellungen bleiben dabei erhalten.

## Einstellungen

Alles wird im Fenster eingestellt und in `settings.json` gespeichert:
überwachter Ordner, Zielordner für Dateien / Filme / Serien, Verschieben oder Kopieren,
Prüfintervall, Dateien am Stück + Pause, Staffel-Unterordner und die Zuordnung Dateiendung → Ordner (Tab „Dateitypen“).

## Dateien

- `app.py` – Oberfläche und Hintergrund-Überwachung
- `sorter.py` – Erkennung und Sortierlogik
- `settings.py` – Standardwerte, Laden/Speichern
- `updater.py` – Update-Suche und Selbst-Austausch der .exe
- `version.py` – Versionsnummer (erhöhen = neues Release)
