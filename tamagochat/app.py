"""L'application : fenêtre du chat, boucle principale, souris, écrans et sauvegarde."""
import json
import os
import queue
import random
import re
import secrets
import time
import tkinter as tk

from . import desktop
from .actions import ActionsMixin
from .behavior import BehaviorMixin
from .bubble import Bubble
from .config import CH, CW, DATA_DIR, FLY_POOL, FPS, SAVE_FILE, SIDE, SIZES, TICK_MS, TOP
from .dialogs import DialogsMixin
from .fly import Fly
from .hunt import HuntMixin
from .menu import MenuMixin
from .reactions import ReactionsMixin
from .remote import Remote, RemoteMixin
from .render import RenderMixin
from .storage import load_save, log_error


class App(BehaviorMixin, ActionsMixin, HuntMixin, ReactionsMixin, RemoteMixin, RenderMixin,
          MenuMixin, DialogsMixin):
    def __init__(self):
        self.data = load_save()
        self.stats = self.data["stats"]

        r = self.root = tk.Tk()
        r.withdraw()
        r.overrideredirect(True)
        desktop.make_transparent(r)
        r.attributes("-topmost", bool(self.data["topmost"]))
        r.title("TamagoChat")
        r.protocol("WM_DELETE_WINDOW", self.quit)   # fermeture propre (sauvegarde)
        desktop.setup_root(r, self.quit)
        self.dpi = desktop.dpi_scale(r)
        self.runs = {}                       # segments de pixels par sprite (voir render.py)
        self.chase_spin = 0                  # durée de la course après sa queue (reactions.py)
        self.ladybug = None                  # coccinelle sur laquelle il louche (reactions.py)
        self.menu, self.menu_open = None, False
        self.scene, self.last_scene = [], None

        self.canvas = tk.Canvas(r, bg=desktop.BG, highlightthickness=0, bd=0, cursor="hand2")
        self.canvas.pack()
        self.S = 4
        self.apply_size(keep_ground=False)

        # état
        self.t = 0
        self.state, self.st_t, self.st_len = "idle", 0, 0
        self.walk_fast = False
        self.phrases_rev, self._pp_rev, self._pp = 0, -1, None
        self.facing = "right"
        self.walk_left = 0.0
        self.monitors = desktop.list_monitors()
        self.vx = self.vy = 0.0
        self.blink = 0
        self.talk = 0
        self.particles = []
        self.pet_times = []
        self.next_decision = 5 * FPS
        self.drag = None
        self.drag_hist = []
        self.yarn = None
        self.stats_win = None
        self.phrases_win = None
        self.crazy = None
        self.after_land = None
        self.last_clock = time.time()
        self.chatter_next = 0.0
        self.crazy_next = 0.0
        self.schedule_chatter()
        self.schedule_crazy()

        # position initiale : posé sur la barre des tâches
        sw = r.winfo_screenwidth()
        x = self.data["x"]
        if x is None:
            x = sw * 0.75
        self.x = float(x)
        self.y = 0.0
        area = self.area()
        self.x = max(area[0] - SIDE * self.S, min(self.x, area[2] - (SIDE + 24) * self.S))
        self.y = self.ground()
        self.move_window()

        r.deiconify()
        r.lift()
        self.bubble = Bubble(self)
        self.hunt = None
        self.flies_announced = False
        self.flies = [Fly(self) for _ in range(FLY_POOL)]
        self.fly_next = 0.0
        self.schedule_flies()

        # identité auprès du serveur (créée au premier lancement)
        if not re.fullmatch(r"[0-9a-f]{32}", str(self.data.get("remote_id"))):
            self.data["remote_id"] = secrets.token_hex(16)
            self.data["remote_secret"] = secrets.token_hex(16)
            self.save()
        self.last_sender = None
        self.reply_win = None
        self.remote = Remote(self.remote_snapshot())
        desktop.cleanup_update_files()
        desktop.migrate_startup()
        r.after(60_000, desktop.cleanup_update_files)   # l'ancien exe peut être encore verrouillé

        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_motion)
        c.bind("<ButtonRelease-1>", self.on_release)
        for button in desktop.MENU_BUTTONS:
            c.bind(button, self.show_menu)

        # absence depuis la dernière fois
        last = self.data.get("last_time")
        away = time.time() - last if last else 0
        if away > 60:
            self.apply_absence(away)
        r.after(900, lambda: self.greet(away))
        r.after(TICK_MS, self.tick)
        r.after(60_000, self.autosave)

    # ---------------------------------------------------------- écrans et position
    def apply_size(self, keep_ground=True):
        old_h = CH * self.S
        factor = SIZES.get(self.data["size"], 1.0)
        self.S = max(2, round(4 * self.dpi * factor))
        self.last_scene = None               # tout redessiner à la nouvelle taille
        self.canvas.config(width=CW * self.S, height=CH * self.S)
        if keep_ground:
            self.y += old_h - CH * self.S
            self.move_window()

    def area(self):
        cx = self.x + (SIDE + 12) * self.S
        cy = self.y + CH * self.S - 2
        a = desktop.work_area_at(cx, cy)
        if a is None:
            a = (0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight())
        return a

    def ground(self):
        return self.area()[3] - CH * self.S

    def x_bounds(self, area):
        return area[0] - SIDE * self.S, area[2] - (SIDE + 24) * self.S

    def current_monitor(self):
        a = self.area()
        for attempt in range(2):
            for m in self.monitors:
                if m["work"] == a:
                    return m
            self.monitors = desktop.list_monitors()
        return {"mon": a, "work": a}

    def neighbor(self, cur, d):
        """Écran voisin à droite (d=1) ou à gauche (d=-1), s'il y en a un."""
        cL, cT, cR, cB = cur["mon"]
        best = None
        for m in self.monitors:
            L, T, R, B = m["mon"]
            if m["mon"] == cur["mon"] or B <= cT or T >= cB:
                continue
            gap = L - cR if d > 0 else cL - R
            if gap >= 0 and (best is None or gap < best[0]):
                best = (gap, m)
        return best[1] if best else None

    def cross_edge(self, d):
        """Fait passer le chat sur l'écran voisin. Renvoie False s'il n'y en a pas."""
        cur = self.current_monitor()
        nb = self.neighbor(cur, d)
        if not nb:
            return False
        S = self.S
        cw, nw, cm, nm = cur["work"], nb["work"], cur["mon"], nb["mon"]
        on_ground = abs(self.y - (cw[3] - CH * S)) < 2
        self.x = nw[0] - SIDE * S if d > 0 else nw[2] - (SIDE + 24) * S
        if on_ground:   # il marchait sur la barre des tâches : il continue sur l'autre
            self.y = nw[3] - CH * S
        else:           # en l'air : même hauteur relative
            frac = (self.y + CH * S - cm[1]) / max(1, cm[3] - cm[1])
            self.y = nm[1] + frac * (nm[3] - nm[1]) - CH * S
            self.y = max(nw[1] - TOP * S, min(self.y, nw[3] - CH * S))
        self.move_window()
        return True

    def move_window(self):
        self.root.geometry(f"+{int(self.x)}+{int(self.y)}")

    def keep_on_top(self):
        """Le chat, ses mouches, sa bulle puis ses fenêtres ouvertes, dans cet ordre (la bulle
        passe devant le chat). Pas pendant que le menu du clic droit est ouvert."""
        if self.menu_open:
            return
        wins = [self.root] if self.data["topmost"] else []
        wins += [f.win for f in self.flies if f.state != "dead"]
        if self.bubble.visible:
            wins.append(self.bubble.win)
        for w in (self.stats_win, self.phrases_win, self.reply_win):
            if w is not None and w.winfo_exists():
                wins.append(w)
        desktop.keep_on_top(wins)

    def head_screen_pos(self):
        if self.state == "sleep":
            col, row = 12, 6
        elif self.uses_walk_sprite():
            col, row = (23, 4) if self.facing == "right" else (7, 4)
        else:
            col, row = 12, 1
            if self.state == "stretch":      # la tête monte quand il s'étire
                row -= self.stretch_pose()[0]
        return self.x + (SIDE + col) * self.S, self.y + (TOP + row) * self.S

    # ---------------------------------------------------------- boucle
    def tick(self):
        try:
            self.step()
        except Exception:
            log_error()
        self.root.after(TICK_MS, self.tick)

    def step(self):
        now = time.time()
        gap = now - self.last_clock
        self.last_clock = now
        if gap > 120:          # sortie de veille du PC
            self.apply_absence(gap)
        else:
            self.decay(gap)

        self.t += 1
        self.st_t += 1
        if self.t % (5 * FPS) == 0:      # écran branché / débranché
            self.monitors = desktop.list_monitors()
        self.talk = max(0, self.talk - 1)
        if self.blink > 0:
            self.blink -= 1
        elif random.random() < 0.012:
            self.blink = 3

        for f in self.flies:
            f.update()
        if self.t % 20 == 0:
            self.remote.snapshot = self.remote_snapshot()
        if self.t % 40 == 0:
            self.keep_on_top()
        try:
            while True:
                self.handle_remote(*self.remote.inbox.get_nowait())
        except queue.Empty:
            pass

        handler = getattr(self, "st_" + self.state, None)
        if handler:
            handler()

        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
        self.particles = [p for p in self.particles if p["life"] > 0]

        self.draw()
        self.bubble.follow()

    def set_state(self, state, length=0):
        self.state, self.st_t, self.st_len = state, 0, length
        if state != "walk":
            self.walk_fast = False

    def spawn(self, kind, x, y, vx=0.0, vy=-0.3, life=30):
        self.particles.append({"kind": kind, "x": x, "y": y, "vx": vx, "vy": vy, "life": life})

    # ---------------------------------------------------------- souris
    def on_press(self, e):
        if self.menu_open:                # ce clic ferme le menu, sans caresser le chat
            self.close_menu()
            return
        self.drag = {"sx": e.x_root, "sy": e.y_root, "x": self.x, "y": self.y, "moved": False}
        self.drag_hist = [(time.time(), e.x_root, e.y_root)]

    def on_motion(self, e):
        d = self.drag
        if not d:
            return
        dx, dy = e.x_root - d["sx"], e.y_root - d["sy"]
        if not d["moved"] and dx * dx + dy * dy > 25:
            d["moved"] = True
            self.yarn = self.crazy = self.after_land = self.hunt = None
            self.set_state("drag")
            self.say("drag", chance=0.35)
        if d["moved"]:
            self.x, self.y = d["x"] + dx, d["y"] + dy
            self.move_window()
            self.drag_hist = (self.drag_hist + [(time.time(), e.x_root, e.y_root)])[-5:]

    def on_release(self, e):
        d, self.drag = self.drag, None
        if not d:
            return
        if d["moved"]:
            t0, x0, _ = self.drag_hist[0]
            t1, x1, _ = self.drag_hist[-1]
            dt = max(t1 - t0, 0.001)
            self.vx = max(-25.0, min(25.0, (x1 - x0) / dt * TICK_MS / 1000)) * self.S / 4
            self.vy = 0
            self.set_state("fall")
        else:
            self.act_pet()

    # ---------------------------------------------------------- sauvegarde
    def save(self):
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            self.data["stats"] = {k: round(v, 2) for k, v in self.stats.items()}
            self.data["last_time"] = time.time()
            self.data["x"] = self.x
            tmp = SAVE_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, SAVE_FILE)
            self.stats = self.data["stats"]
        except Exception:
            log_error()

    def autosave(self):
        self.save()
        self.root.after(60_000, self.autosave)

    def quit(self):
        if getattr(self, "_quitting", False):
            return
        self._quitting = True
        self.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def main():
    desktop.set_dpi_aware()
    problem = desktop.unsupported_reason()
    if problem:
        from tkinter import messagebox
        tk.Tk().withdraw()
        messagebox.showerror("TamagoChat", problem)
        return
    if desktop.already_running():
        return
    try:
        App().run()
    except Exception:
        log_error()
        raise
