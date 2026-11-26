import aiohttp

from ..errors import BadRequest, UpstreamError
from ..settings import GITHUB_API, WORKFLOW


class GitHub:
    def __init__(self, config):
        self.config = config

    async def call(self, method, path, body=None):
        tok = self.config.get("github_token")
        if not tok:
            raise BadRequest("token GitHub non configuré")
        headers = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "TamagoChat-server"}
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.request(method, GITHUB_API + path, json=body, headers=headers) as r:
                if r.status >= 400:
                    msg = (await r.text())[:200]
                    raise UpstreamError(f"GitHub a répondu {r.status} : {msg}")
                return None if r.status == 204 else await r.json()

    async def runs(self, repo):
        data = await self.call("GET", f"/repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=6")
        return [{"id": r["id"], "number": r["run_number"], "status": r["status"],
                 "conclusion": r["conclusion"], "title": r.get("display_title"),
                 "created": r["created_at"], "url": r["html_url"]}
                for r in data.get("workflow_runs", [])]

    async def commits(self, repo, since=None):
        if since:
            cmp = await self.call("GET", f"/repos/{repo}/compare/{since}...main")
            commits = list(reversed(cmp.get("commits", [])))[:30]
        else:
            commits = await self.call("GET", f"/repos/{repo}/commits?sha=main&per_page=8")
        return [{"sha": c["sha"][:7], "message": c["commit"]["message"].split("\n")[0][:120],
                 "author": c["commit"]["author"]["name"], "date": c["commit"]["author"]["date"],
                 "url": c["html_url"]} for c in commits]

    async def run_workflow(self, repo):
        await self.call("POST", f"/repos/{repo}/actions/workflows/{WORKFLOW}/dispatches", {"ref": "main"})

    async def check_access(self, repo):
        await self.call("GET", f"/repos/{repo}/actions/workflows/{WORKFLOW}")
