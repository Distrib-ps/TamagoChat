import json

from support import ServerTestCase


class CatsApiTest(ServerTestCase):
    async def test_sync_registers_cat_and_checks_secret(self):
        cat = self.new_cat()
        r = await self.sync(cat, name="Minou", version="1.3.0", stats={"bonheur": 150, "x": 3})
        self.assertEqual(r, {"messages": [], "update": None})
        row = self.services.db.execute("SELECT * FROM cats").fetchone()
        self.assertEqual((row["name"], row["version"]), ("Minou", "1.3.0"))
        self.assertEqual(json.loads(row["stats"]), {"bonheur": 100.0})
        bad = await self.client.post("/api/sync", json={**cat, "secret": "0" * 32, "wait": False})
        self.assertEqual(bad.status, 403)
        invalid = await self.client.post("/api/sync", json={"cat_id": "x", "secret": "y"})
        self.assertEqual(invalid.status, 400)
        not_json = await self.client.post("/api/sync", data="pas du json")
        self.assertEqual(not_json.status, 400)

    async def test_message_delivery(self):
        cat = self.new_cat()
        await self.sync(cat, name="Minou")
        cid = cat["cat_id"]
        await self.login()
        r = await self.admin("/admin/api/send", {"cat": cid, "kind": "say", "text": " Coucou ", "from": "Théo", "secs": 30})
        self.assertEqual(r, {"ok": True, "sent": 1})
        msgs = (await self.sync(cat))["messages"]
        self.assertEqual(len(msgs), 1)
        self.assertEqual((msgs[0]["kind"], msgs[0]["text"], msgs[0]["from"], msgs[0]["secs"]),
                         ("say", "Coucou", "Théo", 30))
        feed = (await self.admin(f"/admin/api/feed?cat={cid}"))["items"]
        self.assertTrue(feed[0]["fetched"] and not feed[0]["delivered"])
        await self.sync(cat, ack=[msgs[0]["id"]])
        self.assertEqual((await self.sync(cat))["messages"], [])
        feed = (await self.admin("/admin/api/feed?cat=*"))["items"]
        self.assertTrue(feed[0]["delivered"])

    async def test_long_polling_wakes_up_on_message(self):
        cat = self.new_cat()
        await self.sync(cat)
        await self.login()
        waiting = self.loop.create_task(self.client.post("/api/sync", json={**cat, "wait": True}))
        await self.admin("/admin/api/send", {"cat": "*", "kind": "action", "action": "meow"})
        r = await waiting
        self.assertEqual([m["action"] for m in (await r.json())["messages"]], ["meow"])

    async def test_reply_settings_phrases_and_state(self):
        cat = self.new_cat()
        phrases = {"cats": [["idle", "Au repos"]], "list": {"idle": ["Miaou"], "autre": ["x"]}, "custom": ["idle"]}
        await self.sync(cat, name="Minou", allow_settings=True, phrases=phrases,
                        settings={"autowalk": True, "chatter_s": 5, "size": "Grand", "name": "ignoré"})
        r = await self.client.post("/api/reply", json={**cat, "text": "Salut !"})
        self.assertEqual(r.status, 200)
        await self.login()
        state = await self.admin("/admin/api/state")
        c = state["cats"][0]
        self.assertEqual(c["settings"], {"autowalk": True, "size": "Grand"})
        self.assertEqual((c["unread"], c["online"], c["allow_settings"]), (1, True, True))
        self.assertEqual(set(state), {"cats", "release", "release_mac", "now"})
        ph = await self.admin(f"/admin/api/phrases?cat={cat['cat_id']}")
        self.assertEqual(ph["phrases"], {"cats": [["idle", "Au repos"]], "list": {"idle": ["Miaou"]}, "custom": ["idle"]})
        feed = (await self.admin(f"/admin/api/feed?cat={cat['cat_id']}"))["items"]
        self.assertEqual([(i["type"], i["text"]) for i in feed], [("reply", "Salut !")])
        self.assertEqual((await self.admin("/admin/api/state"))["cats"][0]["unread"], 0)
