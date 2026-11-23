"""La bulle de dialogue qui suit la tête du chat."""
import time
import tkinter as tk

from . import desktop


def round_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


class Bubble:
    def __init__(self, app):
        self.app = app
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        desktop.make_transparent(w)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", app.quit)   # extinction du PC, taskkill...
        self.c = tk.Canvas(w, bg=desktop.BG, highlightthickness=0, bd=0, cursor="hand2")
        self.c.pack()
        self.c.bind("<Button-1>", lambda e: self.hide())
        d = app.dpi
        self.pad, self.tail, self.maxw = int(10 * d), int(10 * d), int(230 * d)
        self.font = desktop.font(10)
        self.visible = False
        self.until = 0
        self.locked_until = 0
        self.geom = None
        self.tail_x = None
        self.hide()
        desktop.make_tool_window(w)

    def show(self, text, secs, priority=False):
        if not priority and time.time() < self.locked_until:
            return              # un message reçu est affiché : on ne l'écrase pas
        self.locked_until = time.time() + secs if priority else 0
        c = self.c
        c.delete("all")
        self.text_id = c.create_text(self.pad, self.pad, text=text, anchor="nw",
                                     width=self.maxw, font=self.font, fill="#3b2a22")
        x1, y1, x2, y2 = c.bbox(self.text_id)
        self.w = (x2 - x1) + 2 * self.pad
        self.h = (y2 - y1) + 2 * self.pad
        c.config(width=self.w + 2, height=self.h + self.tail + 2)
        self.until = time.time() + secs
        self.visible = True
        self.tail_x = None
        self.geom = None
        self.follow()

    def hide(self):
        self.visible = False
        self.locked_until = 0
        self.geom = None
        self.win.geometry("1x1+-32000+-32000")

    def follow(self):
        if not self.visible:
            return
        if time.time() > self.until:
            self.hide()
            return
        hx, hy = self.app.head_screen_pos()
        area = self.app.area()
        bx = int(hx - self.w / 2)
        bx = max(area[0] + 2, min(bx, area[2] - self.w - 4))
        by = int(hy - self.h - self.tail + 4)
        by = max(area[1] + 2, by)
        tx = int(max(18, min(hx - bx, self.w - 18)))
        if tx != self.tail_x:
            self.tail_x = tx
            self._draw_shape(tx)
        geom = f"{self.w + 2}x{self.h + self.tail + 2}+{bx}+{by}"
        if geom != self.geom:
            self.geom = geom
            self.win.geometry(geom)

    def _draw_shape(self, tx):
        c = self.c
        c.delete("shape")
        w, h, t = self.w, self.h, self.tail
        ink, paper = "#3b2a22", "#ffffff"
        c.create_polygon(tx - t, h - 4, tx + t * 0.4, h - 4, tx - t * 0.6, h + t - 1,
                         fill=paper, outline=ink, width=2, tags="shape")
        round_rect(c, 1, 1, w, h, 14, fill=paper, outline=ink, width=2, tags="shape")
        c.create_polygon(tx - t + 3, h - 6, tx + t * 0.4 - 2, h - 6, tx - t * 0.6 + 1, h + t - 5,
                         fill=paper, outline="", tags="shape")
        c.tag_raise(self.text_id)
