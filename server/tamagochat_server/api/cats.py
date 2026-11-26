from aiohttp import web

from ..errors import BadRequest
from ..services.releases import platform_of
from ..settings import POLL_TIMEOUT
from ..validation import clip, int_list
from .helpers import ok, read_json, services

routes = web.RouteTableDef()


@routes.post("/api/sync")
async def sync(req):
    svc = services(req)
    body = await read_json(req)
    cid = svc.cats.authenticate(body.get("cat_id"), body.get("secret"))
    accept = svc.cats.record_sync(cid, body)
    svc.messages.acknowledge(cid, int_list(body.get("ack"), 200))
    msgs = []
    if accept:
        msgs = await svc.messages.collect(cid, POLL_TIMEOUT if body.get("wait", True) else 0)
    svc.cats.touch(cid)
    return web.json_response({"messages": msgs,
                              "update": svc.releases.latest(platform_of(body.get("platform")))})


@routes.post("/api/reply")
async def reply(req):
    svc = services(req)
    body = await read_json(req)
    cid = svc.cats.authenticate(body.get("cat_id"), body.get("secret"))
    text = clip(body.get("text"), 500).strip()
    if not text:
        raise BadRequest("message vide")
    svc.messages.add_reply(cid, text)
    return ok()


@routes.get("/api/latest")
async def latest(req):
    return web.json_response({"update": services(req).releases.latest(req.query.get("platform"))})


@routes.get("/download/{name}")
async def download(req):
    path = services(req).releases.file(req.match_info["name"])
    if not path:
        raise web.HTTPNotFound()
    return web.FileResponse(path, headers={"Content-Type": "application/octet-stream"})
