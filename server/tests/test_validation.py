import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagochat_server.errors import BadRequest                                 # noqa: E402
from tamagochat_server.validation import (clean_message, clean_phrases,           # noqa: E402
                                          clean_settings, clean_stats, version_tuple)


class ValidationTest(unittest.TestCase):
    def test_settings(self):
        raw = {"name": " Félix ", "autowalk": 1, "topmost": False, "chatter_s": 10,
               "crazy_min": 3, "flies_min": 2000, "size": "Grand", "other": True}
        self.assertEqual(clean_settings(raw, with_name=True),
                         {"name": "Félix", "topmost": False, "crazy_min": 3, "size": "Grand"})
        self.assertNotIn("name", clean_settings(raw, with_name=False))
        self.assertEqual(clean_settings({"chatter_s": 0}, False), {"chatter_s": 0})
        self.assertEqual(clean_settings("x", False), {})

    def test_stats(self):
        self.assertEqual(clean_stats({"bonheur": 120, "energie": -3, "satiete": True, "x": 5}),
                         {"bonheur": 100.0, "energie": 0.0})

    def test_phrases(self):
        data = json.loads(clean_phrases({"cats": [["idle", "Repos"], "x"],
                                         "list": {"idle": ["a" * 300], "other": ["b"]},
                                         "custom": ["idle", "other"]}))
        self.assertEqual(data["cats"], [["idle", "Repos"]])
        self.assertEqual(len(data["list"]["idle"][0]), 200)
        self.assertEqual(data["custom"], ["idle"])
        self.assertIsNone(clean_phrases({"cats": "x"}))

    def test_message(self):
        self.assertEqual(clean_message({"kind": "say", "text": " Hi ", "secs": 2}),
                         ("say", {"text": "Hi", "from": ""}))
        self.assertEqual(clean_message({"kind": "phrases", "key": "idle", "list": ["a", " "]}),
                         ("phrases", {"key": "idle", "list": ["a"]}))
        for bad in ({"kind": "say", "text": ""}, {"kind": "action", "action": "boom"},
                    {"kind": "stats", "stats": {"bonheur": "100"}}, {"kind": "?"}):
            with self.assertRaises(BadRequest):
                clean_message(bad)

    def test_version_order(self):
        self.assertLess(version_tuple("1.9.0"), version_tuple("1.10.0"))


if __name__ == "__main__":
    unittest.main()
