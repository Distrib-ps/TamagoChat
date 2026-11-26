import asyncio
import json
import os
import random
import secrets
import time

from .settings import STAT_KEYS
from .validation import sha256

PASSWORD = "admin"

PHRASES = {
    "cats": [["idle", "Quand il ne fait rien"], ["eat", "En mangeant"], ["pet", "Quand on le caresse"]],
    "list": {"idle": ["Miaou ?", "Quelqu'un a vu ma pelote ?", "{name} s'ennuie…"],
             "eat": ["Miam !", "Encore un peu ?"],
             "pet": ["Rrrrr…", "Encore !"]},
    "custom": [],
}
SETTINGS = {"autowalk": True, "topmost": True, "chatter_s": 180, "crazy_min": 10,
            "flies_min": 8, "size": "Moyen"}
# (nom, version, en ligne, état, accepte les réglages à distance)
DEMO = (
    ("Minou", "1.3.0", True, "idle", True),
    ("Caramel", "1.3.0", True, "sleep", True),
    ("Pixel", "1.2.0", False, "walk", False),
    ("Vieux Félix", "1.0.4", False, "idle", None),     # ancienne version : pas de réglages
)
STATES = ("idle", "walk", "sleep", "eat", "play", "groom")


def seed(svc):
    if svc.db.execute("SELECT COUNT(*) FROM cats").fetchone()[0]:
        return
    t = time.time()
    alive = []
    for i, (name, version, online, state, allow) in enumerate(DEMO):
        cid = secrets.token_hex(16)
        if online:
            alive.append(cid)
        stats = {k: random.randint(25, 95) for k in STAT_KEYS}
        old = allow is None
        svc.db.execute(
            "INSERT INTO cats(id, secret_hash, name, version, stats, state, accept, first_seen, "
            "last_seen, settings, allow_settings, phrases, phrases_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (cid, sha256(secrets.token_hex(16)), name, version, json.dumps(stats), state, 1,
             t - 86400 * (i + 3), t if online else t - 3600 * (i + 2),
             None if old else json.dumps(SETTINGS), None if old else int(allow),
             None if old else json.dumps(PHRASES, ensure_ascii=False), None if old else t))
        if i == 0:
            svc.db.execute("INSERT INTO messages(cat_id, kind, payload, created, fetched, delivered) "
                          "VALUES(?,?,?,?,?,?)", (cid, "say", json.dumps({"text": "Coucou Minou !",
                          "from": "Théo"}), t - 600, t - 599, t - 598))
            svc.db.execute("INSERT INTO replies(cat_id, text, created) VALUES(?,?,?)",
                          (cid, "Il vient de faire tomber mon verre 😅", t - 300))
    svc.db.commit()
    with open(demo_file(svc), "w", encoding="utf-8") as f:
        json.dump(alive, f)


def demo_file(svc):
    return os.path.join(svc.paths.data, "demo.json")


def apply(svc, cat, kind, payload):
    if kind == "settings":
        settings = json.loads(cat["settings"] or "{}")
        payload = dict(payload["settings"])
        name = payload.pop("name", None)
        settings.update(payload)
        svc.db.execute("UPDATE cats SET settings=?, name=COALESCE(?, name) WHERE id=?",
                      (json.dumps(settings), name, cat["id"]))
    elif kind == "stats":
        stats = json.loads(cat["stats"] or "{}")
        stats.update(payload["stats"])
        svc.db.execute("UPDATE cats SET stats=? WHERE id=?", (json.dumps(stats), cat["id"]))
    elif kind == "phrases" and cat["phrases"]:
        ph = json.loads(cat["phrases"])
        key = payload["key"]
        if payload.get("reset"):
            ph["list"][key] = PHRASES["list"].get(key, [])
            ph["custom"] = [k for k in ph["custom"] if k != key]
        else:
            ph["list"][key] = payload["list"]
            ph["custom"] = sorted(set(ph["custom"]) | {key})
        svc.db.execute("UPDATE cats SET phrases=?, phrases_at=? WHERE id=?",
                      (json.dumps(ph, ensure_ascii=False), time.time(), cat["id"]))
    elif kind == "action":
        svc.db.execute("UPDATE cats SET state=? WHERE id=?",
                      ("sleep" if payload["action"] == "sleep" else "idle", cat["id"]))


async def simulate(svc):
    try:
        with open(demo_file(svc), encoding="utf-8") as f:
            online = json.load(f)
    except (OSError, ValueError):
        online = []
    while True:
        await asyncio.sleep(2)
        t = time.time()
        for cid in online:
            cat = svc.db.execute("SELECT * FROM cats WHERE id=?", (cid,)).fetchone()
            if not cat:
                continue
            for m in svc.db.execute("SELECT * FROM messages WHERE cat_id=? AND delivered IS NULL",
                                   (cid,)).fetchall():
                if cat["allow_settings"] or m["kind"] in ("say", "action"):
                    apply(svc, cat, m["kind"], json.loads(m["payload"]))
                svc.db.execute("UPDATE messages SET fetched=COALESCE(fetched, ?), delivered=? "
                              "WHERE id=?", (t, t, m["id"]))
            state = random.choice(STATES) if random.random() < 0.1 else cat["state"]
            svc.db.execute("UPDATE cats SET last_seen=?, state=? WHERE id=?", (t, state, cid))
        svc.db.commit()
