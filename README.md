# BlockDiagrammEditor

Einfacher Block-Diagramm-Editor:

Rechts: **Attribute** (Ausblendbar), hier können unterschiedliche Atribute eines ausgewählten Objektes verändert werden. Insb. können dort die Namen der Objekte angepasst werden.
Links: **Menü**:

- **Block**: einen Block zeichnen und Attribute setzen.
  Bestehende Blöcke können per Mausdruck ausgewählt und dann verändert werden (Attribute, Löschen, Verschieben).

  Blöcke können innerhalb eines anderen Blockes gezeichnet oder dorthin verschoben werden. Alle Objekte die vollständig innerhalb eines Blockes sind, werden mit diesem mitverschoben.

- **Verbindung**: Gerichtete Verbindung zeichnen: Linke Maustaste innerhalb Quell-Block drücken, gedrückt bis zum 2. Block ziehen und loslassen. In den Attributen Verbindungsrichtung und Farbe wählen.
  Bei einer ausgewählten Verbindung  kann im Attribut-Fenster einer oder mehrere **Datenflüsse** an die Verbindung angedockt werden. Durch simples ziehen kann die Distanz zur Verbindung eingestellt werden. Weiter können Farbe und Pfeilrichtung eingestellt

- Bei einem Block können via Attribute **Interfaces** zugeordnet werden, die von einem anderen Block her per Verbindung verbunden werden können. 

- **Löschen**: Mehrere Objekte mit der Maus  auswählen (Lasso) und dann löschen.

- Auswahl als Grafik: Zeichnungsobjekte als **Grafik-Datei speichern**. Mehrere Objekte können können mit der Maus ausgewählt werden (Lasso) und als Grafik in ein png-File exportiert werden, welches in andere Applikation importiert werden kann.

-  **Speichen/Laden**: Aktuellen Stand als JSON-File speichern oder ein bestehendes File laden. 

- **Undo/Redo**

- **Zoom**-Grad im Menüeinstellbar. Allenfalls mittels  Scrollbars anzuzeigenden Bereich wählen.



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

  

  

