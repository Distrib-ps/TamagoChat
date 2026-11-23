"""Tests rapides, sans écran : python -m unittest discover -s tests"""
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tamagochat import __version__, ed25519, sprites  # noqa: E402
from tamagochat.phrases import PHRASE_CATEGORIES, PHRASES  # noqa: E402
from tamagochat.render import pixel_runs  # noqa: E402


class TestVersion(unittest.TestCase):
    def test_format(self):
        # semantic-release remplace cette ligne : elle doit garder ce format
        self.assertRegex(__version__, r"^\d+\.\d+\.\d+$")
        src = open(os.path.join(os.path.dirname(ed25519.__file__), "__init__.py")).read()
        self.assertTrue(re.search(r'^__version__ = "[^"]*"', src, re.M))


class TestSignature(unittest.TestCase):
    def test_sign_verify(self):
        secret = bytes(range(32))
        pub = ed25519.public_key(secret)
        msg = b"minou-update|1.2.3|abc"
        sig = ed25519.sign(secret, msg)
        self.assertTrue(ed25519.verify(pub, msg, sig))
        # une signature Windows n'est pas valable pour Mac (et inversement)
        self.assertFalse(ed25519.verify(pub, b"minou-update-mac|1.2.3|abc", sig))


class TestSprites(unittest.TestCase):
    def test_runs_cover_opaque_pixels(self):
        rows = sprites.make_sit("open", "normal", "up")
        covered = set()
        for x0, y, x1, color in pixel_runs(rows):
            for x in range(x0, x1):
                self.assertEqual(sprites.PALETTE[rows[y][x]], color)
                covered.add((x, y))
        opaque = {(x, y) for y, row in enumerate(rows) for x, ch in enumerate(row)
                  if ch in sprites.PALETTE}
        self.assertEqual(covered, opaque)


class TestReactions(unittest.TestCase):
    def test_sprites(self):
        for rows in (sprites.make_yawn(), sprites.make_groom(0), sprites.make_groom(1)):
            self.assertEqual((len(rows[0]), len(rows)), (31, 24))
        for extra in range(0, 7):
            rows = sprites.make_stretch(extra, yawn=extra == 6)
            self.assertEqual(len(rows), 24 + extra)          # plus haut, même largeur
            self.assertEqual({len(r) for r in rows}, {31})
        self.assertEqual(sprites.make_stretch(0), sprites.make_sit("closed", "normal", "up"))

    def test_reactions_known_everywhere(self):
        from tamagochat.reactions import REACTION_LABELS, REACTIONS
        self.assertEqual(set(REACTION_LABELS), set(REACTIONS))
        for kind in REACTIONS + ("dizzy",):                  # chaque réaction a ses phrases
            self.assertTrue(PHRASES[kind])
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        server = open(os.path.join(root, "serveur", "server.py"), encoding="utf-8").read()
        admin = open(os.path.join(root, "serveur", "admin.html"), encoding="utf-8").read()
        for kind in REACTIONS:                               # action à distance acceptée et affichée
            self.assertIn(f'"{kind}"', server)
            self.assertIn(f'["{kind}"', admin)


class TestPhrases(unittest.TestCase):
    def test_every_category_has_phrases(self):
        self.assertEqual({k for k, _ in PHRASE_CATEGORIES}, set(PHRASES))


class TestSave(unittest.TestCase):
    def test_load_old_save(self):
        import tamagochat.storage as storage
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "save.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"name": "Félix", "silent": True, "stats": {"satiete": 12},
                           "phrases": {"idle": ["Coucou"], "inconnue": ["x"]}}, f)
            old = storage.SAVE_FILE
            storage.SAVE_FILE = path
            try:
                data = storage.load_save()
            finally:
                storage.SAVE_FILE = old
        self.assertEqual(data["name"], "Félix")
        self.assertEqual(data["chatter_s"], 0)          # ancien « mode silencieux »
        self.assertEqual(data["stats"]["satiete"], 12.0)
        self.assertEqual(data["stats"]["energie"], 80)
        self.assertEqual(data["phrases"], {"idle": ["Coucou"]})


if __name__ == "__main__":
    unittest.main()
