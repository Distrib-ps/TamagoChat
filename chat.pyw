"""TamagoChat : un chat tamagotchi qui vit sur le bureau Windows.

Lancer : double-clic sur chat.pyw (ou `pythonw chat.pyw`).
Clic gauche = caresse, glisser = déplacer, clic droit = menu.
"""
import collections
import ctypes
import glob
import hashlib
import json
import os
import queue
import random
import re
import secrets
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
import urllib.request
from ctypes import wintypes

FROZEN = getattr(sys, "frozen", False)      # True dans la version .exe
HERE = os.path.dirname(os.path.abspath(__file__))
RES_DIR = getattr(sys, "_MEIPASS", HERE)     # fichiers embarqués dans l'exe
sys.path.insert(0, HERE)
import ed25519_min  # noqa: E402
import sprites as sp  # noqa: E402

APP_VERSION = "1.1.1"
# Adresse du serveur et clé publique des mises à jour : dans local_config.py (non versionné,
# voir local_config.example.py). Sans ce fichier, le chat fonctionne mais hors ligne.
try:
    import local_config as _cfg  # noqa: E402
except ImportError:
    _cfg = None
SERVER_URL = os.environ.get("MINOU_SERVER", getattr(_cfg, "SERVER_URL", "")).rstrip("/")
# Seul un exe signé par la clé privée correspondante (qui reste sur le PC du développeur)
# peut être installé automatiquement.
UPDATE_PUBKEY = getattr(_cfg, "UPDATE_PUBKEY", "")

APP_NAME = "ChatTamagotchi"
DATA_DIR = os.path.join(os.environ.get("APPDATA", HERE), APP_NAME)
SAVE_FILE = os.path.join(DATA_DIR, "save.json")
LOG_FILE = os.path.join(DATA_DIR, "erreurs.log")
ICON_FILE = os.path.join(RES_DIR, "chat.ico")
STARTUP_LNK = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup", "TamagoChat.lnk")
OLD_STARTUP_LNK = os.path.join(os.path.dirname(STARTUP_LNK), "Minou.lnk")   # avant le renommage

KEY = "#ff00ff"          # couleur rendue transparente par Windows
TICK_MS = 50
FPS = 1000 // TICK_MS

# Disposition du canvas, en "pixels de sprite"
CAT_W, CAT_H = 31, 24
SIDE, TOP = 16, 14
CW, CH = CAT_W + 2 * SIDE, CAT_H + TOP

STATS = ["satiete", "hydratation", "bonheur", "energie"]
STAT_LABELS = {"satiete": "Satiété", "hydratation": "Hydratation",
               "bonheur": "Bonheur", "energie": "Énergie"}
STAT_COLORS = {"satiete": "#e8a23c", "hydratation": "#4fa3e0",
               "bonheur": "#e8557a", "energie": "#7bc46a"}
DECAY_PER_S = {"satiete": 100 / (3 * 3600), "hydratation": 100 / (2.5 * 3600),
               "bonheur": 100 / (2 * 3600), "energie": 100 / (5 * 3600)}
SLEEP_GAIN_PER_S = 100 / (6 * 60)   # une sieste de 6 min recharge tout
SIZES = {"Petit": 0.75, "Moyen": 1.0, "Grand": 1.5}
CHATTER_PRESETS = [("Très souvent (~30 s)", 30), ("Souvent (~1 min)", 60),
                   ("Normal (~3 min)", 180), ("Rarement (~10 min)", 600),
                   ("Très rarement (~30 min)", 1800), ("Jamais", 0)]
CRAZY_PRESETS = [("Désactivé", 0), ("Rarement (~30 min)", 30),
                 ("Parfois (~10 min)", 10), ("Souvent (~3 min)", 3)]
FLY_PRESETS = [("Désactivées", 0), ("Rarement (~20 min)", 20),
               ("Parfois (~8 min)", 8), ("Souvent (~3 min)", 3)]
FLY_LIFETIME = 45      # secondes avant qu'une mouche s'envole
FLY_POOL = 5           # mouches max en même temps
# réglages modifiables depuis la page admin (si le propriétaire l'autorise)
REMOTE_SETTINGS = ("autowalk", "chatter_s", "crazy_min", "flies_min", "topmost", "size")

DEFAULTS = {
    "name": "Minou",
    "stats": {"satiete": 80, "hydratation": 80, "bonheur": 80, "energie": 80},
    "last_time": None,
    "x": None,
    "autowalk": True,
    "chatter_s": 180,    # délai moyen entre deux phrases spontanées (0 = jamais)
    "crazy_min": 10,     # délai moyen entre deux crises de folie (0 = désactivé)
    "flies_min": 8,      # délai moyen entre deux apparitions de mouches (0 = jamais)
    "topmost": True,
    "size": "Moyen",
    "phrases": {},   # catégories personnalisées : {clé: [phrases]}
    "remote_messages": True,   # recevoir messages / actions envoyés depuis le serveur
    "auto_update": True,
    "remote_settings": True,   # autoriser réglages / phrases / jauges modifiés à distance
    "remote_id": None,
    "remote_secret": None,
    "just_updated": None,
}

PHRASE_CATEGORIES = [
    ("idle", "Au repos (phrases au hasard)"),
    ("night", "La nuit (entre 23 h et 5 h)"),
    ("hungry", "Quand il a faim"),
    ("thirsty", "Quand il a soif"),
    ("bored", "Quand il s'ennuie"),
    ("tired", "Quand il est fatigué"),
    ("pet", "Quand on le caresse"),
    ("pet_too_much", "Quand il y a trop de caresses"),
    ("eat", "Après avoir mangé"),
    ("full", "Refuse de manger (plus faim)"),
    ("drink", "Après avoir bu"),
    ("not_thirsty", "Refuse de boire (pas soif)"),
    ("play", "Début du jeu avec la pelote"),
    ("play_end", "Fin du jeu"),
    ("too_tired", "Trop fatigué pour jouer"),
    ("sleep", "Va faire une sieste"),
    ("wake", "Se réveille tout seul"),
    ("woken", "Réveillé par toi"),
    ("drag", "Quand on le porte"),
    ("land", "Quand il atterrit"),
    ("back", "À ton retour (absence de plus de 2 h)"),
    ("morning", "Bonjour le matin (5 h - 11 h)"),
    ("noon", "Bonjour le midi (11 h - 14 h)"),
    ("afternoon", "Bonjour l'après-midi (14 h - 18 h)"),
    ("evening", "Bonsoir (18 h - 23 h)"),
    ("renamed", "Après l'avoir renommé"),
    ("crazy", "Mode FOU : pendant qu'il court partout"),
    ("crazy_end", "Mode FOU : quand il se calme"),
    ("fly_spot", "Mouches : quand il en repère une"),
    ("fly_eat", "Mouches : quand il en mange une"),
    ("fly_miss", "Mouches : quand il la rate"),
    ("fly_gone", "Mouches : quand elles s'envolent"),
    ("fly_swat", "Mouches : quand tu en écrases une"),
]

