"""Publie une nouvelle version de TamagoChat : tous les chats se mettront à jour tout seuls.

    .\\publier.ps1            -> version suivante automatique (1.0.0 -> 1.0.1)
    .\\publier.ps1 1.2.0      -> version précise

Étapes : change APP_VERSION dans chat.pyw, compile dist\\TamagoChat.exe, le signe avec la clé
privée (~\\.minou\\signing.key, qui ne quitte jamais ce PC) et l'envoie sur le VPS.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ed25519_min  # noqa: E402

try:
    import local_config as cfg  # noqa: E402  (non versionné : voir local_config.example.py)
except ImportError:
    sys.exit("Crée local_config.py à partir de local_config.example.py avant de publier.")
VPS = cfg.VPS                   # ex. "root@1.2.3.4"
REMOTE_DIR = "/opt/minou-server/releases"
KEY_FILE = os.path.expanduser(r"~\.minou\signing.key")
SOURCE = os.path.join(HERE, "chat.pyw")
EXE = os.path.join(HERE, "dist", "TamagoChat.exe")
KEEP = 5   # nombre d'anciennes versions gardées sur le serveur

# Le ssh de Windows refuse la clé (droits du fichier jugés trop larges) : on prend celui de Git.
GIT_BIN = r"C:\Program Files\Git\usr\bin"
SSH = os.path.join(GIT_BIN, "ssh.exe") if os.path.exists(os.path.join(GIT_BIN, "ssh.exe")) else "ssh"
SCP = os.path.join(GIT_BIN, "scp.exe") if os.path.exists(os.path.join(GIT_BIN, "scp.exe")) else "scp"
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]   # échoue au lieu d'attendre un mot de passe


def vt(v):
    return tuple(int(x) for x in v.split("."))


def run(cmd):
    print("  >", " ".join(cmd) if len(" ".join(cmd)) < 140 else cmd[0] + " ...")
    subprocess.run(cmd, check=True)


def main():
    src = open(SOURCE, encoding="utf-8").read()
    current = re.search(r'^APP_VERSION = "([\d.]+)"', src, re.M).group(1)
    try:    # une version a peut-être été publiée depuis GitHub (bouton « Déployer » de l'admin)
        with urllib.request.urlopen(cfg.SERVER_URL.rstrip("/") + "/api/latest", timeout=15) as r:
            upd = json.load(r).get("update")
        if upd and vt(upd["version"]) > vt(current):
            current = upd["version"]
    except Exception as e:
        print(f"(version publiée inconnue : {e})")
    pubkey = cfg.UPDATE_PUBKEY
    if len(sys.argv) > 1:
        new = sys.argv[1].lstrip("v")
        if not re.fullmatch(r"\d+(\.\d+){1,3}", new):
            sys.exit(f"Version invalide : {new} (exemple : 1.2.0)")
        if vt(new) <= vt(current):
            sys.exit(f"La version doit être plus grande que l'actuelle ({current}).")
    else:
        parts = current.split(".")
        parts[-1] = str(int(parts[-1]) + 1)
        new = ".".join(parts)

    secret = bytes.fromhex(open(KEY_FILE).read().strip())
    if ed25519_min.public_key(secret).hex() != pubkey:
        sys.exit("La clé de signature ne correspond pas à UPDATE_PUBKEY de local_config.py : arrêt.")

    print(f"1/4  Version {current} -> {new}")
    src = re.sub(r'^APP_VERSION = "[\d.]+"', f'APP_VERSION = "{new}"', src, count=1, flags=re.M)
    with open(SOURCE, "w", encoding="utf-8", newline="") as f:
        f.write(src)

    print("2/4  Compilation de TamagoChat.exe")
    ico = os.path.join(HERE, "chat.ico")
    build = os.path.join(tempfile.gettempdir(), "minou-build")
    run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--log-level",
         "WARN", "--name", "TamagoChat", "--icon", ico, "--add-data", f"{ico};.", "--workpath", build,
         "--specpath", build, "--distpath", os.path.join(HERE, "dist"), SOURCE])

    print("3/4  Signature")
    data = open(EXE, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    sig = ed25519_min.sign(secret, f"minou-update|{new}|{sha}".encode())
    assert ed25519_min.verify(bytes.fromhex(pubkey), f"minou-update|{new}|{sha}".encode(), sig)
    name = f"TamagoChat-{new}.exe"
    latest = {"version": new, "file": name, "sha256": sha, "size": len(data), "sig": sig.hex(),
              "date": datetime.datetime.now().isoformat(timespec="seconds")}

    print("4/4  Envoi sur le serveur")
    tmp_json = os.path.join(tempfile.gettempdir(), "minou-latest.json")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(latest, f)
    # chemins en /c/... : le scp de Git interprète "C:" comme un nom de machine
    def posix(p):
        return "/" + p[0].lower() + p[2:].replace("\\", "/") if re.match(r"^[A-Za-z]:", p) else p
    run([SCP, "-q", *SSH_OPTS, posix(EXE), f"{VPS}:{REMOTE_DIR}/{name}"])
    run([SCP, "-q", *SSH_OPTS, posix(tmp_json), f"{VPS}:{REMOTE_DIR}/latest.json.tmp"])
    run([SSH, *SSH_OPTS, VPS,
         f"cd {REMOTE_DIR} && mv latest.json.tmp latest.json && chown minou:minou * && "
         f"ls -t *.exe | tail -n +{KEEP + 1} | xargs -r rm --"])
    os.remove(tmp_json)
    print(f"\nVersion {new} publiée. Les chats connectés la recevront dans la minute.")
    print(f"L'exe est aussi dans {EXE} si tu veux le donner à la main.")


if __name__ == "__main__":
    main()
