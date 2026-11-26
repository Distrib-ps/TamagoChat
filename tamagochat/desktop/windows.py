"""Windows : écrans (Win32), instance unique, démarrage automatique et mise à jour de l'exe."""
import ctypes
import glob
import os
import subprocess
import sys
import threading
import time
from ctypes import wintypes

from ..config import FROZEN, ICON_FILE, LAUNCHER, ROOT_DIR
from ..storage import log_error

NAME = "win"
UPDATE_TAG = "minou-update"        # message signé des mises à jour : minou-update|version|sha256
KEY = "#ff00ff"                    # couleur rendue transparente par Windows
BG = KEY
MENU_BUTTONS = ("<Button-3>",)
SEND_KEYS = ("<Control-Return>",)
DELETE_KEYS = ("<Delete>",)
STARTUP_LABEL = "Lancer au démarrage de Windows"
STARTUP_LNK = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup", "TamagoChat.lnk")
OLD_STARTUP_LNK = os.path.join(os.path.dirname(STARTUP_LNK), "Minou.lnk")   # avant le renommage

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT),
                ("rcWork", wintypes.RECT), ("dwFlags", wintypes.DWORD)]


user32.MonitorFromPoint.argtypes = [wintypes.POINT, wintypes.DWORD]
user32.MonitorFromPoint.restype = wintypes.HMONITOR
user32.GetMonitorInfoW.argtypes = [wintypes.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetMonitorInfoW.restype = wintypes.BOOL
kernel32.CreateMutexW.restype = wintypes.HANDLE
MONITORENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HMONITOR, wintypes.HDC,
                                     ctypes.POINTER(wintypes.RECT), wintypes.LPARAM)
user32.EnumDisplayMonitors.argtypes = [wintypes.HDC, ctypes.c_void_p, MONITORENUMPROC,
                                       wintypes.LPARAM]
_MUTEX = None


# ------------------------------------------------------------------ fenêtres
def font(size, *style):
    return ("Segoe UI", size, *style)


def dpi_scale(root):
    return root.winfo_fpixels("1i") / 96.0


def setup_root(root, on_quit):
    pass


def make_transparent(win):
    """Fond de fenêtre invisible (seuls le chat, la bulle ou la mouche apparaissent)."""
    win.configure(bg=KEY)
    win.attributes("-transparentcolor", KEY)


def make_tool_window(widget):
    """Pas d'icône dans Alt+Tab, et la fenêtre ne vole pas le focus."""
    try:
        widget.update_idletasks()
        hwnd = user32.GetParent(widget.winfo_id())
        GWL_EXSTYLE = -20
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | 0x80 | 0x08000000)
    except Exception:
        pass


HWND_TOPMOST = -1
SWP_KEEP_ON_TOP = 0x0001 | 0x0002 | 0x0010 | 0x0200   # NOSIZE | NOMOVE | NOACTIVATE | NOOWNERZORDER
user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wintypes.UINT]
user32.SetWindowPos.restype = wintypes.BOOL


def keep_on_top(widgets):
    """Remet les fenêtres tout en haut des fenêtres « toujours au premier plan », sans prendre le
    focus : une autre appli de ce type (vidéo incrustée, appel, Gestionnaire des tâches...) ouverte
    après coup passerait sinon devant le chat et sa bulle, pour de bon."""
    for w in widgets:
        try:
            # D'abord appliquer les déplacements que Tk n'a pas encore faits : sinon Windows répond
            # avec l'ancienne position, que Tk adopte en annulant le déplacement (la bulle d'un
            # message pouvait ainsi rester hors de l'écran).
            w.update_idletasks()
            hwnd = user32.GetParent(w.winfo_id())
            if hwnd:
                user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_KEEP_ON_TOP)
        except Exception:
            pass


user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short


def mouse_buttons_down():
    return any(user32.GetAsyncKeyState(vk) & 0x8000 for vk in (0x01, 0x02, 0x04))


def set_dpi_aware():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def unsupported_reason():
    return None


# ------------------------------------------------------------------ écrans
def list_monitors():
    """Tous les écrans : {"mon": rect complet, "work": rect sans la barre des tâches}."""
    mons = []

    def cb(hmon, hdc, rect, lp):
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            m, w = mi.rcMonitor, mi.rcWork
            mons.append({"mon": (m.left, m.top, m.right, m.bottom),
                         "work": (w.left, w.top, w.right, w.bottom)})
        return True

    try:
        user32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    except Exception:
        log_error()
    return mons


def work_area_at(x, y):
    try:
        hmon = user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(MONITORINFO)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            r = mi.rcWork
            return r.left, r.top, r.right, r.bottom
    except Exception:
        pass
    return None


# ------------------------------------------------------------------ instance unique
def already_running():
    global _MUTEX
    _MUTEX = kernel32.CreateMutexW(None, False, "Local\\ChatTamagotchiMinou")
    return ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS


# ------------------------------------------------------------------ démarrage de Windows
def pythonw_path():
    cand = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return cand if os.path.exists(cand) else sys.executable


def startup_enabled():
    return os.path.exists(STARTUP_LNK)


def set_startup(enable):
    if enable:
        def q(s):
            return s.replace("'", "''")
        if FROZEN:
            target, args = sys.executable, ""
            workdir, icon = os.path.dirname(sys.executable), sys.executable
        else:
            target = pythonw_path()
            args = '"' + LAUNCHER + '"'
            workdir, icon = ROOT_DIR, ICON_FILE
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{q(STARTUP_LNK)}');"
              f"$s.TargetPath='{q(target)}';"
              f"$s.Arguments='{q(args)}';"
              f"$s.WorkingDirectory='{q(workdir)}';"
              f"$s.IconLocation='{q(icon)}';$s.Save()")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       creationflags=0x08000000, check=False)
    elif os.path.exists(STARTUP_LNK):
        os.remove(STARTUP_LNK)


def migrate_startup():
    """Remplace le raccourci de démarrage de l'ancien nom (Minou.lnk)."""
    if not os.path.exists(OLD_STARTUP_LNK):
        return

    def migrate():
        try:
            os.remove(OLD_STARTUP_LNK)
            set_startup(True)
        except Exception:
            log_error()
    threading.Thread(target=migrate, daemon=True).start()


# ------------------------------------------------------------------ mises à jour
def can_self_update():
    return FROZEN


def update_download_path():
    return sys.executable + ".update"


def prepare_update(path):
    return path


def install_update(path):
    """Remplace l'exe par la nouvelle version (déjà vérifiée)."""
    exe = sys.executable
    old = exe + f".{int(time.time())}.old"
    os.replace(exe, old)          # Windows autorise à renommer un exe en cours d'exécution
    try:
        os.replace(path, exe)
    except Exception:
        os.replace(old, exe)      # on remet l'ancien
        raise


def restart():
    exe = sys.executable
    env = {k: v for k, v in os.environ.items() if not k.startswith(("_PYI", "_MEI"))}
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    kernel32.CloseHandle(_MUTEX)  # laisse la nouvelle version démarrer
    subprocess.Popen([exe], cwd=os.path.dirname(exe), env=env, close_fds=True,
                     creationflags=0x00000008 | 0x00000200)  # détaché


def cleanup_update_files():
    if not FROZEN:
        return
    for f in glob.glob(glob.escape(sys.executable) + ".*.old") + [sys.executable + ".update"]:
        try:
            os.remove(f)
        except OSError:
            pass
