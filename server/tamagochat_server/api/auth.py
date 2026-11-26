import asyncio

from aiohttp import web

from ..errors import Unauthorized
from ..settings import SESSION_COOKIE, SESSION_DAYS
from ..validation import clip
from .helpers import client_ip, ok, read_json, services

routes = web.RouteTableDef()


@routes.post("/admin/api/login")
async def login(req):
    svc = services(req)
    ip = client_ip(req)
    svc.auth.check_attempts(ip)
    body = await read_json(req)
    if not svc.auth.check_password(clip(body.get("password"), 200)):
        svc.auth.failed(ip)
        await asyncio.sleep(1)
        raise Unauthorized("mot de passe incorrect")
    svc.auth.succeeded(ip)
    resp = ok()
    resp.set_cookie(SESSION_COOKIE, svc.auth.open_session(), max_age=SESSION_DAYS * 86400,
                    path="/admin", httponly=True, secure=svc.secure_cookies, samesite="Strict")
    return resp


@routes.post("/admin/api/logout")
async def logout(req):
    services(req).auth.close_session(req.cookies.get(SESSION_COOKIE))
    resp = ok()
    resp.del_cookie(SESSION_COOKIE, path="/admin")
    return resp
