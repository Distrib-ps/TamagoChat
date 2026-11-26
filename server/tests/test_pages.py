import os
import re
import unittest

from support import ServerTestCase

from tamagochat_server.settings import WEB_DIR

BUILT = os.path.isfile(os.path.join(WEB_DIR, "index.html"))


@unittest.skipUnless(BUILT, "page admin non compilée (cd web && npm run build)")
class PagesTest(ServerTestCase):
    async def test_root_redirects_to_admin(self):
        r = await self.client.get("/", allow_redirects=False)
        self.assertEqual((r.status, r.headers["Location"]), (302, "/admin"))

    async def test_admin_page_headers(self):
        r = await self.client.get("/admin")
        self.assertEqual(r.status, 200)
        self.assertIn("script-src 'self'", r.headers["Content-Security-Policy"])
        self.assertEqual((r.headers["Cache-Control"], r.headers["X-Frame-Options"]), ("no-store", "DENY"))

    async def test_every_referenced_file_is_served(self):
        page = await (await self.client.get("/admin")).text()
        todo = re.findall(r'(?:href|src)="(/admin/static/[^"]+)"', page)
        self.assertGreaterEqual(len(todo), 3)
        seen = set()
        while todo:
            url = todo.pop()
            if url in seen:
                continue
            seen.add(url)
            r = await self.client.get(url)
            self.assertEqual(r.status, 200, url)
            self.assertEqual(r.headers["Cache-Control"], "no-cache")
            folder = url.rsplit("/", 1)[0]
            if url.endswith(".js"):
                self.assertIn("javascript", r.headers["Content-Type"])
                refs = re.findall(r'from "(\.[^"]+)"', await r.text())
            elif url.endswith(".css"):
                refs = re.findall(r'@import "([^"]+)"', await r.text())
            else:
                refs = []
            todo += [os.path.normpath(f"{folder}/{ref}") for ref in refs]
        self.assertTrue(any(u.endswith(".js") for u in seen) and any(u.endswith(".css") for u in seen))
        self.assertTrue(os.path.isfile(os.path.join(WEB_DIR, "images", "cat.png")))

    async def test_no_access_outside_web_folder(self):
        r = await self.client.get("/admin/static/../server.py")
        self.assertIn(r.status, (403, 404))
