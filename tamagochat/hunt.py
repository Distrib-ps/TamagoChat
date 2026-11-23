"""Chasse aux mouches."""
import random

from .config import CAT_H, FPS, SIDE, TOP


class HuntMixin:
    def buzzing(self):
        return [f for f in self.flies if f.state == "buzz"]

    def spawn_flies(self, manual=False, count=None):
        S = self.S
        area = self.area()
        cx = self.x + (SIDE + 12) * S
        free = [f for f in self.flies if f.state == "dead"]
        for f in free[:count or random.choice((1, 1, 2, 3))]:
            x = cx + random.choice((-1, 1)) * random.uniform(15, 40) * S
            y = area[3] - random.uniform(2, 5) * CAT_H * S
            f.spawn(max(area[0] + 10, min(area[2] - 10, x)), max(area[1] + 10, y))
        self.flies_announced = False
        self.schedule_flies()
        if manual and self.state == "sleep":
            self.set_state("idle")      # st_idle lancera la chasse

    def start_hunt(self):
        self.hunt = {"phase": "spot", "t": 0, "target": None, "moving": False, "caught": False}
        self.set_state("hunt")
        if not self.flies_announced:
            self.flies_announced = True
            self.say("fly_spot", chance=0.7)

    def hunt_phase(self, phase):
        self.hunt["phase"], self.hunt["t"] = phase, 0

    def mouth_pos(self):
        col = 28.5 if self.facing == "right" else 2.5
        return self.x + (SIDE + col) * self.S, self.y + (TOP + 12) * self.S

    def eat_fly(self, f):
        f.kill()
        self.change("satiete", 3)
        self.change("bonheur", 6)
        mx, my = self.mouth_pos()
        self.spawn("sparkle", (mx - self.x) / self.S - 2.5, (my - self.y) / self.S - 2.5,
                   vy=-0.15, life=12)
        self.say("fly_eat", chance=0.7)

    def swat(self, f):
        if f.state != "buzz":
            return
        f.kill()
        self.say("fly_swat", chance=0.8)

    def fly_left(self):
        if self.state == "hunt" and len(self.buzzing()) <= 1:
            self.say("fly_gone", chance=0.6)

    def st_hunt(self):
        if self.hunt is None:
            self.start_hunt()
        h = self.hunt
        h["t"] += 1
        S = self.S
        G = 0.35 * S
        lo, hi = self.x_bounds(self.area())
        g = self.ground()
        h["moving"] = False

        if h["phase"] == "air":          # en plein bond
            self.vy += G
            self.x = max(lo, min(hi, self.x + self.vx))
            self.y += self.vy
            f = h["target"]
            if f.state == "buzz" and not h["caught"]:
                mx, my = self.mouth_pos()
                if (f.x - mx) ** 2 + (f.y - my) ** 2 < (8 * S) ** 2:
                    self.eat_fly(f)
                    h["caught"] = True
            if self.y >= g:
                self.y, self.vx, self.vy = g, 0.0, 0.0
                if not h["caught"]:
                    self.say("fly_miss", chance=0.35)
                self.hunt_phase("munch" if h["caught"] else "rest")
                h["caught"] = False
            self.move_window()
            return

        if h["phase"] == "munch":         # il mâche
            if h["t"] >= 18:
                self.hunt_phase("stalk")
            return

        flies = self.buzzing()
        if not flies:
            self.hunt = None
            self.set_state("idle")
            self.next_decision = random.randint(3 * FPS, 6 * FPS)
            return
        body_cx = self.x + (SIDE + 15) * S
        f = h["target"] if h["target"] in flies else min(flies, key=lambda fl: abs(fl.x - body_cx))
        h["target"] = f
        self.facing = "right" if f.x > body_cx else "left"
        if (h["phase"] == "spot" and h["t"] < 22) or (h["phase"] == "rest" and h["t"] < 10):
            return                        # il observe / reprend son souffle
        h["phase"] = "stalk"
        mx, my = self.mouth_pos()
        dx = f.x - mx
        if abs(dx) > 12 * S:              # il s'approche
            nx = max(lo, min(hi, self.x + (1.3 * S if dx > 0 else -1.3 * S)))
            if nx != self.x:
                self.x = nx
                h["moving"] = True
                self.move_window()
            return
        height = my - f.y
        if height > 3.5 * CAT_H * S:      # trop haut : il guette en fouettant de la queue
            return
        jump = max(3 * S, height + 2 * S)
        vy0 = (2 * G * jump) ** 0.5
        t_apex = vy0 / G
        self.vy = -vy0
        self.vx = max(-4 * S, min(4 * S, dx / t_apex))
        if random.random() < 0.4:
            f.dodge = max(1, int(t_apex * 0.6))
        self.hunt_phase("air")
