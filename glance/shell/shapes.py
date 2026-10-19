"""
shapes.py — point lists for drawing with the mouse (circle, star, heart, arrow...).

All functions return a list of STROKES; a stroke is a list of (x, y) points the mouse
follows with the button held. Coordinates are in whatever unit the caller uses (Glance
uses physical pixels): pass the centre and sizes in that unit.
"""

from __future__ import annotations

import math


def circle(cx, cy, r, n=48):
    return [[(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
             for i in range(n + 1)]]


def ellipse(cx, cy, rx, ry, n=48):
    return [[(cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
             for i in range(n + 1)]]


def rect(cx, cy, w, h):
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    return [[(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]]


def triangle(cx, cy, r):
    pts = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
           for a in (-90, 30, 150, -90)]
    return [pts]


def star(cx, cy, r, points=5):
    pts = []
    for i in range(points * 2 + 1):
        rr = r if i % 2 == 0 else r * 0.42
        a = -math.pi / 2 + i * math.pi / points
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return [pts]


def heart(cx, cy, r, n=60):
    pts = []
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * r / 17, cy + y * r / 17))
    return [pts]


def spiral(cx, cy, r, turns=3, n=90):
    return [[(cx + r * (i / n) * math.cos(2 * math.pi * turns * i / n),
              cy + r * (i / n) * math.sin(2 * math.pi * turns * i / n)) for i in range(n + 1)]]


def line(x1, y1, x2, y2):
    return [[(x1, y1), (x2, y2)]]


def arrow(x1, y1, x2, y2):
    a = math.atan2(y2 - y1, x2 - x1)
    h = max(14.0, math.hypot(x2 - x1, y2 - y1) * 0.18)
    left = (x2 - h * math.cos(a - 0.45), y2 - h * math.sin(a - 0.45))
    right = (x2 - h * math.cos(a + 0.45), y2 - h * math.sin(a + 0.45))
    return [[(x1, y1), (x2, y2)], [left, (x2, y2), right]]


def zigzag(cx, cy, w, h, teeth=6):
    pts = [(cx - w / 2 + w * i / teeth, cy + (h / 2 if i % 2 else -h / 2)) for i in range(teeth + 1)]
    return [pts]


def wave(cx, cy, w, h, n=60):
    return [[(cx - w / 2 + w * i / n, cy + h / 2 * math.sin(4 * math.pi * i / n)) for i in range(n + 1)]]


def smiley(cx, cy, r):
    eyes = [circle(cx - r * 0.35, cy - r * 0.25, r * 0.08, 12)[0], circle(cx + r * 0.35, cy - r * 0.25, r * 0.08, 12)[0]]
    mouth = [(cx + r * 0.6 * math.cos(math.radians(a)), cy + r * 0.6 * math.sin(math.radians(a)))
             for a in range(20, 161, 10)]
    return circle(cx, cy, r) + eyes + [mouth]


SHAPES = ("circle", "ellipse", "rect", "square", "triangle", "star", "heart", "spiral", "line",
          "arrow", "zigzag", "wave", "smiley")


def make(kind: str, cx: float, cy: float, size: float, size2: float | None = None,
         x2: float | None = None, y2: float | None = None) -> list:
    """Strokes for `kind`. size is a radius or half-extent; size2 the second dimension."""
    k = (kind or "").lower().strip()
    s2 = size if size2 is None else size2
    if k in ("circle", "round", "ring"):
        return circle(cx, cy, size)
    if k in ("ellipse", "oval"):
        return ellipse(cx, cy, size, s2)
    if k in ("rect", "rectangle", "box"):
        return rect(cx, cy, size * 2, s2 * 2)
    if k == "square":
        return rect(cx, cy, size * 2, size * 2)
    if k == "triangle":
        return triangle(cx, cy, size)
    if k == "star":
        return star(cx, cy, size)
    if k == "heart":
        return heart(cx, cy, size)
    if k == "spiral":
        return spiral(cx, cy, size)
    if k in ("line", "straight line") and x2 is not None and y2 is not None:
        return line(cx, cy, x2, y2)
    if k == "arrow" and x2 is not None and y2 is not None:
        return arrow(cx, cy, x2, y2)
    if k == "zigzag":
        return zigzag(cx, cy, size * 2, s2)
    if k == "wave":
        return wave(cx, cy, size * 2, s2)
    if k in ("smiley", "smile", "face", "smiley face"):
        return smiley(cx, cy, size)
    return []
