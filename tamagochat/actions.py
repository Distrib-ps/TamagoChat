"""Ce qu'on peut lui faire faire : soins, jeux, et pouvoirs envoyés depuis la page admin."""
import random
import time

from . import desktop
from .config import CH, FPS, SIDE, TOP


class ActionsMixin:
    # ---------------------------------------------------------- soins et jeux
    def busy(self):
        if self.state == "hunt" and self.hunt and self.hunt["phase"] == "air":
            return True
        return self.state in ("eat", "drink", "play", "drag", "fall", "crazy")

    def act_crazy(self, xl=False):
        if self.state == "crazy":      # le calmer (ou, en XXL, prolonger la crise)
            self.st_len = self.st_t + random.randint(25 * FPS, 35 * FPS) if xl else self.st_t
            return
        if self.state in ("drag", "fall", "eat", "drink"):
            return
        self.yarn = None
        d = random.choice((-1, 1))
        self.crazy = {"dir": d, "speed": random.uniform(4.5, 6.5) * self.S,
                      "freeze": 0, "shout": random.randint(70, 140)}
        self.vx = d * self.crazy["speed"]
        self.vy = -(2 * 0.35 * self.S * 120 * self.dpi) ** 0.5   # petit bond de départ
        self.set_state("crazy", random.randint(25 * FPS, 35 * FPS) if xl
                       else random.randint(8 * FPS, 14 * FPS))
        self.say("crazy")
        self.schedule_crazy()

    def act_pet(self):
        if self.state == "sleep":
            self.wake("woken")
            return
        if self.busy():
            return
        now = time.time()
        self.pet_times = [t for t in self.pet_times if now - t < 20] + [now]
        if len(self.pet_times) > 7:
            self.say("pet_too_much")
            self.pet_times = self.pet_times[-3:]
            return
        self.change("bonheur", 12)
        self.set_state("pet", 50)
        self.say("pet", chance=0.6)

    def act_feed(self):
        if self.busy():
            return
        if self.stats["satiete"] > 90:
            if self.state == "sleep":
                return
            self.say("full")
            return
        self.set_state("eat", 80)

    def act_drink(self):
        if self.busy():
            return
        if self.stats["hydratation"] > 90:
            if self.state == "sleep":
                return
            self.say("not_thirsty")
            return
        self.set_state("drink", 70)

    def act_play(self):
        if self.busy():
            return
        if self.stats["energie"] < 20:
            self.say("too_tired")
            return
        cx = self.x + (SIDE + 12) * self.S
        side = random.choice((-1, 1))
        self.yarn = {"x": cx + side * 14 * self.S, "vx": side * 2.0 * self.S,
                     "h": 6 * self.S, "vh": 0.0, "chasing": False, "pounce": 0}
        self.set_state("play", 220)
        self.say("play")

    def act_sleep(self):
        if self.state == "sleep":
            self.wake("wake")
        elif not self.busy():
            self.say("sleep")
            self.set_state("sleep")

    def wake(self, key):
        self.set_state("idle")
        self.next_decision = random.randint(3 * FPS, 6 * FPS)
        self.say(key)
        if key == "wake" and random.random() < 0.8:      # réveil en douceur : il s'étire
            self.start_reaction("stretch", quiet=True)

    # ---------------------------------------------------------- pouvoirs à distance
    def take_over(self):
        """Interrompt ce qu'il faisait (pelote, folie, chasse...) pour un pouvoir à distance."""
        self.yarn = self.crazy = self.hunt = self.after_land = None
        self.vx = self.vy = 0.0

    def big_jump(self):
        self.take_over()
        a = self.area()
        g = self.ground()
        h = random.uniform(0.35, 0.7) * (g - (a[1] - TOP * self.S))
        self.y = min(self.y, g)
        self.vy = -(2 * 0.35 * self.S * h) ** 0.5
        self.vx = random.uniform(-1.5, 1.5) * self.S
        self.set_state("fall")
        self.after_land = "land"
        self.say_text(random.choice(["Hop !", "Boiiiing !", "Youpiii !", "Haut les pattes !"]))

    def drop_from_sky(self, other_screen=False):
        self.monitors = desktop.list_monitors() or self.monitors
        cur = self.current_monitor()
        choices = [m for m in self.monitors if m["mon"] != cur["mon"]] if other_screen else []
        m = random.choice(choices) if choices else cur
        w = m["work"]
        lo, hi = self.x_bounds(w)
        self.take_over()
        self.x = random.uniform(lo + (hi - lo) * 0.1, hi - (hi - lo) * 0.1)
        self.y = w[1] - TOP * self.S
        self.set_state("fall")
        self.after_land = "land"
        self.move_window()
        self.say_text(random.choice(["Aaaaaaah !", "Je toooombe !", "Wiiiiii !",
                                     "Attention en dessous !"]))

    def run_to_mouse(self):
        px, py = self.root.winfo_pointerxy()
        S = self.S
        target = desktop.work_area_at(px, py)
        if target is not None and target != self.area():   # souris sur un autre écran : il y saute
            lo, hi = self.x_bounds(target)
            self.take_over()
            self.x = max(lo, min(hi, px - (SIDE + 12) * S))
            self.y = target[1] - TOP * S
            self.set_state("fall")
            self.after_land = "land"
            self.move_window()
            self.say_text("J'arrive par la voie des airs !")
            return
        if self.busy() and self.state != "crazy":
            return
        if self.state == "sleep":
            self.say("woken")
        self.take_over()
        dx = px - (self.x + (SIDE + 12) * S)
        self.facing = "right" if dx > 0 else "left"
        self.walk_left = abs(dx)
        self.set_state("walk")
        self.walk_fast = True
        self.say_text(random.choice(["Je vais l'attraper !", "La souris ! LA SOURIS !",
                                     "Hop hop hop !"]))

    def hide_and_seek(self):
        if self.state == "hidden" or (self.busy() and self.state != "crazy"):
            return
        self.take_over()
        self.set_state("hidden", random.randint(20 * FPS, 40 * FPS))
        self.say_text(random.choice(["Cache-cache ! Ferme les yeux...", "Tu me vois... et là ?",
                                     "1, 2, 3... Je me cache !"]), priority=True, secs=2)

    def st_hidden(self):
        if self.st_t == 2 * FPS:          # il disparaît après sa phrase
            self.bubble.hide()
            self.root.geometry("+-32000+-32000")
        if self.st_t >= self.st_len:
            self.unhide()

    def unhide(self, quiet=False):
        """Réapparaît à un endroit au hasard (sur n'importe quel écran)."""
        self.monitors = desktop.list_monitors() or self.monitors
        w = random.choice(self.monitors)["work"] if self.monitors else self.area()
        lo, hi = self.x_bounds(w)
        self.x = random.uniform(lo, hi)
        self.y = w[3] - CH * self.S
        self.set_state("idle")
        self.next_decision = random.randint(3 * FPS, 6 * FPS)
        self.move_window()
        self.spawn("sparkle", SIDE + 12, TOP + 2, vy=-0.2, life=14)
        if not quiet:
            self.say_text(random.choice(["Coucou ! Tu m'as cherché ?", "Me revoilà !",
                                         "Bouh ! Je suis là !"]), priority=True)

    def love_bomb(self):
        if self.state == "sleep":
            self.set_state("idle")
        if self.busy():
            if self.state in ("fall", "crazy"):
                return
            self.take_over()
        self.change("bonheur", 25)
        self.set_state("pet", 90)
        for _ in range(10):
            self.spawn("heart", SIDE + random.uniform(-4, 22), TOP + random.uniform(-2, 8),
                       vx=random.uniform(-0.25, 0.25), vy=random.uniform(-0.45, -0.2), life=40)
        self.say_text(random.choice(["Ronron... ♥", "Trop d'amour !", "Je suis aux anges !"]),
                      priority=True)
