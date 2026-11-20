"""Serveur TamagoChat : messages à distance, actions, état des chats et mises à jour.

    python server.py                    -> lance le serveur (127.0.0.1:8090, derrière nginx)
    python server.py set-password XXX   -> change le mot de passe de la page admin
"""
import asyncio
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "minou.db")
RELEASES = os.path.join(BASE, "releases")
CONFIG_PATH = os.path.join(BASE, "config.json")
ADMIN_HTML = os.path.join(BASE, "admin.html")
HOST, PORT = "127.0.0.1", 8090

POLL_TIMEOUT = 25          # durée max d'une attente (long polling)
ONLINE_AFTER = 50          # un chat vu il y a moins de 50 s est "en ligne"
MAX_CATS = 500
SESSION_DAYS = 30
STAT_KEYS = ("satiete", "hydratation", "bonheur", "energie")
ACTIONS = ("crazy", "flies", "sleep", "wake", "pet", "feed", "drink", "play", "meow",
           "crazy_xl", "swarm", "love", "jump", "drop", "screen", "mouse", "hide")
SIZES = ("Petit", "Moyen", "Grand")
VERSION_RE = re.compile(r"\d+(\.\d+){1,3}")
MAX_RELEASE = 100 * 1024 * 1024
KEEP_RELEASES = 5
GITHUB_API = "https://api.github.com"
WORKFLOW = "release.yml"
MAX_PHRASES_JSON = 200_000
HEX32 = re.compile(r"^[0-9a-f]{32}$")
RELEASE_RE = re.compile(r"^(Minou|TamagoChat)-\d+(\.\d+){1,3}\.exe$")

SCHEMA = """
CREATE TABLE IF NOT EXISTS cats(
    id TEXT PRIMARY KEY, secret_hash TEXT NOT NULL, name TEXT, version TEXT,
    stats TEXT, state TEXT, accept INTEGER DEFAULT 1, first_seen REAL, last_seen REAL);
CREATE TABLE IF NOT EXISTS messages(
    id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id TEXT NOT NULL, kind TEXT NOT NULL,
    payload TEXT NOT NULL, created REAL NOT NULL, fetched REAL, delivered REAL);
CREATE INDEX IF NOT EXISTS msg_cat ON messages(cat_id, delivered);
CREATE TABLE IF NOT EXISTS replies(
    id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id TEXT NOT NULL, text TEXT NOT NULL,
    created REAL NOT NULL, read INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, expires REAL NOT NULL);
"""


def db_connect():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r["name"] for r in con.execute("PRAGMA table_info(cats)")}
    for col, typ in (("settings", "TEXT"), ("allow_settings", "INTEGER"), ("phrases", "TEXT"),
                     ("phrases_at", "REAL")):
        if col not in cols:
            con.execute(f"ALTER TABLE cats ADD COLUMN {col} {typ}")
    con.execute("PRAGMA journal_mode=WAL")
    return con


def load_config():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def hash_password(pw, salt_hex):
    return hashlib.scrypt(pw.encode(), salt=bytes.fromhex(salt_hex), n=2 ** 14, r=8, p=1).hex()


def save_config(cfg):
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    os.chmod(tmp, 0o600)
    os.replace(tmp, CONFIG_PATH)


def set_password(pw):
    salt = secrets.token_hex(16)
    cfg = load_config()
    cfg.update(admin_salt=salt, admin_hash=hash_password(pw, salt))
    save_config(cfg)
    con = db_connect()
    con.execute("DELETE FROM sessions")   # déconnecte les sessions existantes
    con.commit()


def sha256(s):
    return hashlib.sha256(s.encode()).hexdigest()


def clip(v, n):
    return str(v if v is not None else "")[:n]


def version_tuple(v):
    return tuple(int(x) for x in str(v).split(".") if x.isdigit())


def is_int(v, lo, hi):
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


