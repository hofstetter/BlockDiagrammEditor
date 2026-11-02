#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Einfacher Diagram-Editor mit Tkinter
- Linke Werkzeugleiste: Modi und Aktionen
- Canvas in der Mitte: Rechtecke zeichnen, auswählen, verschieben, skalieren
- Rechte Seitenleiste: Attribute bearbeiten (verbergbar)
- Linien zwischen Rechtecken (mit Namen und Pfeil Richtung Auswahlreihenfolge)
- Speichern / Laden im JSON-Format


"""

import tkinter as tk
from tkinter import ttk, filedialog, simpledialog, messagebox, colorchooser
import json
import math
import uuid
import sys
import ctypes
from ctypes import wintypes

# ---------------------------
# Hilfsfunktionen (Geometrie)
# ---------------------------

def rect_center_coords(coords):
    x1, y1, x2, y2 = coords
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

def rect_normalize(coords):
    x1, y1, x2, y2 = coords
    return (min(x1,x2), min(y1,y2), max(x1,x2), max(y1,y2))

def line_rect_intersection(rect, p_from, p_to):
    """
    Berechne Schnittpunkt zwischen Linie (p_from -> p_to) und Rechteckkante.
    Liefert den Punkt auf der Kante des Rechtecks, wo die Linie das Rechteck
    verlässt (oder betritt). Erwartet rect als (x1,y1,x2,y2).
    Wenn Mitte/p_from innerhalb rect, dann wird ein Austrittspunkt berechnet.
    """
    x1, y1, x2, y2 = rect
    cx = (x1 + x2) / 2.0
    cy = (y1 + y2) / 2.0
    # Linie parametrisch: p(t) = p_from + t*(p_to - p_from), 0<=t<=1
    (xA, yA) = p_from
    (xB, yB) = p_to
    dx = xB - xA
    dy = yB - yA
    # Intersektionen mit 4 Kanten berechnen, gültige Punkte sammeln
    candidates = []
    eps = 1e-9
    # Left edge x = x1, y between y1..y2
    if abs(dx) > eps:
        t = (x1 - xA) / dx
        y = yA + t * dy
        if 0 <= t <= 1 and y1-1e-6 <= y <= y2+1e-6:
            candidates.append((t, (x1, y)))
    # Right edge x = x2
    if abs(dx) > eps:
        t = (x2 - xA) / dx
        y = yA + t * dy
        if 0 <= t <= 1 and y1-1e-6 <= y <= y2+1e-6:
            candidates.append((t, (x2, y)))
    # Top edge y = y1
    if abs(dy) > eps:
        t = (y1 - yA) / dy
        x = xA + t * dx
        if 0 <= t <= 1 and x1-1e-6 <= x <= x2+1e-6:
            candidates.append((t, (x, y1)))
    # Bottom edge y = y2
    if abs(dy) > eps:
        t = (y2 - yA) / dy
        x = xA + t * dx
        if 0 <= t <= 1 and x1-1e-6 <= x <= x2+1e-6:
            candidates.append((t, (x, y2)))
    if not candidates:
        # keine Schnittpunkte gefunden (z. B. parallele oder vollständig außerhalb)
        # Fallback: gib Mittelpunkt zurück
        return (cx, cy)
    # Wenn p_from innerhalb Rechteck, wir suchen den nächstgrößeren t>0 (Austritt)
    p_from_inside = (x1 <= xA <= x2 and y1 <= yA <= y2)
    if p_from_inside:
        # wähle den kleinsten t>0
        candidates = [c for c in candidates if c[0] > eps]
        if not candidates:
            return (cx, cy)
        t_min, point = min(candidates, key=lambda it: it[0])
        return point
    else:
        # Wenn p_from außerhalb, wähle t in [0,1] - derjenige, der näher bei p_from ist
        # (das erste encountered)
        candidates = sorted(candidates, key=lambda it: it[0])
        # choose the one with smallest positive t
        for t, pt in candidates:
            if t >= -eps:
                return pt
        return candidates[0][1]

def _seg_normal(p, q):
    dx, dy = q[0] - p[0], q[1] - p[1]
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return (0.0, 0.0)
    return (-dy / length, dx / length)

def offset_polyline(points, offset):
    if not points or abs(offset) < 1e-9:
        return list(points)
    n = len(points)
    if n == 1:
        return list(points)
    out = []
    for i, p in enumerate(points):
        if i == 0:
            nx, ny = _seg_normal(points[0], points[1])
        elif i == n - 1:
            nx, ny = _seg_normal(points[n - 2], points[n - 1])
        else:
            n1 = _seg_normal(points[i - 1], points[i])
            n2 = _seg_normal(points[i], points[i + 1])
            sx, sy = n1[0] + n2[0], n1[1] + n2[1]
            sl = math.hypot(sx, sy)
            if sl < 1e-9:
                nx, ny = n1
            else:
                nx, ny = sx / sl, sy / sl
        out.append((p[0] + nx * offset, p[1] + ny * offset))
    return out

def polyline_length(points):
    total = 0.0
    for i in range(len(points) - 1):
        total += math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
    return total

def point_along_polyline(points, dist):
    if not points:
        return (0.0, 0.0)
    remaining = max(0.0, dist)
    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        seg = math.hypot(x2 - x1, y2 - y1)
        if seg < 1e-9:
            continue
        if remaining <= seg:
            t = remaining / seg
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        remaining -= seg
    return points[-1]

def slice_polyline(points, t0, t1):
    if not points or len(points) < 2:
        return list(points)
    total = polyline_length(points)
    if total < 1e-6:
        return list(points)
    d0 = max(0.0, min(total, t0 * total))
    d1 = max(d0, min(total, t1 * total))
    out = [point_along_polyline(points, d0)]
    acc = 0.0
    for i in range(len(points) - 1):
        seg = math.hypot(points[i + 1][0] - points[i][0], points[i + 1][1] - points[i][1])
        next_acc = acc + seg
        if d0 < next_acc < d1:
            out.append(points[i + 1])
        acc = next_acc
    end = point_along_polyline(points, d1)
    if math.hypot(end[0] - out[-1][0], end[1] - out[-1][1]) > 0.5:
        out.append(end)
    return out

def polyline_distance(points, x, y):
    best = None
    for i in range(len(points) - 1):
        ax, ay = points[i]
        bx, by = points[i + 1]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        if l2 < 1e-9:
            dist = math.hypot(x - ax, y - ay)
        else:
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
            px, py = ax + t * dx, ay + t * dy
            dist = math.hypot(x - px, y - py)
        if best is None or dist < best:
            best = dist
    return float("inf") if best is None else best

def signed_offset_from_polyline(points, x, y):
    best = None
    for i in range(len(points) - 1):
        ax, ay = points[i]
        bx, by = points[i + 1]
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        if l2 < 1e-9:
            continue
        t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / l2))
        px, py = ax + t * dx, ay + t * dy
        dist = math.hypot(x - px, y - py)
        length = math.sqrt(l2)
        unx, uny = -dy / length, dx / length
        signed = (x - px) * unx + (y - py) * uny
        if best is None or dist < best[0]:
            best = (dist, signed)
    return 0.0 if best is None else best[1]

def bbox_intersects(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)

def points_bbox(points):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs), min(ys), max(xs), max(ys))

def parse_color(value, default="#000000"):
    if not value:
        return default
    s = str(value).strip()
    if s.startswith("#") and len(s) == 4:
        s = "#" + "".join(ch * 2 for ch in s[1:])
    if s.startswith("#") and len(s) == 7:
        try:
            int(s[1:], 16)
            return s.lower()
        except ValueError:
            return default
    return default

def hex_to_rgb(color, default=(0, 0, 0)):
    s = parse_color(color, "#%02x%02x%02x" % default)
    try:
        return int(s[1:3], 16), int(s[3:5], 16), int(s[5:7], 16)
    except ValueError:
        return default

def parse_name_offset(data):
    v = data.get("name_offset") if isinstance(data, dict) else None
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        try:
            return (float(v[0]), float(v[1]))
        except (TypeError, ValueError):
            pass
    return (0.0, 0.0)

def next_numbered_name(names, prefix):
    max_n = 0
    head = prefix + "-"
    for name in names:
        if not name:
            continue
        s = str(name).strip()
        if s.upper().startswith(head.upper()) and s[len(head):].isdigit():
            max_n = max(max_n, int(s[len(head):]))
    return f"{prefix}-{max_n + 1:03d}"

def next_parallel_offset(arrows, step=16):
    used = {int(round(a.offset)) for a in arrows}
    n = 1
    while True:
        for cand in (step * n, -step * n):
            if cand not in used:
                return cand
        n += 1

ARROW_HEAD_SIZE = 12
ARROW_HEAD_SPREAD = math.radians(34)

def open_arrow_points(p_from, p_to, size=ARROW_HEAD_SIZE, spread=ARROW_HEAD_SPREAD):
    """Offene V-Spitze an p_to, Richtung p_from -> p_to (Koordinaten wie übergeben)."""
    dx = p_to[0] - p_from[0]
    dy = p_to[1] - p_from[1]
    if math.hypot(dx, dy) < 1e-6:
        return None
    ang = math.atan2(dy, dx)
    back = ang + math.pi
    w1 = (p_to[0] + size * math.cos(back + spread), p_to[1] + size * math.sin(back + spread))
    w2 = (p_to[0] + size * math.cos(back - spread), p_to[1] + size * math.sin(back - spread))
    return (w1, p_to, w2)

def arrow_shaft_pair(points, at_start):
    if not points or len(points) < 2:
        return None
    if at_start:
        return points[1], points[0]
    return points[-2], points[-1]

def sync_open_arrow(canvas, item_id, points, at_start, zoom, color, width, tags):
    pair = arrow_shaft_pair(points, at_start)
    chev = None
    if pair:
        z = zoom
        chev = open_arrow_points((pair[0][0] * z, pair[0][1] * z), (pair[1][0] * z, pair[1][1] * z))
    if not chev:
        if item_id:
            try:
                canvas.delete(item_id)
            except Exception:
                pass
        return None
    flat = [v for p in chev for v in p]
    if item_id is None:
        return canvas.create_line(
            *flat, width=width, fill=color, capstyle=tk.ROUND, joinstyle=tk.MITER, tags=tags
        )
    canvas.coords(item_id, *flat)
    canvas.itemconfig(item_id, fill=color, width=width)
    return item_id

# ---------------------------
# Objektmodelle
# ---------------------------

class RectObj:
    def __init__(self, app, bbox, name=None, obj_id=None, dashed=False, name_offset=None, color=None):
        self.app = app
        self.id = obj_id or str(uuid.uuid4())
        self.bbox = rect_normalize(bbox)  # (x1,y1,x2,y2)
        self.name = name if name is not None else app.next_object_name("B")
        self.name_offset = tuple(name_offset) if name_offset else (0.0, 0.0)
        self.color = parse_color(color)
        self.dashed = bool(dashed)
        self.interfaces = []
        # canvas object ids
        self.canvas_rect = None
        self.canvas_text = None
        self.handles = {}  # keys: 'nw','ne','se','sw' -> canvas id
        self.selected = False

    def to_dict(self):
        return {
            "id": self.id,
            "bbox": list(self.bbox),
            "name": self.name,
            "name_offset": [self.name_offset[0], self.name_offset[1]],
            "color": self.color,
            "dashed": self.dashed,
            "interfaces": [i.to_dict() for i in self.interfaces],
        }

    @classmethod
    def from_dict(cls, app, d):
        rect = cls(
            app, tuple(d["bbox"]), name=d.get("name"), obj_id=d["id"],
            dashed=d.get("dashed", False), name_offset=parse_name_offset(d),
            color=d.get("color"),
        )
        for idata in d.get("interfaces", []):
            iface = InterfaceObj.from_dict(rect, idata)
            rect.interfaces.append(iface)
            app.ifaces[iface.id] = iface
        return rect

    def _dash_style(self):
        return (8, 4) if self.dashed else ""

    def name_anchor(self):
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, y1 + 4)

    def name_pos(self):
        ax, ay = self.name_anchor()
        return (ax + self.name_offset[0], ay + self.name_offset[1])

    def draw(self):
        c = self.app.canvas
        z = getattr(self.app, "zoom", 1.0)
        x1,y1,x2,y2 = self.bbox
        zx1, zy1, zx2, zy2 = x1 * z, y1 * z, x2 * z, y2 * z
        nx, ny = self.name_pos()
        width = 3 if self.selected else 2
        color = self.color
        if self.canvas_rect is None:
            self.canvas_rect = c.create_rectangle(
                zx1, zy1, zx2, zy2, fill="", outline=color, width=width,
                dash=self._dash_style(), tags=("block", self.id)
            )
            self.canvas_text = c.create_text(
                nx * z, ny * z, text=self.name, fill=color, anchor="n", tags=("block_text", self.id)
            )
        else:
            c.coords(self.canvas_rect, zx1, zy1, zx2, zy2)
            c.coords(self.canvas_text, nx * z, ny * z)
            c.itemconfig(self.canvas_text, text=self.name, fill=color)
            c.itemconfig(self.canvas_rect, fill="", outline=color, width=width, dash=self._dash_style())
        c.tag_raise(self.canvas_text)
        if self.selected:
            self._ensure_handles()
        else:
            self._remove_handles()
        for iface in self.interfaces:
            iface.draw()

    def _ensure_handles(self):
        c = self.app.canvas
        z = getattr(self.app, "zoom", 1.0)
        x1,y1,x2,y2 = self.bbox
        size = 6
        coords = {
            "nw": (x1 * z, y1 * z),
            "ne": (x2 * z, y1 * z),
            "se": (x2 * z, y2 * z),
            "sw": (x1 * z, y2 * z),
        }
        for k,p in coords.items():
            if k in self.handles and c.type(self.handles[k]) != "":
                c.coords(self.handles[k], p[0]-size, p[1]-size, p[0]+size, p[1]+size)
            else:
                hid = c.create_rectangle(p[0]-size, p[1]-size, p[0]+size, p[1]+size, fill="#000000", tags=("handle", self.id, k))
                self.handles[k] = hid

    def _remove_handles(self):
        c = self.app.canvas
        for hid in list(self.handles.values()):
            try:
                c.delete(hid)
            except Exception:
                pass
        self.handles.clear()

    def destroy_canvas(self):
        self._remove_handles()
        c = self.app.canvas
        for item in (self.canvas_rect, self.canvas_text):
            if item:
                try:
                    c.delete(item)
                except Exception:
                    pass
        self.canvas_rect = None
        self.canvas_text = None
        for iface in self.interfaces:
            iface.destroy_canvas()

    def set_selected(self, sel: bool):
        self.selected = sel
        c = self.app.canvas
        if self.canvas_rect:
            c.itemconfig(
                self.canvas_rect, fill="", outline=self.color,
                width=3 if sel else 2, dash=self._dash_style()
            )
        self.draw()

    def contains_point(self, x,y):
        x1,y1,x2,y2 = self.bbox
        return x1 <= x <= x2 and y1 <= y <= y2

    def move_by(self, dx, dy):
        x1,y1,x2,y2 = self.bbox
        self.bbox = (x1+dx, y1+dy, x2+dx, y2+dy)
        self.draw()

    def resize_corner(self, corner, new_x, new_y):
    #Fehler: Corner ist falsch, beinhaltet nicht diese tags, oder sie sind "versteckt"           
        x1,y1,x2,y2 = self.bbox
        
        if corner == 'nw':
            x1, y1 = new_x, new_y
        elif corner == 'ne':
            x2, y1 = new_x, new_y
        elif corner == 'se':
            x2, y2 = new_x, new_y
        elif corner == 'sw':
            x1, y2 = new_x, new_y

        
        self.bbox = rect_normalize((x1,y1,x2,y2))   
        self.draw()

    def add_interface(self, side=None, t=None):
        if side is None or t is None:
            side, t = next_iface_slot(self.interfaces)
        iface = InterfaceObj(self, side=side, t=t)
        self.interfaces.append(iface)
        self.app.ifaces[iface.id] = iface
        return iface

    def remove_interface(self, iface_id):
        iface = next((i for i in self.interfaces if i.id == iface_id), None)
        if not iface:
            return
        iface.destroy_canvas()
        self.interfaces = [i for i in self.interfaces if i.id != iface_id]
        self.app.ifaces.pop(iface_id, None)


def next_iface_slot(ifaces):
    used = {(i.side, round(i.t, 2)) for i in ifaces}
    for t in (0.5, 0.28, 0.72, 0.16, 0.84, 0.4, 0.6):
        key = ("e", round(t, 2))
        if key not in used:
            return "e", t
    return "e", min(0.9, 0.12 + 0.12 * len(ifaces))


class InterfaceObj:
    """Lollipop-Interface an der Kante eines Blocks."""

    RADIUS = 8
    STEM = 16
    SIDES = ("e", "w", "n", "s")
    SIDE_LABELS = {"e": "rechts", "w": "links", "n": "oben", "s": "unten"}
    LABEL_SIDES = {v: k for k, v in SIDE_LABELS.items()}

    def __init__(self, block, side="e", t=0.5, name=None, obj_id=None, name_offset=None, color=None):
        self.block = block
        self.id = obj_id or str(uuid.uuid4())
        self.side = side if side in self.SIDES else "e"
        self.t = min(0.92, max(0.08, float(t)))
        self.name = name if name is not None else block.app.next_object_name("I")
        self.name_offset = tuple(name_offset) if name_offset else (0.0, 0.0)
        self.color = parse_color(color)
        self.selected = False
        self.canvas_stem = None
        self.canvas_circle = None
        self.canvas_text = None

    @property
    def block_id(self):
        return self.block.id

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "name_offset": [self.name_offset[0], self.name_offset[1]],
            "color": self.color,
            "side": self.side,
            "t": self.t,
        }

    @classmethod
    def from_dict(cls, block, d):
        return cls(
            block,
            side=d.get("side", "e"),
            t=d.get("t", 0.5),
            name=d.get("name"),
            obj_id=d.get("id"),
            name_offset=parse_name_offset(d),
            color=d.get("color"),
        )

    def attach_point(self):
        x1, y1, x2, y2 = self.block.bbox
        t = self.t
        if self.side == "e":
            return (x2, y1 + t * (y2 - y1))
        if self.side == "w":
            return (x1, y1 + t * (y2 - y1))
        if self.side == "n":
            return (x1 + t * (x2 - x1), y1)
        return (x1 + t * (x2 - x1), y2)

    def outward(self):
        return {"e": (1, 0), "w": (-1, 0), "n": (0, -1), "s": (0, 1)}[self.side]

    def circle_center(self):
        ax, ay = self.attach_point()
        ox, oy = self.outward()
        dist = self.STEM + self.RADIUS
        return (ax + ox * dist, ay + oy * dist)

    def stem_end(self):
        ax, ay = self.attach_point()
        ox, oy = self.outward()
        return (ax + ox * self.STEM, ay + oy * self.STEM)

    def rim_point_from(self, p):
        cx, cy = self.circle_center()
        dx, dy = cx - p[0], cy - p[1]
        length = math.hypot(dx, dy)
        if length < 1e-6:
            ox, oy = self.outward()
            return (cx - ox * self.RADIUS, cy - oy * self.RADIUS)
        ux, uy = dx / length, dy / length
        return (cx - ux * self.RADIUS, cy - uy * self.RADIUS)

    def bbox(self):
        cx, cy = self.circle_center()
        ax, ay = self.attach_point()
        r = self.RADIUS
        xs = [cx - r, cx + r, ax]
        ys = [cy - r, cy + r, ay]
        return (min(xs), min(ys), max(xs), max(ys))

    def contains_point(self, x, y):
        cx, cy = self.circle_center()
        if math.hypot(x - cx, y - cy) <= self.RADIUS + 5:
            return True
        ax, ay = self.attach_point()
        sx, sy = self.stem_end()
        return _point_near_segment(x, y, ax, ay, sx, sy, 5)

    def place_at(self, x, y):
        x1, y1, x2, y2 = self.block.bbox
        candidates = [
            ("n", abs(y - y1), 0 if x2 <= x1 else (x - x1) / (x2 - x1)),
            ("s", abs(y - y2), 0 if x2 <= x1 else (x - x1) / (x2 - x1)),
            ("w", abs(x - x1), 0 if y2 <= y1 else (y - y1) / (y2 - y1)),
            ("e", abs(x - x2), 0 if y2 <= y1 else (y - y1) / (y2 - y1)),
        ]
        side, _, t = min(candidates, key=lambda it: it[1])
        self.side = side
        self.t = min(0.92, max(0.08, t))

    def name_anchor(self):
        cx, cy = self.circle_center()
        r = self.RADIUS
        ox, oy = self.outward()
        tx = cx + ox * (r + 10)
        ty = cy + oy * (r + 10)
        if self.side in ("e", "w"):
            ty = cy
        else:
            tx = cx
        return (tx, ty)

    def name_pos(self):
        ax, ay = self.name_anchor()
        return (ax + self.name_offset[0], ay + self.name_offset[1])

    def draw(self):
        c = self.block.app.canvas
        z = getattr(self.block.app, "zoom", 1.0)
        ax, ay = self.attach_point()
        sx, sy = self.stem_end()
        cx, cy = self.circle_center()
        r = self.RADIUS
        color = self.color
        width = 3 if self.selected else 2
        tags = ("iface", self.id)
        if self.canvas_stem is None:
            self.canvas_stem = c.create_line(
                ax * z, ay * z, sx * z, sy * z, width=width, fill=color, tags=tags
            )
            self.canvas_circle = c.create_oval(
                (cx - r) * z, (cy - r) * z, (cx + r) * z, (cy + r) * z,
                outline=color, width=width, fill="", tags=tags
            )
            nx, ny = self.name_pos()
            self.canvas_text = c.create_text(
                nx * z, ny * z, text=self.name, fill=color,
                tags=("iface_text", self.id)
            )
        else:
            c.coords(self.canvas_stem, ax * z, ay * z, sx * z, sy * z)
            c.coords(self.canvas_circle, (cx - r) * z, (cy - r) * z, (cx + r) * z, (cy + r) * z)
            c.itemconfig(self.canvas_stem, fill=color, width=width)
            c.itemconfig(self.canvas_circle, outline=color, width=width)
            c.itemconfig(self.canvas_text, text=self.name, fill=color)
        nx, ny = self.name_pos()
        c.coords(self.canvas_text, nx * z, ny * z)
        c.tag_raise(self.canvas_stem)
        c.tag_raise(self.canvas_circle)
        c.tag_raise(self.canvas_text)

    def destroy_canvas(self):
        c = self.block.app.canvas
        for item in (self.canvas_stem, self.canvas_circle, self.canvas_text):
            if item:
                try:
                    c.delete(item)
                except Exception:
                    pass
        self.canvas_stem = None
        self.canvas_circle = None
        self.canvas_text = None


def _point_near_segment(x, y, x1, y1, x2, y2, dist):
    dx, dy = x2 - x1, y2 - y1
    length2 = dx * dx + dy * dy
    if length2 < 1e-9:
        return math.hypot(x - x1, y - y1) <= dist
    t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / length2))
    px, py = x1 + t * dx, y1 + t * dy
    return math.hypot(x - px, y - py) <= dist


class ParallelArrow:
    """Kurzer Datenfluss parallel zur Stammlinie, in deren Mitte."""

    LENGTH_RATIO = 0.38

    def __init__(self, line, offset=16, name=None, obj_id=None, length_ratio=None, arrow_at_start=False, name_offset=None, color=None):
        self.line = line
        self.id = obj_id or str(uuid.uuid4())
        self.offset = offset
        self.length_ratio = length_ratio if length_ratio is not None else self.LENGTH_RATIO
        self.name = name if name is not None else line.app.next_object_name("D")
        self.name_offset = tuple(name_offset) if name_offset else (0.0, 0.0)
        self.color = parse_color(color, "#555555")
        self.arrow_at_start = bool(arrow_at_start)
        self.canvas_line = None
        self.canvas_arrow = None
        self.canvas_text = None
        self.selected = False

    def to_dict(self):
        return {
            "id": self.id,
            "offset": self.offset,
            "length_ratio": self.length_ratio,
            "name": self.name,
            "name_offset": [self.name_offset[0], self.name_offset[1]],
            "color": self.color,
            "arrow_at_start": self.arrow_at_start,
        }

    @classmethod
    def from_dict(cls, line, d):
        return cls(
            line,
            offset=d.get("offset", 16),
            name=d.get("name"),
            obj_id=d.get("id"),
            length_ratio=d.get("length_ratio"),
            arrow_at_start=d.get("arrow_at_start", False),
            name_offset=parse_name_offset(d),
            color=d.get("color"),
        )

    def geometry(self):
        pts = self.line.polyline_points()
        if not pts:
            return None
        offset_pts = offset_polyline(pts, self.offset)
        ratio = min(max(self.length_ratio, 0.15), 0.8)
        t0 = 0.5 - ratio / 2.0
        t1 = 0.5 + ratio / 2.0
        mid = slice_polyline(offset_pts, t0, t1)
        if len(mid) < 2:
            return None
        return mid

    def name_anchor(self):
        pts = self.geometry()
        if not pts:
            return (0.0, 0.0)
        mx = sum(p[0] for p in pts) / len(pts)
        my = min(p[1] for p in pts) - 10
        return (mx, my)

    def name_pos(self):
        ax, ay = self.name_anchor()
        return (ax + self.name_offset[0], ay + self.name_offset[1])

    def draw(self):
        c = self.line.app.canvas
        z = getattr(self.line.app, "zoom", 1.0)
        pts = self.geometry()
        if not pts:
            return
        flat = [v for p in pts for v in (p[0] * z, p[1] * z)]
        color = self.color
        width = 3 if self.selected else 2
        tags = ("parrow", self.line.id, self.id)
        if self.canvas_line is None:
            self.canvas_line = c.create_line(
                *flat, width=width, joinstyle=tk.MITER,
                fill=color, tags=tags
            )
            nx, ny = self.name_pos()
            self.canvas_text = c.create_text(
                nx * z, ny * z, text=self.name, fill=color,
                tags=("parrow_text", self.line.id, self.id)
            )
        else:
            c.coords(self.canvas_line, *flat)
            c.itemconfig(self.canvas_line, fill=color, width=width)
            c.itemconfig(self.canvas_text, text=self.name, fill=color)
        self.canvas_arrow = sync_open_arrow(
            c, self.canvas_arrow, pts, self.arrow_at_start, z, color, width, tags
        )
        nx, ny = self.name_pos()
        c.coords(self.canvas_text, nx * z, ny * z)
        c.tag_raise(self.canvas_line)
        if self.canvas_arrow:
            c.tag_raise(self.canvas_arrow)
        c.tag_raise(self.canvas_text)

    def destroy_canvas(self):
        c = self.line.app.canvas
        for item in (self.canvas_line, self.canvas_arrow, self.canvas_text):
            if item:
                try:
                    c.delete(item)
                except Exception:
                    pass
        self.canvas_line = None
        self.canvas_arrow = None
        self.canvas_text = None


class LineObj:
    def __init__(self, app, source_rect_id, target_rect_id, name=None, obj_id=None, waypoint=None, arrow_at_start=False, target_kind="block", name_offset=None, color=None):
        self.app = app
        self.id = obj_id or str(uuid.uuid4())
        self.source = source_rect_id
        self.target = target_rect_id
        self.target_kind = target_kind if target_kind in ("block", "iface") else "block"
        self.name = name if name is not None else app.next_object_name("V")
        self.name_offset = tuple(name_offset) if name_offset else (0.0, 0.0)
        self.color = parse_color(color)
        self.line_offset = 0
        self.waypoint = tuple(waypoint) if waypoint else None
        self.arrow_at_start = bool(arrow_at_start)
        self.parallel_arrows = []
        # canvas items
        self.canvas_line = None
        self.canvas_arrow = None
        self.canvas_text = None
        self.canvas_handle = None
        self.selected = False

    def to_dict(self):
        data = {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "target_kind": self.target_kind,
            "name": self.name,
            "name_offset": [self.name_offset[0], self.name_offset[1]],
            "color": self.color,
            "arrow_at_start": self.arrow_at_start,
            "parallel_arrows": [a.to_dict() for a in self.parallel_arrows]
        }
        if self.waypoint:
            data["waypoint"] = [self.waypoint[0], self.waypoint[1]]
        return data

    @classmethod
    def from_dict(cls, app, d):
        wp = d.get("waypoint")
        line = cls(
            app, d["source"], d["target"], name=d.get("name"), obj_id=d["id"],
            waypoint=wp, arrow_at_start=d.get("arrow_at_start", False),
            target_kind=d.get("target_kind", "block"),
            name_offset=parse_name_offset(d),
            color=d.get("color"),
        )
        for ad in d.get("parallel_arrows", []):
            line.parallel_arrows.append(ParallelArrow.from_dict(line, ad))
        return line

    def get_parallel(self, arrow_id):
        for a in self.parallel_arrows:
            if a.id == arrow_id:
                return a
        return None

    def add_parallel_arrow(self):
        offset = next_parallel_offset(self.parallel_arrows)
        pa = ParallelArrow(self, offset=offset)
        self.parallel_arrows.append(pa)
        return pa

    def remove_parallel(self, arrow_id):
        pa = self.get_parallel(arrow_id)
        if not pa:
            return
        pa.destroy_canvas()
        self.parallel_arrows = [a for a in self.parallel_arrows if a.id != arrow_id]

    def target_anchor(self):
        if self.target_kind == "iface":
            return self.app.ifaces.get(self.target)
        return self.app.rects.get(self.target)

    def polyline_points(self):
        src = self.app.rects.get(self.source)
        if not src:
            return None
        a_center = rect_center_coords(src.bbox)
        if self.target_kind == "iface":
            iface = self.app.ifaces.get(self.target)
            if not iface:
                return None
            b_center = iface.circle_center()
            if self.waypoint:
                a_point = line_rect_intersection(src.bbox, a_center, self.waypoint)
                b_point = iface.rim_point_from(self.waypoint)
                return (a_point, self.waypoint, b_point)
            a_point = line_rect_intersection(src.bbox, a_center, b_center)
            b_point = iface.rim_point_from(a_point)
            return (a_point, b_point)
        tgt = self.app.rects.get(self.target)
        if not tgt:
            return None
        b_center = rect_center_coords(tgt.bbox)
        if self.waypoint:
            a_point = line_rect_intersection(src.bbox, a_center, self.waypoint)
            b_point = line_rect_intersection(tgt.bbox, b_center, self.waypoint)
            mid = self.waypoint
            if self.line_offset > 0:
                a_point = (a_point[0] + self.line_offset, a_point[1] + self.line_offset)
                mid = (mid[0] + self.line_offset, mid[1] + self.line_offset)
                b_point = (b_point[0] + self.line_offset, b_point[1] + self.line_offset)
            return (a_point, mid, b_point)
        a_point = line_rect_intersection(src.bbox, a_center, b_center)
        b_point = line_rect_intersection(tgt.bbox, b_center, a_center)
        if self.line_offset > 0:
            a_point = (a_point[0] + self.line_offset, a_point[1] + self.line_offset)
            b_point = (b_point[0] + self.line_offset, b_point[1] + self.line_offset)
        return (a_point, b_point)

    def name_anchor(self):
        if self.waypoint:
            return (self.waypoint[0], self.waypoint[1] - 12)
        points = self.polyline_points()
        if not points:
            return (0.0, 0.0)
        return (
            (points[0][0] + points[-1][0]) / 2.0,
            (points[0][1] + points[-1][1]) / 2.0 - 10,
        )

    def name_pos(self):
        ax, ay = self.name_anchor()
        return (ax + self.name_offset[0], ay + self.name_offset[1])

    def draw(self):
        c = self.app.canvas
        z = getattr(self.app, "zoom", 1.0)
        points = self.polyline_points()
        if not points:
            return
        flat = [v for p in points for v in (p[0] * z, p[1] * z)]
        color = self.color
        width = 3 if self.selected else 2
        tags = ("verbindung", self.id)
        if self.canvas_line is None:
            self.canvas_line = c.create_line(
                *flat, width=width, joinstyle=tk.MITER, fill=color, tags=tags
            )
            nx, ny = self.name_pos()
            self.canvas_text = c.create_text(nx * z, ny * z, text=self.name, tags=("verbindung_text", self.id))
        else:
            c.coords(self.canvas_line, *flat)
            c.itemconfig(self.canvas_text, text=self.name)
        self.canvas_arrow = sync_open_arrow(
            c, self.canvas_arrow, points, self.arrow_at_start, z, color, width, tags
        )
        nx, ny = self.name_pos()
        c.coords(self.canvas_text, nx * z, ny * z)
        c.itemconfig(self.canvas_line, fill=color, width=width)
        c.itemconfig(self.canvas_text, fill=color)
        c.tag_raise(self.canvas_line)
        if self.canvas_arrow:
            c.tag_raise(self.canvas_arrow)
        c.tag_raise(self.canvas_text)
        if self.selected and self.waypoint:
            self._ensure_handle()
        else:
            self._remove_handle()
        for pa in self.parallel_arrows:
            pa.draw()

    def destroy_canvas(self):
        c = self.app.canvas
        for item in (self.canvas_line, self.canvas_arrow, self.canvas_text, self.canvas_handle):
            if item:
                try:
                    c.delete(item)
                except Exception:
                    pass
        self.canvas_line = None
        self.canvas_arrow = None
        self.canvas_text = None
        self.canvas_handle = None
        for pa in self.parallel_arrows:
            pa.destroy_canvas()

    def _ensure_handle(self):
        c = self.app.canvas
        z = getattr(self.app, "zoom", 1.0)
        x, y = self.waypoint[0] * z, self.waypoint[1] * z
        size = 5
        box = (x - size, y - size, x + size, y + size)
        if self.canvas_handle:
            c.coords(self.canvas_handle, *box)
        else:
            self.canvas_handle = c.create_rectangle(
                *box, fill="#ffffff", outline="#0077ff", width=2,
                tags=("handle", "line_handle", self.id)
            )
        c.tag_raise(self.canvas_handle)

    def _remove_handle(self):
        if self.canvas_handle:
            try:
                self.app.canvas.delete(self.canvas_handle)
            except Exception:
                pass
            self.canvas_handle = None

    def set_selected(self, sel: bool):
        self.selected = sel
        self.draw()

# ---------------------------
# Hauptanwendung
# ---------------------------

class DiagramApp:
    def __init__(self, root):
        self.root = root
        root.title("Diagram Editor")
        root.geometry("1100x700")

        # Datenmodelle
        self.rects = {}  # id -> RectObj
        self.lines = {}  # id -> LineObj
        self.ifaces = {}  # id -> InterfaceObj

        # Zustand
        self.mode = "select"  # modes: select, draw_block, draw_verbindung
        self.min_rect_size = 12
        self.current_draw_rect = None  # temp RectObj while drawing
        self.line_first_rect = None  # unused leftover; connections are drag-based
        self.line_drag_source = None  # rect id while dragging a new connection
        self.line_preview_id = None  # canvas id of rubber-band line
        self.line_preview_arrow_id = None
        self.selected_obj = None  # primary if exactly one; else None
        self.selection = []  # ("block", id) / ("verbindung", id) / ("parrow", ...) / ("iface", id)
        self.iface_btn = None
        self.drag_iface_id = None
        self.dragging = False
        self.drag_start = (0,0)
        self.drag_rect_id = None
        self.drag_handles_corner = None  # if resizing: which corner
        self.drag_line_id = None  # line whose waypoint is being dragged
        self.drag_parrow = None  # (line_id, arrow_id) while adjusting offset
        self.drag_name_key = None
        self.drag_name_grab = (0.0, 0.0)
        self.move_group_ids = set()  # rectangles that follow when moving a rect
        self.marquee_id = None
        self.marquee_start = (0, 0)
        self.moving_selection = False
        self.zoom = 1.0
        self.zoom_min = 0.25
        self.zoom_max = 4.0

        self._syncing_attrs = False
        self.parallel_arrow_btn = None
        self._history = []
        self._history_index = -1
        self._history_restoring = False
        self._history_limit = 50
        self._build_ui()
        self._bind_events()
        self._push_history()

    def next_object_name(self, prefix):
        if prefix == "B":
            names = [r.name for r in self.rects.values()]
        elif prefix == "V":
            names = [l.name for l in self.lines.values()]
        elif prefix == "I":
            names = [i.name for r in self.rects.values() for i in r.interfaces]
        else:
            names = [pa.name for l in self.lines.values() for pa in l.parallel_arrows]
        return next_numbered_name(names, prefix)

    # ---------------------------
    # UI Aufbau
    # ---------------------------

    def _build_ui(self):
        # Layout: left tools, center canvas, right attributes
        self.left_frame = ttk.Frame(self.root, width=140)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.right_frame = ttk.Frame(self.root, width=260)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Left toolbar
        ttk.Label(self.left_frame, text="Menü", font=("Arial", 12, "bold")).pack(pady=6)
        self.btn_draw_rect = ttk.Button(self.left_frame, text="Block", command=lambda: self.toggle_mode("draw_block"))
        self.btn_draw_line = ttk.Button(self.left_frame, text="Verbindung", command=lambda: self.toggle_mode("draw_verbindung"))
        self.btn_delete = ttk.Button(self.left_frame, text="Löschen", command=self.delete_selected)
        self.btn_save = ttk.Button(self.left_frame, text="Speichern (JSON)", command=self.save_json)
        self.btn_load = ttk.Button(self.left_frame, text="Laden (JSON)", command=self.load_json)
        self.btn_copy_image = ttk.Button(self.left_frame, text="Grafik ins Clipboard", command=self.copy_canvas_to_clipboard)

        for w in (self.btn_draw_rect, self.btn_draw_line, self.btn_delete, self.btn_copy_image, self.btn_save, self.btn_load):
            w.pack(fill=tk.X, padx=8, pady=4)

        undo_row = ttk.Frame(self.left_frame)
        undo_row.pack(fill=tk.X, padx=8, pady=4)
        undo_row.columnconfigure(0, weight=1, uniform="hist")
        undo_row.columnconfigure(1, weight=1, uniform="hist")
        self.btn_undo = ttk.Button(undo_row, text="Undo", command=self.undo)
        self.btn_redo = ttk.Button(undo_row, text="Redo", command=self.redo)
        self.btn_undo.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.btn_redo.grid(row=0, column=1, sticky="ew", padx=(2, 0))

        zoom_row = ttk.Frame(self.left_frame)
        zoom_row.pack(fill=tk.X, padx=8, pady=4)
        zoom_row.columnconfigure(0, weight=2, uniform="zoom")
        zoom_row.columnconfigure(1, weight=2, uniform="zoom")
        zoom_row.columnconfigure(2, weight=3, uniform="zoom")
        zoom_row.columnconfigure(3, weight=8)
        self.btn_zoom_in = ttk.Button(zoom_row, text="+", width=2, command=lambda: self._zoom_by(1.2))
        self.btn_zoom_out = ttk.Button(zoom_row, text="−", width=2, command=lambda: self._zoom_by(1 / 1.2))
        self.btn_zoom_100 = ttk.Button(zoom_row, text="100%", width=4, command=lambda: self._set_zoom(1.0))
        self.btn_zoom_in.grid(row=0, column=0, sticky="ew", padx=(0, 2))
        self.btn_zoom_out.grid(row=0, column=1, sticky="ew", padx=1)
        self.btn_zoom_100.grid(row=0, column=2, sticky="ew", padx=(2, 0))
        ttk.Frame(zoom_row).grid(row=0, column=3, sticky="ew")

        # Canvas with scrollbars
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#f3f3f3", highlightthickness=0)
        self.vbar = ttk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.hbar = ttk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<Configure>", lambda e: self._update_scrollregion())

        # Right attribute panel (initially visible)
        self.attr_visible = True
        attr_header = ttk.Frame(self.right_frame)
        attr_header.pack(fill=tk.X, padx=4, pady=4)
        ttk.Label(attr_header, text="Attribute", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
        self.btn_hide_attr = ttk.Button(attr_header, text="»", width=2, command=self.toggle_sidebar)
        self.btn_hide_attr.pack(side=tk.RIGHT)
        self.attr_restore = ttk.Frame(self.root, width=28)
        self.btn_show_attr = ttk.Button(self.attr_restore, text="«", width=2, command=self.toggle_sidebar)
        self.btn_show_attr.pack(side=tk.TOP, padx=2, pady=6)
        self.attr_container = ttk.Frame(self.right_frame)
        self.attr_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        ttk.Label(self.attr_container, text="Typ:").grid(row=0, column=0, sticky="w")
        self.attr_type_var = tk.StringVar(value="")
        self.attr_type_label = ttk.Label(self.attr_container, textvariable=self.attr_type_var)
        self.attr_type_label.grid(row=0, column=1, sticky="w")

        ttk.Label(self.attr_container, text="Name:").grid(row=1, column=0, sticky="w")
        self.attr_name_var = tk.StringVar()
        self.attr_name_entry = ttk.Entry(self.attr_container, textvariable=self.attr_name_var)
        self.attr_name_entry.grid(row=1, column=1, sticky="ew")
        self.attr_name_entry.bind("<Return>", lambda e: self._on_name_changed() or "break")
        self.attr_name_entry.bind("<FocusOut>", lambda e: self._on_name_changed())

        ttk.Label(self.attr_container, text="Farbe:").grid(row=2, column=0, sticky="w")
        self.attr_color_row = ttk.Frame(self.attr_container)
        self.attr_color_row.grid(row=2, column=1, sticky="ew")
        self.attr_color_preview = tk.Canvas(
            self.attr_color_row, width=28, height=18, highlightthickness=1,
            highlightbackground="#888888", bg="#000000"
        )
        self.attr_color_preview.pack(side=tk.LEFT)
        self.attr_color_preview.bind("<Button-1>", lambda e: self._on_color_pick())
        self.attr_color_btn = ttk.Button(self.attr_color_row, text="Wählen…", command=self._on_color_pick)
        self.attr_color_btn.pack(side=tk.LEFT, padx=(6, 0), fill=tk.X, expand=True)

        self.attr_edge_label = ttk.Label(self.attr_container, text="Kante:")
        self.attr_edge_label.grid(row=3, column=0, sticky="w")
        self.attr_edge_var = tk.StringVar(value="ausgezogen")
        self.attr_edge_combo = ttk.Combobox(
            self.attr_container, textvariable=self.attr_edge_var,
            values=("ausgezogen", "gestrichelt"), state="readonly", width=12
        )
        self.attr_edge_combo.grid(row=3, column=1, sticky="ew")
        self.attr_edge_combo.bind("<<ComboboxSelected>>", lambda e: self._on_edge_changed())

        self.attr_side_label = ttk.Label(self.attr_container, text="Seite:")
        self.attr_side_label.grid(row=4, column=0, sticky="w")
        self.attr_side_var = tk.StringVar(value="rechts")
        self.attr_side_combo = ttk.Combobox(
            self.attr_container, textvariable=self.attr_side_var,
            values=("rechts", "links", "oben", "unten"), state="readonly", width=12
        )
        self.attr_side_combo.grid(row=4, column=1, sticky="ew")
        self.attr_side_combo.bind("<<ComboboxSelected>>", lambda e: self._on_side_changed())

        ttk.Label(self.attr_container, text="Abstand:").grid(row=5, column=0, sticky="w")
        self.attr_offset_var = tk.StringVar()
        self.attr_offset_spin = ttk.Spinbox(
            self.attr_container, from_=-200, to=200, increment=2,
            textvariable=self.attr_offset_var, command=self._on_offset_changed
        )
        self.attr_offset_spin.grid(row=5, column=1, sticky="ew")
        self.attr_offset_spin.bind("<Return>", lambda e: self._on_offset_changed())
        self.attr_offset_spin.bind("<FocusOut>", lambda e: self._on_offset_changed())

        self.attr_arrow_label = ttk.Label(self.attr_container, text="Pfeilspitze:")
        self.attr_arrow_label.grid(row=6, column=0, sticky="w")
        self.attr_arrow_var = tk.StringVar(value="Ende")
        self.attr_arrow_combo = ttk.Combobox(
            self.attr_container, textvariable=self.attr_arrow_var,
            values=("Ende", "Anfang"), state="readonly", width=12
        )
        self.attr_arrow_combo.grid(row=6, column=1, sticky="ew")
        self.attr_arrow_combo.bind("<<ComboboxSelected>>", lambda e: self._on_arrow_changed())

        for i in range(2):
            self.attr_container.grid_columnconfigure(i, weight=1)

        self.attr_name_entry.state(["disabled"])
        self.attr_color_btn.state(["disabled"])
        self.attr_offset_spin.state(["disabled"])
        self.attr_arrow_combo.state(["disabled"])
        self.attr_edge_combo.state(["disabled"])
        self.attr_arrow_label.grid_remove()
        self.attr_arrow_combo.grid_remove()
        self.attr_edge_label.grid_remove()
        self.attr_edge_combo.grid_remove()
        self.attr_side_combo.state(["disabled"])
        self.attr_side_label.grid_remove()
        self.attr_side_combo.grid_remove()

        # Set initial mode look
        self.update_mode_buttons()

    # ---------------------------
    # Eventbindung
    # ---------------------------

    def _bind_events(self):
        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_canvas_button_press)
        c.bind("<B1-Motion>", self.on_canvas_move)
        c.bind("<ButtonRelease-1>", self.on_canvas_release)
        c.bind("<Button-3>", self.on_right_click)
        c.bind("<MouseWheel>", self._on_mousewheel)
        c.bind("<Shift-MouseWheel>", self._on_shift_mousewheel)
        c.bind("<Enter>", lambda e: c.focus_set())
        self.root.bind("<Delete>", lambda e: self.delete_selected())
        self.root.bind("<Escape>", lambda e: self.set_mode("select"))
        self.root.bind("<Control-plus>", lambda e: self._zoom_by(1.2) or "break")
        self.root.bind("<Control-equal>", lambda e: self._zoom_by(1.2) or "break")
        self.root.bind("<Control-minus>", lambda e: self._zoom_by(1 / 1.2) or "break")
        self.root.bind("<Control-0>", lambda e: self._set_zoom(1.0) or "break")
        self.root.bind("<Control-KP_Add>", lambda e: self._zoom_by(1.2) or "break")
        self.root.bind("<Control-KP_Subtract>", lambda e: self._zoom_by(1 / 1.2) or "break")
        self.root.bind("<Control-z>", self.undo)
        self.root.bind("<Control-Z>", self.undo)
        self.root.bind("<Control-y>", self.redo)
        self.root.bind("<Control-Y>", self.redo)
        self.root.bind("<Control-Shift-Z>", self.redo)
        self.root.bind("<Control-Shift-z>", self.redo)

    def _diagram_data(self):
        return {
            "blocks": [r.to_dict() for r in self.rects.values()],
            "verbindungen": [l.to_dict() for l in self.lines.values()],
        }

    def _apply_diagram_data(self, data):
        self._clear_all()
        for rd in data.get("blocks", data.get("rects", [])):
            r = RectObj.from_dict(self, rd)
            self.rects[r.id] = r
            r.draw()
        for ld in data.get("verbindungen", data.get("lines", [])):
            kind = ld.get("target_kind", "block")
            if ld.get("source") not in self.rects:
                continue
            if kind == "iface" and ld.get("target") not in self.ifaces:
                continue
            if kind != "iface" and ld.get("target") not in self.rects:
                continue
            l = LineObj.from_dict(self, ld)
            self.lines[l.id] = l
            l.draw()
        self._update_scrollregion()

    def _push_history(self):
        if self._history_restoring:
            return
        encoded = json.dumps(self._diagram_data(), sort_keys=True, ensure_ascii=False)
        if 0 <= self._history_index < len(self._history) and self._history[self._history_index] == encoded:
            return
        self._history = self._history[: self._history_index + 1]
        self._history.append(encoded)
        if len(self._history) > self._history_limit:
            overflow = len(self._history) - self._history_limit
            self._history = self._history[overflow:]
            self._history_index = len(self._history) - 1
        else:
            self._history_index += 1

    def _reset_history(self):
        self._history = []
        self._history_index = -1
        self._push_history()

    def _focus_in_attr_field(self):
        w = self.root.focus_get()
        if w is None:
            return False
        return w.winfo_class() in ("Entry", "TEntry", "TCombobox", "TSpinbox", "Spinbox")

    def undo(self, event=None):
        if self._focus_in_attr_field():
            return
        if self._history_index <= 0:
            return "break"
        self._history_index -= 1
        self._history_restoring = True
        try:
            self._apply_diagram_data(json.loads(self._history[self._history_index]))
        finally:
            self._history_restoring = False
        return "break"

    def redo(self, event=None):
        if self._focus_in_attr_field():
            return
        if self._history_index >= len(self._history) - 1:
            return "break"
        self._history_index += 1
        self._history_restoring = True
        try:
            self._apply_diagram_data(json.loads(self._history[self._history_index]))
        finally:
            self._history_restoring = False
        return "break"

    # ---------------------------
    # Mode Management
    # ---------------------------

    def toggle_mode(self, mode):
        if self.mode == mode:
            self.set_mode("select")
        else:
            self.set_mode(mode)

    def set_mode(self, mode):
        self._cancel_line_drag()
        self.mode = mode
        self.line_first_rect = None
        self.update_mode_buttons()
        self.canvas.config(cursor="arrow")
        if mode == "draw_block":
            self.canvas.config(cursor="crosshair")
        elif mode == "draw_verbindung":
            self.canvas.config(cursor="tcross")

    def update_mode_buttons(self):
        for btn, m in ((self.btn_draw_rect, "draw_block"), (self.btn_draw_line, "draw_verbindung")):
            if self.mode == m:
                btn.state(["pressed"])
            else:
                try:
                    btn.state(["!pressed"])
                except Exception:
                    pass
    
    # ---------------------------
    # Canvas Event Handler
    # ---------------------------
    def _canvas_xy(self, event):
        z = self.zoom or 1.0
        return (self.canvas.canvasx(event.x) / z, self.canvas.canvasy(event.y) / z)

    def _redraw_all(self):
        for r in self.rects.values():
            r.draw()
        for l in self.lines.values():
            l.draw()
        if self.current_draw_rect:
            self.current_draw_rect.draw()
        self._update_scrollregion()

    def _set_zoom(self, zoom, screen_x=None, screen_y=None):
        zoom = max(self.zoom_min, min(self.zoom_max, zoom))
        if screen_x is None:
            screen_x = self.canvas.winfo_width() / 2
            screen_y = self.canvas.winfo_height() / 2
        old = self.zoom or 1.0
        wx = self.canvas.canvasx(screen_x) / old
        wy = self.canvas.canvasy(screen_y) / old
        self.zoom = zoom
        self._redraw_all()
        self.canvas.update_idletasks()
        sr = self.canvas.cget("scrollregion")
        if not sr:
            return
        x1, y1, x2, y2 = [float(v) for v in str(sr).split()]
        w, h = x2 - x1, y2 - y1
        if w > 0:
            self.canvas.xview_moveto(((wx * zoom) - screen_x - x1) / w)
        if h > 0:
            self.canvas.yview_moveto(((wy * zoom) - screen_y - y1) / h)

    def _zoom_by(self, factor, screen_x=None, screen_y=None):
        self._set_zoom(self.zoom * factor, screen_x, screen_y)

    def zoom_fit(self):
        boxes = [r.bbox for r in self.rects.values()]
        for iface in self.ifaces.values():
            boxes.append(iface.bbox())
        for l in self.lines.values():
            pts = l.polyline_points()
            if pts:
                boxes.append(points_bbox(pts))
        if not boxes:
            self._set_zoom(1.0)
            return
        x1 = min(b[0] for b in boxes)
        y1 = min(b[1] for b in boxes)
        x2 = max(b[2] for b in boxes)
        y2 = max(b[3] for b in boxes)
        ww, hh = max(x2 - x1, 1), max(y2 - y1, 1)
        cw = max(self.canvas.winfo_width() - 40, 50)
        ch = max(self.canvas.winfo_height() - 40, 50)
        z = min(cw / ww, ch / hh, self.zoom_max)
        self._set_zoom(max(self.zoom_min, z))

    def _update_scrollregion(self):
        pad = 48
        bbox = self.canvas.bbox("all")
        cw = max(int(self.canvas.winfo_width()), 1)
        ch = max(int(self.canvas.winfo_height()), 1)
        if bbox:
            x1, y1, x2, y2 = bbox
            x1 = min(0, x1 - pad)
            y1 = min(0, y1 - pad)
            x2 = max(cw, x2 + pad)
            y2 = max(ch, y2 + pad)
        else:
            x1, y1, x2, y2 = 0, 0, cw, ch
        self.canvas.configure(scrollregion=(x1, y1, x2, y2))

    def _on_mousewheel(self, event):
        if event.state & 0x0004:
            self._zoom_by(1.1 if event.delta > 0 else 1 / 1.1, event.x, event.y)
            return "break"
        self.canvas.yview_scroll(int(-event.delta / 120), "units")
        return "break"

    def _on_shift_mousewheel(self, event):
        self.canvas.xview_scroll(int(-event.delta / 120), "units")
        return "break"

    def on_canvas_button_press(self, event):
        x, y = self._canvas_xy(event)
        self.drag_start = (x, y)

        clicked = self.canvas.find_withtag(tk.CURRENT)
        tag_info = self.canvas.gettags(clicked[-1]) if clicked else ()

        if self.mode == "draw_verbindung":
            if self._begin_select_hit(tag_info, x, y, include_rects=False):
                return
            source_id = self.rect_at(x, y)
            if source_id:
                self._start_line_drag(source_id, x, y)
                return
            self.select_object(None)
            return

        if self.mode == "draw_block":
            self.current_draw_rect = RectObj(self, (x, y, x, y), name="")
            self.current_draw_rect.draw()
            self.dragging = True
            self.drag_rect_id = self.current_draw_rect.id
            return

        if not self._begin_select_hit(tag_info, x, y, include_rects=True):
            self._start_marquee(x, y)

    def _begin_select_hit(self, tag_info, x, y, include_rects=True):
        """Wählt ein vorhandenes Objekt unter der Maus und startet ggf. das Ziehen."""
        name_key = self._name_key_from_tags(tag_info)
        if not name_key:
            name_key = self.name_at(x, y)
        if name_key:
            return self._start_name_drag(name_key, x, y)

        if tag_info and "parrow" in tag_info and "parrow_text" not in tag_info:
            tags = [t for t in tag_info if t not in ("current", "parrow", "parrow_text")]
            if len(tags) >= 2:
                lid, aid = tags[0], tags[1]
                if lid in self.lines and self.lines[lid].get_parallel(aid):
                    key = ("parrow", lid, aid)
                    if key not in self.selection:
                        self.select_object(key)
                    if len(self.selection) > 1:
                        self.start_selection_drag(x, y)
                    else:
                        self.dragging = True
                        self.drag_parrow = (lid, aid)
                    return True

        if tag_info and "line_handle" in tag_info:
            lid = next((t for t in tag_info if t in self.lines), None)
            if lid:
                self.select_object(("verbindung", lid))
                self.dragging = True
                self.drag_line_id = lid
                return True

        if tag_info and "iface" in tag_info and "iface_text" not in tag_info:
            iid = next((t for t in tag_info if t in self.ifaces), None)
            if iid:
                key = ("iface", iid)
                if key not in self.selection:
                    self.select_object(key)
                self.dragging = True
                self.drag_iface_id = iid
                return True

        if tag_info and "handle" in tag_info and "line_handle" not in tag_info:
            relevant_tags = [
                t for t in tag_info
                if t in self.rects or t == "handle" or t in ["nw", "ne", "sw", "se"]
            ]
            if "handle" in relevant_tags:
                try:
                    handle_index = relevant_tags.index("handle")
                    corner = relevant_tags[handle_index + 2] if handle_index + 1 < len(relevant_tags) else None
                    rid = next((t for t in relevant_tags if t in self.rects), None)
                    if rid and corner:
                        self.start_resizing(rid, corner, x, y)
                        return True
                except Exception as e:
                    print("Fehler beim Handle-Resizing:", e)

        if include_rects:
            iid = self.iface_at(x, y)
            if iid:
                key = ("iface", iid)
                if key not in self.selection:
                    self.select_object(key)
                self.dragging = True
                self.drag_iface_id = iid
                return True

        hit_parrow = self.parrow_at(x, y)
        if hit_parrow:
            lid, aid = hit_parrow
            key = ("parrow", lid, aid)
            if key not in self.selection:
                self.select_object(key)
            if len(self.selection) > 1:
                self.start_selection_drag(x, y)
            else:
                self.dragging = True
                self.drag_parrow = (lid, aid)
            return True

        lid = self.verbindung_at(x, y)
        if not lid and tag_info and "verbindung" in tag_info and "verbindung_text" not in tag_info:
            lid = next((t for t in tag_info if t in self.lines), None)
        if lid:
            key = ("verbindung", lid)
            if key not in self.selection:
                self.select_object(key)
                self.dragging = True
                self.drag_line_id = lid
            elif len(self.selection) > 1:
                self.start_selection_drag(x, y)
            else:
                self.dragging = True
                self.drag_line_id = lid
            return True

        if include_rects:
            rid = self.rect_at(x, y)
            if rid:
                key = ("block", rid)
                if key not in self.selection:
                    self.select_object(key)
                self.start_dragging_rect(rid, x, y)
                return True
        return False

    def on_canvas_move(self, event):
        x,y = self._canvas_xy(event)
        if self.marquee_id:
            x0, y0 = self.marquee_start
            z = self.zoom
            self.canvas.coords(self.marquee_id, x0 * z, y0 * z, x * z, y * z)
            self.canvas.tag_raise(self.marquee_id)
            return
        if self.dragging and self.current_draw_rect:
            # update temporary rectangle
            self.current_draw_rect.bbox = rect_normalize((self.drag_start[0], self.drag_start[1], x, y))
            self.current_draw_rect.draw()
        elif self.dragging and self.drag_name_key:
            obj = self._labeled_object(self.drag_name_key)
            if obj:
                gx, gy = self.drag_name_grab
                ax, ay = obj.name_anchor()
                obj.name_offset = (x - gx - ax, y - gy - ay)
                self._redraw_labeled(self.drag_name_key)
        elif self.dragging and self.drag_iface_id:
            iface = self.ifaces.get(self.drag_iface_id)
            if iface:
                iface.place_at(x, y)
                iface.draw()
                self.update_all_lines_for(iface.block_id)
                self._set_side_field(iface.side, visible=True)
        elif self.line_drag_source:
            self._update_line_preview(x, y)
        elif self.dragging and self.drag_parrow:
            lid, aid = self.drag_parrow
            line = self.lines.get(lid)
            pa = line.get_parallel(aid) if line else None
            pts = line.polyline_points() if line else None
            if pa and pts:
                off = signed_offset_from_polyline(pts, x, y)
                if abs(off) < 6:
                    off = 6 if off >= 0 else -6
                pa.offset = round(off)
                self.attr_offset_var.set(str(int(pa.offset)))
                line.draw()
        elif self.dragging and self.drag_line_id:
            if abs(x - self.drag_start[0]) > 4 or abs(y - self.drag_start[1]) > 4:
                line = self.lines.get(self.drag_line_id)
                if line:
                    line.waypoint = (x, y)
                    line.draw()
        elif self.dragging and self.drag_rect_id:
            # dragging an existing rect (move) OR resizing depending on drag_handles_corner
            if self.drag_handles_corner:
                # resizing
                rid = self.drag_rect_id
                rect = self.rects.get(rid)
                if rect:
                    rect.resize_corner(self.drag_handles_corner, x, y)
                    self.update_all_lines_for(rect.id)
                    self._update_scrollregion()
            else:
                # moving: compute delta since last event
                dx = x - self.drag_last_pos[0]
                dy = y - self.drag_last_pos[1]
                rid = self.drag_rect_id
                if rid in self.rects:
                    self._move_group_by(dx, dy)
                self.drag_last_pos = (x,y)
        elif self.dragging and self.moving_selection:
            dx = x - self.drag_last_pos[0]
            dy = y - self.drag_last_pos[1]
            self._move_group_by(dx, dy)
            self.drag_last_pos = (x, y)

    def on_canvas_release(self, event):
        x,y = self._canvas_xy(event)
        if self.marquee_id:
            self._finish_marquee(x, y)
            self._update_scrollregion()
            return
        if self.line_drag_source:
            self._finish_line_drag(x, y)
            self._update_scrollregion()
            return
        if self.dragging and self.current_draw_rect:
            x1, y1, x2, y2 = self.current_draw_rect.bbox
            w, h = abs(x2 - x1), abs(y2 - y1)
            if w >= self.min_rect_size and h >= self.min_rect_size:
                rect = self.current_draw_rect
                if not rect.name:
                    rect.name = self.next_object_name("B")
                self.rects[rect.id] = rect
                rect.draw()
                self.set_mode("select")
                self.select_object(("block", rect.id))
                self._push_history()
            else:
                self.current_draw_rect.destroy_canvas()
                self.set_mode("select")
            self.current_draw_rect = None
            self.dragging = False
            self.drag_rect_id = None
        elif self.dragging:
            self.dragging = False
            self.drag_rect_id = None
            self.drag_handles_corner = None
            self.drag_line_id = None
            self.drag_parrow = None
            self.drag_iface_id = None
            self.drag_name_key = None
            self.moving_selection = False
            self.move_group_ids.clear()
            self._push_history()
        self._update_scrollregion()

    def on_right_click(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Block", command=lambda: self.toggle_mode("draw_block"))
        menu.add_command(label="Verbindung", command=lambda: self.toggle_mode("draw_verbindung"))
        menu.add_separator()
        menu.add_command(label="Grafik ins Clipboard", command=self.copy_canvas_to_clipboard)
        menu.post(event.x_root, event.y_root)

    # ---------------------------
    # Drag & Resize helpers
    # ---------------------------

    def rect_at(self, x, y):
        """Kleinster Block, der den Punkt enthält (bei Überlappung der innere)."""
        hits = []
        for rid, rect in self.rects.items():
            x1, y1, x2, y2 = rect.bbox
            if x1 <= x <= x2 and y1 <= y <= y2:
                hits.append(((x2 - x1) * (y2 - y1), rid))
        if not hits:
            return None
        hits.sort(key=lambda it: it[0])
        return hits[0][1]

    def _name_key_from_tags(self, tag_info):
        if not tag_info:
            return None
        if "block_text" in tag_info:
            rid = next((t for t in tag_info if t in self.rects), None)
            return ("block", rid) if rid else None
        if "verbindung_text" in tag_info:
            lid = next((t for t in tag_info if t in self.lines), None)
            return ("verbindung", lid) if lid else None
        if "parrow_text" in tag_info:
            tags = [t for t in tag_info if t not in ("current", "parrow", "parrow_text")]
            if len(tags) >= 2 and tags[0] in self.lines and self.lines[tags[0]].get_parallel(tags[1]):
                return ("parrow", tags[0], tags[1])
            return None
        if "iface_text" in tag_info:
            iid = next((t for t in tag_info if t in self.ifaces), None)
            return ("iface", iid) if iid else None
        return None

    def name_at(self, x, y):
        z = self.zoom
        cx, cy = x * z, y * z
        hits = []

        def consider(item, key):
            if not item:
                return
            bb = self.canvas.bbox(item)
            if not bb:
                return
            x1, y1, x2, y2 = bb
            if x1 - 2 <= cx <= x2 + 2 and y1 - 2 <= cy <= y2 + 2:
                hits.append(((x2 - x1) * (y2 - y1), key))

        for rid, rect in self.rects.items():
            consider(rect.canvas_text, ("block", rid))
        for lid, line in self.lines.items():
            consider(line.canvas_text, ("verbindung", lid))
            for pa in line.parallel_arrows:
                consider(pa.canvas_text, ("parrow", lid, pa.id))
        for iid, iface in self.ifaces.items():
            consider(iface.canvas_text, ("iface", iid))
        if not hits:
            return None
        hits.sort(key=lambda it: it[0])
        return hits[0][1]

    def _labeled_object(self, key):
        typ = key[0]
        if typ == "block":
            return self.rects.get(key[1])
        if typ == "verbindung":
            return self.lines.get(key[1])
        if typ == "iface":
            return self.ifaces.get(key[1])
        if typ == "parrow":
            line = self.lines.get(key[1])
            return line.get_parallel(key[2]) if line else None
        return None

    def _redraw_labeled(self, key):
        if key[0] == "parrow":
            line = self.lines.get(key[1])
            if line:
                line.draw()
            return
        obj = self._labeled_object(key)
        if obj:
            obj.draw()

    def _start_name_drag(self, key, x, y):
        obj = self._labeled_object(key)
        if not obj:
            return False
        self.select_object(key)
        self.dragging = True
        self.drag_name_key = key
        nx, ny = obj.name_pos()
        self.drag_name_grab = (x - nx, y - ny)
        return True

    def iface_at(self, x, y):
        hits = []
        for iid, iface in self.ifaces.items():
            if iface.contains_point(x, y):
                cx, cy = iface.circle_center()
                hits.append((math.hypot(x - cx, y - cy), iid))
        if not hits:
            return None
        hits.sort(key=lambda it: it[0])
        return hits[0][1]

    def verbindung_at(self, x, y, max_dist=6):
        """Nächste Verbindung in Reichweite, auch innerhalb eines Blocks."""
        hits = []
        for lid, line in self.lines.items():
            pts = line.polyline_points()
            if not pts:
                continue
            dist = polyline_distance(pts, x, y)
            if dist <= max_dist:
                hits.append((dist, lid))
        if not hits:
            return None
        hits.sort(key=lambda it: it[0])
        return hits[0][1]

    def parrow_at(self, x, y, max_dist=6):
        hits = []
        for lid, line in self.lines.items():
            for pa in line.parallel_arrows:
                pts = pa.geometry()
                if not pts:
                    continue
                dist = polyline_distance(pts, x, y)
                if dist <= max_dist:
                    hits.append((dist, lid, pa.id))
        if not hits:
            return None
        hits.sort(key=lambda it: it[0])
        return (hits[0][1], hits[0][2])

    def _start_line_drag(self, source_id, x, y):
        self.line_drag_source = source_id
        self.select_object(("block", source_id))
        src = self.rects[source_id]
        sx, sy = rect_center_coords(src.bbox)
        z = self.zoom
        pts = ((sx, sy), (x, y))
        self.line_preview_id = self.canvas.create_line(
            sx * z, sy * z, x * z, y * z, width=2, fill="#0077ff", dash=(6, 4), tags=("line_preview",)
        )
        self.line_preview_arrow_id = sync_open_arrow(
            self.canvas, None, pts, False, z, "#0077ff", 2, ("line_preview",)
        )
        self.canvas.tag_raise(self.line_preview_id)
        if self.line_preview_arrow_id:
            self.canvas.tag_raise(self.line_preview_arrow_id)

    def _update_line_preview(self, x, y):
        if not self.line_preview_id or not self.line_drag_source:
            return
        src = self.rects.get(self.line_drag_source)
        if not src:
            self._cancel_line_drag()
            return
        sx, sy = rect_center_coords(src.bbox)
        z = self.zoom
        self.canvas.coords(self.line_preview_id, sx * z, sy * z, x * z, y * z)
        self.line_preview_arrow_id = sync_open_arrow(
            self.canvas, self.line_preview_arrow_id, ((sx, sy), (x, y)), False, z, "#0077ff", 2, ("line_preview",)
        )
        self.canvas.tag_raise(self.line_preview_id)
        if self.line_preview_arrow_id:
            self.canvas.tag_raise(self.line_preview_arrow_id)

    def _cancel_line_drag(self):
        for item in (self.line_preview_id, self.line_preview_arrow_id):
            if item:
                try:
                    self.canvas.delete(item)
                except Exception:
                    pass
        self.line_preview_id = None
        self.line_preview_arrow_id = None
        self.line_drag_source = None

    def _finish_line_drag(self, x, y):
        source_id = self.line_drag_source
        iface_id = self.iface_at(x, y)
        target_id = self.rect_at(x, y)
        self._cancel_line_drag()
        if not source_id:
            return
        if iface_id:
            iface = self.ifaces.get(iface_id)
            if not iface or iface.block_id == source_id:
                return
            line = LineObj(self, source_id, iface_id, target_kind="iface")
        elif target_id and target_id != source_id:
            line = LineObj(self, source_id, target_id, target_kind="block")
        else:
            return
        self.lines[line.id] = line
        line.draw()
        self.set_mode("select")
        self.select_object(("verbindung", line.id))
        self._push_history()

    def start_dragging_rect(self, rect_id, x, y):
        self._cancel_line_drag()
        self.current_draw_rect = None
        self.dragging = True
        self.drag_rect_id = rect_id
        self.drag_handles_corner = None
        self.drag_line_id = None
        self.drag_parrow = None
        self.drag_iface_id = None
        self.drag_last_pos = (x, y)
        selected_rects = [k[1] for k in self.selection if k[0] == "block"]
        if len(self.selection) > 1 and rect_id in selected_rects:
            self.moving_selection = True
            self._build_multi_move_group(selected_rects)
        else:
            self.moving_selection = False
            rect = self.rects.get(rect_id)
            if rect:
                self._update_move_group(rect)

    def start_selection_drag(self, x, y):
        self._cancel_line_drag()
        self.dragging = True
        self.moving_selection = True
        self.drag_line_id = None
        self.drag_parrow = None
        self.drag_iface_id = None
        self.drag_handles_corner = None
        self.drag_last_pos = (x, y)
        selected_rects = [k[1] for k in self.selection if k[0] == "block"]
        self.drag_rect_id = selected_rects[0] if selected_rects else None
        self._build_multi_move_group(selected_rects)

    def _build_multi_move_group(self, rect_ids):
        group = set()
        for rid in rect_ids:
            r = self.rects.get(rid)
            if r:
                group |= self._contained_ids(r)
        self.move_group_ids = group

    def _contained_ids(self, rect):
        x1, y1, x2, y2 = rect.bbox
        found = {rect.id}
        for rid, other in self.rects.items():
            if rid == rect.id:
                continue
            ox1, oy1, ox2, oy2 = other.bbox
            if x1 <= ox1 and y1 <= oy1 and x2 >= ox2 and y2 >= oy2:
                found.add(rid)
        return found

    def _move_group_by(self, dx, dy):
        moved = set()
        for rid in list(self.move_group_ids):
            rect = self.rects.get(rid)
            if rect:
                rect.move_by(dx, dy)
                moved.add(rid)
        selected_lines = {k[1] for k in self.selection if k[0] == "verbindung"}
        for lid, line in self.lines.items():
            if not line.waypoint:
                continue
            tgt_block = line.target
            if line.target_kind == "iface":
                iface = self.ifaces.get(line.target)
                tgt_block = iface.block_id if iface else None
            both_ends = line.source in self.move_group_ids and tgt_block in self.move_group_ids
            if both_ends or lid in selected_lines:
                line.waypoint = (line.waypoint[0] + dx, line.waypoint[1] + dy)
        if moved:
            self.update_all_lines_for(moved)
        else:
            for lid in selected_lines:
                line = self.lines.get(lid)
                if line:
                    line.draw()
        self._update_scrollregion()

    def _start_marquee(self, x, y):
        self._cancel_line_drag()
        if self.marquee_id:
            try:
                self.canvas.delete(self.marquee_id)
            except Exception:
                pass
        self.marquee_start = (x, y)
        z = self.zoom
        self.marquee_id = self.canvas.create_rectangle(
            x * z, y * z, x * z, y * z, outline="#333333", dash=(6, 4), width=1, fill="", tags=("marquee",)
        )

    def _finish_marquee(self, x, y):
        x0, y0 = self.marquee_start
        if self.marquee_id:
            try:
                self.canvas.delete(self.marquee_id)
            except Exception:
                pass
        self.marquee_id = None
        if abs(x - x0) < 4 and abs(y - y0) < 4:
            self.select_object(None)
            return
        keys = self._objects_in_marquee(rect_normalize((x0, y0, x, y)))
        self.select_objects(keys)

    def _objects_in_marquee(self, box):
        keys = []
        for rid, rect in self.rects.items():
            if bbox_intersects(box, rect.bbox):
                keys.append(("block", rid))
        for lid, line in self.lines.items():
            pts = line.polyline_points()
            if pts and bbox_intersects(box, points_bbox(pts)):
                keys.append(("verbindung", lid))
            for pa in line.parallel_arrows:
                geom = pa.geometry()
                if geom and bbox_intersects(box, points_bbox(geom)):
                    keys.append(("parrow", line.id, pa.id))
        for iid, iface in self.ifaces.items():
            if bbox_intersects(box, iface.bbox()):
                keys.append(("iface", iid))
        return keys

    def start_resizing(self, rect_id, corner, x, y):
        self.dragging = True
        self.drag_rect_id = rect_id
        self.drag_handles_corner = corner
        self.drag_last_pos = (x,y)
        #self.resizing = True          
        #self.resizing_rect_id = rect_id
        #self.resizing_corner = corner
        #self.drag_start = (x, y)
        #self.select_object(("block", rect_id))

    def _update_move_group(self, rect):
        self.move_group_ids = self._contained_ids(rect)

    
    

    # ---------------------------
    # Selection / Attribute panel
    # ---------------------------

    def _clear_parallel_btn(self):
        if self.parallel_arrow_btn:
            try:
                self.parallel_arrow_btn.destroy()
            except Exception:
                pass
            self.parallel_arrow_btn = None
        if self.iface_btn:
            try:
                self.iface_btn.destroy()
            except Exception:
                pass
            self.iface_btn = None

    def _set_offset_field(self, value=None, enabled=False):
        self._syncing_attrs = True
        try:
            if value is None:
                self.attr_offset_var.set("")
            else:
                self.attr_offset_var.set(str(int(value)))
            if enabled:
                self.attr_offset_spin.state(["!disabled"])
            else:
                self.attr_offset_spin.state(["disabled"])
        finally:
            self._syncing_attrs = False

    def _set_edge_field(self, dashed=False, visible=False):
        self._syncing_attrs = True
        try:
            self.attr_edge_var.set("gestrichelt" if dashed else "ausgezogen")
            if visible:
                self.attr_edge_label.grid()
                self.attr_edge_combo.grid()
                self.attr_edge_combo.state(["!disabled", "readonly"])
            else:
                self.attr_edge_label.grid_remove()
                self.attr_edge_combo.grid_remove()
        finally:
            self._syncing_attrs = False

    def _set_side_field(self, side="e", visible=False):
        self._syncing_attrs = True
        try:
            self.attr_side_var.set(InterfaceObj.SIDE_LABELS.get(side, "rechts"))
            if visible:
                self.attr_side_label.grid()
                self.attr_side_combo.grid()
                self.attr_side_combo.state(["!disabled", "readonly"])
            else:
                self.attr_side_label.grid_remove()
                self.attr_side_combo.grid_remove()
        finally:
            self._syncing_attrs = False

    def _set_arrow_field(self, arrow_at_start=False, enabled=False, visible=None):
        if visible is None:
            visible = enabled
        self._syncing_attrs = True
        try:
            self.attr_arrow_var.set("Anfang" if arrow_at_start else "Ende")
            if visible:
                self.attr_arrow_label.grid()
                self.attr_arrow_combo.grid()
                if enabled:
                    self.attr_arrow_combo.state(["!disabled", "readonly"])
                else:
                    self.attr_arrow_combo.state(["disabled"])
            else:
                self.attr_arrow_label.grid_remove()
                self.attr_arrow_combo.grid_remove()
        finally:
            self._syncing_attrs = False

    def _set_key_selected(self, key, sel):
        typ = key[0]
        if typ == "block":
            r = self.rects.get(key[1])
            if r:
                r.set_selected(sel)
        elif typ == "verbindung":
            l = self.lines.get(key[1])
            if l:
                l.set_selected(sel)
        elif typ == "parrow":
            line = self.lines.get(key[1])
            pa = line.get_parallel(key[2]) if line else None
            if pa:
                pa.selected = sel
                line.draw()
        elif typ == "iface":
            iface = self.ifaces.get(key[1])
            if iface:
                iface.selected = sel
                iface.draw()

    def select_objects(self, keys):
        for old in self.selection:
            self._set_key_selected(old, False)
        self.selection = list(keys)
        self.selected_obj = self.selection[0] if len(self.selection) == 1 else None
        for key in self.selection:
            self._set_key_selected(key, True)
        self._refresh_attr_from_selection()

    def select_object(self, obj):
        if obj is None:
            self.select_objects([])
        else:
            self.select_objects([obj])

    def _set_type_field(self, text=""):
        self.attr_type_var.set(text)

    def _set_color_field(self, color="#000000", enabled=False):
        if enabled:
            fill = parse_color(color)
            self.attr_color_preview.configure(bg=fill)
            self.attr_color_btn.state(["!disabled"])
        else:
            self.attr_color_preview.configure(bg="#dddddd")
            self.attr_color_btn.state(["disabled"])

    def _on_color_pick(self):
        if getattr(self, "_syncing_attrs", False):
            return
        if not self.selected_obj:
            return
        obj = self._labeled_object(self.selected_obj)
        if not obj:
            return
        _rgb, chosen = colorchooser.askcolor(color=obj.color, title="Farbe", parent=self.root)
        if not chosen:
            return
        obj.color = parse_color(chosen)
        self._redraw_labeled(self.selected_obj)
        self._set_color_field(obj.color, enabled=True)
        self._push_history()

    def _set_name_field(self, value="", enabled=False):
        self._syncing_attrs = True
        try:
            self.attr_name_var.set(value)
            if enabled:
                self.attr_name_entry.state(["!disabled"])
            else:
                self.attr_name_entry.state(["disabled"])
        finally:
            self._syncing_attrs = False

    def _refresh_attr_from_selection(self):
        self._clear_parallel_btn()
        if len(self.selection) > 1:
            self._set_type_field("Mehrfachauswahl")
            self._set_name_field(enabled=False)
            self._set_color_field(enabled=False)
            self._set_offset_field(enabled=False)
            self._set_arrow_field(visible=False)
            self._set_edge_field(visible=False)
            self._set_side_field(visible=False)
            return
        obj = self.selected_obj
        if obj is None:
            self._set_type_field("")
            self._set_name_field(enabled=False)
            self._set_color_field(enabled=False)
            self._set_offset_field(enabled=False)
            self._set_arrow_field(visible=False)
            self._set_edge_field(visible=False)
            self._set_side_field(visible=False)
            return
        typ = obj[0]
        if typ == "block":
            oid = obj[1]
            r = self.rects.get(oid)
            if not r:
                return
            r.set_selected(True)
            self._set_type_field("Block")
            self._set_name_field(r.name, enabled=True)
            self._set_color_field(r.color, enabled=True)
            self._set_offset_field(enabled=False)
            self._set_arrow_field(visible=False)
            self._set_edge_field(r.dashed, visible=True)
            self._set_side_field(visible=False)
            self.iface_btn = ttk.Button(
                self.attr_container,
                text="Interface erstellen",
                command=self.create_interface
            )
            self.iface_btn.grid(row=7, column=0, columnspan=2, pady=(6, 6), sticky="ew")
        elif typ == "verbindung":
            oid = obj[1]
            l = self.lines.get(oid)
            if not l:
                return
            l.set_selected(True)
            self._set_type_field("Verbindung")
            self._set_name_field(l.name, enabled=True)
            self._set_color_field(l.color, enabled=True)
            self._set_offset_field(enabled=False)
            self._set_arrow_field(l.arrow_at_start, enabled=True, visible=True)
            self._set_edge_field(visible=False)
            self.parallel_arrow_btn = ttk.Button(
                self.attr_container,
                text="Datenfluss erstellen",
                command=self.create_parallel_arrow
            )
            self.parallel_arrow_btn.grid(row=7, column=0, columnspan=2, pady=(6, 6), sticky="ew")
            self._set_side_field(visible=False)
        elif typ == "parrow":
            _, lid, aid = obj
            l = self.lines.get(lid)
            pa = l.get_parallel(aid) if l else None
            if not l or not pa:
                return
            pa.selected = True
            l.draw()
            self._set_type_field("Datenfluss")
            self._set_name_field(pa.name, enabled=True)
            self._set_color_field(pa.color, enabled=True)
            self._set_offset_field(pa.offset, enabled=True)
            self._set_arrow_field(pa.arrow_at_start, enabled=True, visible=True)
            self._set_edge_field(visible=False)
            self._set_side_field(visible=False)
        elif typ == "iface":
            iface = self.ifaces.get(obj[1])
            if not iface:
                return
            iface.selected = True
            iface.draw()
            self._set_type_field("Interface")
            self._set_name_field(iface.name, enabled=True)
            self._set_color_field(iface.color, enabled=True)
            self._set_offset_field(enabled=False)
            self._set_arrow_field(visible=False)
            self._set_edge_field(visible=False)
            self._set_side_field(iface.side, visible=True)

    def _on_name_changed(self):
        if getattr(self, "_syncing_attrs", False):
            return
        if not self.selected_obj:
            return
        name = self.attr_name_var.get().strip()
        typ = self.selected_obj[0]
        if typ == "block":
            r = self.rects.get(self.selected_obj[1])
            if not r:
                return
            if not name:
                self._set_name_field(r.name, enabled=True)
                return
            r.name = name
            r.draw()
            self._push_history()
        elif typ == "verbindung":
            l = self.lines.get(self.selected_obj[1])
            if not l:
                return
            if not name:
                self._set_name_field(l.name, enabled=True)
                return
            l.name = name
            l.draw()
            self._push_history()
        elif typ == "parrow":
            _, lid, aid = self.selected_obj
            l = self.lines.get(lid)
            pa = l.get_parallel(aid) if l else None
            if not pa:
                return
            if not name:
                self._set_name_field(pa.name, enabled=True)
                return
            pa.name = name
            l.draw()
            self._push_history()
        elif typ == "iface":
            iface = self.ifaces.get(self.selected_obj[1])
            if not iface:
                return
            if not name:
                self._set_name_field(iface.name, enabled=True)
                return
            iface.name = name
            iface.draw()
            self._push_history()

    def _on_offset_changed(self):
        if getattr(self, "_syncing_attrs", False):
            return
        if not self.selected_obj or self.selected_obj[0] != "parrow":
            return
        _, lid, aid = self.selected_obj
        l = self.lines.get(lid)
        pa = l.get_parallel(aid) if l else None
        if not pa:
            return
        try:
            pa.offset = int(float(self.attr_offset_var.get()))
        except Exception:
            return
        if pa.offset == 0:
            pa.offset = 6
            self.attr_offset_var.set("6")
        l.draw()
        if not self.dragging:
            self._push_history()

    def _on_arrow_changed(self):
        if getattr(self, "_syncing_attrs", False):
            return
        if not self.selected_obj:
            return
        typ = self.selected_obj[0]
        at_start = self.attr_arrow_var.get() == "Anfang"
        if typ == "verbindung":
            line = self.lines.get(self.selected_obj[1])
            if not line:
                return
            line.arrow_at_start = at_start
            line.draw()
            self._push_history()
        elif typ == "parrow":
            _, lid, aid = self.selected_obj
            line = self.lines.get(lid)
            pa = line.get_parallel(aid) if line else None
            if not pa:
                return
            pa.arrow_at_start = at_start
            line.draw()
            self._push_history()

    def _on_edge_changed(self):
        if getattr(self, "_syncing_attrs", False):
            return
        if not self.selected_obj or self.selected_obj[0] != "block":
            return
        r = self.rects.get(self.selected_obj[1])
        if not r:
            return
        r.dashed = self.attr_edge_var.get() == "gestrichelt"
        r.draw()
        self._push_history()

    def _on_side_changed(self):
        if getattr(self, "_syncing_attrs", False):
            return
        if not self.selected_obj or self.selected_obj[0] != "iface":
            return
        iface = self.ifaces.get(self.selected_obj[1])
        if not iface:
            return
        side = InterfaceObj.LABEL_SIDES.get(self.attr_side_var.get())
        if not side:
            return
        iface.side = side
        iface.draw()
        self.update_all_lines_for(iface.block_id)
        self._push_history()

    def create_interface(self):
        if not self.selected_obj or self.selected_obj[0] != "block":
            return
        block = self.rects.get(self.selected_obj[1])
        if not block:
            return
        iface = block.add_interface()
        block.draw()
        self.select_object(("iface", iface.id))
        self._push_history()

    def create_parallel_arrow(self):
        """Datenfluss parallel zur ausgewählten Stammlinie anlegen."""
        if not self.selected_obj or self.selected_obj[0] != "verbindung":
            return
        lid = self.selected_obj[1]
        line = self.lines.get(lid)
        if not line or not line.polyline_points():
            return
        pa = line.add_parallel_arrow()
        line.draw()
        self.select_object(("parrow", line.id, pa.id))
        self._push_history()

    # ---------------------------
    # Lines / Updates
    # ---------------------------

    def update_all_lines_for(self, rect_id_or_iterable):
        # update any line connected to rect_id(s)
        if isinstance(rect_id_or_iterable, (set, list, tuple)):
            rect_ids = set(rect_id_or_iterable)
        else:
            rect_ids = {rect_id_or_iterable}
        for lid, line in self.lines.items():
            tgt_block = line.target
            if line.target_kind == "iface":
                iface = self.ifaces.get(line.target)
                tgt_block = iface.block_id if iface else None
            if line.source in rect_ids or tgt_block in rect_ids or line.target in rect_ids:
                line.draw()

    # ---------------------------
    # Delete, Save, Load
    # ---------------------------

    def delete_selected(self):
        if not self.selection:
            return
        if len(self.selection) > 1:
            n = len(self.selection)
            if not messagebox.askyesno("Löschen", f"{n} ausgewählte Objekte wirklich löschen?"):
                return
            keys = list(self.selection)
            for k in keys:
                if k[0] == "parrow":
                    line = self.lines.get(k[1])
                    if line:
                        line.remove_parallel(k[2])
            for k in keys:
                if k[0] == "verbindung" and k[1] in self.lines:
                    self._delete_line(k[1])
            for k in keys:
                if k[0] == "iface":
                    self._delete_iface(k[1])
            for k in keys:
                if k[0] == "block" and k[1] in self.rects:
                    self._delete_rect(k[1])
            self.select_object(None)
            self._push_history()
            return
        typ = self.selected_obj[0]
        if typ == "block":
            oid = self.selected_obj[1]
            if oid not in self.rects:
                return
            # delete rect and any lines connected to it
            # ask confirm
            if not messagebox.askyesno("Löschen", "Block und verbundene Verbindungen wirklich löschen?"):
                return
            self._delete_rect(oid)
            self.select_object(None)
            self._push_history()
        elif typ == "verbindung":
            oid = self.selected_obj[1]
            if oid not in self.lines:
                return
            if not messagebox.askyesno("Löschen", "Verbindung und zugehörige Datenflüsse wirklich löschen?"):
                return
            self._delete_line(oid)
            self.selected_obj = None
            self.select_object(None)
            self._push_history()
        elif typ == "parrow":
            _, lid, aid = self.selected_obj
            line = self.lines.get(lid)
            if not line:
                return
            if not messagebox.askyesno("Löschen", "Datenfluss wirklich löschen?"):
                return
            line.remove_parallel(aid)
            self.selected_obj = None
            self.select_object(("verbindung", lid))
            self._push_history()
        elif typ == "iface":
            iid = self.selected_obj[1]
            iface = self.ifaces.get(iid)
            if not iface:
                return
            if not messagebox.askyesno("Löschen", "Interface und verbundene Verbindungen wirklich löschen?"):
                return
            bid = iface.block_id
            self._delete_iface(iid)
            self.select_object(("block", bid) if bid in self.rects else None)
            self._push_history()

    def _delete_iface(self, iid):
        to_delete = [
            lid for lid, l in self.lines.items()
            if l.target_kind == "iface" and l.target == iid
        ]
        for lid in to_delete:
            self._delete_line(lid)
        iface = self.ifaces.get(iid)
        if iface:
            block = self.rects.get(iface.block_id)
            if block:
                block.remove_interface(iid)
            else:
                iface.destroy_canvas()
                self.ifaces.pop(iid, None)

    def _delete_rect(self, oid):
        iface_ids = [i.id for i in self.rects[oid].interfaces] if oid in self.rects else []
        for iid in iface_ids:
            self._delete_iface(iid)
        to_delete_lines = [
            lid for lid, l in self.lines.items()
            if l.source == oid or (l.target_kind == "block" and l.target == oid)
        ]
        for lid in to_delete_lines:
            self._delete_line(lid)
        r = self.rects.pop(oid, None)
        if r:
            r.destroy_canvas()

    def _delete_line(self, lid):
        l = self.lines.pop(lid, None)
        if not l:
            return
        l.destroy_canvas()

    def save_json(self):
        file = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json"), ("All files","*.*")])
        if not file:
            return
        data = self._diagram_data()
        try:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Gespeichert", f"In {file} gespeichert.")
        except Exception as e:
            messagebox.showerror("Fehler", f"Speichern fehlgeschlagen: {e}")

    def load_json(self):
        file = filedialog.askopenfilename(filetypes=[("JSON files","*.json"), ("All files","*.*")])
        if not file:
            return
        try:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Fehler", f"Laden fehlgeschlagen: {e}")
            return
        self._apply_diagram_data(data)
        self._reset_history()
        messagebox.showinfo("Geladen", f"Datei {file} geladen.")

    def _clear_all(self):
        # remove all canvas items and clear data
        self.canvas.delete("all")
        self.rects.clear()
        self.lines.clear()
        self.ifaces.clear()
        self.selection = []
        self.selected_obj = None
        self.marquee_id = None
        self._update_scrollregion()

    def copy_canvas_to_clipboard(self):
        """Ausgewählte Objekte als Bild in die Windows-Zwischenablage legen."""
        if sys.platform != "win32":
            messagebox.showerror("Zwischenablage", "Das Kopieren als Bild ist derzeit nur unter Windows verfügbar.")
            return
        if not self.selection:
            messagebox.showinfo("Als Bild kopieren", "Bitte zuerst Objekte mit der Maus auswählen.")
            return
        try:
            self._copy_selection_bitmap_windows()
        except Exception as e:
            messagebox.showerror("Zwischenablage", f"Kopieren fehlgeschlagen: {e}")

    def _clipboard_export_set(self):
        rect_ids = set()
        line_ids = set()
        parrow_ids = set()
        iface_ids = set()
        for key in self.selection:
            if key[0] == "block" and key[1] in self.rects:
                rect_ids.add(key[1])
            elif key[0] == "verbindung" and key[1] in self.lines:
                line_ids.add(key[1])
            elif key[0] == "parrow":
                parrow_ids.add((key[1], key[2]))
            elif key[0] == "iface" and key[1] in self.ifaces:
                iface_ids.add(key[1])
        extra = set()
        for rid in list(rect_ids):
            r = self.rects.get(rid)
            if r:
                extra |= self._contained_ids(r)
        rect_ids |= extra
        for rid in rect_ids:
            r = self.rects.get(rid)
            if r:
                for iface in r.interfaces:
                    iface_ids.add(iface.id)
        return rect_ids, line_ids, parrow_ids, iface_ids

    def _clipboard_export_bbox(self, rect_ids, line_ids, parrow_ids, iface_ids):
        boxes = []
        for rid in rect_ids:
            boxes.append(self.rects[rid].bbox)
        for iid in iface_ids:
            iface = self.ifaces.get(iid)
            if iface:
                boxes.append(iface.bbox())
        for lid in line_ids:
            pts = self.lines[lid].polyline_points()
            if pts:
                boxes.append(points_bbox(pts))
            for pa in self.lines[lid].parallel_arrows:
                geom = pa.geometry()
                if geom:
                    boxes.append(points_bbox(geom))
        for lid, aid in parrow_ids:
            line = self.lines.get(lid)
            pa = line.get_parallel(aid) if line else None
            geom = pa.geometry() if pa else None
            if geom:
                boxes.append(points_bbox(geom))
        if not boxes:
            return None
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )

    def _copy_selection_bitmap_windows(self):
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        kernel32 = ctypes.windll.kernel32

        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", ctypes.c_uint32),
                ("biWidth", ctypes.c_int32),
                ("biHeight", ctypes.c_int32),
                ("biPlanes", ctypes.c_uint16),
                ("biBitCount", ctypes.c_uint16),
                ("biCompression", ctypes.c_uint32),
                ("biSizeImage", ctypes.c_uint32),
                ("biXPelsPerMeter", ctypes.c_int32),
                ("biYPelsPerMeter", ctypes.c_int32),
                ("biClrUsed", ctypes.c_uint32),
                ("biClrImportant", ctypes.c_uint32),
            ]

        gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
        gdi32.CreateCompatibleDC.restype = wintypes.HDC
        gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
        gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
        gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
        gdi32.SelectObject.restype = wintypes.HGDIOBJ
        gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
        gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
        gdi32.CreatePen.argtypes = [ctypes.c_int, ctypes.c_int, wintypes.COLORREF]
        gdi32.CreatePen.restype = wintypes.HPEN
        gdi32.Rectangle.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        gdi32.Ellipse.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        gdi32.Polyline.argtypes = [wintypes.HDC, ctypes.c_void_p, ctypes.c_int]
        gdi32.Polygon.argtypes = [wintypes.HDC, ctypes.c_void_p, ctypes.c_int]
        gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
        gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
        gdi32.SetTextAlign.argtypes = [wintypes.HDC, ctypes.c_uint]
        gdi32.TextOutW.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.LPCWSTR, ctypes.c_int]
        gdi32.CreateFontW.restype = wintypes.HFONT
        gdi32.GetDIBits.argtypes = [
            wintypes.HDC, wintypes.HBITMAP, ctypes.c_uint, ctypes.c_uint,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint
        ]
        gdi32.DeleteDC.argtypes = [wintypes.HDC]
        gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
        gdi32.GetStockObject.argtypes = [ctypes.c_int]
        gdi32.GetStockObject.restype = wintypes.HGDIOBJ
        user32.GetDC.argtypes = [wintypes.HWND]
        user32.GetDC.restype = wintypes.HDC
        user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        user32.OpenClipboard.argtypes = [wintypes.HWND]
        user32.OpenClipboard.restype = wintypes.BOOL
        user32.EmptyClipboard.restype = wintypes.BOOL
        user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
        user32.SetClipboardData.restype = wintypes.HANDLE
        user32.CloseClipboard.restype = wintypes.BOOL
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = wintypes.HANDLE
        kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
        kernel32.GlobalFree.argtypes = [wintypes.HANDLE]

        rect_ids, line_ids, parrow_ids, iface_ids = self._clipboard_export_set()
        box = self._clipboard_export_bbox(rect_ids, line_ids, parrow_ids, iface_ids)
        if not box:
            raise RuntimeError("Keine Zeichenobjekte in der Auswahl.")

        pad = 16
        origin_x, origin_y = box[0] - pad, box[1] - pad
        width = max(1, int(math.ceil(box[2] - box[0] + 2 * pad)))
        height = max(1, int(math.ceil(box[3] - box[1] + 2 * pad)))

        def mx(x):
            return int(round(x - origin_x))

        def my(y):
            return int(round(y - origin_y))

        def col(r, g, b):
            return r | (g << 8) | (b << 16)

        def draw_poly(hdc, points, closed=False):
            n = len(points)
            arr = (POINT * n)(*[POINT(mx(p[0]), my(p[1])) for p in points])
            if closed:
                gdi32.Polygon(hdc, ctypes.byref(arr), n)
            else:
                gdi32.Polyline(hdc, ctypes.byref(arr), n)

        def draw_arrow_head(hdc, p_from, p_to, size=11):
            pts = open_arrow_points(p_from, p_to, size=size)
            if pts:
                draw_poly(hdc, pts, closed=False)

        PS_SOLID = 0
        PS_DASH = 1
        NULL_BRUSH = 5
        TRANSPARENT = 1
        TA_CENTER = 6
        TA_TOP = 0
        CF_DIB = 8
        GMEM_MOVEABLE = 0x0002

        hdc_screen = user32.GetDC(None)
        hdc = gdi32.CreateCompatibleDC(hdc_screen)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_screen, width, height)
        if not hdc or not hbmp:
            if hdc:
                gdi32.DeleteDC(hdc)
            if hbmp:
                gdi32.DeleteObject(hbmp)
            user32.ReleaseDC(None, hdc_screen)
            raise RuntimeError("Bitmap konnte nicht erzeugt werden.")
        old_bmp = gdi32.SelectObject(hdc, hbmp)

        white_br = gdi32.CreateSolidBrush(col(255, 255, 255))
        white_pen = gdi32.CreatePen(PS_SOLID, 1, col(255, 255, 255))
        black_pen = gdi32.CreatePen(PS_SOLID, 2, col(0, 0, 0))
        dash_pen = gdi32.CreatePen(PS_DASH, 1, col(0, 0, 0))
        gray_pen = gdi32.CreatePen(PS_SOLID, 2, col(85, 85, 85))
        black_br = gdi32.CreateSolidBrush(col(0, 0, 0))
        gray_br = gdi32.CreateSolidBrush(col(85, 85, 85))
        font = gdi32.CreateFontW(-14, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 0, 0, "Segoe UI")
        old_font = gdi32.SelectObject(hdc, font)
        old_pen = gdi32.SelectObject(hdc, white_pen)
        old_br = gdi32.SelectObject(hdc, white_br)
        gdi32.SetBkMode(hdc, TRANSPARENT)
        gdi32.SetTextColor(hdc, col(0, 0, 0))
        gdi32.SetTextAlign(hdc, TA_CENTER | TA_TOP)
        gdi32.Rectangle(hdc, 0, 0, width, height)

        extra_pens = []

        def stroke_pen(hex_color, dashed=False):
            r, g, b = hex_to_rgb(hex_color)
            cref = col(r, g, b)
            pen = gdi32.CreatePen(PS_DASH if dashed else PS_SOLID, 1 if dashed else 2, cref)
            extra_pens.append(pen)
            gdi32.SelectObject(hdc, pen)
            gdi32.SetTextColor(hdc, cref)
            return cref

        null_br = gdi32.GetStockObject(NULL_BRUSH)
        gdi32.SelectObject(hdc, null_br)
        for rid in rect_ids:
            r = self.rects[rid]
            x1, y1, x2, y2 = r.bbox
            stroke_pen(r.color, r.dashed)
            gdi32.Rectangle(hdc, mx(x1), my(y1), mx(x2) + 1, my(y2) + 1)
            name = r.name or ""
            if name:
                gdi32.TextOutW(hdc, mx((x1 + x2) / 2), my(y1) + 4, name, len(name))

        gdi32.SelectObject(hdc, null_br)
        for iid in iface_ids:
            iface = self.ifaces.get(iid)
            if not iface:
                continue
            ax, ay = iface.attach_point()
            sx, sy = iface.stem_end()
            cx, cy = iface.circle_center()
            rad = iface.RADIUS
            stroke_pen(iface.color)
            draw_poly(hdc, ((ax, ay), (sx, sy)), closed=False)
            gdi32.Ellipse(hdc, mx(cx - rad), my(cy - rad), mx(cx + rad) + 1, my(cy + rad) + 1)
            name = iface.name or ""
            if name:
                gdi32.TextOutW(hdc, mx(cx), my(cy - rad) - 16, name, len(name))

        def paint_polyline(points, pen, brush, text, text_color, arrow_at_start=False):
            if not points or len(points) < 2:
                return
            gdi32.SelectObject(hdc, pen)
            draw_poly(hdc, points, closed=False)
            if arrow_at_start:
                draw_arrow_head(hdc, points[1], points[0])
            else:
                draw_arrow_head(hdc, points[-2], points[-1])
            if text:
                gdi32.SetTextColor(hdc, text_color)
                if len(points) >= 3:
                    tx, ty = points[1]
                else:
                    tx = (points[0][0] + points[-1][0]) / 2
                    ty = (points[0][1] + points[-1][1]) / 2
                gdi32.TextOutW(hdc, mx(tx), my(ty) - 14, text, len(text))
                gdi32.SetTextColor(hdc, col(0, 0, 0))

        for lid in line_ids:
            line = self.lines[lid]
            r, g, b = hex_to_rgb(line.color)
            cref = col(r, g, b)
            lpen = gdi32.CreatePen(PS_SOLID, 2, cref)
            extra_pens.append(lpen)
            paint_polyline(
                line.polyline_points(), lpen, black_br, line.name, cref,
                arrow_at_start=line.arrow_at_start,
            )
            for pa in line.parallel_arrows:
                pr, pg, pb = hex_to_rgb(pa.color)
                pcref = col(pr, pg, pb)
                ppen = gdi32.CreatePen(PS_SOLID, 2, pcref)
                extra_pens.append(ppen)
                paint_polyline(
                    pa.geometry(), ppen, gray_br, pa.name, pcref,
                    arrow_at_start=pa.arrow_at_start,
                )
        for lid, aid in parrow_ids:
            if lid in line_ids:
                continue
            line = self.lines.get(lid)
            pa = line.get_parallel(aid) if line else None
            if pa:
                pr, pg, pb = hex_to_rgb(pa.color)
                pcref = col(pr, pg, pb)
                ppen = gdi32.CreatePen(PS_SOLID, 2, pcref)
                extra_pens.append(ppen)
                paint_polyline(
                    pa.geometry(), ppen, gray_br, pa.name, pcref,
                    arrow_at_start=pa.arrow_at_start,
                )

        header = BITMAPINFOHEADER()
        header.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        header.biWidth = width
        header.biHeight = height
        header.biPlanes = 1
        header.biBitCount = 32
        header.biCompression = 0
        stride = ((width * 32 + 31) // 32) * 4
        buf = (ctypes.c_byte * (stride * height))()
        got = gdi32.GetDIBits(hdc, hbmp, 0, height, buf, ctypes.byref(header), 0)

        gdi32.SelectObject(hdc, old_pen)
        gdi32.SelectObject(hdc, old_br)
        gdi32.SelectObject(hdc, old_font)
        gdi32.SelectObject(hdc, old_bmp)
        for obj in (white_br, white_pen, black_pen, dash_pen, gray_pen, black_br, gray_br, font, *extra_pens):
            gdi32.DeleteObject(obj)
        gdi32.DeleteDC(hdc)
        gdi32.DeleteObject(hbmp)
        user32.ReleaseDC(None, hdc_screen)
        if not got:
            raise RuntimeError("Pixeldaten konnten nicht gelesen werden.")

        dib = bytes(header) + bytes(buf)
        hglob = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(dib))
        if not hglob:
            raise RuntimeError("Speicher für Zwischenablage fehlt.")
        ptr = kernel32.GlobalLock(hglob)
        ctypes.memmove(ptr, dib, len(dib))
        kernel32.GlobalUnlock(hglob)
        if not user32.OpenClipboard(wintypes.HWND(int(self.root.winfo_id()))):
            kernel32.GlobalFree(hglob)
            raise RuntimeError("Zwischenablage ist belegt.")
        try:
            user32.EmptyClipboard()
            if not user32.SetClipboardData(CF_DIB, hglob):
                kernel32.GlobalFree(hglob)
                raise RuntimeError("SetClipboardData fehlgeschlagen.")
        finally:
            user32.CloseClipboard()

    def toggle_sidebar(self):
        if self.attr_visible:
            self.right_frame.forget()
            self.attr_restore.pack(side=tk.RIGHT, fill=tk.Y)
            self.attr_visible = False
        else:
            self.attr_restore.forget()
            self.right_frame.pack(side=tk.RIGHT, fill=tk.Y)
            self.attr_visible = True

# ---------------------------
# App starten
# ---------------------------

def main():
    root = tk.Tk()
    app = DiagramApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()    