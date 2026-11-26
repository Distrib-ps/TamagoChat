import hashlib
import hmac
import secrets
import time

from ..errors import TooManyRequests
from ..settings import MAX_LOGIN_ATTEMPTS, SESSION_DAYS
from ..validation import sha256

LOCKOUT_SECONDS = 15 * 60


def hash_password(pw, salt_hex):
    return hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1).hex()


class Auth:
    def __init__(self, db, config):
        self.db = db
        self.config = config
        self._failures = {}       # ip -> (nombre, début)

    def set_password(self, pw):
        salt = secrets.token_hex(16)
        self.config.update(admin_salt=salt, admin_hash=hash_password(pw, salt))
        self.db.execute("DELETE FROM sessions")   # déconnecte les sessions existantes
        self.db.commit()

    def has_password(self):
        return bool(self.config.get("admin_hash"))

    def check_password(self, pw):
        cfg = self.config.load()
        return bool(cfg.get("admin_hash")) and hmac.compare_digest(
            hash_password(pw, cfg["admin_salt"]), cfg["admin_hash"])

    def check_attempts(self, ip):
        count, start = self._failures.get(ip, (0, time.time()))
        if time.time() - start > LOCKOUT_SECONDS:
            self._failures.pop(ip, None)
        elif count >= MAX_LOGIN_ATTEMPTS:
            raise TooManyRequests("trop d'essais, réessaie dans 15 minutes")

    def failed(self, ip):
        count, start = self._failures.get(ip, (0, time.time()))
        if time.time() - start > LOCKOUT_SECONDS:
            count, start = 0, time.time()
        self._failures[ip] = (count + 1, start)

    def succeeded(self, ip):
        self._failures.pop(ip, None)

    def open_session(self):
        tok = secrets.token_urlsafe(32)
        self.db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
        self.db.execute("INSERT INTO sessions VALUES(?,?)",
                        (sha256(tok), time.time() + SESSION_DAYS * 86400))
        self.db.commit()
        return tok

    def session_valid(self, tok):
        if not tok:
            return False
        row = self.db.execute("SELECT expires FROM sessions WHERE token_hash=?",
                              (sha256(tok),)).fetchone()
        return bool(row and row["expires"] > time.time())

    def close_session(self, tok):
        if tok:
            self.db.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(tok),))
            self.db.commit()

    def create_deploy_token(self, repo, pubkey):
        """Active la publication depuis GitHub Actions ; le jeton n'est gardé que hashé."""
        token = secrets.token_urlsafe(32)
        self.config.update(github_repo=repo, update_pubkey=pubkey, deploy_hash=sha256(token))
        return token

    def deploy_token_valid(self, authorization):
        expected = self.config.get("deploy_hash")
        return bool(expected and authorization.startswith("Bearer ") and
                    hmac.compare_digest(sha256(authorization[7:].strip()), expected))
