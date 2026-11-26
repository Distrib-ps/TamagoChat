import os

from aiohttp import web

from ..settings import WEB_DIR

routes = web.RouteTableDef()

PAGE_HEADERS = {
    "Cache-Control": "no-store", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'self'; "
        "frame-ancestors 'none'"),
}


@routes.get("/")
async def root(req):
    raise web.HTTPFound("/admin")


@routes.get("/admin")
async def admin_page(req):
    return web.FileResponse(os.path.join(WEB_DIR, "index.html"), headers=PAGE_HEADERS)
