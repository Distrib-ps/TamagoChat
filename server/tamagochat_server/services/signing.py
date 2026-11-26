"""Vérification des signatures Ed25519 des versions.

En production, ed25519.py (copie de tamagochat/ed25519.py) est à côté de server.py ;
dans le dépôt, on prend directement tamagochat/ed25519.py."""
import importlib.util
import os

from ..settings import SERVER_DIR

REPO_COPY = os.path.join(os.path.dirname(SERVER_DIR), "tamagochat", "ed25519.py")


def _load():
    try:
        import ed25519
        return ed25519
    except ImportError:
        pass
    try:
        import ed25519_min       # ancien nom
        return ed25519_min
    except ImportError:
        pass
    if os.path.isfile(REPO_COPY):
        spec = importlib.util.spec_from_file_location("minou_ed25519", REPO_COPY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    raise ImportError("ed25519.py introuvable : copiez tamagochat/ed25519.py à côté de server.py")


_module = None


def ed25519():
    global _module
    if _module is None:
        _module = _load()
    return _module


def verify(pubkey_hex, message, sig_hex):
    try:
        return ed25519().verify(bytes.fromhex(pubkey_hex), message, bytes.fromhex(sig_hex))
    except ValueError:
        return False
