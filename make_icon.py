"""Erzeugt icon.ico für die .exe aus demselben Bild wie das Tray-Icon."""
from tray import make_image

make_image(True, 256).save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icon.ico erstellt")
