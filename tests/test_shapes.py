import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "glance", "shell"))

import shapes  # noqa: E402


def test_circle_is_closed_and_round():
    (s,) = shapes.circle(100, 100, 50)
    assert s[0] == s[-1] or math.dist(s[0], s[-1]) < 1e-6
    assert all(abs(math.dist(p, (100, 100)) - 50) < 1e-6 for p in s)


def test_make_covers_every_named_shape():
    for k in shapes.SHAPES:
        strokes = shapes.make(k, 300, 300, 80, 60, 400, 380)
        assert strokes and all(len(st) >= 2 for st in strokes), k
    assert shapes.make("unknown thing", 0, 0, 10) == []
    assert len(shapes.arrow(0, 0, 100, 0)) == 2          # shaft + head


def test_rect_corners():
    (r,) = shapes.rect(50, 50, 40, 20)
    assert (30, 40) in r and (70, 60) in r
