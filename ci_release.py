"""Publication automatique, utilisée par GitHub Actions (.github/workflows/release.yml).

    python ci_release.py prepare   -> choisit la version, l'écrit dans chat.pyw, crée local_config.py
    python ci_release.py upload    -> signe dist/TamagoChat.exe et l'envoie au serveur

Variables d'environnement (secrets / variables du dépôt GitHub) :
    SERVER_URL, UPDATE_PUBKEY, SIGNING_KEY, DEPLOY_TOKEN, INPUT_VERSION (facultatif), GITHUB_SHA
Le serveur revérifie la signature avec sa propre copie de la clé publique avant de publier.
"""
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ed25519_min  # noqa: E402

SOURCE = os.path.join(HERE, "chat.pyw")
EXE = os.path.join(HERE, "dist", "TamagoChat.exe")
VERSION_RE = re.compile(r"\d+(\.\d+){1,3}")


def env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        sys.exit(f"Variable manquante : {name} (à définir dans les secrets / variables du dépôt)")
    return v


def vt(v):
    return tuple(int(x) for x in v.split("."))


def server():
    return env("SERVER_URL").rstrip("/")


def published_version():
    req = urllib.request.Request(server() + "/api/latest", headers={"User-Agent": "TamagoChat-CI"})
    with urllib.request.urlopen(req, timeout=20) as r:
        upd = json.load(r).get("update")
    return upd["version"] if upd else None


def prepare():
    src = open(SOURCE, encoding="utf-8").read()
    in_code = re.search(r'^APP_VERSION = "([\d.]+)"', src, re.M).group(1)
    latest = published_version()
    wanted = os.environ.get("INPUT_VERSION", "").strip().lstrip("v")
    if wanted:
        if not VERSION_RE.fullmatch(wanted):
            sys.exit(f"Version invalide : {wanted!r} (exemple : 1.2.0)")
        if latest and vt(wanted) <= vt(latest):
            sys.exit(f"La version {wanted} doit être plus grande que la version publiée ({latest}).")
        new = wanted
    else:
        base = max([v for v in (latest, in_code) if v], key=vt)
        parts = base.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new = ".".join(parts)
    src = re.sub(r'^APP_VERSION = "[\d.]+"', f'APP_VERSION = "{new}"', src, count=1, flags=re.M)
    with open(SOURCE, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    pubkey = env("UPDATE_PUBKEY")
    if not re.fullmatch(r"[0-9a-f]{64}", pubkey):
        sys.exit("UPDATE_PUBKEY invalide")
    with open(os.path.join(HERE, "local_config.py"), "w", encoding="utf-8") as f:
        f.write(f"SERVER_URL = {server()!r}\nUPDATE_PUBKEY = {pubkey!r}\nVPS = ''\n")
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(f"version={new}\n")
    print(f"Version publiée : {latest or 'aucune'} -> nouvelle version : {new}")


def upload():
    src = open(SOURCE, encoding="utf-8").read()
    version = re.search(r'^APP_VERSION = "([\d.]+)"', src, re.M).group(1)
    secret = bytes.fromhex(env("SIGNING_KEY"))
    if ed25519_min.public_key(secret).hex() != env("UPDATE_PUBKEY"):
        sys.exit("SIGNING_KEY ne correspond pas à UPDATE_PUBKEY : arrêt.")
    data = open(EXE, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    sig = ed25519_min.sign(secret, f"minou-update|{version}|{sha}".encode()).hex()
    req = urllib.request.Request(server() + "/api/release", data=data, method="POST", headers={
        "Authorization": "Bearer " + env("DEPLOY_TOKEN"), "Content-Type": "application/octet-stream",
        "X-Version": version, "X-Sha256": sha, "X-Signature": sig,
        "X-Commit": os.environ.get("GITHUB_SHA", ""), "User-Agent": "TamagoChat-CI"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            print("Serveur :", json.load(r))
    except urllib.error.HTTPError as e:
        sys.exit(f"Le serveur a refusé ({e.code}) : {e.read().decode(errors='replace')[:300]}")
    print(f"Version {version} publiée ({len(data) / 1e6:.1f} Mo). Les chats se mettent à jour seuls.")


if __name__ == "__main__":
    {"prepare": prepare, "upload": upload}[sys.argv[1] if len(sys.argv) > 1 else ""]()