PHRASES = {
    "idle": [
        "Miaou !", "Mrrrp ?", "Je surveille ton écran, tout va bien.",
        "Tu travailles beaucoup aujourd'hui...", "J'ai vu une mouche passer !",
        "Tu sais que je t'aime bien, toi ?", "Ce bureau est à moi maintenant.",
        "*se lèche la patte*", "Prrrr...", "Et si on jouait ?",
        "Tu as pensé à faire une pause ?", "Je suis le meilleur chat du monde, non ?",
        "J'ai entendu un bruit bizarre...", "*regarde fixement le vide*",
        "Je peux m'asseoir sur ton clavier ?", "*bâille*",
        "Ta souris, elle se mange ?", "Je garde la barre des tâches.",
        "Tu as fermé combien d'onglets aujourd'hui ?", "Miaou miaou !",
        "Une petite caresse, ce serait pas de refus.",
    ],
    "night": ["Il est tard... tu devrais aller dormir, non ?",
              "Toi aussi tu es un animal nocturne ?", "Moi je dors, toi tu travailles..."],
    "hungry": ["J'ai faim...", "Mon ventre gargouille !", "Des croquettes, s'il te plaît ?",
               "Miaaaou ! (traduction : À MANGER)", "Je mangerais bien quelque chose..."],
    "thirsty": ["J'ai soif...", "Un peu d'eau fraîche ?", "Ma gamelle d'eau est vide !"],
    "bored": ["Je m'ennuie...", "Personne ne joue avec moi ?", "Une caresse ?",
              "Tu m'as oublié ?"],
    "tired": ["Je suis épuisé...", "*bâille* Je tombe de sommeil..."],
    "pet": ["Rrrrr... ronron...", "Encore ! Encore !", "Prrrrrrr <3",
            "Juste là, derrière l'oreille...", "Mmmh, c'est agréable.",
            "Tu as des mains magiques."],
    "pet_too_much": ["Bon, ça suffit les caresses !", "Hé, doucement !",
                     "J'ai besoin d'espace, là."],
    "eat": ["Miam ! C'était délicieux !", "Croc croc croc... merci !",
            "Mon plat préféré !", "Ah, ça va mieux."],
    "full": ["J'ai plus faim, merci.", "Je vais exploser si je mange encore !",
             "Non merci, j'ai le ventre plein."],
    "drink": ["Lap lap lap... merci !", "Ah, ça rafraîchit !", "Rien de tel qu'une eau bien fraîche."],
    "not_thirsty": ["J'ai pas soif.", "Plus tard, peut-être."],
    "play": ["Attrape ! Attrape !", "Je vais l'avoir !", "Elle ne m'échappera pas !"],
    "play_end": ["C'était trop bien !", "Encore une partie plus tard ?",
                 "Je suis le roi de la pelote !"],
    "too_tired": ["Trop fatigué pour jouer...", "Laisse-moi souffler un peu d'abord."],
    "sleep": ["Bonne nuit...", "Je vais faire une petite sieste.", "Zzz..."],
    "wake": ["Bien dormi !", "*s'étire* Me revoilà !", "Quelle bonne sieste !"],
    "woken": ["Mmh... tu m'as réveillé...", "Hein ? Quoi ? J'dormais pas !",
              "Encore cinq minutes..."],
    "drag": ["Hé ! Pose-moi !", "Wouaah, je vole !", "Où est-ce qu'on va ?", "Miaou ?!"],
    "land": ["Je retombe toujours sur mes pattes !", "Atterrissage parfait.", "Ouf !"],
    "back": ["Te revoilà ! Tu m'as manqué !",
             "Ah, enfin ! J'ai cru que tu m'avais oublié."],
    "morning": ["Bonjour ! Bien dormi ?", "Bonjour ! On commence la journée ?"],
    "noon": ["Coucou ! C'est bientôt l'heure de manger, non ?"],
    "afternoon": ["Coucou ! Me revoilà !"],
    "evening": ["Bonsoir !", "Bonsoir, la journée s'est bien passée ?"],
    "renamed": ["{name} ? J'adore mon nouveau nom !", "Appelle-moi {name} désormais."],
    "crazy": ["NYAAAAAAAA !!!", "ZOOMIES !!!", "J'AI VU UN FANTÔME !!",
              "ON COURT ! ON COURT !", "MIAOU MIAOU MIAOU MIAOU",
              "LE SOL C'EST DE LA LAVE !!!", "YOUPIIIIIII !"],
    "crazy_end": ["... quoi ?", "Il s'est passé quelque chose ?",
                  "*fait comme si de rien n'était*", "Je sais pas ce qui m'a pris.",
                  "Ouf. J'avais un trop-plein d'énergie."],
    "fly_spot": ["Une mouche !", "Oh ! Qu'est-ce que c'est que ça ?", "*fixe la mouche*",
                 "Bzzz ? Je t'ai vue, toi !", "Mode chasseur activé."],
    "fly_eat": ["Miam, une mouche !", "Gloups ! Croustillante.", "Je suis un grand chasseur !",
                "Et une de moins !", "Protéines !"],
    "fly_miss": ["Raté !", "Reviens ici !", "Grrr, elle est rapide !", "Je l'avais presque !"],
    "fly_gone": ["Elle s'est enfuie...", "La prochaine fois, je l'aurai."],
    "fly_swat": ["Hé ! C'était la mienne !", "Tu me voles mon goûter ?",
                 "Bien visé... mais c'était MA proie."],
}
NEED_PHRASE = {"satiete": "hungry", "hydratation": "thirsty",
               "bonheur": "bored", "energie": "tired"}

