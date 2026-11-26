import hmac
import json
import time

from ..errors import BadRequest, Forbidden, NotFound, Unavailable
from ..settings import HEX32, MAX_CATS, ONLINE_AFTER
from ..validation import clean_phrases, clean_settings, clean_stats, clip, sha256


class Cats:
    def __init__(self, db):
        self.db = db

    def authenticate(self, cat_id, secret):
        cid, sec = clip(cat_id, 64), clip(secret, 64)
        if not HEX32.match(cid) or not HEX32.match(sec):
            raise BadRequest("identifiant invalide")
        h = sha256(sec)
        row = self.db.execute("SELECT secret_hash FROM cats WHERE id=?", (cid,)).fetchone()
        if row is None:
            if self.db.execute("SELECT COUNT(*) FROM cats").fetchone()[0] >= MAX_CATS:
                raise Unavailable("trop de chats enregistrés")
            t = time.time()
            self.db.execute("INSERT INTO cats(id, secret_hash, first_seen, last_seen) VALUES(?,?,?,?)",
                            (cid, h, t, t))
            self.db.commit()
        elif not hmac.compare_digest(row["secret_hash"], h):
            raise Forbidden("secret invalide")
        return cid

    def record_sync(self, cid, body):
        accept = bool(body.get("accept", True))
        settings = clean_settings(body.get("settings"), with_name=False)
        allow = body.get("allow_settings")
        self.db.execute(
            "UPDATE cats SET name=?, version=?, stats=?, state=?, accept=?, last_seen=?, "
            "settings=?, allow_settings=? WHERE id=?",
            (clip(body.get("name"), 40), clip(body.get("version"), 20),
             json.dumps(clean_stats(body.get("stats"))), clip(body.get("state"), 20),
             int(accept), time.time(), json.dumps(settings) if settings else None,
             None if allow is None else int(bool(allow)), cid))
        if "phrases" in body:
            phrases = clean_phrases(body["phrases"])
            if phrases:
                self.db.execute("UPDATE cats SET phrases=?, phrases_at=? WHERE id=?",
                                (phrases, time.time(), cid))
        self.db.commit()
        return accept

    def touch(self, cid):
        self.db.execute("UPDATE cats SET last_seen=? WHERE id=?", (time.time(), cid))
        self.db.commit()

    def exists(self, cid):
        return self.db.execute("SELECT 1 FROM cats WHERE id=?", (cid,)).fetchone() is not None

    def ids(self):
        return [r["id"] for r in self.db.execute("SELECT id FROM cats")]

    def names(self):
        return {r["id"]: r["name"] or "?" for r in self.db.execute("SELECT id, name FROM cats")}

    def overview(self):
        t = time.time()
        cats = []
        for r in self.db.execute("SELECT * FROM cats ORDER BY last_seen DESC"):
            unread = self.db.execute("SELECT COUNT(*) FROM replies WHERE cat_id=? AND read=0",
                                     (r["id"],)).fetchone()[0]
            waiting = self.db.execute("SELECT COUNT(*) FROM messages WHERE cat_id=? AND delivered "
                                      "IS NULL", (r["id"],)).fetchone()[0]
            cats.append({"id": r["id"], "name": r["name"] or "?", "version": r["version"],
                         "stats": json.loads(r["stats"] or "{}"), "state": r["state"],
                         "accept": bool(r["accept"]), "last_seen": r["last_seen"],
                         "first_seen": r["first_seen"],
                         "online": t - (r["last_seen"] or 0) < ONLINE_AFTER,
                         "unread": unread, "waiting": waiting,
                         "settings": json.loads(r["settings"]) if r["settings"] else None,
                         "allow_settings": (None if r["allow_settings"] is None
                                            else bool(r["allow_settings"])),
                         "phrases_at": r["phrases_at"]})
        return cats

    def phrases(self, cid):
        row = self.db.execute("SELECT phrases, phrases_at FROM cats WHERE id=?", (cid,)).fetchone()
        if not row:
            raise NotFound("chat inconnu")
        return {"phrases": json.loads(row["phrases"]) if row["phrases"] else None,
                "at": row["phrases_at"]}

    def forget(self, cid):
        for table, col in (("messages", "cat_id"), ("replies", "cat_id"), ("cats", "id")):
            self.db.execute(f"DELETE FROM {table} WHERE {col}=?", (cid,))
        self.db.commit()
