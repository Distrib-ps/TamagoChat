import hashlib
import json
import os
import re
import time

from ..errors import BadRequest, Conflict, TooLarge
from ..settings import KEEP_RELEASES, MAX_RELEASE, PLATFORMS, RELEASE_FILE_RE, VERSION_RE
from ..validation import version_tuple
from .signing import verify


def platform_of(value):
    """Plateforme annoncée par un chat ; les anciens chats Windows n'en envoient pas."""
    return value if isinstance(value, str) and value in PLATFORMS else "win"


class Releases:
    def __init__(self, folder):
        self.folder = folder
        self._cache = {}
        os.makedirs(folder, exist_ok=True)

    def latest(self, platform="win"):
        platform = platform_of(platform)
        path = os.path.join(self.folder, PLATFORMS[platform]["latest"])
        cache = self._cache.setdefault(platform, {"mtime": None, "data": None})
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return None
        if mtime != cache["mtime"]:
            try:
                with open(path, encoding="utf-8") as f:
                    rel = json.load(f)
                cache["data"] = {
                    "version": rel["version"], "url": "/download/" + rel["file"],
                    "sha256": rel["sha256"], "size": rel["size"], "sig": rel["sig"],
                    "date": rel.get("date"), "commit": rel.get("commit")}
            except Exception:
                cache["data"] = None
            cache["mtime"] = mtime
        return cache["data"]

    def file(self, name):
        path = os.path.join(self.folder, name)
        return path if RELEASE_FILE_RE.match(name) and os.path.isfile(path) else None

    async def receive(self, chunks, platform, version, sha, sig, commit, pubkey):
        sha, sig, commit = sha.lower(), sig.lower(), commit.lower()
        if (not VERSION_RE.fullmatch(version) or not re.fullmatch(r"[0-9a-f]{64}", sha)
                or not re.fullmatch(r"[0-9a-f]{128}", sig) or platform not in PLATFORMS):
            raise BadRequest("en-têtes invalides")
        current = self.latest(platform)
        if current and current["version"] == version and current["sha256"] == sha:
            return True, current["size"]                     # publication relancée
        # même numéro mais autre fichier : publication relancée après un échec (la compilation
        # n'est pas reproductible à l'octet près) ; on remplace, c'est le même code source
        if current and version_tuple(version) < version_tuple(current["version"]):
            raise Conflict(f"la version doit être plus grande que {current['version']}")

        name = PLATFORMS[platform]["file"].format(v=version)
        path = os.path.join(self.folder, name)
        tmp = path + ".part"
        h, size = hashlib.sha256(), 0
        try:
            with open(tmp, "wb") as f:
                async for chunk in chunks:
                    size += len(chunk)
                    if size > MAX_RELEASE:
                        raise TooLarge(f"fichier trop gros (max {MAX_RELEASE // 2 ** 20} Mo)")
                    f.write(chunk)
                    h.update(chunk)
            if h.hexdigest() != sha:
                raise BadRequest("fichier corrompu (sha256)")
            message = f"{PLATFORMS[platform]['tag']}|{version}|{sha}".encode()
            if not verify(pubkey, message, sig):
                raise BadRequest("signature invalide : refusé")
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
        self._publish(platform, name, version, sha, sig, size,
                      commit if re.fullmatch(r"[0-9a-f]{40}", commit) else None)
        return False, size

    def _publish(self, platform, name, version, sha, sig, size, commit):
        latest = {"version": version, "file": name, "sha256": sha, "size": size, "sig": sig,
                  "date": time.strftime("%Y-%m-%dT%H:%M:%S"), "commit": commit}
        lj = os.path.join(self.folder, PLATFORMS[platform]["latest"])
        with open(lj + ".tmp", "w", encoding="utf-8") as f:
            json.dump(latest, f)
        os.replace(lj + ".tmp", lj)
        same = (p for p in os.listdir(self.folder)
                if RELEASE_FILE_RE.match(p) and p.endswith("-mac.zip") == (platform == "mac"))
        files = sorted(same, key=lambda p: os.path.getmtime(os.path.join(self.folder, p)),
                       reverse=True)
        for old in files[KEEP_RELEASES:]:
            if old != name:
                os.remove(os.path.join(self.folder, old))