# ------------------------------------------------------------------ Win32
user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
kernel32.CreateMutexW.restype = wintypes.HANDLE
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, MONITORENUMPROC,
                                       wintypes.LPARAM]
_MUTEX = None


def list_monitors():
    """Tous les écrans : {"mon": rect complet, "work": rect sans la barre des tâches}."""
    mons = []

    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            m, w = mi.rcMonitor, mi.rcWork
            mons.append({"mon": (m.left, m.top, m.right, m.bottom),
                         "work": (w.left, w.top, w.right, w.bottom)})
        return True

    try:
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    except Exception:
        log_error()
    return mons


def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def already_running():
    global _MUTEX
    _MUTEX = kernel32.CreateMutexW(None, False, "Local\\ChatTamagotchiMinou")
    return ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS


def work_area_at(x, y):
    try:
        hmon = user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            r = mi.rcWork
            return r.left, r.top, r.right, r.bottom
    except Exception:
        pass
    return None


def make_tool_window(widget):
    """Pas d'icône dans Alt+Tab, et la fenêtre ne vole pas le focus."""
    try:
        widget.update_idletasks()
        hwnd = user32.GetParent(widget.winfo_id())
        GWL_EXSTYLE = -20
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x80 | 0x08000000)
    except Exception:
        pass


def log_error():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S]\n") + traceback.format_exc() + "\n")
    except Exception:
        pass


def pythonw_path():
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else sys.executable


def set_startup(enable):
    if enable:
        def q(s):
            return s.replace("'", "''")
        if FROZEN:
            target, args = sys.executable, ""
            workdir, icon = os.path.dirname(sys.executable), sys.executable
        else:
            target = pythonw_path()
            args = '"' + os.path.join(HERE, "chat.pyw") + '"'
            workdir, icon = HERE, ICON_FILE
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(STARTUP_LNK)}');"
              f"$s.TargetPath='{q(target)}';"
              f"$s.Arguments='{q(args)}';"
              f"$s.WorkingDirectory='{q(workdir)}';"
              f"$s.IconLocation='{q(icon)}';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       creationflags=0x08000000, check=False)
    elif os.path.exists(STARTUP_LNK):
        os.remove(STARTUP_LNK)


def load_save():
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        for k, v in saved.items():
            if k == "stats":
                data["stats"].update({s: float(v.get(s, 80)) for s in STATS})
            elif k == "phrases":
                if isinstance(v, dict):
                    data["phrases"] = {key: [str(p) for p in lst] for key, lst in v.items()
                                       if key in PHRASES and isinstance(lst, list)}
            elif k in data:
                data[k] = v
        if saved.get("silent") and "chatter_s" not in saved:  # ancien "mode silencieux"
            data["chatter_s"] = 0
    except FileNotFoundError:
        pass
    except Exception:
        log_error()
    return data


def fmt_delay(secs):
    if secs <= 0:
        return "jamais"
    if secs < 60:
        return f"{secs:.0f} s"
    return f"{secs / 60:g} min".replace(".", ",")


