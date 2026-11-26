import hashlib
import os
import secrets
import sys
import tempfile

from aiohttp.test_utils import AioHTTPTestCase

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagochat_server.app import Services, create_app      # noqa: E402
from tamagochat_server.services.signing import ed25519      # noqa: E402
from tamagochat_server.validation import sha256             # noqa: E402

PASSWORD = "chut"
SIGNING_KEY = bytes(range(32))


class ServerTestCase(AioHTTPTestCase):
    async def get_application(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.services = Services(self.tmp.name)
        self.services.auth.set_password(PASSWORD)
        self.deploy_token = "jeton-de-test"
        self.services.config.update(
            github_repo="moi/TamagoChat", deploy_hash=sha256(self.deploy_token),
            update_pubkey=ed25519().public_key(SIGNING_KEY).hex())
        self.cookie = None
        return create_app(self.services)

    async def asyncTearDown(self):
        await super().asyncTearDown()
        self.services.close()
        self.tmp.cleanup()

    def new_cat(self):
        return {"cat_id": secrets.token_hex(16), "secret": secrets.token_hex(16)}

    async def sync(self, cat, **body):
        r = await self.client.post("/api/sync", json={**cat, "wait": False, **body})
        self.assertEqual(r.status, 200, await r.text())
        return await r.json()

    async def login(self):
        r = await self.client.post("/admin/api/login", json={"password": PASSWORD})
        self.assertEqual(r.status, 200)
        set_cookie = r.headers["Set-Cookie"]
        self.assertIn("Secure", set_cookie)
        self.assertIn("HttpOnly", set_cookie)
        self.cookie = r.cookies["minou_admin"].value

    async def admin(self, path, body=None, status=200):
        headers = {"Cookie": f"minou_admin={self.cookie}"} if self.cookie else {}
        if body is None:
            r = await self.client.get(path, headers=headers)
        else:
            r = await self.client.post(path, json=body, headers=headers)
        self.assertEqual(r.status, status, await r.text())
        return await r.json() if status == 200 else await r.text()

    async def upload(self, data, version, platform="win", tag="minou-update", token=None, key=SIGNING_KEY):
        sha = hashlib.sha256(data).hexdigest()
        sig = ed25519().sign(key, f"{tag}|{version}|{sha}".encode()).hex()
        return await self.client.post("/api/release", data=data, headers={
            "Authorization": f"Bearer {token or self.deploy_token}", "X-Platform": platform,
            "X-Version": version, "X-Sha256": sha, "X-Signature": sig, "X-Commit": "a" * 40})
