import sys
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QFileDialog, QPushButton, QVBoxLayout
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPointF



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
        self.rectangles = []
        self.connections = []
        self.current_rect = None
        self.selected_rect = None
        self.offset = None
        self.line_start_rect = None 
        self.mode = None


        # Beispiel: Zwei Rechtecke + Verbindung
        r1 = QRect(100, 100, 100, 80)
        r2 = QRect(300, 200, 120, 90)
        self.rectangles.extend([r1, r2])
        self.connections.append((r1, r2))

    # def mousePressEvent(self, event):
    #    if event.button() == Qt.LeftButton:
    #         for rect in reversed(self.rectangles):
    #             if rect.contains(event.pos()):
    #                 self.selected_rect = rect
    #                 self.offset = event.pos() - rect.topLeft()
    #                 return

    #         self.current_rect = QRect(event.pos(), event.pos())
    #         self.rectangles.append(self.current_rect) 

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Prüfen auf Rechteck-Klick für Verschieben oder Linienstart
            if(self.mode == "move"):
                for rect in reversed(self.rectangles):
                    if rect.contains(event.pos()):
                        self.selected_rect = rect
                        self.offset = event.pos() - rect.topLeft()
                        return

            for rect in reversed(self.rectangles):
                if rect.contains(event.pos()):
                    if self.line_start_rect is None:
                        # Erste Auswahl für Linie
                        self.line_start_rect = rect
                        return
                    else:
                        # Zweite Auswahl -> Linie erstellen
                        if rect != self.line_start_rect:
                            self.connections.append((self.line_start_rect, rect))
                        self.line_start_rect = None
                        self.update()
                        return

            # Rechteck erstellen
            self.current_rect = QRect(event.pos(), event.pos())
            self.rectangles.append(self.current_rect)

    #def mouseMoveEvent(self, event):
    #    if self.selected_rect is not None and self.offset is not None:
    #        new_top_left = event.pos() - self.offset
    #        self.selected_rect.moveTopLeft(new_top_left)
    #        self.update()
    #    elif self.current_rect is not None:
    #        self.current_rect.setBottomRight(event.pos())
    #        self.update()

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
        

    #def mouseReleaseEvent(self, event):
    #    if self.selected_rect is not None:
    #        self.selected_rect = None
    #        self.offset = None
    #    elif self.current_rect is not None:
    #        self.current_rect = None

    def mouseReleaseEvent(self, event):
        self.current_rect = None
        self.selected_rect = None
        self.offset = None

    def paintEvent(self, event):
        painter = QPainter(self)
        pen = QPen(QColor(0, 0, 0), 2)
        painter.setPen(pen)

        # Rechtecke zeichnen
        for rect in self.rectangles:
            painter.drawRect(rect)

        # Verbindungen zeichnen
        line_pen = QPen(QColor(200, 0, 0), 2)
        painter.setPen(line_pen)
        for r1, r2 in self.connections:
            c1, c2 = QPointF(r1.center()), QPointF(r2.center())
            p1 = rect_edge_intersection(r1, c1, c2)
            p2 = rect_edge_intersection(r2, c2, c1)
            painter.drawLine(p1, p2)

    def set_mode(self,mode):
        self.mode =mode 


# def save_to_file(self, filename):
#       data = {
#            'rectangles': [{'x': r.x(), 'y': r.y(), 'w': r.width(), 'h': r.height()} for r in self.rectangles],
#            'connections': [(self.rectangles.index(r1), self.rectangles.index(r2)) for r1, r2 in self.connections]
#        }
#        with open(filename, 'w') as f:
#            json.dump(data, f)

#def load_from_file(self, filename):
#        with open(filename, 'r') as f:
#            data = json.load(f)
#        self.rectangles = [QRect(d['x'], d['y'], d['w'], d['h']) for d in data['rectangles']]
#        self.connections = [(self.rectangles[i], self.rectangles[j]) for i, j in data['connections']]
#        self.update()



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
        
        #save_btn.clicked.connect(self.save)
        #load_btn.clicked.connect(self.load)

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
