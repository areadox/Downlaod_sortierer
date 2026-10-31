"""Tray-Icon (Infobereich neben der Uhr) und Windows-Autostart."""
import os
import sys

try:
    import pystray
    from PIL import Image, ImageDraw
    AVAILABLE = True
except ImportError:  # ohne pystray/Pillow läuft das Programm ganz normal ohne Tray
    AVAILABLE = False


def make_image(active=False, size=64):
    """Zeichnet das Icon: Ordner mit Pfeil, grüner Punkt = Überwachung läuft."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size / 64
    # Ordner
    d.rounded_rectangle([4 * s, 12 * s, 28 * s, 22 * s], radius=3 * s, fill=(232, 170, 40))
    d.rounded_rectangle([4 * s, 18 * s, 60 * s, 56 * s], radius=5 * s, fill=(250, 196, 60))
    # Pfeil nach unten
    d.rectangle([28 * s, 24 * s, 36 * s, 40 * s], fill=(60, 60, 60))
    d.polygon([(20 * s, 38 * s), (44 * s, 38 * s), (32 * s, 50 * s)], fill=(60, 60, 60))
    # Status-Punkt
    color = (40, 180, 70) if active else (150, 150, 150)
    d.ellipse([42 * s, 40 * s, 62 * s, 60 * s], fill=color, outline=(255, 255, 255), width=max(1, int(2 * s)))
    return img


class Tray:
    """Tray-Icon mit Menü. Alle Aktionen werden über app.after() im Tk-Thread ausgeführt."""

    def __init__(self, app):
        self.app = app
        call = lambda fn: (lambda icon, item: app.after(0, fn))  # noqa: E731
        menu = pystray.Menu(
            pystray.MenuItem("Fenster öffnen", call(app.show_window), default=True),
            pystray.MenuItem(
                lambda item: "Überwachung stoppen" if app.watcher else "Überwachung starten",
                call(app.toggle_watch)),
            pystray.MenuItem("Jetzt einmal aufräumen", call(app.run_now)),
            pystray.MenuItem("Nach Updates suchen", call(lambda: app.check_updates(silent=False))),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Beenden", call(app.quit_app)),
        )
        self.icon = pystray.Icon("Download-Sortierer", make_image(False), "Download-Sortierer", menu)
        self.icon.run_detached()

    def set_active(self, active, tooltip):
        self.icon.icon = make_image(active)
        self.icon.title = tooltip[:120]
        self.icon.update_menu()

    def notify(self, text):
        try:
            self.icon.notify(text, "Download-Sortierer")
        except Exception:
            pass

    def stop(self):
        self.icon.stop()


# ---------- Mit Windows starten ----------
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_NAME = "Download-Sortierer"


def _command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --tray'
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(sys.argv[0])
    return f'"{pyw if os.path.isfile(pyw) else sys.executable}" "{script}" --tray'


def set_windows_autostart(enabled):
    """Trägt das Programm in den Windows-Autostart ein bzw. aus (nur Windows)."""
    if sys.platform != "win32":
        return
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _RUN_NAME, 0, winreg.REG_SZ, _command())
        else:
            try:
                winreg.DeleteValue(key, _RUN_NAME)
            except FileNotFoundError:
                pass