def round_rect(c, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return c.create_polygon(pts, smooth=True, **kw)


# ------------------------------------------------------------------ bulle
class Bubble:
    def __init__(self, app):
        self.app = app
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        w.configure(bg=KEY)
        w.attributes("-transparentcolor", KEY)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", app.quit)   # extinction du PC, taskkill...
        self.c = tk.Canvas(w, bg=KEY, highlightthickness=0, bd=0, cursor="hand2")
        self.c.pack()
        self.c.bind("<Button-1>", lambda e: self.hide())
        d = app.dpi
        self.pad, self.tail, self.maxw = int(10 * d), int(10 * d), int(230 * d)
        self.font = ("Segoe UI", 10)
        self.visible = False
        self.until = 0
        self.locked_until = 0
        self.geom = None
        self.tail_x = None
        self.hide()
        make_tool_window(w)

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


def make_photo(rows, s):
    w, h = len(rows[0]), len(rows)
    img = tk.PhotoImage(width=w * s, height=h * s)
    pal = sp.PALETTE
    lines = []
    for row in rows:
        line = "{" + " ".join(" ".join([pal.get(ch, KEY)] * s) for ch in row) + "}"
        lines.extend([line] * s)
    img.put(" ".join(lines))
    return img


# ------------------------------------------------------------------ connexion au serveur
def version_tuple(v):
    return tuple(int(x) for x in re.findall(r"\d+", str(v))) or (0,)


class Remote(threading.Thread):
    """Fil réseau : reçoit messages/actions (long polling) et télécharge les mises à jour.

    Ne touche jamais à Tk : tout passe par la file `inbox`, lue par la boucle principale.
    """

    def __init__(self, snapshot):
        super().__init__(daemon=True)
        self.snapshot = snapshot      # remplacé régulièrement par le fil principal
        self.inbox = queue.Queue()
        self.ack = []
        self.seen = collections.deque(maxlen=300)
        self.failed_versions = set()
        self.wakeup = threading.Event()
        self.sent_prev = None         # version des phrases déjà envoyée au serveur
        self.start()

    def request(self, path, body=None, timeout=20):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(SERVER_URL + path, data=data, headers={
            "Content-Type": "application/json", "User-Agent": f"TamagoChat/{APP_VERSION}"})
        return urllib.request.urlopen(req, timeout=timeout)

    def post(self, path, body, timeout=20):
        with self.request(path, body, timeout) as r:
            return json.load(r)

    def pause(self, secs):
        self.wakeup.wait(secs)
        self.wakeup.clear()

    def run(self):
        if not SERVER_URL:             # pas de serveur configuré : chat 100 % local
            return
        delay = 5
        while True:
            snap = self.snapshot
            if not (snap["accept"] or snap["auto_update"]):
                self.pause(30)
                continue
            try:
                body = {k: v for k, v in snap.items() if not k.startswith("_")}
                if snap.get("_prev") != self.sent_prev:      # phrases modifiées : on les envoie
                    body["phrases"] = snap["_phrases"]
                res = self.post("/api/sync", dict(body, ack=self.ack, wait=snap["accept"]),
                                timeout=45)
                self.sent_prev = snap.get("_prev")
                self.ack = []
                msgs = res.get("messages", [])
                for m in msgs:
                    self.ack.append(m["id"])
                    if m["id"] not in self.seen:
                        self.seen.append(m["id"])
                        self.inbox.put(("message", m))
                if msgs:
                    # laisse le fil principal les appliquer, pour renvoyer tout de suite le
                    # nouvel état (réglages, jauges...) au lieu d'attendre le prochain tour
                    self.wakeup.clear()
                    self.wakeup.wait(1.5)
                    self.wakeup.clear()
                upd = res.get("update")
                if upd and snap["auto_update"]:
                    self.check_update(upd)
                delay = 5
                if not snap["accept"]:
                    self.pause(1800)          # seulement les mises à jour : on vérifie de temps en temps
            except Exception:
                self.pause(delay)             # serveur injoignable : on réessaie de plus en plus tard
                delay = min(delay * 2, 300)

    def check_update(self, upd):
        v = str(upd.get("version", ""))
        if (not FROZEN or not UPDATE_PUBKEY or v in self.failed_versions
                or version_tuple(v) <= version_tuple(APP_VERSION)):
            return
        tmp = sys.executable + ".update"
        try:
            h, size = hashlib.sha256(), 0
            with self.request(upd["url"], timeout=60) as r, open(tmp, "wb") as f:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 200 * 1024 * 1024:
                        raise ValueError("fichier trop gros")
                    f.write(chunk)
                    h.update(chunk)
            sha = h.hexdigest()
            if sha != upd["sha256"] or size != upd["size"]:
                raise ValueError("fichier corrompu")
            msg = f"minou-update|{v}|{sha}".encode()
            if not ed25519_min.verify(bytes.fromhex(UPDATE_PUBKEY), msg, bytes.fromhex(upd["sig"])):
                raise ValueError("signature invalide : mise à jour refusée")
            self.inbox.put(("update", tmp, v))
            self.failed_versions.add(v)       # ne pas la retélécharger en attendant l'installation
        except Exception:
            self.failed_versions.add(v)
            log_error()
            try:
                os.remove(tmp)
            except OSError:
                pass

    def send_reply(self, text):
        def job():
            try:
                self.post("/api/reply", dict(self.snapshot, text=text))
                self.inbox.put(("reply_result", True))
            except Exception:
                self.inbox.put(("reply_result", False))
        threading.Thread(target=job, daemon=True).start()


# ------------------------------------------------------------------ mouche
class Fly:
    """Une mouche dans sa propre petite fenêtre (réutilisée, jamais recréée)."""

    def __init__(self, app):
        self.app = app
        w = self.win = tk.Toplevel(app.root)
        w.overrideredirect(True)
        w.configure(bg=KEY)
        w.attributes("-transparentcolor", KEY)
        w.attributes("-topmost", True)
        w.protocol("WM_DELETE_WINDOW", app.quit)
        self.c = tk.Canvas(w, bg=KEY, highlightthickness=0, bd=0, cursor="hand2")
        self.c.pack()
        self.c.bind("<Button-1>", lambda e: app.swat(self))
        self.state = "dead"     # dead / buzz / leave
        self.item = None
        self.scale = None
        self.frame = -1
        self.geom = None
        self.hide()
        make_tool_window(w)

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
            self.c.delete("all")
            self.item = self.c.create_image(0, 0, anchor="nw")
            self.frame = -1
        frame = self.t % 2
        if frame != self.frame:
            self.frame = frame
            self.c.itemconfig(self.item, image=self.app.fly_image(frame, fs))
        geom = f"{fw * fs}x{fh * fs}+{int(self.x - fw * fs / 2)}+{int(self.y - fh * fs / 2)}"
        if geom != self.geom:
            self.geom = geom
            self.win.geometry(geom)


# ------------------------------------------------------------------ application
class App:
    def __init__(self):
        self.data = load_save()
        self.stats = self.data["stats"]

        r = self.root = tk.Tk()
        r.withdraw()
        r.overrideredirect(True)
        r.configure(bg=KEY)
        r.attributes("-transparentcolor", KEY)
        r.attributes("-topmost", bool(self.data["topmost"]))
        r.title("TamagoChat")
        r.protocol("WM_DELETE_WINDOW", self.quit)   # fermeture propre (sauvegarde)
        self.dpi = r.winfo_fpixels("1i") / 96.0
        self.images = {}

        self.canvas = tk.Canvas(r, bg=KEY, highlightthickness=0, bd=0, cursor="hand2")
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
        self.monitors = list_monitors()
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
        self.fly_images = {}
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
        self.cleanup_update_files()
        if os.path.exists(OLD_STARTUP_LNK):          # raccourci de démarrage de l'ancien nom
            def migrate():
                try:
                    os.remove(OLD_STARTUP_LNK)
                    set_startup(True)
                except Exception:
                    log_error()
            threading.Thread(target=migrate, daemon=True).start()
        r.after(60_000, self.cleanup_update_files)   # l'ancien exe peut être encore verrouillé

        c = self.canvas
        c.bind("<ButtonPress-1>", self.on_press)
        c.bind("<B1-Motion>", self.on_motion)
        c.bind("<ButtonRelease-1>", self.on_release)
        c.bind("<Button-3>", self.show_menu)

        # absence depuis la dernière fois
        last = self.data.get("last_time")
        away = time.time() - last if last else 0
        if away > 60:
            self.apply_absence(away)
        r.after(900, lambda: self.greet(away))
        r.after(TICK_MS, self.tick)
        r.after(60_000, self.autosave)

    # ---------------------------------------------------------- géométrie
    def apply_size(self, keep_ground=True):
        old_h = CH * self.S
        factor = SIZES.get(self.data["size"], 1.0)
        self.S = max(2, round(4 * self.dpi * factor))
        self.images.clear()
        self.canvas.config(width=CW * self.S, height=CH * self.S)
        if keep_ground:
            self.y += old_h - CH * self.S
            self.move_window()

    def area(self):
        cx = self.x + (SIDE + 12) * self.S
        cy = self.y + CH * self.S - 2
        a = work_area_at(cx, cy)
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
            self.monitors = list_monitors()
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

    def head_screen_pos(self):
        if self.state == "sleep":
            col, row = 12, 6
        elif self.uses_walk_sprite():
            col, row = (23, 4) if self.facing == "right" else (7, 4)
        else:
            col, row = 12, 1
        return self.x + (SIDE + col) * self.S, self.y + (TOP + row) * self.S

    # ---------------------------------------------------------- stats
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

    # ---------------------------------------------------------- parole
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
            self.monitors = list_monitors()
        self.talk = max(0, self.talk - 1)
        if self.blink > 0:
            self.blink -= 1
        elif random.random() < 0.012:
            self.blink = 3

        for f in self.flies:
            f.update()
        if self.t % 20 == 0:
            self.remote.snapshot = self.remote_snapshot()
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

    # ---------------------------------------------------------- chasse aux mouches
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

    # ---------------------------------------------------------- à distance
    def remote_snapshot(self):
        d = self.data
        return {"cat_id": d["remote_id"], "secret": d["remote_secret"],
                "name": d["name"], "version": APP_VERSION, "state": self.state,
                "stats": {k: round(v, 1) for k, v in self.stats.items()},
                "accept": bool(d["remote_messages"]),
                "auto_update": bool(d["auto_update"]),
                "allow_settings": bool(d["remote_settings"]),
                "settings": {k: d[k] for k in REMOTE_SETTINGS},
                "_prev": self.phrases_rev, "_phrases": self.phrases_payload()}

    def phrases_payload(self):
        """Toutes les phrases (origine + perso), recalculées seulement quand elles changent."""
        if self._pp_rev != self.phrases_rev:
            self._pp = {"cats": [list(c) for c in PHRASE_CATEGORIES],
                        "list": {k: list(self.phrases(k)) for k, _ in PHRASE_CATEGORIES},
                        "custom": sorted(self.data["phrases"])}
            self._pp_rev = self.phrases_rev
        return self._pp

    def push_state(self):
        """Renvoie tout de suite l'état au serveur (après un changement à distance)."""
        self.remote.snapshot = self.remote_snapshot()
        self.remote.wakeup.set()

    def handle_remote(self, kind, *args):
        if kind == "message":
            m = args[0]
            k = m.get("kind")
            if k == "say":
                frm = str(m.get("from") or "").strip()
                text = str(m.get("text") or "")
                if frm:
                    self.last_sender = frm
                    text = f"Message de {frm} :\n{text}"
                if self.state == "sleep":
                    self.set_state("idle")
                self.spawn("sparkle", SIDE + 18, TOP + 1, vy=-0.15, life=14)
                secs = m.get("secs")
                if not isinstance(secs, (int, float)) or not 3 <= secs <= 600:
                    secs = min(30, 5 + len(text) * 0.08)
                self.say_text(text, priority=True, secs=secs)
            elif k == "action":
                self.remote_action(m.get("action"))
            elif k in ("settings", "phrases", "stats") and self.data["remote_settings"]:
                try:
                    getattr(self, "remote_" + k)(m)
                except Exception:
                    log_error()
            self.push_state()
        elif kind == "update":
            path, version = args
            self.say_text(f"Une nouvelle version ({version}) ! Je me mets à jour, à tout de suite...",
                          priority=True, secs=5)
            self.root.after(3500, lambda: self.apply_update(path, version))
        elif kind == "reply_result":
            self.say_text("Message envoyé !" if args[0] else
                          "Impossible d'envoyer le message (pas de connexion ?)", priority=True)

    def remote_settings(self, m):
        s = m.get("settings")
        if not isinstance(s, dict):
            return
        d = self.data
        name = str(s.get("name") or "").strip()[:24]
        if name and name != d["name"]:
            d["name"] = name
            self.say("renamed")
        for k in ("autowalk", "topmost"):
            if isinstance(s.get(k), bool):
                d[k] = s[k]
        self.root.attributes("-topmost", bool(d["topmost"]))
        v = s.get("chatter_s")
        if isinstance(v, int) and not isinstance(v, bool) and (v == 0 or 15 <= v <= 86400):
            d["chatter_s"] = v
            self.schedule_chatter()
        for k, sched in (("crazy_min", self.schedule_crazy), ("flies_min", self.schedule_flies)):
            v = s.get(k)
            if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 1440:
                d[k] = v
                sched()
        if s.get("size") in SIZES and s["size"] != d["size"]:
            d["size"] = s["size"]
            self.apply_size(keep_ground=self.state != "hidden")   # caché : ne pas le montrer
        self.save()

    def remote_phrases(self, m):
        key = m.get("key")
        if key not in PHRASES:
            return
        if m.get("reset"):
            self.data["phrases"].pop(key, None)
        elif isinstance(m.get("list"), list):
            self.data["phrases"][key] = [str(p).strip()[:200] for p in m["list"]
                                         if str(p).strip()][:100]
        else:
            return
        self.phrases_rev += 1
        self.save()

    def remote_stats(self, m):
        st = m.get("stats")
        if not isinstance(st, dict):
            return
        for k in STATS:
            v = st.get(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                self.stats[k] = max(0.0, min(100.0, float(v)))
        if self.state == "sleep" and self.stats["energie"] >= 100:
            self.wake("wake")
        self.spawn("sparkle", SIDE + 10, TOP + 2, vy=-0.2, life=12)
        self.save()

    def remote_action(self, action):
        if self.state == "drag":            # il est tenu à la souris : on ne fait rien
            return
        if self.state == "hidden" and action != "hide":
            self.unhide(quiet=True)
        if action == "crazy":
            if self.state != "crazy":
                self.act_crazy()
        elif action == "crazy_xl":
            self.act_crazy(xl=True)
        elif action == "flies":
            self.spawn_flies(manual=True)
        elif action == "swarm":
            self.spawn_flies(manual=True, count=FLY_POOL)
        elif action == "sleep":
            if self.state != "sleep" and not self.busy():
                self.say("sleep")
                self.set_state("sleep")
        elif action == "wake":
            if self.state == "sleep":
                self.wake("wake")
        elif action == "pet":
            self.act_pet()
        elif action == "love":
            self.love_bomb()
        elif action == "feed":
            self.act_feed()
        elif action == "drink":
            self.act_drink()
        elif action == "play":
            if self.state == "sleep":
                self.set_state("idle")
            self.act_play()
        elif action == "meow":
            self.say_text(random.choice(["Miaou !", "MIAOU !", "Miaaaou ?", "Mrrrp !"]),
                          priority=True)
        elif action == "jump":
            self.big_jump()
        elif action == "drop":
            self.drop_from_sky()
        elif action == "screen":
            self.drop_from_sky(other_screen=True)
        elif action == "mouse":
            self.run_to_mouse()
        elif action == "hide":
            self.hide_and_seek()

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
        self.monitors = list_monitors() or self.monitors
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
        target = work_area_at(px, py)
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
        self.monitors = list_monitors() or self.monitors
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

    def apply_update(self, path, version):
        """Remplace l'exe par la nouvelle version (déjà vérifiée) puis redémarre."""
        exe = sys.executable
        old = exe + f".{int(time.time())}.old"
        try:
            os.replace(exe, old)          # Windows autorise à renommer un exe en cours d'exécution
            try:
                os.replace(path, exe)
            except Exception:
                os.replace(old, exe)      # on remet l'ancien
                raise
        except Exception:
            log_error()
            self.say_text("La mise à jour a échoué, je reste comme je suis.", priority=True)
            return
        self.data["just_updated"] = version
        self.save()
        env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI", "_MEI"))}
        env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        try:
            kernel32.CloseHandle(_MUTEX)  # laisse la nouvelle version démarrer
            subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env, close_fds=True,
                             creationflags=0x00000008 | 0x00000200)  # détaché
        except Exception:
            log_error()
        self._quitting = True
        self.root.destroy()

    def cleanup_update_files(self):
        if not FROZEN:
            return
        for f in glob.glob(glob.escape(sys.executable) + ".*.old") + [sys.executable + ".update"]:
            try:
                os.remove(f)
            except OSError:
                pass

    def open_reply(self):
        from tkinter import ttk
        if self.reply_win and self.reply_win.winfo_exists():
            self.reply_win.lift()
            return
        w = self.reply_win = tk.Toplevel(self.root)
        w.title("Envoyer un message")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        frm = ttk.Frame(w, padding=14)
        frm.pack()
        to = f"à {self.last_sender}" if self.last_sender else "à la personne qui t'envoie des messages"
        ttk.Label(frm, text=f"Ton message sera envoyé {to} :",
                  font=("Segoe UI", 10)).pack(anchor="w")
        txt = tk.Text(frm, width=46, height=4, font=("Segoe UI", 10), wrap="word")
        txt.pack(pady=8)

        def send(_=None):
            text = txt.get("1.0", "end").strip()[:500]
            if text:
                self.remote.send_reply(text)
                w.destroy()
            return "break"

        ttk.Button(frm, text="Envoyer", command=send).pack(anchor="e")
        txt.bind("<Control-Return>", send)
        w.bind("<Escape>", lambda _: w.destroy())
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 220)}+{max(0, y - 220)}")
        w.after(50, lambda: (w.focus_force(), txt.focus_set()))

    def set_remote_opt(self, key, value):
        self.data[key] = value
        self.save()
        self.remote.snapshot = self.remote_snapshot()
        self.remote.wakeup.set()

    # ---------------------------------------------------------- actions
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

    # ---------------------------------------------------------- souris
    def on_press(self, e):
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

    # ---------------------------------------------------------- dessin
    def image(self, key, build):
        img = self.images.get(key)
        if img is None:
            img = self.images[key] = make_photo(build(), self.S)
        return img

    def fly_image(self, frame, fs):
        img = self.fly_images.get((frame, fs))
        if img is None:
            img = self.fly_images[(frame, fs)] = make_photo(sp.FLY[frame], fs)
        return img

    def blit(self, key, build, ux, uy):
        self.canvas.create_image(round(ux * self.S), round(uy * self.S),
                                 image=self.image(key, build), anchor="nw")

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
        self.canvas.delete("all")
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

    # ---------------------------------------------------------- menu
    def show_menu(self, e):
        name = self.data["name"]
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Caresser {name}", command=self.act_pet)
        m.add_command(label="Donner à manger", command=self.act_feed)
        m.add_command(label="Donner à boire", command=self.act_drink)
        m.add_command(label="Jouer avec la pelote", command=self.act_play)
        m.add_command(label="Le réveiller" if self.state == "sleep" else "Faire une sieste",
                      command=self.act_sleep)
        m.add_command(label="Le calmer !" if self.state == "crazy" else "Crise de folie !",
                      command=self.act_crazy)
        m.add_command(label="Lâcher des mouches", command=lambda: self.spawn_flies(manual=True))
        m.add_separator()
        m.add_command(label="Voir son état...", command=self.open_stats)
        m.add_command(label="Le renommer...", command=self.open_rename)
        m.add_command(label="Ses phrases...", command=self.open_phrases)
        if SERVER_URL and self.data["remote_messages"]:
            m.add_command(label="Envoyer un message...", command=self.open_reply)

        opts = tk.Menu(m, tearoff=0)
        self.v_walk = tk.BooleanVar(value=self.data["autowalk"])
        self.v_top = tk.BooleanVar(value=self.data["topmost"])
        self.v_start = tk.BooleanVar(value=os.path.exists(STARTUP_LNK))
        self.v_size = tk.StringVar(value=self.data["size"])
        opts.add_checkbutton(label="Se promène tout seul", variable=self.v_walk,
                             command=lambda: self.set_opt("autowalk", self.v_walk.get()))

        cur = self.data["chatter_s"]
        presets = [s for _, s in CHATTER_PRESETS]
        self.v_chat = tk.IntVar(value=cur if cur in presets else -1)
        chat_m = tk.Menu(opts, tearoff=0)
        for label, secs in CHATTER_PRESETS:
            chat_m.add_radiobutton(label=label, value=secs, variable=self.v_chat,
                                   command=lambda s=secs: self.set_chatter(s))
        chat_m.add_separator()
        custom = "Personnalisé..." if cur in presets else f"Personnalisé ({fmt_delay(cur)})..."
        chat_m.add_radiobutton(label=custom, value=-1, variable=self.v_chat,
                               command=self.open_chatter_custom)
        opts.add_cascade(label="Fréquence des phrases spontanées", menu=chat_m)

        self.v_crazy = tk.IntVar(value=self.data["crazy_min"])
        crazy_m = tk.Menu(opts, tearoff=0)
        for label, mins in CRAZY_PRESETS:
            crazy_m.add_radiobutton(label=label, value=mins, variable=self.v_crazy,
                                    command=lambda m_=mins: self.set_crazy(m_))
        crazy_m.add_separator()
        crazy_m.add_command(label="Crise de folie maintenant !", command=self.act_crazy)
        opts.add_cascade(label="Mode FOU", menu=crazy_m)

        self.v_flies = tk.IntVar(value=self.data["flies_min"])
        flies_m = tk.Menu(opts, tearoff=0)
        for label, mins in FLY_PRESETS:
            flies_m.add_radiobutton(label=label, value=mins, variable=self.v_flies,
                                    command=lambda m_=mins: self.set_flies(m_))
        flies_m.add_separator()
        flies_m.add_command(label="Lâcher des mouches maintenant",
                            command=lambda: self.spawn_flies(manual=True))
        opts.add_cascade(label="Mouches", menu=flies_m)
        opts.add_separator()
        if SERVER_URL:            # options inutiles sans serveur (voir local_config.example.py)
            self.v_remote = tk.BooleanVar(value=self.data["remote_messages"])
            self.v_update = tk.BooleanVar(value=self.data["auto_update"])
            self.v_rset = tk.BooleanVar(value=self.data["remote_settings"])
            opts.add_checkbutton(label="Recevoir des messages à distance", variable=self.v_remote,
                                 command=lambda: self.set_remote_opt("remote_messages",
                                                                     self.v_remote.get()))
            opts.add_checkbutton(label="Mises à jour automatiques", variable=self.v_update,
                                 command=lambda: self.set_remote_opt("auto_update",
                                                                     self.v_update.get()))
            opts.add_checkbutton(label="Autoriser les réglages à distance", variable=self.v_rset,
                                 command=lambda: self.set_remote_opt("remote_settings",
                                                                     self.v_rset.get()))
        opts.add_command(label=f"Version {APP_VERSION}", state="disabled")
        opts.add_separator()
        opts.add_checkbutton(label="Toujours au premier plan", variable=self.v_top,
                             command=self.toggle_topmost)
        opts.add_checkbutton(label="Lancer au démarrage de Windows", variable=self.v_start,
                             command=lambda: set_startup(self.v_start.get()))
        sizes = tk.Menu(opts, tearoff=0)
        for label in SIZES:
            sizes.add_radiobutton(label=label, value=label, variable=self.v_size,
                                  command=self.change_size)
        opts.add_cascade(label="Taille", menu=sizes)
        m.add_cascade(label="Options", menu=opts)
        m.add_separator()
        m.add_command(label="Quitter", command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def set_opt(self, key, value):
        self.data[key] = value
        self.save()

    def set_chatter(self, secs):
        self.data["chatter_s"] = int(secs)
        self.schedule_chatter()
        self.save()

    def set_flies(self, mins):
        self.data["flies_min"] = mins
        self.schedule_flies()
        self.save()

    def set_crazy(self, mins):
        self.data["crazy_min"] = mins
        self.schedule_crazy()
        self.save()

    def open_chatter_custom(self):
        from tkinter import ttk
        w = tk.Toplevel(self.root)
        w.title("Fréquence des phrases")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        font = ("Segoe UI", 10)
        frm = ttk.Frame(w, padding=14)
        frm.pack()
        ttk.Label(frm, text=f"{self.data['name']} dit une phrase spontanée environ toutes les :",
                  font=font).grid(row=0, column=0, columnspan=2, sticky="w")
        cur = self.data["chatter_s"] or 180
        v = tk.StringVar(value=f"{cur / 60:g}")
        spin = ttk.Spinbox(frm, from_=0.5, to=240, increment=0.5, textvariable=v,
                           width=7, font=font)
        spin.grid(row=1, column=0, sticky="w", pady=8)
        ttk.Label(frm, text="minutes", font=font).grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(frm, text="Les réponses à tes actions (caresses, repas...) ne sont pas concernées.",
                  font=("Segoe UI", 9), foreground="#6b5a4e").grid(row=2, column=0, columnspan=2,
                                                                   sticky="w")

        def ok(_=None):
            try:
                mins = float(v.get().replace(",", "."))
            except ValueError:
                return
            self.set_chatter(max(15, min(mins * 60, 24 * 3600)))
            w.destroy()

        ttk.Button(frm, text="OK", command=ok).grid(row=3, column=0, columnspan=2, pady=(10, 0))
        spin.bind("<Return>", ok)
        w.bind("<Escape>", lambda _: w.destroy())
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 200)}+{max(0, y - 200)}")
        w.after(50, lambda: (w.focus_force(), spin.focus_set(), spin.selection_range(0, "end")))

    def toggle_topmost(self):
        self.data["topmost"] = self.v_top.get()
        self.root.attributes("-topmost", self.data["topmost"])
        self.save()

    def change_size(self):
        self.data["size"] = self.v_size.get()
        self.apply_size()
        self.save()

    # ---------------------------------------------------------- fenêtres annexes
    def open_stats(self):
        if self.stats_win and self.stats_win.winfo_exists():
            self.stats_win.lift()
            return
        w = self.stats_win = tk.Toplevel(self.root)
        w.title(f"{self.data['name']} : état")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        w.configure(bg="#fff8ef")
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        d = self.dpi
        width, height = int(300 * d), int(205 * d)
        c = tk.Canvas(w, width=width, height=height, bg="#fff8ef", highlightthickness=0)
        c.pack(padx=int(10 * d), pady=int(10 * d))
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - width // 2)}+{max(0, y - height - int(60 * d))}")

        def refresh():
            if not w.winfo_exists():
                return
            c.delete("all")
            c.create_text(0, 0, anchor="nw", text=self.data["name"],
                          font=("Segoe UI", 14, "bold"), fill="#3b2a22")
            for i, k in enumerate(STATS):
                top = int((38 + i * 34) * d)
                v = self.stats[k]
                c.create_text(0, top, anchor="nw", text=STAT_LABELS[k],
                              font=("Segoe UI", 10), fill="#3b2a22")
                bx, bw, bh = int(100 * d), int(160 * d), int(16 * d)
                c.create_rectangle(bx, top + 2, bx + bw, top + 2 + bh,
                                   fill="#eee2d4", outline="#3b2a22", width=2)
                if v > 0.5:
                    c.create_rectangle(bx + 2, top + 4, bx + 2 + (bw - 4) * v / 100,
                                       top + bh, fill=STAT_COLORS[k], outline="")
                c.create_text(bx + bw + int(6 * d), top, anchor="nw", text=f"{v:.0f}",
                              font=("Segoe UI", 10), fill="#3b2a22")
            avg = sum(self.stats.values()) / 4
            mood = ("Aux anges" if avg > 85 else "Content" if avg > 65 else "Ça va"
                    if avg > 45 else "Grognon" if avg > 25 else "Malheureux")
            if self.state == "sleep":
                mood += " (il dort)"
            c.create_text(0, int(178 * d), anchor="nw", text=f"Humeur : {mood}",
                          font=("Segoe UI", 10, "italic"), fill="#3b2a22")
            w.after(500, refresh)

        refresh()

    def open_rename(self):
        w = tk.Toplevel(self.root)
        w.title("Renommer")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        tk.Label(w, text="Nouveau nom :", font=("Segoe UI", 10)).pack(padx=12, pady=(12, 4))
        v = tk.StringVar(value=self.data["name"])
        ent = tk.Entry(w, textvariable=v, font=("Segoe UI", 11), width=22)
        ent.pack(padx=12)
        ent.select_range(0, "end")

        def ok(_=None):
            name = v.get().strip()[:24]
            if name:
                self.data["name"] = name
                self.save()
                self.say("renamed")
            w.destroy()

        tk.Button(w, text="OK", width=10, command=ok).pack(pady=10)
        ent.bind("<Return>", ok)
        ent.bind("<Escape>", lambda _: w.destroy())
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 100)}+{max(0, y - 150)}")
        w.after(50, lambda: (w.focus_force(), ent.focus_set()))

    def open_phrases(self):
        from tkinter import messagebox, ttk
        if self.phrases_win and self.phrases_win.winfo_exists():
            self.phrases_win.lift()
            return
        w = self.phrases_win = tk.Toplevel(self.root)
        w.title(f"Les phrases de {self.data['name']}")
        w.attributes("-topmost", True)
        w.minsize(480, 380)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        font = ("Segoe UI", 10)
        frm = ttk.Frame(w, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(1, weight=1)

        labels = [label for _, label in PHRASE_CATEGORIES]
        key_of = {label: key for key, label in PHRASE_CATEGORIES}
        v_cat = tk.StringVar(value=labels[0])
        ttk.Label(frm, text="Situation :", font=font).grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(frm, values=labels, textvariable=v_cat, state="readonly",
                             font=font, height=20)
        combo.grid(row=0, column=1, columnspan=4, sticky="we", pady=(0, 8), padx=(6, 0))

        lb = tk.Listbox(frm, font=font, activestyle="none", exportselection=False, height=12)
        sb = ttk.Scrollbar(frm, orient="vertical", command=lb.yview)
        lb.config(yscrollcommand=sb.set)
        lb.grid(row=1, column=0, columnspan=4, sticky="nsew")
        sb.grid(row=1, column=4, sticky="ns")

        v_text = tk.StringVar()
        ent = ttk.Entry(frm, textvariable=v_text, font=font)
        ent.grid(row=2, column=0, columnspan=5, sticky="we", pady=8)

        status = ttk.Label(frm, font=("Segoe UI", 9), foreground="#6b5a4e")

        def key():
            return key_of[v_cat.get()]

        def current():
            return list(self.phrases(key()))

        def store(lst, select=None):
            self.data["phrases"][key()] = lst
            self.phrases_rev += 1
            self.save()
            refresh(select)

        def refresh(select=None):
            lst = current()
            lb.delete(0, "end")
            for p in lst:
                lb.insert("end", p)
            if select is not None and lst:
                select = max(0, min(select, len(lst) - 1))
                lb.selection_set(select)
                lb.see(select)
            perso = key() in self.data["phrases"]
            n = len(lst)
            txt = f"{n} phrase{'s' if n > 1 else ''}"
            txt += " (personnalisées)" if perso else " (celles d'origine)"
            if n == 0:
                txt += " : il ne dira rien dans cette situation"
            status.config(text=txt)

        def selected():
            sel = lb.curselection()
            return sel[0] if sel else None

        def on_select(_=None):
            i = selected()
            if i is not None:
                v_text.set(lb.get(i))

        def add(_=None):
            text = v_text.get().strip()[:200]
            if not text:
                return
            lst = current() + [text]
            store(lst, len(lst) - 1)
            v_text.set("")
            ent.focus_set()

        def modify():
            i, text = selected(), v_text.get().strip()[:200]
            if i is None or not text:
                return
            lst = current()
            lst[i] = text
            store(lst, i)

        def delete():
            i = selected()
            if i is None:
                return
            lst = current()
            del lst[i]
            store(lst, i)
            v_text.set("")

        def test():
            i = selected()
            text = v_text.get().strip() or (lb.get(i) if i is not None else "")
            if text:
                if self.state == "sleep":
                    self.set_state("idle")
                self.say_text(text)

        def reset():
            if key() not in self.data["phrases"]:
                return
            if messagebox.askyesno("Rétablir", "Remettre les phrases d'origine pour cette "
                                   "situation ?\nTes phrases perso de cette situation seront "
                                   "effacées.", parent=w):
                self.data["phrases"].pop(key(), None)
                self.phrases_rev += 1
                self.save()
                refresh()

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=5, sticky="we")
        ttk.Button(btns, text="Ajouter", command=add).pack(side="left")
        ttk.Button(btns, text="Modifier", command=modify).pack(side="left", padx=4)
        ttk.Button(btns, text="Supprimer", command=delete).pack(side="left")
        ttk.Button(btns, text="Lui faire dire", command=test).pack(side="left", padx=4)
        ttk.Button(btns, text="Rétablir l'origine", command=reset).pack(side="right")

        status.grid(row=4, column=0, columnspan=5, sticky="w", pady=(8, 0))
        ttk.Label(frm, text="Astuce : écris {name} pour qu'il dise son propre nom. "
                  "Sélectionne une phrase pour la modifier.",
                  font=("Segoe UI", 9), foreground="#6b5a4e").grid(
            row=5, column=0, columnspan=5, sticky="w")

        combo.bind("<<ComboboxSelected>>", lambda _: (v_text.set(""), refresh()))
        lb.bind("<<ListboxSelect>>", on_select)
        lb.bind("<Delete>", lambda _: delete())
        ent.bind("<Return>", add)

        refresh()
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 260)}+{max(0, y - 480)}")
        w.after(50, lambda: (w.focus_force(), ent.focus_set()))

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
    set_dpi_aware()
    if already_running():
        return
    try:
        App().run()
    except Exception:
        log_error()
        raise


if __name__ == "__main__":
    main()
