import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GLib
strokes = []
class W(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Canvas", default_width=700, default_height=500)
        self.da = Gtk.DrawingArea(); self.da.set_draw_func(self.draw); self.set_child(self.da)
        g = Gtk.GestureDrag(); g.connect("drag-begin", self.begin); g.connect("drag-update", self.update); self.da.add_controller(g)
        self.cur = None
    def begin(self, g, x, y): self.cur = [(x, y)]; strokes.append(self.cur)
    def update(self, g, dx, dy):
        sx, sy = self.cur[0]; self.cur.append((sx + dx, sy + dy)); self.da.queue_draw()
    def draw(self, area, cr, w, h):
        cr.set_source_rgb(1, 1, 1); cr.paint(); cr.set_source_rgb(0.9, 0.1, 0.1); cr.set_line_width(4)
        for s in strokes:
            cr.move_to(*s[0])
            for p in s[1:]: cr.line_to(*p)
            cr.stroke()
class A(Gtk.Application):
    def do_activate(self): W(self).present()
A(application_id="test.canvas").run()
