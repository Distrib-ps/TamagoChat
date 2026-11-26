import asyncio

from aiohttp import web

from ..errors import Unauthorized
from ..validation import clip
from .helpers import admin_services, ok, read_json, services

routes = web.RouteTableDef()


@routes.get("/admin/api/deploy")
async def status(req):
    svc = admin_services(req)
    return web.json_response(await svc.deploy.status(force=req.query.get("force") == "1"))


@routes.post("/admin/api/deploy")
async def launch(req):
    await admin_services(req).deploy.launch()
    return ok()


@routes.post("/admin/api/deploy/token")
async def set_token(req):
    svc = admin_services(req)
    body = await read_json(req)
    error = await svc.deploy.set_token(clip(body.get("token"), 300).strip())
    return web.json_response({"ok": False, "error": error} if error else {"ok": True})


@routes.post("/api/release")
async def receive_release(req):
    svc = services(req)
    if not svc.auth.deploy_token_valid(req.headers.get("Authorization", "")):
        await asyncio.sleep(1)
        raise Unauthorized("jeton invalide")
    h = req.headers
    version, platform = h.get("X-Version", ""), h.get("X-Platform", "win")
    already, size = await svc.releases.receive(
        req.content.iter_chunked(65536), platform, version, h.get("X-Sha256", ""),
        h.get("X-Signature", ""), h.get("X-Commit", ""), svc.config.get("update_pubkey", ""))
    svc.deploy.forget_cache()
    if already:
        return ok(version=version, already=True)
    return ok(version=version, platform=platform, size=size)
