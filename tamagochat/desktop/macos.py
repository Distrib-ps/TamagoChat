"""macOS : écrans (NSScreen via ctypes), instance unique, ouverture de session et mise à jour du .app.

Aucune dépendance : AppKit est appelé via le runtime Objective-C.
"""
import ctypes
import ctypes.util
import fcntl
import glob
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import time

from ..config import DATA_DIR, FROZEN, LAUNCHER

NAME = "mac"
UPDATE_TAG = "minou-update-mac"    # distinct de Windows : un .exe n'est jamais accepté ici
BG = "systemTransparent"           # pas de couleur transparente sur Mac : fenêtres -transparent
MENU_BUTTONS = ("<Button-3>", "<Button-2>", "<Control-Button-1>")   # Button-2 = clic droit en Tk 8.6
SEND_KEYS = ("<Control-Return>", "<Command-Return>")
DELETE_KEYS = ("<Delete>", "<BackSpace>")
STARTUP_LABEL = "Lancer à l'ouverture de session"
LAUNCH_AGENT = os.path.expanduser("~/Library/LaunchAgents/fr.tamagochat.plist")
# TamagoChat.app/Contents/MacOS/TamagoChat -> TamagoChat.app
_bundle = os.path.abspath(os.path.join(os.path.dirname(sys.executable), "..", ".."))
APP_BUNDLE = _bundle if FROZEN and _bundle.endswith(".app") else None


# ------------------------------------------------------------------ fenêtres
def font(size, *style):
    """Tk sur Mac compte en points à 72 dpi : un peu plus grand que sous Windows."""
    return ("Helvetica Neue", size + 3, *style)


def dpi_scale(root):
    return 1.0                     # les coordonnées sont déjà en points


def setup_root(root, on_quit):
    root.createcommand("::tk::mac::Quit", on_quit)   # Cmd+Q, fermeture de session


def make_transparent(win):
    win.configure(bg=BG)
    win.attributes("-transparent", True)


def make_tool_window(widget):
    pass                           # l'app n'a pas d'icône dans le Dock (LSUIElement)


def keep_on_top(widgets):
    """Réapplique le niveau « premier plan » (Tk) aux fenêtres du chat."""
    for w in widgets:
        try:
            w.attributes("-topmost", True)
        except Exception:
            pass


def mouse_buttons_down():
    try:
        o = _init_objc()
        return bool(o["send_ulong"](o["cls"]("NSEvent"), o["sel"]("pressedMouseButtons")))
    except Exception:
        return False


def set_dpi_aware():
    pass


def unsupported_reason():
    import tkinter
    if tkinter.TkVersion >= 9:
        return (f"Ce Python utilise Tk {tkinter.TkVersion}, qui n'affiche pas les fenêtres "
                "transparentes sur Mac.\n\nInstalle Python depuis python.org (Tk 8.6) "
                "ou télécharge l'application TamagoChat.")
    return None


# ------------------------------------------------------------------ écrans (NSScreen)
class _Rect(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double),
                ("w", ctypes.c_double), ("h", ctypes.c_double)]


_objc = {}


def _init_objc():
    if _objc:
        return _objc
    lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library("objc"))
    ctypes.cdll.LoadLibrary(ctypes.util.find_library("AppKit"))
    lib.objc_getClass.restype = ctypes.c_void_p
    lib.objc_getClass.argtypes = [ctypes.c_char_p]
    lib.sel_registerName.restype = ctypes.c_void_p
    lib.sel_registerName.argtypes = [ctypes.c_char_p]
    vp, ul = ctypes.c_void_p, ctypes.c_ulong
    # une signature par usage d'objc_msgSend ; sur Intel, une structure de 32 octets
    # est renvoyée via objc_msgSend_stret
    stret = "objc_msgSend" if platform.machine() == "arm64" else "objc_msgSend_stret"
    _objc.update(
        cls=lambda name: lib.objc_getClass(name.encode()),
        sel=lambda name: lib.sel_registerName(name.encode()),
        send_id=ctypes.CFUNCTYPE(vp, vp, vp)(("objc_msgSend", lib)),
        send_ulong=ctypes.CFUNCTYPE(ul, vp, vp)(("objc_msgSend", lib)),
        send_idx=ctypes.CFUNCTYPE(vp, vp, vp, ul)(("objc_msgSend", lib)),
        send_rect=ctypes.CFUNCTYPE(_Rect, vp, vp)((stret, lib)))
    return _objc


