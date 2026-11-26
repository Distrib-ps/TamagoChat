from support import ServerTestCase


class AdminApiTest(ServerTestCase):
    async def test_send_validation(self):
        cat = self.new_cat()
        await self.sync(cat)
        cid = cat["cat_id"]
        await self.login()
        ok = [{"kind": "settings", "settings": {"name": "Félix", "crazy_min": 3}},
              {"kind": "stats", "stats": {"bonheur": 100}},
              {"kind": "phrases", "key": "idle", "list": ["a", " ", "b"]},
              {"kind": "phrases", "key": "idle", "reset": True}]
        for body in ok:
            await self.admin("/admin/api/send", {"cat": cid, **body})
        bad = [{"kind": "say", "text": "  "}, {"kind": "action", "action": "explode"},
               {"kind": "settings", "settings": {"size": "Énorme"}}, {"kind": "stats", "stats": {"bonheur": 101}},
               {"kind": "phrases", "key": "Idle!", "list": []}, {"kind": "nope"}]
        for body in bad:
            await self.admin("/admin/api/send", {"cat": cid, **body}, status=400)
        await self.admin("/admin/api/send", {"cat": "0" * 32, "kind": "action", "action": "meow"}, status=404)
        msgs = (await self.sync(cat))["messages"]
        self.assertEqual([m["kind"] for m in msgs], ["settings", "stats", "phrases", "phrases"])
        self.assertEqual(msgs[2]["list"], ["a", "b"])

    async def test_forget(self):
        cat = self.new_cat()
        await self.sync(cat)
        await self.login()
        await self.admin("/admin/api/forget", {"cat": cat["cat_id"]})
        self.assertEqual((await self.admin("/admin/api/state"))["cats"], [])

    async def test_admin_requires_login(self):
        for path in ("/admin/api/state", "/admin/api/feed", "/admin/api/deploy"):
            await self.admin(path, status=401)
        await self.admin("/admin/api/send", {"cat": "*", "kind": "action", "action": "meow"}, status=401)
        r = await self.client.post("/admin/api/login", json={"password": "faux"})
        self.assertEqual(r.status, 401)
        await self.login()
        await self.admin("/admin/api/state")
        await self.admin("/admin/api/logout", {})
        await self.admin("/admin/api/state", status=401)

    async def test_deploy_state_without_github_token(self):
        await self.login()
        d = await self.admin("/admin/api/deploy")
        self.assertEqual((d["has_deploy"], d["has_token"], d["repo"]), (True, False, "moi/TamagoChat"))
        await self.admin("/admin/api/deploy/token", {"token": "pas-un-token"}, status=400)