def clean_settings(s, with_name):
    """Réglages d'un chat : valeurs vérifiées, le reste est ignoré."""
    if not isinstance(s, dict):
        return {}
    out = {}
    name = clip(s.get("name"), 24).strip()
    if name and with_name:
        out["name"] = name
    for k in ("autowalk", "topmost"):
        if isinstance(s.get(k), bool):
            out[k] = s[k]
    v = s.get("chatter_s")
    if is_int(v, 0, 86400) and (v == 0 or v >= 15):
        out["chatter_s"] = v
    for k in ("crazy_min", "flies_min"):
        if is_int(s.get(k), 0, 1440):
            out[k] = s[k]
    if s.get("size") in SIZES:
        out["size"] = s["size"]
    return out


def clean_phrases(p):
    """Phrases envoyées par un chat : {cats: [[clé, libellé]], list: {clé: [...]}, custom: [...]}."""
    if not isinstance(p, dict) or not isinstance(p.get("cats"), list):
        return None
    cats = [[clip(c[0], 40), clip(c[1], 80)] for c in p["cats"][:80]
            if isinstance(c, list) and len(c) == 2]
    keys = {c[0] for c in cats}
    lists = p.get("list") if isinstance(p.get("list"), dict) else {}
    custom = p.get("custom") if isinstance(p.get("custom"), list) else []
    out = {"cats": cats,
           "list": {k: [clip(x, 200) for x in v[:150]] for k, v in lists.items()
                    if k in keys and isinstance(v, list)},
           "custom": [k for k in custom if k in keys]}
    data = json.dumps(out, ensure_ascii=False)
    return data if len(data) <= MAX_PHRASES_JSON else None


