"""Contenu du menu du clic droit et options (le dessin est dans popup_menu.py)."""
from . import desktop
from .popup_menu import SEPARATOR, Item, PopupMenu
from .reactions import REACTION_LABELS
from .config import APP_VERSION, CHATTER_PRESETS, CRAZY_PRESETS, FLY_PRESETS, SERVER_URL, SIZES


def fmt_delay(secs):
    if secs <= 0:
        return "jamais"
    if secs < 60:
        return f"{secs:.0f} s"
    return f"{secs / 60:g} min".replace(".", ",")


class MenuMixin:
    def show_menu(self, e):
        self.close_menu()
        self.menu_open = True             # pas de remise au premier plan par-dessus le menu
        self.menu = PopupMenu(self.root, self.menu_items(), self.dpi, on_close=self.menu_closed)
        self.menu.show(e.x_root, e.y_root)

    def close_menu(self):
        if self.menu:
            self.menu.close()

    def menu_closed(self):
        self.menu = None
        self.menu_open = False

    def menu_items(self):
        d = self.data
        items = [
            Item(f"Caresser {d['name']}", self.act_pet, icon="pet"),
            Item("Donner à manger", self.act_feed, icon="food"),
            Item("Donner à boire", self.act_drink, icon="water"),
            Item("Jouer avec la pelote", self.act_play, icon="yarn"),
            Item("Le réveiller", self.act_sleep, icon="wake") if self.state == "sleep"
            else Item("Faire une sieste", self.act_sleep, icon="sleep"),
            Item("Le calmer !" if self.state == "crazy" else "Crise de folie !", self.act_crazy,
                 icon="crazy"),
            Item("Lâcher des mouches", lambda: self.spawn_flies(manual=True), icon="flies"),
            Item("Réactions", icon="star", items=[
                Item(label, lambda k=kind: self.start_reaction(k))
                for kind, label in REACTION_LABELS.items()]),
            SEPARATOR,
            Item("Voir son état...", self.open_stats, icon="stats"),
            Item("Le renommer...", self.open_rename, icon="rename"),
            Item("Ses phrases...", self.open_phrases, icon="phrases"),
        ]
        if SERVER_URL and d["remote_messages"]:
            items.append(Item("Envoyer un message...", self.open_reply, icon="message"))
        items += [Item("Options", icon="options", items=self.option_items()), SEPARATOR,
                  Item("Quitter", self.quit, icon="quit")]
        return items

    def option_items(self):
        d = self.data
        cur = d["chatter_s"]
        presets = [s for _, s in CHATTER_PRESETS]
        custom = "Personnalisé..." if cur in presets else f"Personnalisé ({fmt_delay(cur)})..."
        chatter = [Item(label, lambda s=secs: self.set_chatter(s), radio=cur == secs)
                   for label, secs in CHATTER_PRESETS]
        chatter += [SEPARATOR, Item(custom, self.open_chatter_custom, radio=cur not in presets)]
        crazy = [Item(label, lambda m=mins: self.set_crazy(m), radio=d["crazy_min"] == mins)
                 for label, mins in CRAZY_PRESETS]
        crazy += [SEPARATOR, Item("Crise de folie maintenant !", self.act_crazy)]
        flies = [Item(label, lambda m=mins: self.set_flies(m), radio=d["flies_min"] == mins)
                 for label, mins in FLY_PRESETS]
        flies += [SEPARATOR, Item("Lâcher des mouches maintenant",
                                  lambda: self.spawn_flies(manual=True))]

        items = [
            Item("Se promène tout seul", lambda: self.set_opt("autowalk", not d["autowalk"]),
                 check=d["autowalk"]),
            Item("Fréquence des phrases spontanées", items=chatter),
            Item("Mode FOU", items=crazy),
            Item("Mouches", items=flies),
            SEPARATOR,
        ]
        if SERVER_URL:            # options inutiles sans serveur (voir local_config.example.py)
            for key, label in (("remote_messages", "Recevoir des messages à distance"),
                               ("auto_update", "Mises à jour automatiques"),
                               ("remote_settings", "Autoriser les réglages à distance")):
                items.append(Item(label, lambda k=key: self.set_remote_opt(k, not d[k]),
                                  check=d[key]))
        startup = desktop.startup_enabled()
        items += [
            Item(f"Version {APP_VERSION}", enabled=False),
            SEPARATOR,
            Item("Toujours au premier plan", self.toggle_topmost, check=d["topmost"]),
            Item(desktop.STARTUP_LABEL, lambda: desktop.set_startup(not startup), check=startup),
            Item("Taille", items=[Item(label, lambda s=label: self.change_size(s),
                                       radio=d["size"] == label) for label in SIZES]),
        ]
        return items

    def set_opt(self, key, value):
        self.data[key] = value
        self.save()

    def set_chatter(self, secs):
        self.data["chatter_s"] = int(secs)
        self.schedule_chatter()
        self.save()

    def set_flies(self, mins):
        self.data["flies_min"] = mins
        self.schedule_flies()
        self.save()

    def set_crazy(self, mins):
        self.data["crazy_min"] = mins
        self.schedule_crazy()
        self.save()

    def toggle_topmost(self):
        self.data["topmost"] = not self.data["topmost"]
        self.root.attributes("-topmost", self.data["topmost"])
        self.save()

    def change_size(self, size):
        self.data["size"] = size
        self.apply_size()
        self.save()
