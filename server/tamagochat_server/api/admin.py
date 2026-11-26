import time

from aiohttp import web

from ..errors import NotFound
from ..validation import clean_message, clip
from .helpers import admin_services, ok, read_json

routes = web.RouteTableDef()


@routes.get("/admin/api/state")
async def state(req):
    svc = admin_services(req)
    return web.json_response({"cats": svc.cats.overview(), "release": svc.releases.latest("win"),
                              "release_mac": svc.releases.latest("mac"), "now": time.time()})


@routes.get("/admin/api/feed")
async def feed(req):
    svc = admin_services(req)
    items = svc.messages.conversation(req.query.get("cat", "*"), svc.cats.names())
    return web.json_response({"items": items})


@routes.get("/admin/api/phrases")
async def phrases(req):
    svc = admin_services(req)
    return web.json_response(svc.cats.phrases(req.query.get("cat", "")))


@routes.post("/admin/api/send")
async def send(req):
    svc = admin_services(req)
    body = await read_json(req)
    kind, payload = clean_message(body)
    cat = clip(body.get("cat"), 64)
    if cat == "*":
        targets = svc.cats.ids()
    elif svc.cats.exists(cat):
        targets = [cat]
    else:
        raise NotFound("chat inconnu")
    svc.messages.send(targets, kind, payload)
    return ok(sent=len(targets))


@routes.post("/admin/api/forget")
async def forget(req):
    svc = admin_services(req)
    body = await read_json(req)
    svc.cats.forget(clip(body.get("cat"), 64))
    return ok()
