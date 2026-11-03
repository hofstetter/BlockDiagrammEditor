# BlockDiagrammEditor

Einfacher Diagramm-Editor für Windows. Rechtecke zeichnen, verbinden, beschriften und als JSON speichern. Die Oberfläche nutzt nur die Python-Standardbibliothek (Tkinter).

## Direkt starten

Voraussetzung: Python 3.11 oder neuer, installiert vom [python.org-Installer](https://www.python.org/downloads/windows/) (Tkinter ist darin enthalten).

```powershell
py -3 BlockDiagrammEditor.py
```

Beispieldateien zum Laden: `test.json`, `Test1.json`, `test2.json`.

## Als einzelnes Windows-Programm bauen

Das Ergebnis ist `dist\BlockDiagrammEditor.exe`. Diese Datei enthält Python und Tkinter und startet auf einem anderen 64-Bit-Windows ohne weitere Installation.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Dasselbe von Hand:

```powershell
py -3 -m pip install -r requirements-build.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name BlockDiagrammEditor BlockDiagrammEditor.py
```

Die EXE ist nur für die Architektur gedacht, auf der sie gebaut wurde (hier 64-Bit). Solange sie nicht signiert ist, kann Windows SmartScreen beim ersten Start warnen.
