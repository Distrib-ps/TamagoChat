import re
import time

from ..errors import BadRequest, ServiceError

TOKEN_RE = re.compile(r"(github_pat_|ghp_)[A-Za-z0-9_]{20,280}")
CACHE_SECONDS = 8


class Deploy:
    def __init__(self, config, releases, github):
        self.config = config
        self.releases = releases
        self.github = github
        self._cache = {"t": 0.0, "data": None}

    def forget_cache(self):
        self._cache["data"] = None

    async def status(self, force=False):
        cfg = self.config.load()
        repo, rel = cfg.get("github_repo"), self.releases.latest("win")
        out = {"release": rel, "release_mac": self.releases.latest("mac"), "repo": repo,
               "has_token": bool(cfg.get("github_token")), "has_deploy": bool(cfg.get("deploy_hash")),
               "commits": [], "runs": [], "base_known": bool(rel and rel.get("commit")), "error": None}
        if not (repo and out["has_token"]):
            return out
        if self._cache["data"] and time.time() - self._cache["t"] < CACHE_SECONDS and not force:
            return {**out, **self._cache["data"]}
        try:
            data = {"runs": await self.github.runs(repo),
                    "commits": await self.github.commits(repo, rel["commit"] if out["base_known"] else None)}
            self._cache.update(t=time.time(), data=data)
            out.update(data)
        except ServiceError as e:
            out["error"] = e.message
        except Exception as e:
            out["error"] = f"GitHub injoignable ({type(e).__name__})"
        return out

    async def launch(self):
        repo = self.config.get("github_repo")
        if not repo or not self.config.get("deploy_hash"):
            raise BadRequest("déploiement non configuré sur le serveur")
        await self.github.run_workflow(repo)
        self.forget_cache()

    async def set_token(self, token):
        if token and not TOKEN_RE.fullmatch(token):
            raise BadRequest("ce n'est pas un token GitHub valide")
        cfg = self.config.load()
        if token:
            cfg["github_token"] = token
        else:
            cfg.pop("github_token", None)
        self.config.save(cfg)
        self.forget_cache()
        if token and cfg.get("github_repo"):
            try:
                await self.github.check_access(cfg["github_repo"])
            except ServiceError as e:
                return e.message
        return None