def _query_monitors():
    o = _init_objc()
    screens = o["send_id"](o["cls"]("NSScreen"), o["sel"]("screens"))
    n = o["send_ulong"](screens, o["sel"]("count")) if screens else 0
    mons, main_h = [], None
    for i in range(n):
        s = o["send_idx"](screens, o["sel"]("objectAtIndex:"), i)
        f = o["send_rect"](s, o["sel"]("frame"))
        v = o["send_rect"](s, o["sel"]("visibleFrame"))
        if main_h is None:     # le premier écran (barre des menus) sert d'origine aux coordonnées
            main_h = f.h

        def tk_rect(r):        # AppKit : origine en bas à gauche, y vers le haut ; Tk : l'inverse
            return (round(r.x), round(main_h - r.y - r.h), round(r.x + r.w), round(main_h - r.y))
        mons.append({"mon": tk_rect(f), "work": tk_rect(v)})
    return mons


_cache = {"t": 0.0, "mons": []}


def list_monitors(max_age=0.0):
    """Tous les écrans : {"mon": rect complet, "work": rect sans la barre des menus ni le Dock}."""
    if max_age and time.time() - _cache["t"] < max_age:
        return _cache["mons"]
    try:
        mons = _query_monitors()
    except Exception:
        mons = []
    _cache.update(t=time.time(), mons=mons)
    return mons


def work_area_at(x, y):
    mons = list_monitors(max_age=1.0)     # appelé de nombreuses fois par image : petit cache
    if not mons:
        return None

    def dist(m):
        L, T, R, B = m["mon"]
        return max(L - x, 0, x - R + 1) ** 2 + max(T - y, 0, y - B + 1) ** 2
    return min(mons, key=dist)["work"]


# ------------------------------------------------------------------ instance unique
_LOCK = None


def already_running():
    global _LOCK
    os.makedirs(DATA_DIR, exist_ok=True)
    _LOCK = open(os.path.join(DATA_DIR, "instance.lock"), "w")
    try:
        fcntl.flock(_LOCK, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return True
    return False


# ------------------------------------------------------------------ ouverture de session
def startup_enabled():
    return os.path.exists(LAUNCH_AGENT)


def set_startup(enable):
    if enable:
        if APP_BUNDLE:
            args = ["/usr/bin/open", "-a", APP_BUNDLE]
        elif FROZEN:
            args = [sys.executable]
        else:
            args = [sys.executable, LAUNCHER]
        os.makedirs(os.path.dirname(LAUNCH_AGENT), exist_ok=True)
        with open(LAUNCH_AGENT, "wb") as f:
            plistlib.dump({"Label": "fr.tamagochat", "ProgramArguments": args,
                           "RunAtLoad": True, "ProcessType": "Interactive"}, f)
    elif os.path.exists(LAUNCH_AGENT):
        os.remove(LAUNCH_AGENT)


def migrate_startup():
    pass


# ------------------------------------------------------------------ mises à jour
def can_self_update():
    return APP_BUNDLE is not None


def update_download_path():
    return os.path.join(DATA_DIR, "update.zip")


def _staging():
    return os.path.join(os.path.dirname(APP_BUNDLE), ".TamagoChat-update")


def prepare_update(zip_path):
    """Décompresse le .zip (déjà vérifié) à côté de l'app ; renvoie le chemin du nouveau .app.

    ditto conserve les liens symboliques et les droits d'exécution, contrairement à zipfile.
    """
    staging = _staging()
    shutil.rmtree(staging, ignore_errors=True)
    subprocess.run(["/usr/bin/ditto", "-x", "-k", zip_path, staging], check=True)
    os.remove(zip_path)
    apps = glob.glob(os.path.join(glob.escape(staging), "*.app"))
    if not apps:
        raise ValueError("pas d'application dans la mise à jour")
    subprocess.run(["/usr/bin/xattr", "-dr", "com.apple.quarantine", apps[0]], check=False)
    return apps[0]


def install_update(new_app):
    """Remplace l'app par la nouvelle version (macOS autorise à renommer une app lancée)."""
    old = f"{APP_BUNDLE}.{int(time.time())}.old"
    os.rename(APP_BUNDLE, old)
    try:
        os.rename(new_app, APP_BUNDLE)
    except Exception:
        os.rename(old, APP_BUNDLE)     # on remet l'ancienne
        raise


def restart():
    global _LOCK
    if _LOCK:                          # laisse la nouvelle version démarrer
        _LOCK.close()
        _LOCK = None
    subprocess.Popen(["/usr/bin/open", "-n", APP_BUNDLE], close_fds=True)


def cleanup_update_files():
    if not APP_BUNDLE:
        return
    for d in glob.glob(glob.escape(APP_BUNDLE) + ".*.old") + [_staging()]:
        shutil.rmtree(d, ignore_errors=True)
    try:
        os.remove(update_download_path())
    except OSError:
        pass
