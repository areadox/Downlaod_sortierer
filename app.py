"""Download-Sortierer: überwacht einen Ordner und räumt ihn automatisch auf.

Start mit Oberfläche:   python app.py
Einmal ohne Fenster:    python app.py --once
"""
import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import settings
import sorter


class Watcher(threading.Thread):
    """Prüft den Ordner im Hintergrund alle X Sekunden."""

    def __init__(self, get_cfg, log):
        super().__init__(daemon=True)
        self.get_cfg = get_cfg
        self.log = log
        self.stop_event = threading.Event()
        self.processed = set()

    def run(self):
        while not self.stop_event.is_set():
            cfg = self.get_cfg()
            try:
                sorter.run_once(cfg, self.log, self.processed, self.stop_event.is_set)
            except Exception as e:  # Watcher soll nie abstürzen
                self.log(f"Unerwarteter Fehler: {e}")
            self.stop_event.wait(max(2, int(cfg.get("interval_seconds", 10))))

    def stop(self):
        self.stop_event.set()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Download-Sortierer")
        self.geometry("820x600")
        self.minsize(640, 480)
        self.cfg = settings.load()
        self.watcher = None
        self.log_queue = queue.Queue()
        self.cfg_lock = threading.Lock()

        self._build_ui()
        self.after(200, self._drain_log)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        if self.cfg.get("autostart_watch"):
            self.toggle_watch()

    # ---------- Oberfläche ----------
    def _build_ui(self):
        pad = {"padx": 6, "pady": 3}
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # --- Tab: Ordner ---
        tab = ttk.Frame(nb)
        nb.add(tab, text="Ordner & Optionen")
        tab.columnconfigure(1, weight=1)

        self.vars = {}
        rows = [
            ("watch_folder", "Überwachter Ordner (Downloads):"),
            ("target_folder", "Ziel für normale Dateien:"),
            ("movies_folder", "Ziel für Filme:"),
            ("series_folder", "Ziel für Serien:"),
        ]
        for r, (key, label) in enumerate(rows):
            ttk.Label(tab, text=label).grid(row=r, column=0, sticky="w", **pad)
            var = tk.StringVar(value=self.cfg[key])
            self.vars[key] = var
            ttk.Entry(tab, textvariable=var).grid(row=r, column=1, sticky="ew", **pad)
            ttk.Button(tab, text="…", width=3,
                       command=lambda v=var: self._pick_folder(v)).grid(row=r, column=2, **pad)

        r = len(rows)
        ttk.Label(tab, text="Modus:").grid(row=r, column=0, sticky="w", **pad)
        self.vars["mode"] = tk.StringVar(value=self.cfg["mode"])
        mf = ttk.Frame(tab)
        mf.grid(row=r, column=1, sticky="w")
        ttk.Radiobutton(mf, text="Verschieben (Downloads wird leer)", value="move",
                        variable=self.vars["mode"]).pack(side="left")
        ttk.Radiobutton(mf, text="Kopieren (Original bleibt)", value="copy",
                        variable=self.vars["mode"]).pack(side="left", padx=10)

        r += 1
        ttk.Label(tab, text="Prüfen alle (Sekunden):").grid(row=r, column=0, sticky="w", **pad)
        self.vars["interval_seconds"] = tk.IntVar(value=self.cfg["interval_seconds"])
        ttk.Spinbox(tab, from_=2, to=3600, width=8,
                    textvariable=self.vars["interval_seconds"]).grid(row=r, column=1, sticky="w", **pad)

        r += 1
        ttk.Label(tab, text="Datei unverändert seit (Sek.):").grid(row=r, column=0, sticky="w", **pad)
        self.vars["min_age_seconds"] = tk.IntVar(value=self.cfg["min_age_seconds"])
        ttk.Spinbox(tab, from_=0, to=3600, width=8,
                    textvariable=self.vars["min_age_seconds"]).grid(row=r, column=1, sticky="w", **pad)

        r += 1
        ttk.Label(tab, text="Dateien am Stück:").grid(row=r, column=0, sticky="w", **pad)
        bf0 = ttk.Frame(tab)
        bf0.grid(row=r, column=1, sticky="w", **pad)
        self.vars["batch_size"] = tk.IntVar(value=self.cfg["batch_size"])
        ttk.Spinbox(bf0, from_=1, to=1000, width=6, textvariable=self.vars["batch_size"]).pack(side="left")
        ttk.Label(bf0, text="  danach Pause (Sek.):").pack(side="left")
        self.vars["batch_pause_seconds"] = tk.IntVar(value=self.cfg["batch_pause_seconds"])
        ttk.Spinbox(bf0, from_=0, to=3600, width=6, textvariable=self.vars["batch_pause_seconds"]).pack(side="left")

        for key, text in [
            ("rename_videos", "Videos umbenennen und nach Film / Serie einsortieren"),
            ("season_subfolders", "Serien in Unterordner „Staffel 01“ usw. legen"),
            ("autostart_watch", "Überwachung beim Programmstart automatisch starten"),
        ]:
            r += 1
            self.vars[key] = tk.BooleanVar(value=self.cfg[key])
            ttk.Checkbutton(tab, text=text, variable=self.vars[key]).grid(
                row=r, column=0, columnspan=3, sticky="w", **pad)

        r += 1
        bf = ttk.Frame(tab)
        bf.grid(row=r, column=0, columnspan=3, sticky="w", pady=10)
        ttk.Button(bf, text="Einstellungen speichern", command=self.save).pack(side="left", padx=6)
        ttk.Button(bf, text="Vorschau (Test-Dateiname)", command=self._preview).pack(side="left", padx=6)

        # --- Tab: Dateitypen ---
        tab2 = ttk.Frame(nb)
        nb.add(tab2, text="Dateitypen")
        ttk.Label(tab2, text="Eine Zeile pro Endung:  endung = Ordnername   (Videos: video = …)").pack(
            anchor="w", padx=6, pady=4)
        self.types_text = tk.Text(tab2, height=20, font=("Consolas", 10))
        self.types_text.pack(fill="both", expand=True, padx=6, pady=4)
        lines = [f"{k} = {v}" for k, v in sorted(self.cfg["file_type_map"].items(), key=lambda kv: (kv[1], kv[0]))]
        lines += [f"{e} = video" for e in self.cfg["video_extensions"]]
        self.types_text.insert("1.0", "\n".join(lines))
        ttk.Button(tab2, text="Speichern", command=self.save).pack(anchor="w", padx=6, pady=6)

        # --- unten: Steuerung + Protokoll ---
        ctrl = ttk.Frame(self)
        ctrl.pack(fill="x", padx=8)
        self.watch_btn = ttk.Button(ctrl, text="▶ Überwachung starten", command=self.toggle_watch)
        self.watch_btn.pack(side="left")
        ttk.Button(ctrl, text="Jetzt einmal aufräumen", command=self.run_now).pack(side="left", padx=6)
        self.status = ttk.Label(ctrl, text="Gestoppt")
        self.status.pack(side="right")

        self.log_box = tk.Text(self, height=10, state="disabled", font=("Consolas", 9))
        self.log_box.pack(fill="both", expand=False, padx=8, pady=8)

    def _pick_folder(self, var):
        path = filedialog.askdirectory(initialdir=var.get() or None)
        if path:
            var.set(path)

    # ---------- Einstellungen ----------
    def _read_ui(self):
        cfg = dict(self.cfg)
        for key, var in self.vars.items():
            cfg[key] = var.get()
        types, videos = {}, []
        for line in self.types_text.get("1.0", "end").splitlines():
            if "=" not in line:
                continue
            ext, folder = (s.strip() for s in line.split("=", 1))
            ext = ext.lower().lstrip(".")
            if not ext or not folder:
                continue
            if folder.lower() == "video":
                videos.append(ext)
            else:
                types[ext] = folder
        cfg["file_type_map"], cfg["video_extensions"] = types, videos
        return cfg

    def save(self):
        try:
            cfg = self._read_ui()
        except tk.TclError:
            messagebox.showerror("Fehler", "Bitte bei den Sekunden nur Zahlen eintragen.")
            return
        with self.cfg_lock:
            self.cfg = cfg
        settings.save(cfg)
        self.log("Einstellungen gespeichert.")

    def _get_cfg(self):
        with self.cfg_lock:
            return dict(self.cfg)

    def _preview(self):
        win = tk.Toplevel(self)
        win.title("Vorschau")
        win.geometry("700x140")
        ttk.Label(win, text="Dateiname eingeben, z. B.  Episode 3 Staffel 1 von Dark.mp4").pack(anchor="w", padx=8, pady=4)
        var = tk.StringVar()
        entry = ttk.Entry(win, textvariable=var)
        entry.pack(fill="x", padx=8)
        out = ttk.Label(win, text="", wraplength=680, foreground="#0a5")
        out.pack(anchor="w", padx=8, pady=8)

        def update(*_):
            if var.get().strip():
                out.config(text="→ " + sorter.plan(var.get().strip(), self._read_ui()))
        var.trace_add("write", update)
        entry.focus()

    # ---------- Steuerung ----------
    def toggle_watch(self):
        if self.watcher:
            self.watcher.stop()
            self.watcher = None
            self.watch_btn.config(text="▶ Überwachung starten")
            self.status.config(text="Gestoppt")
            self.log("Überwachung gestoppt.")
        else:
            self.save()
            self.watcher = Watcher(self._get_cfg, self.log)
            self.watcher.start()
            self.watch_btn.config(text="■ Überwachung stoppen")
            self.status.config(text=f"Überwacht: {self.cfg['watch_folder']}")
            self.log("Überwachung gestartet.")

    def run_now(self):
        self.save()
        cfg = self._get_cfg()
        cfg["min_age_seconds"] = min(cfg.get("min_age_seconds", 15), 5)
        threading.Thread(target=lambda: self.log(
            f"Fertig, {sorter.run_once(cfg, self.log)} Datei(en) verarbeitet."), daemon=True).start()

    # ---------- Protokoll ----------
    def log(self, msg):
        self.log_queue.put(msg)

    def _drain_log(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_box.config(state="normal")
            self.log_box.insert("end", msg + "\n")
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(200, self._drain_log)

    def _on_close(self):
        if self.watcher:
            self.watcher.stop()
        self.destroy()


if __name__ == "__main__":
    if "--once" in sys.argv:
        sorter.run_once(settings.load())
    else:
        App().mainloop()
