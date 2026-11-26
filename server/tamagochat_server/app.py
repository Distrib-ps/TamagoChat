from aiohttp import web

from .errors import ServiceError
from .services.auth import Auth
from .services.cats import Cats
from .services.deploy import Deploy
from .services.github import GitHub
from .services.messages import Messages
from .services.releases import Releases
from .settings import MAX_REQUEST, WEB_DIR, Paths
from .storage import database
from .storage.config_store import ConfigStore


class Services:

    def __init__(self, data_dir, secure_cookies=True):
        self.paths = Paths(data_dir)
        self.db = database.connect(self.paths.database)
        self.config = ConfigStore(self.paths.config)
        self.auth = Auth(self.db, self.config)
        self.cats = Cats(self.db)
        self.messages = Messages(self.db)
        self.releases = Releases(self.paths.releases)
        self.deploy = Deploy(self.config, self.releases, GitHub(self.config))
        self.secure_cookies = secure_cookies      # False seulement en test local (http://)

    def close(self):
        self.db.close()


SERVICES = web.AppKey("services", Services)


@web.middleware
async def service_errors(req, handler):
    try:
        return await handler(req)
    except ServiceError as e:
        return web.Response(status=e.status, text=e.message)


@web.middleware
async def security_headers(req, handler):
    resp = await handler(req)
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    if req.path.startswith("/admin/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


def create_app(services):
    from .api import admin, auth, cats, deploy, pages

    app = web.Application(client_max_size=MAX_REQUEST, middlewares=[security_headers, service_errors])
    app[SERVICES] = services
    for module in (pages, cats, auth, admin, deploy):
        app.add_routes(module.routes)
    app.router.add_static("/admin/static", WEB_DIR)
    return app
