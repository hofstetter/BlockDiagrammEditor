import sys
import json
import math
from PyQt5.QtGui import QPolygonF
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QPushButton, QVBoxLayout
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPointF
from PyQt5.QtWidgets import QInputDialog
from collections import namedtuple

#Listen von Tupeln
Dobject = namedtuple("Dobject", ["obj", "name"])            #drawable object, obj ist z.B. vom Typ QRect
Dconnection = namedtuple("Dconnection", ["i1","i2","name"]) # i1,i2: Index der beiden Objekte (ID's sind zwischen Programmstarts nicht stabil')

def line_intersection(p1, p2, p3, p4):
    """Schnittpunkt zweier Liniensegmente (p1-p2 und p3-p4)."""
    x1, y1, x2, y2 = p1.x(), p1.y(), p2.x(), p2.y()
    x3, y3, x4, y4 = p3.x(), p3.y(), p4.x(), p4.y()

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return None

    px = ((x1 * y2 - y1 * x2) * (x3 - x4) -
          (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
    py = ((x1 * y2 - y1 * x2) * (y3 - y4) -
          (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
    inter = QPointF(px, py)

    # prüfen, ob Schnittpunkt innerhalb der beiden Segmente liegt
    if (min(x1, x2) - 0.1 <= px <= max(x1, x2) + 0.1 and
        min(y1, y2) - 0.1 <= py <= max(y1, y2) + 0.1 and
        min(x3, x4) - 0.1 <= px <= max(x3, x4) + 0.1 and
        min(y3, y4) - 0.1 <= py <= max(y3, y4) + 0.1):
        return inter
    return None


def rect_edge_intersection(rect, p_center, p_other):
    """ Finde den echten Schnittpunkt der Linie center->other mit dem Rechteckrand."""
    edges = [
        (QPointF(rect.left(), rect.top()), QPointF(rect.right(), rect.top())),  # oben
        (QPointF(rect.right(), rect.top()), QPointF(rect.right(), rect.bottom())),  # rechts
        (QPointF(rect.right(), rect.bottom()), QPointF(rect.left(), rect.bottom())),  # unten
        (QPointF(rect.left(), rect.bottom()), QPointF(rect.left(), rect.top()))   # links
    ]
    for p1, p2 in edges:
        inter = line_intersection(p_center, p_other, p1, p2)
        if inter is not None:
            return inter
    return p_center  # fallback


class DrawingWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.dobjects = []  # Drawable Objects
        self.connections = []
        self.current_rect = None
        self.selected_rect = None
        self.offset = None
        self.line_start_rect = None 
        self.line_start_index = None
        self.mode = None


    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Prüfen auf Rechteck-Klick für Verschieben oder Linienstart
            if(self.mode == "move"):
                #for rect,name in reversed(self.dobjects):
                for rect,name in self.dobjects:
                    if rect.contains(event.pos()):
                        self.selected_rect = rect
                        self.offset = event.pos() - rect.topLeft()
                        return
            i=-1
            #for ob,name in reversed(self.dobjects):
            for ob,name in self.dobjects:
                i=i+1 # Index für gefundenes Objekt
                if ob.contains(event.pos()):
                    if self.line_start_rect is None:
                        # Erste Auswahl für Linie
                        self.line_start_rect = ob
                        self.line_start_index = i
                        return
                    else:
                        # Zweite Auswahl -> Linie erstellen
                        if ob != self.line_start_rect:
                           self.connections.append(Dconnection(i2=i,i1=self.line_start_index,name="Verbindung"))
                        self.line_start_rect = None
                        self.line_start_index = None
                        self.update()
                        return

           
            
            # Vorsicht: Name interaktib abfragen  -> Verändert die Daten, current_rect erst nach der Namenseingabe erstellen, oder
            #den Namen erst nach dem MouseRelease abfragen.
            #text, ok = QInputDialog.getText(self, "Blockname", "Name für das Rechteck eingeben:")
            
            # Rechteck erstellen
            self.current_rect = QRect(event.pos(), event.pos())
            obj=Dobject(self.current_rect,"Name")
            self.dobjects.append(obj)
            self.update()
            
    def mouseMoveEvent(self, event):
        if(self.mode == "move"):
            if self.selected_rect is not None and self.offset is not None:
                new_top_left = event.pos() - self.offset
                self.selected_rect.moveTopLeft(new_top_left)
                self.update()
                return

        if self.selected_rect is not None and self.offset is not None:
            new_top_left = event.pos() - self.offset
            self.selected_rect.moveTopLeft(new_top_left)
            self.update()
        elif self.current_rect is not None:
            self.current_rect.setBottomRight(event.pos())
            self.update()
        

    def mouseReleaseEvent(self, event):
        self.current_rect = None
        self.selected_rect = None
        self.offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0), 2)
        painter.setPen(pen)

        # Rechtecke zeichnen
        for dobj in self.dobjects:
            painter.drawRect(dobj.obj)
            painter.drawText(dobj.obj, Qt.AlignCenter, dobj.name)

        # Verbindungen zeichnen
        line_pen = QPen(QColor(200, 0, 0), 2)
        painter.setPen(line_pen)
        for c in self.connections:
            c1, c2 = QPointF(self.dobjects[c.i1].obj.center()), QPointF(self.dobjects[c.i2].obj.center())
            p1 = rect_edge_intersection(self.dobjects[c.i1].obj,c1,c2)
            p2 = rect_edge_intersection(self.dobjects[c.i2].obj,c2,c1)
            blue_pen = QPen(QColor(0, 0, 255), 2)
            painter.setPen(blue_pen)
            painter.drawLine(p1, p2)
            self.draw_arrow(painter, p1, p2)
            self.draw_text_on_line(painter, p1, p2, "Test")
            red_pen = QPen(QColor(255, 0, 0), 2)  # R=255, G=0, B=0
            painter.setPen(red_pen)
            self.draw_parallel_line(painter, p1, p2, 20, 80)
        
    """Zeichnet einen Pfeilkopf an 'end' in Richtung von 'start' → 'end'"""        
    def draw_arrow(self, painter, start, end): 
   
            # Richtung der Linie
            dx = end.x() -start.x()
            dy = end.y() - start.y()
            angle = math.atan2(dy, dx)

            # Größe des Pfeilkopfs
            arrow_size = 12

            # Zwei Punkte für die Seitenflügel
            pa = QPointF(
                end.x() - arrow_size * math.cos(angle - math.pi / 6),
                end.y() - arrow_size * math.sin(angle - math.pi / 6)
            )
            pb = QPointF(
                end.x() - arrow_size * math.cos(angle + math.pi / 6),
                end.y() - arrow_size * math.sin(angle + math.pi / 6)
            )

            # Polygon (Pfeilspitze)
            arrow_head = QPolygonF([end, pa, pb])
            painter.setBrush(QColor(200, 0, 0))  # rote Füllung
            painter.drawPolygon(arrow_head)
    
    def draw_parallel_line(self, painter, p1, p2, offset=20, shorten=40):
        import math
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.hypot(dx, dy)

        if length == 0:
            return

        # Normalenvektor für den Versatz berechnen
        nx = -dy / length * offset
        ny = dx / length * offset

        # Neue Start- und Endpunkte mit Versatz
        q1 = QPointF(p1.x() + nx, p1.y() + ny)
        q2 = QPointF(p2.x() + nx, p2.y() + ny)

        # Kürzen: von beiden Enden jeweils shorten/2 abziehen
        shrink = shorten / 2
        ux = dx / length
        uy = dy / length
        q1 = QPointF(q1.x() + ux * shrink, q1.y() + uy * shrink)
        q2 = QPointF(q2.x() - ux * shrink, q2.y() - uy * shrink)

        # Zeichnen
        painter.drawLine(q1, q2)
        self.draw_arrow(painter, q1, q2)
 
            
    def draw_text_on_line(self, painter, p1, p2, text):
        import math
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        angle = math.degrees(math.atan2(dy, dx))  # Grad für rotate()

        # sicherstellen, dass Text nicht auf dem Kopf steht
        if angle > 90 or angle < -90:
            angle += 180

        # Mittelpunkt der Linie
        mx = (p1.x() + p2.x()) / 2
        my = (p1.y() + p2.y()) / 2

        # Abstand von der Linie (normale Richtung)
        offset = 15
        length = math.hypot(dx, dy)
        if(length == 0):
            length=0.001
        nx = -dy / length * offset
        ny = dx / length * offset

        painter.save()  # aktuellen Zustand merken
        painter.translate(mx + nx, my + ny)
        painter.rotate(angle)
        painter.drawText(0, 0, text)
        painter.restore()  # Zustand zurücksetzen



    
    def set_mode(self,mode):
        self.mode =mode 


    def save_to_file(self, filename):
        data = {
           'dobjects': [{'x': r.obj.x(), 'y': r.obj.y(), 'w': r.obj.width(), 'h': r.obj.height(), 'n':r.name} for r in self.dobjects],
           'connections': [(i1, i2, n) for i1, i2, n in self.connections]
         
        }
        with open(filename, 'w') as f:
           json.dump(data, f)

    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        
        self.dobjects.clear
        self.connections.clear
        self.update
        for d in data['dobjects']:
            rect = QRect(d['x'], d['y'], d['w'], d['h'])
            name1 = d['n']
            self.dobjects.append(Dobject(obj=rect,name=name1))

        for i,j,n in data['connections']:
            self.connections.append(Dconnection(i1=i,i2=j,name=n))
        self.update()



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rechtecke + Linien Rand-zu-Rand")
        self.setGeometry(200, 200, 800, 600)
        self.drawing_widget = DrawingWidget()
        self.setCentralWidget(self.drawing_widget)
        
        save_btn = QPushButton("Speichern")
        load_btn = QPushButton("Laden")
        drawbox_btn = QPushButton("DrawBox")
        drawline_btn = QPushButton("DrawLine")
        move_btn = QPushButton("Move")
        
        move_btn.clicked.connect(lambda: self.drawing_widget.set_mode("move"))
        drawbox_btn.clicked.connect(lambda: self.drawing_widget.set_mode("drawbox"))
        drawline_btn.clicked.connect(lambda: self.drawing_widget.set_mode("drawline"))
        
        save_btn.clicked.connect(self.save)
        load_btn.clicked.connect(self.load)

        layout = QVBoxLayout()
        layout.addWidget(save_btn)
        layout.addWidget(load_btn)
        layout.addWidget(drawbox_btn)
        layout.addWidget(drawline_btn)
        layout.addWidget(move_btn)
        layout.addWidget(self.drawing_widget)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def save(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Datei speichern", "", "JSON Files (*.json)")
        if filename:
            self.drawing_widget.save_to_file(filename)


    def load(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Datei oeffnen", "", "JSON Files (*.json)")
        if filename:
            self.drawing_widget.load_from_file(filename)

    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
