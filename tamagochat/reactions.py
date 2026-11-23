"""Petites réactions : toilette, étirement (avec bâillement), éternuement, course après sa queue.

Il les fait tout seul de temps en temps quand il est tranquille ; on peut aussi les déclencher
depuis le menu ou la page admin. Ce sont des états courts, interrompus par n'importe quelle action.
"""
import random

from . import sprites as sp
from .config import CH, FPS, SIDE, TOP

REACTIONS = ("groom", "stretch", "sneeze", "chase_tail")
REACTION_LABELS = {"groom": "Faire sa toilette", "stretch": "S'étirer",
                   "sneeze": "Éternuer", "chase_tail": "Courir après sa queue"}
STRETCH_MAX = 6          # lignes de pixels gagnées au plus fort de l'étirement


class ReactionsMixin:
    def pick_reaction(self):
        """Réaction spontanée : plutôt un étirement (et un bâillement) quand il est fatigué."""
        tired = self.stats["energie"] < 40
        weights = {"groom": 40, "stretch": 45 if tired else 25, "sneeze": 10,
                   "chase_tail": 5 if tired else 25}
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
        if st == "chase_tail":
            if self.st_t < self.chase_spin:          # il tourne sur lui-même
                self.facing = "right" if (t // 3) % 2 else "left"
                frame, facing = (t // 2) % 2, self.facing
                return ("walk", frame, facing), lambda: sp.make_walk(frame, facing), 0
            return (("sit", "cross", "open", "side", False),
                    lambda: sp.make_sit("cross", "open", "side"), 0)
        return None
