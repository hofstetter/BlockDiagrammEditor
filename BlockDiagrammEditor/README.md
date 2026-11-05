# BlockDiagrammEditor

Einfacher Block-Diagramm-Editor:

- Blöcke zeichnen und gerichtet verbinden. 
- Datenflüsse mit Richtung an Verbindungen andocken und mitbewegen.
- Blöcke innerhalb Blöcken darstellen und bewegen. 
- Interface anbinden.
- Resultat in als JSON-File speichern und zurücklesen. 
- Ausgabe der Grafik als Grafik (png)-File) für Import in andere Programme. 


Das Skript läuft unter Windows, macOS und Linux mit Python, Tkinter und Pillow.



## Skript starten

Voraussetzung: Python 3.11 oder neuer. Tkinter gehört bei Windows und macOS zum Installer von [python.org](https://www.python.org/downloads/). Unter Linux ist es oft ein separates Paket (`python3-tk`). Grafikausgabe in ein File braucht Pillow.

**Zum Starten:**

- Die Files BlockdiagrammEditor.py, requirements.txt und Diagramm1.json in ein Verzeichnis auf den lokalen Rechner runter laden.
- Kommando Shell in diesem Verzeichnis starten:

```powershell
py -3 -m pip install -r requirements.txt
py -3 BlockDiagrammEditor.py
```



Unter macOS und Linux entsprechend `python3 -m pip install -r requirements.txt` und `python3 BlockDiagrammEditor.py`.



Beispieldatei zum Laden: `Diagramm1.json`.



Bemerkung: 

- Unter Windows erzeugt `build.ps1` eine EXE in `dist/`. Sie wird nicht ins Repository eingecheckt.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

- **Sicherheit**: Das Programm wurde in einer ersten Phase mit "Gemini" und dann mit "Cursor" weiter entwickelt. Es hat eine Sicherheitsüberprüfung des Code mittels "Cursor" stattgefunden. Es wurden keine kritischen Aspekte gefunden. Das hängt auch zusammen, dass das Programm relativ simpel ist: Tastatur- und Mauseingabe, Ausgabe auf den Bildschirm. Lesen und Speichern von Files. Bei der "Cursor" Analyse wurden im Code keine Verbindungen ins Internet gefunden.
  Trotzdem gilt: Ein Einsatz des Codes geschieht auf eigenes Risiko.

  

  

