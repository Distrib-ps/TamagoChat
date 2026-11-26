import os
import re

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_env_file(path):
    """Lignes CLE=valeur de server/.env ; les variables déjà définies l'emportent."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.strip().partition("=")
                if sep and key and not key.startswith("#"):
                    os.environ.setdefault(key.strip(), value.strip().strip('"\''))
    except FileNotFoundError:
        pass


_load_env_file(os.path.join(SERVER_DIR, ".env"))


def _web_dir():
    """Page admin compilée (npm run build) : copiée à côté de server.py sur le VPS,
    dans web/dist à la racine du projet dans le dépôt."""
    for d in (os.path.join(SERVER_DIR, "web"), os.path.join(os.path.dirname(SERVER_DIR), "web", "dist")):
        if os.path.isfile(os.path.join(d, "index.html")):
            return d
    return os.path.join(SERVER_DIR, "web")


WEB_DIR = _web_dir()
DEV_DATA_DIR = os.path.join(SERVER_DIR, ".dev")
HOST = os.environ.get("TAMAGOCHAT_HOST", "127.0.0.1")
PORT = int(os.environ.get("TAMAGOCHAT_PORT", "8090"))

POLL_TIMEOUT = 25
ONLINE_AFTER = 50
MAX_CATS = 500
MESSAGE_TTL = 7 * 86400
STAT_KEYS = ("satiete", "hydratation", "bonheur", "energie")
ACTIONS = ("crazy", "flies", "sleep", "wake", "pet", "feed", "drink", "play", "meow",
           "crazy_xl", "swarm", "love", "jump", "drop", "screen", "mouse", "hide",
           "groom", "stretch", "sneeze", "chase_tail", "cross_eyed")
SIZES = ("Petit", "Moyen", "Grand")
MAX_PHRASES_JSON = 200_000
HEX32 = re.compile(r"^[0-9a-f]{32}$")

SESSION_DAYS = 30
SESSION_COOKIE = "minou_admin"
MAX_LOGIN_ATTEMPTS = 10    # par adresse IP, sur 15 minutes
MAX_REQUEST = 512 * 1024

VERSION_RE = re.compile(r"\d+(\.\d+){1,3}")
MAX_RELEASE = 100 * 1024 * 1024
KEEP_RELEASES = 5
RELEASE_FILE_RE = re.compile(r"^(Minou|TamagoChat)-\d+(\.\d+){1,3}(\.exe|-mac\.zip)$")
PLATFORMS = {
    "win": {"latest": "latest.json", "file": "TamagoChat-{v}.exe", "tag": "minou-update"},
    "mac": {"latest": "latest-mac.json", "file": "TamagoChat-{v}-mac.zip", "tag": "minou-update-mac"},
}

GITHUB_API = "https://api.github.com"
WORKFLOW = "release.yml"


class Paths:

    def __init__(self, data_dir):
        self.data = data_dir
        self.database = os.path.join(data_dir, "minou.db")
        self.config = os.path.join(data_dir, "config.json")
        self.releases = os.path.join(data_dir, "releases")