# ---------------------------------------------------------------------------- serveur
def main():
    import aiohttp
    from aiohttp import web

    db = db_connect()
    events = {}           # cat_id -> asyncio.Event (réveille l'attente du chat)
    failed_logins = {}    # ip -> [nombre, début]
    release_cache = {"mtime": None, "data": None}

    def now():
        return time.time()

    def latest_release():
        path = os.path.join(RELEASES, "latest.json")
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return None
        if mtime != release_cache["mtime"]:
            try:
                with open(path, encoding="utf-8") as f:
                    rel = json.load(f)
                release_cache["data"] = {
                    "version": rel["version"], "url": "/download/" + rel["file"],
                    "sha256": rel["sha256"], "size": rel["size"], "sig": rel["sig"],
                    "date": rel.get("date"), "commit": rel.get("commit")}
            except Exception:
                release_cache["data"] = None
            release_cache["mtime"] = mtime
        return release_cache["data"]

    async def read_json(req):
        try:
            data = await req.json()
        except Exception:
            raise web.HTTPBadRequest(text="JSON invalide")
        if not isinstance(data, dict):
            raise web.HTTPBadRequest(text="JSON invalide")
        return data

    def cat_auth(body):
        cid, sec = clip(body.get("cat_id"), 64), clip(body.get("secret"), 64)
        if not HEX32.match(cid) or not HEX32.match(sec):
            raise web.HTTPBadRequest(text="identifiant invalide")
        h = sha256(sec)
        row = db.execute("SELECT secret_hash FROM cats WHERE id=?", (cid,)).fetchone()
        if row is None:
            if db.execute("SELECT COUNT(*) FROM cats").fetchone()[0] >= MAX_CATS:
                raise web.HTTPServiceUnavailable()
            t = now()
            db.execute("INSERT INTO cats(id, secret_hash, first_seen, last_seen) VALUES(?,?,?,?)",
                       (cid, h, t, t))
            db.commit()
        elif not hmac.compare_digest(row["secret_hash"], h):
            raise web.HTTPForbidden(text="secret invalide")
        return cid

    def pending(cid):
        rows = db.execute(
            "SELECT id, kind, payload, created FROM messages WHERE cat_id=? AND delivered IS NULL "
            "AND created > ? ORDER BY id LIMIT 20", (cid, now() - 7 * 86400)).fetchall()
        return [{"id": r["id"], "kind": r["kind"], "created": r["created"],
                 **json.loads(r["payload"])} for r in rows]

    # ------------------------------------------------------------ API des chats
    async def api_sync(req):
        body = await read_json(req)
        cid = cat_auth(body)
        stats = body.get("stats")
        stats = ({k: round(max(0.0, min(100.0, float(stats[k]))), 1) for k in STAT_KEYS
                  if isinstance(stats.get(k), (int, float)) and not isinstance(stats[k], bool)}
                 if isinstance(stats, dict) else {})
        accept = bool(body.get("accept", True))
        settings = clean_settings(body.get("settings"), with_name=False)
        allow = body.get("allow_settings")
        db.execute("UPDATE cats SET name=?, version=?, stats=?, state=?, accept=?, last_seen=?, "
                   "settings=?, allow_settings=? WHERE id=?",
                   (clip(body.get("name"), 40), clip(body.get("version"), 20),
                    json.dumps(stats), clip(body.get("state"), 20), int(accept), now(),
                    json.dumps(settings) if settings else None,
                    None if allow is None else int(bool(allow)), cid))
        if "phrases" in body:
            ph = clean_phrases(body["phrases"])
            if ph:
                db.execute("UPDATE cats SET phrases=?, phrases_at=? WHERE id=?", (ph, now(), cid))
        ack = [i for i in body.get("ack") or [] if isinstance(i, int)][:200]
        if ack:
            db.execute(f"UPDATE messages SET delivered=? WHERE cat_id=? AND delivered IS NULL "
                       f"AND id IN ({','.join('?' * len(ack))})", (now(), cid, *ack))
        db.commit()

        deadline = now() + (POLL_TIMEOUT if body.get("wait", True) and accept else 0)
        while True:
            msgs = pending(cid) if accept else []
            if msgs or now() >= deadline:
                break
            ev = events.setdefault(cid, asyncio.Event())
            ev.clear()
            try:
                await asyncio.wait_for(ev.wait(), max(0.0, deadline - now()))
            except asyncio.TimeoutError:
                pass
        if msgs:
            ids = [m["id"] for m in msgs]
            db.execute(f"UPDATE messages SET fetched=COALESCE(fetched, ?) "
                       f"WHERE id IN ({','.join('?' * len(ids))})", (now(), *ids))
        db.execute("UPDATE cats SET last_seen=? WHERE id=?", (now(), cid))
        db.commit()
        return web.json_response({"messages": msgs, "update": latest_release()})

    async def api_reply(req):
        body = await read_json(req)
        cid = cat_auth(body)
        text = clip(body.get("text"), 500).strip()
        if not text:
            raise web.HTTPBadRequest(text="message vide")
        db.execute("INSERT INTO replies(cat_id, text, created) VALUES(?,?,?)", (cid, text, now()))
        db.commit()
        return web.json_response({"ok": True})

    async def api_latest(req):
        return web.json_response({"update": latest_release()})

    async def download(req):
        name = req.match_info["name"]
        path = os.path.join(RELEASES, name)
        if not RELEASE_RE.match(name) or not os.path.isfile(path):
            raise web.HTTPNotFound()
        return web.FileResponse(path, headers={"Content-Type": "application/octet-stream"})

    # ------------------------------------------------------------ admin
    def client_ip(req):
        return req.headers.get("X-Real-IP") or req.remote or "?"

    def check_admin(req):
        tok = req.cookies.get("minou_admin")
        if tok:
            row = db.execute("SELECT expires FROM sessions WHERE token_hash=?",
                             (sha256(tok),)).fetchone()
            if row and row["expires"] > now():
                return
        raise web.HTTPUnauthorized(text="non connecté")

    async def admin_page(req):
        return web.FileResponse(ADMIN_HTML, headers={
            "Cache-Control": "no-store", "X-Frame-Options": "DENY",
            "Referrer-Policy": "no-referrer"})

    async def admin_login(req):
        ip = client_ip(req)
        count, start = failed_logins.get(ip, (0, now()))
        if now() - start > 900:
            count, start = 0, now()
        if count >= 10:
            raise web.HTTPTooManyRequests(text="trop d'essais, réessaie dans 15 minutes")
        body = await read_json(req)
        cfg = load_config()
        pw = clip(body.get("password"), 200)
        ok = cfg.get("admin_hash") and hmac.compare_digest(
            hash_password(pw, cfg["admin_salt"]), cfg["admin_hash"])
        if not ok:
            failed_logins[ip] = (count + 1, start)
            await asyncio.sleep(1)
            raise web.HTTPUnauthorized(text="mot de passe incorrect")
        failed_logins.pop(ip, None)
        tok = secrets.token_urlsafe(32)
        db.execute("DELETE FROM sessions WHERE expires < ?", (now(),))
        db.execute("INSERT INTO sessions VALUES(?,?)", (sha256(tok), now() + SESSION_DAYS * 86400))
        db.commit()
        resp = web.json_response({"ok": True})
        resp.set_cookie("minou_admin", tok, max_age=SESSION_DAYS * 86400, path="/admin",
                        httponly=True, secure=True, samesite="Strict")
        return resp

    async def admin_logout(req):
        tok = req.cookies.get("minou_admin")
        if tok:
            db.execute("DELETE FROM sessions WHERE token_hash=?", (sha256(tok),))
            db.commit()
        resp = web.json_response({"ok": True})
        resp.del_cookie("minou_admin", path="/admin")
        return resp

    async def admin_state(req):
        check_admin(req)
        t = now()
        cats = []
        for r in db.execute("SELECT * FROM cats ORDER BY last_seen DESC"):
            unread = db.execute("SELECT COUNT(*) FROM replies WHERE cat_id=? AND read=0",
                                (r["id"],)).fetchone()[0]
            waiting = db.execute("SELECT COUNT(*) FROM messages WHERE cat_id=? AND delivered "
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
        return web.json_response({"cats": cats, "release": latest_release(), "now": t})

    async def admin_feed(req):
        check_admin(req)
        cat = req.query.get("cat", "*")
        names = {r["id"]: r["name"] or "?" for r in db.execute("SELECT id, name FROM cats")}
        where, args = ("", ()) if cat == "*" else ("WHERE cat_id=?", (cat,))
        items = []
        for r in db.execute(f"SELECT * FROM messages {where} ORDER BY id DESC LIMIT 150", args):
            items.append({"type": "sent", "id": r["id"], "cat": names.get(r["cat_id"], "?"),
                          "kind": r["kind"], "created": r["created"], "fetched": r["fetched"],
                          "delivered": r["delivered"], **json.loads(r["payload"])})
        for r in db.execute(f"SELECT * FROM replies {where} ORDER BY id DESC LIMIT 150", args):
            items.append({"type": "reply", "id": r["id"], "cat": names.get(r["cat_id"], "?"),
                          "text": r["text"], "created": r["created"]})
        db.execute(f"UPDATE replies SET read=1 {where}", args)
        db.commit()
        items.sort(key=lambda i: i["created"])
        return web.json_response({"items": items[-150:]})

    async def admin_phrases(req):
        check_admin(req)
        row = db.execute("SELECT phrases, phrases_at FROM cats WHERE id=?",
                         (req.query.get("cat", ""),)).fetchone()
        if not row:
            raise web.HTTPNotFound(text="chat inconnu")
        return web.json_response({"phrases": json.loads(row["phrases"]) if row["phrases"] else None,
                                  "at": row["phrases_at"]})

    async def admin_send(req):
        check_admin(req)
        body = await read_json(req)
        kind = body.get("kind")
        if kind == "say":
            text = clip(body.get("text"), 500).strip()
            if not text:
                raise web.HTTPBadRequest(text="message vide")
            payload = {"text": text, "from": clip(body.get("from"), 40).strip()}
            if is_int(body.get("secs"), 3, 600):
                payload["secs"] = body["secs"]
        elif kind == "action" and body.get("action") in ACTIONS:
            payload = {"action": body["action"]}
        elif kind == "settings":
            settings = clean_settings(body.get("settings"), with_name=True)
            if not settings:
                raise web.HTTPBadRequest(text="réglage invalide")
            payload = {"settings": settings}
        elif kind == "stats":
            st = body.get("stats") if isinstance(body.get("stats"), dict) else {}
            st = {k: st[k] for k in STAT_KEYS if is_int(st.get(k), 0, 100)}
            if not st:
                raise web.HTTPBadRequest(text="jauges invalides")
            payload = {"stats": st}
        elif kind == "phrases" and re.fullmatch(r"[a-z_]{1,40}", str(body.get("key", ""))):
            if body.get("reset") is True:
                payload = {"key": body["key"], "reset": True}
            elif isinstance(body.get("list"), list):
                lst = [clip(x, 200).strip() for x in body["list"][:100]]
                payload = {"key": body["key"], "list": [x for x in lst if x]}
            else:
                raise web.HTTPBadRequest(text="phrases invalides")
        else:
            raise web.HTTPBadRequest(text="type inconnu")
        cat = clip(body.get("cat"), 64)
        if cat == "*":
            targets = [r["id"] for r in db.execute("SELECT id FROM cats")]
        elif db.execute("SELECT 1 FROM cats WHERE id=?", (cat,)).fetchone():
            targets = [cat]
        else:
            raise web.HTTPNotFound(text="chat inconnu")
        t = now()
        for cid in targets:
            db.execute("INSERT INTO messages(cat_id, kind, payload, created) VALUES(?,?,?,?)",
                       (cid, kind, json.dumps(payload, ensure_ascii=False), t))
        db.commit()
        for cid in targets:
            if cid in events:
                events[cid].set()
        return web.json_response({"ok": True, "sent": len(targets)})

    async def admin_forget(req):
        check_admin(req)
        body = await read_json(req)
        cat = clip(body.get("cat"), 64)
        for table, col in (("messages", "cat_id"), ("replies", "cat_id"), ("cats", "id")):
            db.execute(f"DELETE FROM {table} WHERE {col}=?", (cat,))
        db.commit()
        return web.json_response({"ok": True})

    # ------------------------------------------------------------ déploiement (GitHub Actions)
    gh_cache = {"t": 0.0, "data": None}

    async def github(method, path, body=None):
        cfg = load_config()
        tok = cfg.get("github_token")
        if not tok:
            raise web.HTTPBadRequest(text="token GitHub non configuré")
        headers = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "TamagoChat-server"}
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, GITHUB_API + path, json=body, headers=headers) as r:
                if r.status >= 400:
                    msg = (await r.text())[:200]
                    raise web.HTTPBadGateway(text=f"GitHub a répondu {r.status} : {msg}")
                return None if r.status == 204 else await r.json()

    async def admin_deploy_state(req):
        check_admin(req)
        cfg = load_config()
        repo, rel = cfg.get("github_repo"), latest_release()
        out = {"release": rel, "repo": repo, "has_token": bool(cfg.get("github_token")),
               "has_deploy": bool(cfg.get("deploy_hash")), "commits": [], "runs": [],
               "base_known": bool(rel and rel.get("commit")), "error": None}
        if not (repo and out["has_token"]):
            return web.json_response(out)
        if gh_cache["data"] and now() - gh_cache["t"] < 8 and req.query.get("force") != "1":
            out.update(gh_cache["data"])
            return web.json_response(out)
        try:
            runs = await github("GET", f"/repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=6")
            gh_runs = [{"id": r["id"], "number": r["run_number"], "status": r["status"],
                        "conclusion": r["conclusion"], "title": r.get("display_title"),
                        "created": r["created_at"], "url": r["html_url"]}
                       for r in runs.get("workflow_runs", [])]
            if out["base_known"]:
                cmp = await github("GET", f"/repos/{repo}/compare/{rel['commit']}...main")
                commits = list(reversed(cmp.get("commits", [])))[:30]
            else:
                commits = await github("GET", f"/repos/{repo}/commits?sha=main&per_page=8")
            gh_commits = [{"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n")[0][:120],
                           "author": c["commit"]["author"]["name"], "date": c["commit"]["author"]["date"],
                           "url": c["html_url"]} for c in commits]
            gh_cache.update(t=now(), data={"runs": gh_runs, "commits": gh_commits})
            out.update(gh_cache["data"])
        except web.HTTPException as e:
            out["error"] = e.text
        except Exception as e:
            out["error"] = f"GitHub injoignable ({type(e).__name__})"
        return web.json_response(out)

    async def admin_deploy(req):
        check_admin(req)
        body = await read_json(req)
        cfg = load_config()
        if not cfg.get("github_repo") or not cfg.get("deploy_hash"):
            raise web.HTTPBadRequest(text="déploiement non configuré sur le serveur")
        v = clip(body.get("version"), 20).strip().lstrip("v")
        if v:
            rel = latest_release()
            if not VERSION_RE.fullmatch(v):
                raise web.HTTPBadRequest(text="version invalide (exemple : 1.2.0)")
            if rel and version_tuple(v) <= version_tuple(rel["version"]):
                raise web.HTTPBadRequest(text=f"la version doit être plus grande que {rel['version']}")
        await github("POST", f"/repos/{cfg['github_repo']}/actions/workflows/{WORKFLOW}/dispatches",
                     {"ref": "main", "inputs": {"version": v}})
        gh_cache["data"] = None
        return web.json_response({"ok": True})

    async def admin_deploy_token(req):
        check_admin(req)
        body = await read_json(req)
        tok = clip(body.get("token"), 300).strip()
        cfg = load_config()
        if tok and not re.fullmatch(r"(github_pat_|ghp_)[A-Za-z0-9_]{20,280}", tok):
            raise web.HTTPBadRequest(text="ce n'est pas un token GitHub valide")
        if tok:
            cfg["github_token"] = tok
        else:
            cfg.pop("github_token", None)
        save_config(cfg)
        gh_cache["data"] = None
        if tok and cfg.get("github_repo"):      # vérifie qu'il marche tout de suite
            try:
                await github("GET", f"/repos/{cfg['github_repo']}/actions/workflows/{WORKFLOW}")
            except web.HTTPException as e:
                return web.json_response({"ok": False, "error": e.text})
        return web.json_response({"ok": True})

    async def api_release(req):
        """Reçoit un exe compilé et signé par GitHub Actions (jeton DEPLOY_TOKEN).
        Le serveur revérifie la signature avec la clé publique avant de le publier."""
        import ed25519_min
        cfg = load_config()
        auth = req.headers.get("Authorization", "")
        if (not cfg.get("deploy_hash") or not auth.startswith("Bearer ")
                or not hmac.compare_digest(sha256(auth[7:].strip()), cfg["deploy_hash"])):
            await asyncio.sleep(1)
            raise web.HTTPUnauthorized(text="jeton invalide")
        v = req.headers.get("X-Version", "")
        sha = req.headers.get("X-Sha256", "").lower()
        sig = req.headers.get("X-Signature", "").lower()
        commit = req.headers.get("X-Commit", "").lower()
        if (not VERSION_RE.fullmatch(v) or not re.fullmatch(r"[0-9a-f]{64}", sha)
                or not re.fullmatch(r"[0-9a-f]{128}", sig)):
            raise web.HTTPBadRequest(text="en-têtes invalides")
        rel = latest_release()
        if rel and version_tuple(v) <= version_tuple(rel["version"]):
            raise web.HTTPConflict(text=f"la version doit être plus grande que {rel['version']}")
        name = f"TamagoChat-{v}.exe"
        path = os.path.join(RELEASES, name)
        tmp = path + ".part"
        h, size = hashlib.sha256(), 0
        try:
            with open(tmp, "wb") as f:
                async for chunk in req.content.iter_chunked(65536):
                    size += len(chunk)
                    if size > MAX_RELEASE:
                        raise web.HTTPRequestEntityTooLarge(max_size=MAX_RELEASE, actual_size=size)
                    f.write(chunk)
                    h.update(chunk)
            if h.hexdigest() != sha:
                raise web.HTTPBadRequest(text="fichier corrompu (sha256)")
            if not ed25519_min.verify(bytes.fromhex(cfg.get("update_pubkey", "")),
                                      f"minou-update|{v}|{sha}".encode(), bytes.fromhex(sig)):
                raise web.HTTPBadRequest(text="signature invalide : refusé")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        latest = {"version": v, "file": name, "sha256": sha, "size": size, "sig": sig,
                  "date": time.strftime("%Y-%m-%dT%H:%M:%S"),
                  "commit": commit if re.fullmatch(r"[0-9a-f]{40}", commit) else None}
        lj = os.path.join(RELEASES, "latest.json")
        with open(lj + ".tmp", "w", encoding="utf-8") as f:
            json.dump(latest, f)
        os.replace(lj + ".tmp", lj)
        exes = sorted((p for p in os.listdir(RELEASES) if RELEASE_RE.match(p)),
                      key=lambda p: os.path.getmtime(os.path.join(RELEASES, p)), reverse=True)
        for old in exes[KEEP_RELEASES:]:
            if old != name:
                os.remove(os.path.join(RELEASES, old))
        gh_cache["data"] = None
        return web.json_response({"ok": True, "version": v, "size": size})

    async def root(req):
        raise web.HTTPFound("/admin")

    app = web.Application(client_max_size=512 * 1024)
    app.add_routes([
        web.get("/", root),
        web.post("/api/sync", api_sync),
        web.post("/api/reply", api_reply),
        web.get("/api/latest", api_latest),
        web.get("/download/{name}", download),
        web.get("/admin", admin_page),
        web.post("/admin/api/login", admin_login),
        web.post("/admin/api/logout", admin_logout),
        web.get("/admin/api/state", admin_state),
        web.get("/admin/api/feed", admin_feed),
        web.post("/admin/api/send", admin_send),
        web.get("/admin/api/phrases", admin_phrases),
        web.get("/admin/api/deploy", admin_deploy_state),
        web.post("/admin/api/deploy", admin_deploy),
        web.post("/admin/api/deploy/token", admin_deploy_token),
        web.post("/api/release", api_release),
        web.post("/admin/api/forget", admin_forget),
    ])
    os.makedirs(RELEASES, exist_ok=True)
    web.run_app(app, host=HOST, port=PORT, access_log=None, print=None)


def setup_deploy(repo, pubkey):
    """Active le déploiement depuis GitHub Actions. Affiche le jeton à mettre dans le secret
    DEPLOY_TOKEN du dépôt (il n'est stocké ici que sous forme de hash)."""
    if not re.fullmatch(r"[\w.-]+/[\w.-]+", repo) or not re.fullmatch(r"[0-9a-f]{64}", pubkey):
        sys.exit("usage : server.py setup-deploy PROPRIETAIRE/DEPOT CLE_PUBLIQUE_HEX")
    token = secrets.token_urlsafe(32)
    cfg = load_config()
    cfg.update(github_repo=repo, update_pubkey=pubkey, deploy_hash=sha256(token))
    save_config(cfg)
    print(token)


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "set-password":
        set_password(sys.argv[2])
        print("Mot de passe admin mis à jour.")
    elif len(sys.argv) >= 4 and sys.argv[1] == "setup-deploy":
        setup_deploy(sys.argv[2], sys.argv[3])
    else:
        main()
