# BlockDiagrammEditor

Der Quelltext liegt im Ordner `BlockDiagrammEditor`. Dort stehen die Beschreibung, die Beispieldatei `Diagramm1.json` und der Bau einer Windows-EXE.

## Skript starten

Voraussetzung: Python 3.11 oder neuer. Tkinter gehört bei Windows und macOS zum Installer von [python.org](https://www.python.org/downloads/). Unter Linux ist es oft ein separates Paket (`python3-tk`).

```powershell
cd BlockDiagrammEditor
py -3 -m pip install -r requirements.txt
py -3 BlockDiagrammEditor.py
```

Unter macOS und Linux entsprechend `python3 -m pip install -r requirements.txt` und `python3 BlockDiagrammEditor.py`.

## Optionale Windows-EXE

```powershell
cd BlockDiagrammEditor
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Die EXE entsteht als `dist/BlockDiagrammEditor.exe` und wird nicht eingecheckt. Sie läuft auf derselben Architektur, auf der sie gebaut wurde. Ohne Signatur kann Windows SmartScreen beim ersten Start warnen.
