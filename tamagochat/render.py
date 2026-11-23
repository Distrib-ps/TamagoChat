"""Dessin du chat en pixel art.

Les sprites sont dessinés en rectangles (un par segment de pixels de même couleur) plutôt
qu'en images : sur Mac, Tk n'affiche pas les images dans une fenêtre transparente.
On ne redessine que quand la scène change (le plus souvent, seule la fenêtre bouge).
"""
import itertools

from . import sprites as sp
from .config import CH, SIDE, TOP


def pixel_runs(rows):
    """Sprite -> segments horizontaux de même couleur : [(x0, y, x1, couleur)]."""
    runs = []
    for y, row in enumerate(rows):
        x = 0
        for ch, group in itertools.groupby(row):
            n = len(list(group))
            if ch in sp.PALETTE:
                runs.append((x, y, x + n, sp.PALETTE[ch]))
            x += n
    return runs


def draw_runs(canvas, runs, s, px, py):
    for x0, y, x1, color in runs:
        canvas.create_rectangle(px + x0 * s, py + y * s, px + x1 * s, py + (y + 1) * s,
                                fill=color, outline="", width=0)


class RenderMixin:
    def blit(self, key, build, ux, uy):
        """Ajoute un sprite à la scène (dessinée à la fin de draw)."""
        self.scene.append((key, build, round(ux * self.S), round(uy * self.S)))

    def uses_walk_sprite(self):
        if self.state == "walk":
            return True
        if self.state == "crazy":
            return not (self.crazy and self.crazy["freeze"] > 0)
        if self.state == "hunt" and self.hunt:
            return self.hunt["phase"] == "air" or self.hunt["moving"]
        return self.state == "play" and self.yarn and self.yarn["chasing"]

    def cat_sprite(self):
        st, t = self.state, self.t
        if st == "sleep":
            return ("sleep",), sp.make_sleep
        if st == "crazy":
            if self.uses_walk_sprite():
                frame, facing = (t // 2) % 2, self.facing
                return (("walk", frame, facing, True),
                        lambda: sp.make_walk(frame, facing, crazy=True))
            return (("sit", "cross", "open", "side", False),
                    lambda: sp.make_sit("cross", "open", "side"))
        if st == "hunt" and self.hunt:
            ph, facing = self.hunt["phase"], self.facing
            if ph == "air":
                return (("walk", 1, facing, True),
                        lambda: sp.make_walk(1, facing, crazy=True))
            if self.hunt["moving"]:
                frame = (t // 3) % 2
                return ("walk", frame, facing), lambda: sp.make_walk(frame, facing)
            if ph == "munch":
                mouth = "open" if (t // 3) % 2 else "normal"
                return (("sit", "happy", mouth, "up", False),
                        lambda: sp.make_sit("happy", mouth, "up"))
            eyes = "closed" if self.blink else "open"
            tail = "side" if (t // 4) % 2 else "up"     # queue qui fouette : il guette
            return (("sit", eyes, "normal", tail, False),
                    lambda: sp.make_sit(eyes, "normal", tail))
        if self.uses_walk_sprite():
            frame, facing = (t // 4) % 2, self.facing
            return ("walk", frame, facing), lambda: sp.make_walk(frame, facing)
        eyes = self.mood_eyes()
        mouth = "open" if self.talk and (t // 3) % 2 == 0 else "normal"
        happy = self.stats["bonheur"] > 60
        tail = "side" if happy and (t // 14) % 2 else "up"
        blush = False
        if st == "pet":
            eyes, blush, tail = "happy", True, ("side" if (t // 5) % 2 else "up")
        elif st == "eat":
            eyes = "closed" if (t // 8) % 2 else "happy"
            mouth = "open" if (t // 4) % 2 else "normal"
        elif st == "drink":
            eyes = "closed"
            mouth = "open" if (t // 3) % 2 else "normal"
        elif st in ("drag", "fall"):
            eyes, mouth, tail = "open", "open", "side"
        elif st == "play":
            eyes, mouth = "happy", "open"
            tail = "side" if (t // 4) % 2 else "up"
        if self.blink and eyes in ("open", "sad"):
            eyes = "closed"
        return (("sit", eyes, mouth, tail, blush),
                lambda: sp.make_sit(eyes, mouth, tail, blush))

    def draw(self):
        self.scene = []
        self.compose()
        sig = [(key, x, y) for key, _, x, y in self.scene]
        if sig == self.last_scene:
            return
        self.last_scene = sig
        self.canvas.delete("all")
        for key, build, x, y in self.scene:
            if key not in self.runs:
                self.runs[key] = pixel_runs(build())
            draw_runs(self.canvas, self.runs[key], self.S, x, y)

    def compose(self):
        """La scène : gamelle, chat, pelote et particules."""
        st = self.state
        if st == "eat":
            full = self.st_t < self.st_len * 0.7
            self.blit(("bowl", full), lambda: sp.BOWL_FOOD if full else sp.BOWL_FOOD_EMPTY,
                      SIDE - 13, CH - 6)
        elif st == "drink":
            full = self.st_t < self.st_len * 0.7
            self.blit(("water", full), lambda: sp.BOWL_WATER if full else sp.BOWL_FOOD_EMPTY,
                      SIDE - 13, CH - 6)
        key, build = self.cat_sprite()
        self.blit(key, build, SIDE, TOP)
        if st == "play" and self.yarn:
            ux = (self.yarn["x"] - self.x) / self.S - 4
            uy = CH - 7 - self.yarn["h"] / self.S
            self.blit(("yarn",), lambda: sp.YARN, ux, uy)
        art = {"heart": sp.HEART, "zzz": sp.ZZZ, "sparkle": sp.SPARKLE, "dust": sp.DUST}
        for p in self.particles:
            rows = art[p["kind"]]
            self.blit((p["kind"],), lambda rows=rows: rows, p["x"], p["y"])
