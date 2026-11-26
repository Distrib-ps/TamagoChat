"""Relu à chaque usage : une commande (set-password, setup-deploy) s'applique sans redémarrer."""
import json
import os


class ConfigStore:
    def __init__(self, path):
        self.path = path

    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save(self, cfg):
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def update(self, **values):
        cfg = self.load()
        cfg.update(values)
        self.save(cfg)

    def get(self, key, default=None):
        return self.load().get(key, default)
