"""Petites réactions : toilette, étirement (avec bâillement), éternuement, course après sa queue.

Il les fait tout seul de temps en temps quand il est tranquille ; on peut aussi les déclencher
depuis le menu ou la page admin. Ce sont des états courts, interrompus par n'importe quelle action.
"""
import random

from . import sprites as sp
from .config import CH, FPS, SIDE, TOP

REACTIONS = ("groom", "stretch", "sneeze", "chase_tail", "cross_eyed")
REACTION_LABELS = {"groom": "Faire sa toilette", "stretch": "S'étirer",
                   "sneeze": "Éternuer", "chase_tail": "Courir après sa queue",
                   "cross_eyed": "Loucher sur une coccinelle"}
# coccinelle : posée sur son nez (coin haut gauche du sprite, en pixels du canvas) et étapes
BUG_REST = (SIDE + 8, TOP + 3)
BUG_LAND, BUG_LEAVE, BUG_GONE = int(1.2 * FPS), int(3.2 * FPS), int(4.0 * FPS)
BUG_END = int(4.4 * FPS)
STRETCH_MAX = 6          # lignes de pixels gagnées au plus fort de l'étirement


class ReactionsMixin:
    def pick_reaction(self):
        """Réaction spontanée : plutôt un étirement (et un bâillement) quand il est fatigué."""
        tired = self.stats["energie"] < 40
        weights = {"groom": 40, "stretch": 45 if tired else 25, "sneeze": 10,
                   "chase_tail": 5 if tired else 25, "cross_eyed": 15}
        return random.choices(list(weights), weights=list(weights.values()))[0]

    def start_reaction(self, kind=None, quiet=False):
        kind = kind or self.pick_reaction()
        if kind not in REACTIONS:
            return
        if self.state == "sleep":
            self.set_state("idle")
        if self.busy() and self.state != "crazy":
            return
        if self.y < self.ground() - 1:       # en plein saut : on attend qu'il soit posé
            return
        self.take_over()
        if kind == "groom":
            self.set_state("groom", random.randint(4 * FPS, 6 * FPS))
            if not quiet:
                self.say("groom", chance=0.5)
        elif kind == "stretch":
            self.set_state("stretch", int(2.6 * FPS))
            if not quiet:
                self.say("stretch", chance=0.6)
        elif kind == "sneeze":
            self.set_state("sneeze", int(2.2 * FPS))
            self.say_text(random.choice(["A... a...", "Ah... aah...", "Aaah..."]), secs=1.2)
        elif kind == "cross_eyed":
            side = random.choice((-1, 1))         # elle arrive d'un côté et repart de l'autre
            self.ladybug = {"from": (BUG_REST[0] + side * 16, BUG_REST[1] - 16),
                            "to": (BUG_REST[0] - side * 18, BUG_REST[1] - 18)}
            self.set_state("cross_eyed", BUG_END)
        elif kind == "chase_tail":
            self.chase_spin = random.randint(int(2.5 * FPS), int(3.5 * FPS))
            self.set_state("chase_tail", self.chase_spin + int(1.6 * FPS))
            if not quiet:
                self.say("chase_tail", chance=0.7)

    def end_reaction(self):
        self.set_state("idle")
        self.next_decision = random.randint(3 * FPS, 7 * FPS)

    # ---------------------------------------------------------- états
    def st_groom(self):
        if self.st_t >= self.st_len:
            self.change("bonheur", 3)
            self.end_reaction()

    def stretch_pose(self):
        """(lignes gagnées, bâillement ?) selon l'avancement de l'étirement."""
        up, top, down = int(0.5 * FPS), int(1.8 * FPS), int(2.3 * FPS)
        t = self.st_t
        if t < up:
            return round(STRETCH_MAX * t / up), False
        if t < top:
            return STRETCH_MAX, True
        if t < down:
            return round(STRETCH_MAX * (down - t) / (down - top)), False
        return 0, False

    def st_stretch(self):
        if self.st_t >= self.st_len:
            self.change("energie", 2)
            self.end_reaction()

    def st_sneeze(self):
        boom = int(1.0 * FPS)
        if self.st_t == boom:
            self.say("sneeze")
            for _ in range(4):           # postillons
                self.spawn("dust", SIDE + random.uniform(6, 14), TOP + random.uniform(10, 13),
                           vx=random.uniform(-0.5, 0.5), vy=random.uniform(-0.3, 0.1), life=12)
        if boom <= self.st_t < boom + 4:     # petit sursaut
            jolt = -self.S if self.st_t < boom + 2 else 0
            self.root.geometry(f"+{int(self.x)}+{int(self.y + jolt)}")
        if self.st_t >= self.st_len:
            self.move_window()
            self.end_reaction()

    def st_chase_tail(self):
        if self.st_t < self.chase_spin:
            if self.st_t % 3 == 0:
                rear = SIDE + (2 if self.facing == "right" else 25)
                self.spawn("dust", rear, CH - 4, vx=random.uniform(-0.4, 0.4), vy=-0.05, life=8)
        elif self.st_t == self.chase_spin:
            self.say("dizzy", chance=0.8)
        if self.st_t >= self.st_len:
            self.change("bonheur", 6)
            self.change("energie", -3)
            self.end_reaction()

    def st_cross_eyed(self):
        if self.st_t == BUG_LAND:
            self.say("cross_eyed", chance=0.8)
        if self.st_t >= self.st_len:
            self.ladybug = None
            self.change("bonheur", 3)
            self.say("cross_eyed_end", chance=0.5)
            self.end_reaction()

    def ladybug_pose(self):
        """(x, y, en vol ?) de la coccinelle, en pixels du canvas, selon l'avancement."""
        t, bug = self.st_t, self.ladybug
        if t < BUG_LAND:                          # elle arrive en volant
            k = t / BUG_LAND
            k = 1 - (1 - k) ** 2                  # elle ralentit en se posant
            (x0, y0), (x1, y1) = bug["from"], BUG_REST
        elif t < BUG_LEAVE:
            return BUG_REST[0], BUG_REST[1], False
        else:                                     # elle repart
            k = min(1.0, (t - BUG_LEAVE) / (BUG_GONE - BUG_LEAVE))
            k = k * k
            (x0, y0), (x1, y1) = BUG_REST, bug["to"]
        return x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, True

    def purr(self):
        """Ronronnement pendant les caresses : le chat vibre très légèrement."""
        if self.st_t % 2 == 0:
            dx = 1 if (self.st_t // 2) % 2 else -1
            self.root.geometry(f"+{int(self.x) + dx}+{int(self.y)}")

    # ---------------------------------------------------------- dessin
    def reaction_sprite(self):
        """(clé, construction, décalage vers le haut) pour les états de réaction, sinon None."""
        st, t = self.state, self.t
        if st == "groom":
            frame = (t // 6) % 2
            return ("groom", frame), lambda: sp.make_groom(frame), 0
        if st == "stretch":
            extra, yawn = self.stretch_pose()
            return ("stretch", extra, yawn), lambda: sp.make_stretch(extra, yawn), extra
        if st == "sneeze":
            if self.st_t < int(1.0 * FPS):          # ça monte...
                mouth = "open" if (t // 4) % 2 else "normal"
                return (("sit", "closed", mouth, "up", False),
                        lambda: sp.make_sit("closed", mouth, "up"), 0)
            return (("sit", "closed", "open", "side", False),
                    lambda: sp.make_sit("closed", "open", "side"), 0)
        if st == "cross_eyed":
            t0 = self.st_t
            if t0 < BUG_LAND * 0.45 or t0 >= BUG_GONE:
                look = "center"                   # il la voit arriver / la regarde partir
            elif t0 < BUG_LAND or t0 >= BUG_LEAVE:
                look = "in"
            else:                                 # posée sur son nez : il louche, ses yeux tremblotent
                look = "in" if (t0 // 7) % 5 == 0 else "down"
            mouth = "open" if BUG_LAND <= t0 < BUG_LAND + 8 else "normal"     # « oh ! »
            return (("louche", look, mouth),
                    lambda: sp.make_cross_eyed(look, mouth), 0)
        if st == "chase_tail":
            if self.st_t < self.chase_spin:          # il tourne sur lui-même
                self.facing = "right" if (t // 3) % 2 else "left"
                frame, facing = (t // 2) % 2, self.facing
                return ("walk", frame, facing), lambda: sp.make_walk(frame, facing), 0
            return (("sit", "cross", "open", "side", False),
                    lambda: sp.make_sit("cross", "open", "side"), 0)
        return None

    def reaction_extras(self):
        """Ce qui se dessine par-dessus le chat pendant une réaction (la coccinelle)."""
        if self.state != "cross_eyed" or not self.ladybug or self.st_t >= BUG_GONE:
            return []
        x, y, flying = self.ladybug_pose()
        if flying:
            frame = (self.t // 2) % 2           # battements d'ailes
            rows = sp.LADYBUG_FLY if frame else sp.LADYBUG
            return [(("ladybug", frame), lambda rows=rows: rows, x, y)]
        return [(("ladybug", 0), lambda: sp.LADYBUG, x, y)]
