# BlockDiagrammEditor

Einfacher Diagramm-Editor. Rechtecke zeichnen, verbinden, beschriften und als JSON speichern. Über „Auswahl als Grafik“ wird die Markierung als PNG-Datei gespeichert und kann in ein anderes Programm übernommen werden.

Das Skript läuft unter Windows, macOS und Linux mit Python, Tkinter und Pillow. Der Quelltext liegt im Ordner `BlockDiagrammEditor`.

## Skript starten

Voraussetzung: Python 3.11 oder neuer. Tkinter gehört bei Windows und macOS zum Installer von [python.org](https://www.python.org/downloads/). Unter Linux ist es oft ein separates Paket (`python3-tk`). „Auswahl als Grafik“ braucht Pillow.

```powershell
cd BlockDiagrammEditor
py -3 -m pip install -r requirements.txt
py -3 BlockDiagrammEditor.py
```

Unter macOS und Linux entsprechend `python3 -m pip install -r requirements.txt` und `python3 BlockDiagrammEditor.py`.

Beispieldatei zum Laden: `BlockDiagrammEditor/Diagramm1.json`.

## Optionale Windows-EXE

Nur für den lokalen Gebrauch unter Windows. Das Ergebnis ist `BlockDiagrammEditor/dist/BlockDiagrammEditor.exe`. Diese Datei enthält Python, Tkinter und Pillow und startet auf einem anderen 64-Bit-Windows ohne weitere Installation. Sie wird nicht ins Repository eingecheckt.

```powershell
cd BlockDiagrammEditor
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Dasselbe von Hand:

```powershell
cd BlockDiagrammEditor
py -3 -m pip install -r requirements-build.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name BlockDiagrammEditor --hidden-import PIL.Image --hidden-import PIL.ImageDraw --hidden-import PIL.ImageFont --hidden-import PIL.PngImagePlugin --exclude-module numpy BlockDiagrammEditor.py
```

Die EXE ist nur für die Architektur gedacht, auf der sie gebaut wurde (hier 64-Bit). Solange sie nicht signiert ist, kann Windows SmartScreen beim ersten Start warnen.
