"""Comportement autonome : jauges, paroles, décisions et états (marche, sieste, folie...)."""
import random
import time

from .config import APP_VERSION, CH, CW, DECAY_PER_S, FPS, SIDE, SLEEP_GAIN_PER_S, STATS, TOP
from .phrases import NEED_PHRASE, PHRASES


class BehaviorMixin:
    # ---------------------------------------------------------- jauges
    def change(self, stat, delta):
        self.stats[stat] = max(0.0, min(100.0, self.stats[stat] + delta))

    def decay(self, secs):
        asleep = self.state == "sleep"
        for k in ("satiete", "hydratation"):
            self.change(k, -DECAY_PER_S[k] * secs * (0.5 if asleep else 1))
        if asleep:
            self.change("energie", SLEEP_GAIN_PER_S * secs)
        else:
            self.change("energie", -DECAY_PER_S["energie"] * secs)
            mult = 2 if min(self.stats["satiete"], self.stats["hydratation"]) < 20 else 1
            self.change("bonheur", -DECAY_PER_S["bonheur"] * secs * mult)

    def apply_absence(self, secs):
        secs = min(secs, 12 * 3600)
        for k in ("satiete", "hydratation", "bonheur"):
            floor = min(self.stats[k], 15)
            self.stats[k] = max(floor, self.stats[k] - DECAY_PER_S[k] * secs * 0.5)
        self.change("energie", secs * SLEEP_GAIN_PER_S)  # il a dormi pendant ton absence

    def mood_eyes(self):
        return "sad" if min(self.stats.values()) < 25 else "open"

    # ---------------------------------------------------------- paroles
    def phrases(self, key):
        custom = self.data["phrases"]
        return custom[key] if key in custom else PHRASES[key]

    def say(self, key, chance=1.0):
        if random.random() > chance:
            return
        options = self.phrases(key)
        if options:
            self.say_text(random.choice(options))

    def say_text(self, text, priority=False, secs=None):
        text = text.replace("{name}", self.data["name"])
        self.bubble.show(text, secs or 2.5 + len(text) * 0.06, priority)
        self.talk = 14

    def greet(self, away):
        if self.data.get("just_updated"):
            self.data["just_updated"] = None
            self.save()
            self.say_text(f"Tadaa ! Me voilà en version {APP_VERSION} !", priority=True, secs=6)
            return
        if away > 2 * 3600:
            self.say("back")
            return
        h = time.localtime().tm_hour
        key = ("night" if h >= 23 or h < 5 else "morning" if h < 11 else
               "noon" if h < 14 else "afternoon" if h < 18 else "evening")
        self.say(key)

    # ---------------------------------------------------------- décisions
    def schedule_chatter(self):
        cd = self.data["chatter_s"]
        self.chatter_next = time.time() + cd * random.uniform(0.7, 1.3) if cd > 0 else 0

    def schedule_flies(self):
        mins = self.data["flies_min"]
        self.fly_next = time.time() + mins * 60 * random.uniform(0.5, 1.5) if mins > 0 else 0

    def schedule_crazy(self):
        mins = self.data["crazy_min"]
        self.crazy_next = time.time() + mins * 60 * random.uniform(0.5, 1.5) if mins > 0 else 0

    def decide(self):
        s = self.stats
        now = time.time()
        self.next_decision = random.randint(4 * FPS, 12 * FPS)
        if s["energie"] < 10:
            self.say("tired")
            self.set_state("sleep")
            return
        if self.data["crazy_min"] > 0 and now >= self.crazy_next and s["energie"] > 30:
            self.act_crazy()
            return
        if self.data["flies_min"] > 0 and now >= self.fly_next and s["energie"] > 15:
            self.spawn_flies()
            return
        # phrase spontanée, au plus une fois par délai configuré
        if self.data["chatter_s"] > 0 and now >= self.chatter_next and random.random() < 0.6:
            self.schedule_chatter()
            lowest = min(STATS, key=lambda k: s[k])
            if s[lowest] < 30:
                self.say(NEED_PHRASE[lowest])
            else:
                h = time.localtime().tm_hour
                night = (h >= 23 or h < 5) and random.random() < 0.4
                self.say("night" if night else "idle")
            return
        if s["energie"] < 30 and random.random() < 0.15:
            self.set_state("sleep")
            return
        if self.data["autowalk"] and random.random() < 0.45:
            area = self.area()
            lo, hi = self.x_bounds(area)
            width = area[2] - area[0]
            d = random.choice((-1, 1))
            room = hi - self.x if d > 0 else self.x - lo
            if room < 20 * self.S and not self.neighbor(self.current_monitor(), d):
                d = -d
            # le plus souvent une petite balade, parfois une grande traversée
            frac = random.uniform(0.05, 0.3) if random.random() < 0.85 else random.uniform(0.5, 1.1)
            self.walk_left = frac * width
            self.facing = "right" if d > 0 else "left"
            self.set_state("walk")

    # ---------------------------------------------------------- états
    def st_idle(self):
        g = self.ground()
        if self.y < g - 1:
            self.vx = self.vy = 0
            self.set_state("fall")
            return
        lo, hi = self.x_bounds(self.area())
        if self.y > g or not lo <= self.x <= hi:   # écran débranché / barre déplacée
            self.y = min(self.y, g)
            self.x = max(lo, min(hi, self.x))
            self.move_window()
        if self.buzzing():
            self.start_hunt()
            return
        self.next_decision -= 1
        if self.next_decision <= 0:
            self.decide()

    def st_walk(self):
        S = self.S
        d = 1 if self.facing == "right" else -1
        lo, hi = self.x_bounds(self.area())
        step = min((2.6 if self.walk_fast else 0.9) * S, self.walk_left)
        nx = self.x + d * step
        if nx < lo or nx > hi:
            if self.walk_left > 3 * S and self.cross_edge(d):
                self.walk_left -= step
            else:
                self.x = max(lo, min(hi, nx))
                self.set_state("idle")
        else:
            self.x = nx
            self.walk_left -= step
            if self.walk_left <= 0:
                self.set_state("idle")
        self.move_window()

    def st_fall(self):
        area = self.area()
        self.vy += 0.35 * self.S
        self.y += self.vy
        self.x += self.vx
        self.vx *= 0.97
        lo, hi = self.x_bounds(area)
        if self.x < lo or self.x > hi:
            d = 1 if self.x > hi else -1
            if not (abs(self.vx) > self.S and self.cross_edge(d)):   # lancé vers l'autre écran
                self.x = max(lo, min(hi, self.x))
                self.vx = -self.vx * 0.5
        g = self.ground()
        if self.y >= g:
            self.y = g
            if self.after_land:
                self.say(self.after_land)
                self.after_land = None
            elif self.vy > 9 * self.S:
                self.say("land", chance=0.6)
            self.vx = self.vy = 0
            self.set_state("idle")
            self.next_decision = random.randint(2 * FPS, 5 * FPS)
        self.move_window()

    def st_pet(self):
        if self.st_t % 7 == 1:
            self.spawn("heart", SIDE + random.uniform(3, 15), TOP + random.uniform(-1, 3),
                       vx=random.uniform(-0.12, 0.12), vy=-0.3, life=28)
        if self.st_t >= self.st_len:
            self.set_state("idle")

    def st_eat(self):
        if self.st_t >= self.st_len:
            self.change("satiete", 35)
            self.change("bonheur", 5)
            self.spawn("sparkle", SIDE + 3, TOP + 2, vy=-0.2, life=12)
            self.say("eat")
            self.set_state("idle")

    def st_drink(self):
        if self.st_t >= self.st_len:
            self.change("hydratation", 40)
            self.change("bonheur", 3)
            self.spawn("sparkle", SIDE + 3, TOP + 2, vy=-0.2, life=12)
            self.say("drink")
            self.set_state("idle")

    def st_sleep(self):
        if self.st_t % 22 == 1:
            self.spawn("zzz", SIDE + 19, TOP + 4, vx=0.12, vy=-0.2, life=40)
        if self.stats["energie"] >= 100:
            self.wake("wake")

    def st_play(self):
        y = self.yarn
        S = self.S
        area = self.area()
        # physique de la pelote
        y["x"] += y["vx"]
        y["vx"] *= 0.95
        y["vh"] -= 0.3 * S
        y["h"] += y["vh"]
        if y["h"] <= 0:
            y["h"] = 0
            y["vh"] = -y["vh"] * 0.45 if abs(y["vh"]) > S else 0
        if y["x"] < area[0] + 4 * S or y["x"] > area[2] - 4 * S:
            y["x"] = max(area[0] + 4 * S, min(area[2] - 4 * S, y["x"]))
            y["vx"] = -y["vx"]
        # le chat la poursuit
        cx = self.x + (SIDE + 12) * S
        dist = y["x"] - cx
        y["pounce"] = max(0, y["pounce"] - 1)
        if abs(dist) > 11 * S:
            self.facing = "right" if dist > 0 else "left"
            self.x += (1.5 * S) if dist > 0 else (-1.5 * S)
            self.x = max(area[0] - SIDE * S, min(area[2] - (SIDE + 24) * S, self.x))
            y["chasing"] = True
            self.move_window()
        else:
            y["chasing"] = False
            if abs(y["vx"]) < 0.5 * S and y["h"] == 0:
                y["vx"] = random.choice((-1, 1)) * random.uniform(5, 9) * S / 4
                y["vh"] = random.uniform(2, 4) * S / 4
                y["pounce"] = 8
                self.spawn("sparkle", (y["x"] - self.x) / S - 2, CH - 12, vy=-0.15, life=10)
        # garder la pelote dans le canvas
        y["x"] = max(self.x + 4 * S, min(self.x + (CW - 4) * S, y["x"]))
        if self.st_t >= self.st_len:
            self.change("bonheur", 25)
            self.change("energie", -12)
            self.change("satiete", -5)
            self.change("hydratation", -8)
            self.yarn = None
            self.say("play_end")
            self.set_state("idle")

    def st_crazy(self):
        cz, S = self.crazy, self.S
        a = self.area()
        G = 0.35 * S
        g = self.ground()
        top = a[1] - TOP * S
        lo, hi = a[0] - SIDE * S, a[2] - (SIDE + 24) * S
        on_ground = self.y >= g - 0.5 and self.vy >= 0
        if cz["freeze"] > 0 and on_ground:
            cz["freeze"] -= 1
        else:
            if on_ground:
                self.y, self.vy = g, 0.0
                self.vx = cz["dir"] * cz["speed"]
                r = random.random()
                if r < 0.05:      # grand bond, parfois jusqu'en haut de l'écran
                    h = random.uniform(0.15, 1.0) * (g - top)
                    self.vy = -(2 * G * h) ** 0.5
                elif r < 0.07:    # demi-tour brutal
                    cz["dir"] *= -1
                    cz["speed"] = random.uniform(4.5, 6.5) * S
                elif r < 0.08:    # se fige net en louchant
                    cz["freeze"] = random.randint(8, 18)
                if self.t % 3 == 0:
                    rear = SIDE + (2 if cz["dir"] > 0 else 25)
                    self.spawn("dust", rear, CH - 4, vx=-cz["dir"] * 0.6, vy=-0.05, life=9)
            else:
                self.vy += G
            self.x += self.vx
            self.y += self.vy
            if self.y < top:      # bonk au plafond
                self.y, self.vy = top, abs(self.vy) * 0.3
            if self.y > g:
                self.y = g
            if self.x <= lo or self.x >= hi:
                d = 1 if self.x >= hi else -1
                if random.random() < 0.6 and self.cross_edge(d):
                    pass    # il fonce sur l'autre écran
                else:       # rebond sur le bord (+ saut au mur)
                    self.x = max(lo, min(hi, self.x))
                    cz["dir"] *= -1
                    self.vx = cz["dir"] * cz["speed"]
                    if random.random() < 0.5:
                        self.vy = -(2 * G * random.uniform(0.2, 0.8) * (g - top)) ** 0.5
            self.facing = "right" if self.vx > 0 else "left"
            self.move_window()
        cz["shout"] -= 1
        if cz["shout"] <= 0:
            cz["shout"] = random.randint(70, 140)
            self.say("crazy", chance=0.5)
        if self.st_t >= self.st_len:
            self.change("energie", -15)
            self.change("bonheur", 10)
            self.crazy = None
            self.vx *= 0.3
            self.after_land = "crazy_end"
            self.set_state("fall")
