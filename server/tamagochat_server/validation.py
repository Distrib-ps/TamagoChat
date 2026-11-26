import hashlib
import json
import re

from .errors import BadRequest
from .settings import ACTIONS, MAX_PHRASES_JSON, SIZES, STAT_KEYS


def sha256(s):
    return hashlib.sha256(s.encode()).hexdigest()


def clip(v, n):
    return str(v if v is not None else "")[:n]


def version_tuple(v):
    return tuple(int(x) for x in str(v).split(".") if x.isdigit())


def is_int(v, lo, hi):
    return isinstance(v, int) and not isinstance(v, bool) and lo <= v <= hi


def int_list(v, limit):
    return [i for i in v if isinstance(i, int)][:limit] if isinstance(v, list) else []


def clean_stats(stats):
    if not isinstance(stats, dict):
        return {}
    return {k: round(max(0.0, min(100.0, float(stats[k]))), 1) for k in STAT_KEYS
            if isinstance(stats.get(k), (int, float)) and not isinstance(stats[k], bool)}


def clean_settings(s, with_name):
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
    """Phrases envoyées par un chat : {cats: [[clé, libellé]], list: {clé: [...]}, custom: [...]}.
    Renvoie le JSON à stocker, ou None si c'est invalide ou trop gros."""
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


def clean_message(body):
    kind = body.get("kind")
    if kind == "say":
        text = clip(body.get("text"), 500).strip()
        if not text:
            raise BadRequest("message vide")
        payload = {"text": text, "from": clip(body.get("from"), 40).strip()}
        if is_int(body.get("secs"), 3, 600):
            payload["secs"] = body["secs"]
        return kind, payload
    if kind == "action" and body.get("action") in ACTIONS:
        return kind, {"action": body["action"]}
    if kind == "settings":
        settings = clean_settings(body.get("settings"), with_name=True)
        if not settings:
            raise BadRequest("réglage invalide")
        return kind, {"settings": settings}
    if kind == "stats":
        st = body.get("stats") if isinstance(body.get("stats"), dict) else {}
        st = {k: st[k] for k in STAT_KEYS if is_int(st.get(k), 0, 100)}
        if not st:
            raise BadRequest("jauges invalides")
        return kind, {"stats": st}
    if kind == "phrases" and re.fullmatch(r"[a-z_]{1,40}", str(body.get("key", ""))):
        if body.get("reset") is True:
            return kind, {"key": body["key"], "reset": True}
        if isinstance(body.get("list"), list):
            lst = [clip(x, 200).strip() for x in body["list"][:100]]
            return kind, {"key": body["key"], "list": [x for x in lst if x]}
        raise BadRequest("phrases invalides")
    raise BadRequest("type inconnu")
