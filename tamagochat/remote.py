"""Lien avec le serveur : messages et actions reçus, état envoyé, mises à jour signées."""
import collections
import hashlib
import json
import os
import queue
import random
import re
import threading
import urllib.request

from . import desktop, ed25519
from .config import (APP_VERSION, FLY_POOL, FROZEN, REMOTE_SETTINGS, SERVER_URL, SIDE, SIZES, STATS,
                     TOP, UPDATE_PUBKEY)
from .phrases import PHRASES, PHRASE_CATEGORIES
from .reactions import REACTIONS
from .storage import log_error


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
        if not desktop.can_self_update():
            return
        tmp = desktop.update_download_path()
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
            msg = f"{desktop.UPDATE_TAG}|{v}|{sha}".encode()
            if not ed25519.verify(bytes.fromhex(UPDATE_PUBKEY), msg, bytes.fromhex(upd["sig"])):
                raise ValueError("signature invalide : mise à jour refusée")
            tmp = desktop.prepare_update(tmp)   # Mac : .zip vérifié -> nouveau .app prêt à côté
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


class RemoteMixin:
    def remote_snapshot(self):
        d = self.data
        return {"cat_id": d["remote_id"], "secret": d["remote_secret"],
                "name": d["name"], "version": APP_VERSION, "state": self.state,
                "stats": {k: round(v, 1) for k, v in self.stats.items()},
                "accept": bool(d["remote_messages"]),
                "auto_update": bool(d["auto_update"]),
                "allow_settings": bool(d["remote_settings"]),
                "settings": {k: d[k] for k in REMOTE_SETTINGS},
                "_prev": self.phrases_rev, "_phrases": self.phrases_payload(),
                "platform": desktop.NAME}

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
        elif action in REACTIONS:
            self.start_reaction(action)

    def set_remote_opt(self, key, value):
        self.data[key] = value
        self.save()
        self.remote.snapshot = self.remote_snapshot()
        self.remote.wakeup.set()

    def apply_update(self, path, version):
        """Installe la nouvelle version (déjà vérifiée) puis redémarre."""
        try:
            desktop.install_update(path)
        except Exception:
            log_error()
            self.say_text("La mise à jour a échoué, je reste comme je suis.", priority=True)
            return
        self.data["just_updated"] = version
        self.save()
        try:
            desktop.restart()
        except Exception:
            log_error()
        self._quitting = True
        self.root.destroy()
