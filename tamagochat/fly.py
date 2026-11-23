"""Une mouche, dans sa propre petite fenêtre transparente."""
import random
import time
import tkinter as tk

from . import desktop
from . import sprites as sp
from .config import CAT_H, FLY_LIFETIME, SIDE
from .render import draw_runs, pixel_runs

FLY_RUNS = [pixel_runs(frame) for frame in sp.FLY]


class Fly:
    """Une mouche dans sa propre petite fenêtre (réutilisée, jamais recréée)."""

    def __init__(self, app):
        self.app = app
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        desktop.make_transparent(w)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", app.quit)
        self.c = tk.Canvas(w, bg=desktop.BG, highlightthickness=0, bd=0, cursor="hand2")
        self.c.pack()
        self.c.bind("<Button-1>", lambda e: app.swat(self))
        self.state = "dead"     # dead / buzz / leave
        self.scale = None
        self.frame = -1
        self.geom = None
        self.hide()
        desktop.make_tool_window(w)

    def hide(self):
        self.geom = None
        self.win.geometry("1x1+-32000+-32000")

    def spawn(self, x, y):
        self.x, self.y = float(x), float(y)
        self.vx = self.vy = 0.0
        self.t = 0
        self.state = "buzz"
        self.born = time.time()
        self.retarget = 0
        self.ox = self.alt = 0.0
        self.dodge = -1

    def kill(self):
        self.state = "dead"
        self.hide()

    def update(self):
        if self.state == "dead":
            return
        app, S = self.app, self.app.S
        self.t += 1
        area = app.area()
        if self.state == "buzz" and time.time() - self.born > FLY_LIFETIME:
            self.state = "leave"
            self.vx = random.choice((-1, 1)) * 2 * S
            self.vy = -1.5 * S
            app.fly_left()
        if self.state == "buzz":
            self.retarget -= 1
            if self.retarget <= 0:    # nouveau point autour du chat
                self.retarget = random.randint(30, 90)
                self.ox = random.uniform(-35, 35) * S
                low = random.random() < 0.35
                self.alt = random.uniform(0.3, 1.2 if low else 4.5) * CAT_H * S
            tx = app.x + (SIDE + 12) * S + self.ox
            ty = area[3] - self.alt
            self.vx += (tx - self.x) * 0.004 + random.uniform(-0.35, 0.35) * S
            self.vy += (ty - self.y) * 0.004 + random.uniform(-0.35, 0.35) * S
            if self.dodge > 0:
                self.dodge -= 1
                if self.dodge == 0:   # esquive au dernier moment
                    self.vx += random.choice((-1, 1)) * 4 * S
                    self.vy -= 3 * S
            self.vx = max(-4 * S, min(4 * S, self.vx * 0.9))
            self.vy = max(-4 * S, min(4 * S, self.vy * 0.9))
        else:
            self.vy -= 0.05 * S
            self.vx *= 1.03
        self.x += self.vx
        self.y += self.vy
        if self.state == "buzz":
            self.x = max(area[0] + 10, min(area[2] - 10, self.x))
            self.y = max(area[1] + 10, min(area[3] - 4 * S, self.y))
        elif not (area[0] - 200 < self.x < area[2] + 200 and self.y > area[1] - 200):
            self.kill()
            return
        self.draw()

    def draw(self):
        fs = max(2, round(self.app.S * 0.6))
        fw, fh = len(sp.FLY[0][0]), len(sp.FLY[0])
        if fs != self.scale:
            self.scale = fs
            self.c.config(width=fw * fs, height=fh * fs)
            self.frame = -1
        frame = self.t % 2
        if frame != self.frame:
            self.frame = frame
            self.c.delete("all")
            draw_runs(self.c, FLY_RUNS[frame], fs, 0, 0)
        geom = f"{fw * fs}x{fh * fs}+{int(self.x - fw * fs / 2)}+{int(self.y - fh * fs / 2)}"
        if geom != self.geom:
            self.geom = geom
            self.win.geometry(geom)
