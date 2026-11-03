# BlockDiagrammEditor

Einfacher Diagramm-Editor für Windows. Rechtecke zeichnen, verbinden, beschriften und als JSON speichern. Die Oberfläche nutzt nur die Python-Standardbibliothek (Tkinter).

Der Quelltext liegt im Ordner `BlockDiagrammEditor`.

## Direkt starten

Voraussetzung: Python 3.11 oder neuer, installiert vom [python.org-Installer](https://www.python.org/downloads/windows/) (Tkinter ist darin enthalten).

```powershell
cd BlockDiagrammEditor
py -3 BlockDiagrammEditor.py
```

Beispieldatei zum Laden: `Diagramm1.json`.

## Als einzelnes Windows-Programm bauen

Das Ergebnis ist `BlockDiagrammEditor\dist\BlockDiagrammEditor.exe`. Diese Datei enthält Python und Tkinter und startet auf einem anderen 64-Bit-Windows ohne weitere Installation.

```powershell
cd BlockDiagrammEditor
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Dasselbe von Hand:

```powershell
cd BlockDiagrammEditor
py -3 -m pip install -r requirements-build.txt
py -3 -m PyInstaller --noconfirm --onefile --windowed --name BlockDiagrammEditor BlockDiagrammEditor.py
```

Die EXE ist nur für die Architektur gedacht, auf der sie gebaut wurde (hier 64-Bit). Solange sie nicht signiert ist, kann Windows SmartScreen beim ersten Start warnen.
