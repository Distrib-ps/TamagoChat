import asyncio
import json
import time

from ..settings import MESSAGE_TTL


class Messages:
    def __init__(self, db):
        self.db = db
        self._events = {}       # cat_id -> asyncio.Event : réveille l'attente du chat

    def pending(self, cid):
        rows = self.db.execute(
            "SELECT id, kind, payload, created FROM messages WHERE cat_id=? AND delivered IS NULL "
            "AND created > ? ORDER BY id LIMIT 20", (cid, time.time() - MESSAGE_TTL)).fetchall()
        return [{"id": r["id"], "kind": r["kind"], "created": r["created"],
                 **json.loads(r["payload"])} for r in rows]

    def acknowledge(self, cid, ids):
        if ids:
            self.db.execute(f"UPDATE messages SET delivered=? WHERE cat_id=? AND delivered IS NULL "
                            f"AND id IN ({','.join('?' * len(ids))})", (time.time(), cid, *ids))
            self.db.commit()

    async def collect(self, cid, timeout):
        deadline = time.time() + timeout
        while True:
            msgs = self.pending(cid)
            if msgs or time.time() >= deadline:
                break
            ev = self._events.setdefault(cid, asyncio.Event())
            ev.clear()
            try:
                await asyncio.wait_for(ev.wait(), max(0.0, deadline - time.time()))
            except asyncio.TimeoutError:
                pass
        if msgs:
            ids = [m["id"] for m in msgs]
            self.db.execute(f"UPDATE messages SET fetched=COALESCE(fetched, ?) "
                            f"WHERE id IN ({','.join('?' * len(ids))})", (time.time(), *ids))
            self.db.commit()
        return msgs

    def add_reply(self, cid, text):
        self.db.execute("INSERT INTO replies(cat_id, text, created) VALUES(?,?,?)",
                        (cid, text, time.time()))
        self.db.commit()

    def send(self, targets, kind, payload):
        t = time.time()
        data = json.dumps(payload, ensure_ascii=False)
        for cid in targets:
            self.db.execute("INSERT INTO messages(cat_id, kind, payload, created) VALUES(?,?,?,?)",
                            (cid, kind, data, t))
        self.db.commit()
        for cid in targets:
            if cid in self._events:
                self._events[cid].set()

    def conversation(self, cat, names):
        where, args = ("", ()) if cat == "*" else ("WHERE cat_id=?", (cat,))
        items = []
        for r in self.db.execute(f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT 150", args):
            items.append({"type": "sent", "id": r["id"], "cat": names.get(r["cat_id"], "?"),
                          "kind": r["kind"], "created": r["created"], "fetched": r["fetched"],
                          "delivered": r["delivered"], **json.loads(r["payload"])})
        for r in self.db.execute(f"SELECT * FROM replies {where} ORDER BY id DESC LIMIT 150", args):
            items.append({"type": "reply", "id": r["id"], "cat": names.get(r["cat_id"], "?"),
                          "text": r["text"], "created": r["created"]})
        self.db.execute(f"UPDATE replies SET read=1 {where}", args)
        self.db.commit()
        items.sort(key=lambda i: i["created"])
        return items[-150:]
