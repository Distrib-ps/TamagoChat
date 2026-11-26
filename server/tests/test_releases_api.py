import hashlib
import os

from support import ServerTestCase, ed25519, SIGNING_KEY


class ReleasesApiTest(ServerTestCase):
    async def test_release_upload_per_platform(self):
        exe, mac = b"MZ" + os.urandom(1000), b"PK" + os.urandom(1000)
        r = await self.upload(exe, "1.3.0")
        self.assertEqual(r.status, 200, await r.text())
        r = await self.upload(mac, "1.3.0", platform="mac", tag="minou-update-mac")
        self.assertEqual(r.status, 200, await r.text())
        again = await self.upload(exe, "1.3.0")
        self.assertTrue((await again.json())["already"])

        cat = self.new_cat()
        win = (await self.sync(cat))["update"]
        self.assertEqual((win["version"], win["url"]), ("1.3.0", "/download/TamagoChat-1.3.0.exe"))
        self.assertEqual(win["sha256"], hashlib.sha256(exe).hexdigest())
        self.assertTrue(ed25519().verify(ed25519().public_key(SIGNING_KEY),
                                         f"minou-update|1.3.0|{win['sha256']}".encode(), bytes.fromhex(win["sig"])))
        macu = (await self.sync(cat, platform="mac"))["update"]
        self.assertEqual(macu["url"], "/download/TamagoChat-1.3.0-mac.zip")
        latest = await (await self.client.get("/api/latest?platform=mac")).json()
        self.assertEqual(latest["update"]["version"], "1.3.0")
        r = await self.client.get(win["url"])
        self.assertEqual(await r.read(), exe)
        self.assertEqual((await self.client.get("/download/server.py")).status, 404)

    async def test_release_upload_rejections(self):
        data = os.urandom(100)
        self.assertEqual((await self.upload(data, "2.0.0", token="faux")).status, 401)
        self.assertEqual((await self.upload(data, "2.0.0", key=bytes(32))).status, 400)
        self.assertEqual((await self.upload(data, "2.0.0", tag="minou-update-mac")).status, 400)
        self.assertEqual((await self.upload(data, "2.0.0", platform="linux")).status, 400)
        self.assertEqual((await self.upload(data, "2.0.0")).status, 200)
        self.assertEqual((await self.upload(os.urandom(100), "1.9.0")).status, 409)
        self.assertEqual(sorted(os.listdir(self.services.paths.releases)), ["TamagoChat-2.0.0.exe", "latest.json"])


if __name__ == "__main__":
    import unittest
    unittest.main()
