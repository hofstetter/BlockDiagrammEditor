# BlockDiagrammEditor

Windows-Anwendung zum Zeichnen von Blockdiagrammen. Rechtecke zeichnen, verbinden, beschriften und als JSON speichern. Über „Auswahl als Grafik“ wird die Markierung als PNG-Datei gespeichert und kann in ein anderes Programm übernommen werden.

## Windows-Programm bauen

Das Ergebnis ist `dist\BlockDiagrammEditor.exe`. Diese Datei enthält Python, Tkinter und Pillow und startet auf einem anderen 64-Bit-Windows ohne weitere Installation.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Dasselbe von Hand:

```powershell
py -3 -m pip install -r requirements-build.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name BlockDiagrammEditor --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFont --hidden-import PIL.PngImagePlugin --exclude-module numpy BlockDiagrammEditor.py
```

Die EXE ist nur für die Architektur gedacht, auf der sie gebaut wurde (hier 64-Bit). Solange sie nicht signiert ist, kann Windows SmartScreen beim ersten Start warnen.

## Skript starten

Voraussetzung: Python 3.11 oder neuer vom [python.org-Installer](https://www.python.org/downloads/windows/) (Tkinter ist darin enthalten). „Auswahl als Grafik“ braucht Pillow.

```powershell
py -3 -m pip install -r requirements.txt
py -3 BlockDiagrammEditor.py
```

Beispieldatei zum Laden: `Diagramm1.json`.
