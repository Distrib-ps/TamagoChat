"""Constantes, chemins et configuration privée (local_config.py)."""
import os
import sys

from . import __version__

APP_VERSION = __version__

FROZEN = getattr(sys, "frozen", False)      # True dans l'app compilée (.exe / .app)
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(PACKAGE_DIR)
RES_DIR = getattr(sys, "_MEIPASS", os.path.join(PACKAGE_DIR, "assets"))   # fichiers embarqués
ICON_FILE = os.path.join(RES_DIR, "chat.ico")
LAUNCHER = os.path.join(ROOT_DIR, "chat.pyw")   # lancé au démarrage quand on tourne depuis le code

# Adresse du serveur et clé publique des mises à jour : dans local_config.py (non versionné,
# voir local_config.example.py). Sans ce fichier, le chat fonctionne mais hors ligne.
try:
    import local_config as _cfg
except ImportError:
    _cfg = None
SERVER_URL = os.environ.get("MINOU_SERVER", getattr(_cfg, "SERVER_URL", "")).rstrip("/")
# Seule une version signée par la clé privée correspondante peut être installée automatiquement.
UPDATE_PUBKEY = getattr(_cfg, "UPDATE_PUBKEY", "")

APP_NAME = "ChatTamagotchi"
if sys.platform == "darwin":
    DATA_DIR = os.path.join(os.path.expanduser("~/Library/Application Support"), APP_NAME)
else:
    DATA_DIR = os.path.join(os.environ.get("APPDATA", ROOT_DIR), APP_NAME)
SAVE_FILE = os.path.join(DATA_DIR, "save.json")
LOG_FILE = os.path.join(DATA_DIR, "erreurs.log")

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
