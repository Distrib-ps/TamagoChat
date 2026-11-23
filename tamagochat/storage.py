"""Sauvegarde du chat et journal d'erreurs."""
import json
import os
import time
import traceback

from .config import DATA_DIR, DEFAULTS, LOG_FILE, SAVE_FILE, STATS
from .phrases import PHRASES


def log_error():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(time.strftime("[%Y-%m-%d %H:%M:%S]\n") + traceback.format_exc() + "\n")
    except Exception:
        pass


def load_save():
    data = json.loads(json.dumps(DEFAULTS))
    try:
        with open(SAVE_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        for k, v in saved.items():
            if k == "stats":
                data["stats"].update({s: float(v.get(s, 80)) for s in STATS})
            elif k == "phrases":
                if isinstance(v, dict):
                    data["phrases"] = {key: [str(p) for p in lst] for key, lst in v.items()
                                       if key in PHRASES and isinstance(lst, list)}
            elif k in data:
                data[k] = v
        if saved.get("silent") and "chatter_s" not in saved:  # ancien "mode silencieux"
            data["chatter_s"] = 0
    except FileNotFoundError:
        pass
    except Exception:
        log_error()
    return data
