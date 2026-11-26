from aiohttp import web

from ..app import SERVICES
from ..errors import BadRequest, Unauthorized
from ..settings import SESSION_COOKIE


def services(req):
    return req.app[SERVICES]


async def read_json(req):
    try:
        data = await req.json()
    except Exception:
        raise BadRequest("JSON invalide")
    if not isinstance(data, dict):
        raise BadRequest("JSON invalide")
    return data


def client_ip(req):
    return req.headers.get("X-Real-IP") or req.remote or "?"


def admin_services(req):
    svc = services(req)
    if not svc.auth.session_valid(req.cookies.get(SESSION_COOKIE)):
        raise Unauthorized("non connecté")
    return svc


def ok(**data):
    return web.json_response({"ok": True, **data})
