"""Menu du clic droit et options."""
import tkinter as tk

from . import desktop
from .config import APP_VERSION, CHATTER_PRESETS, CRAZY_PRESETS, FLY_PRESETS, SERVER_URL, SIZES


def fmt_delay(secs):
    if secs <= 0:
        return "jamais"
    if secs < 60:
        return f"{secs:.0f} s"
    return f"{secs / 60:g} min".replace(".", ",")


class MenuMixin:
    def show_menu(self, e):
        name = self.data["name"]
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Caresser {name}", command=self.act_pet)
        m.add_command(label="Donner à manger", command=self.act_feed)
        m.add_command(label="Donner à boire", command=self.act_drink)
        m.add_command(label="Jouer avec la pelote", command=self.act_play)
        m.add_command(label="Le réveiller" if self.state == "sleep" else "Faire une sieste",
                      command=self.act_sleep)
        m.add_command(label="Le calmer !" if self.state == "crazy" else "Crise de folie !",
                      command=self.act_crazy)
        m.add_command(label="Lâcher des mouches", command=lambda: self.spawn_flies(manual=True))
        m.add_separator()
        m.add_command(label="Voir son état...", command=self.open_stats)
        m.add_command(label="Le renommer...", command=self.open_rename)
        m.add_command(label="Ses phrases...", command=self.open_phrases)
        if SERVER_URL and self.data["remote_messages"]:
            m.add_command(label="Envoyer un message...", command=self.open_reply)

        opts = tk.Menu(m, tearoff=0)
        self.v_walk = tk.BooleanVar(value=self.data["autowalk"])
        self.v_top = tk.BooleanVar(value=self.data["topmost"])
        self.v_start = tk.BooleanVar(value=desktop.startup_enabled())
        self.v_size = tk.StringVar(value=self.data["size"])
        opts.add_checkbutton(label="Se promène tout seul", variable=self.v_walk,
                             command=lambda: self.set_opt("autowalk", self.v_walk.get()))

        cur = self.data["chatter_s"]
        presets = [s for _, s in CHATTER_PRESETS]
        self.v_chat = tk.IntVar(value=cur if cur in presets else -1)
        chat_m = tk.Menu(opts, tearoff=0)
        for label, secs in CHATTER_PRESETS:
            chat_m.add_radiobutton(label=label, value=secs, variable=self.v_chat,
                                   command=lambda s=secs: self.set_chatter(s))
        chat_m.add_separator()
        custom = "Personnalisé..." if cur in presets else f"Personnalisé ({fmt_delay(cur)})..."
        chat_m.add_radiobutton(label=custom, value=-1, variable=self.v_chat,
                               command=self.open_chatter_custom)
        opts.add_cascade(label="Fréquence des phrases spontanées", menu=chat_m)

        self.v_crazy = tk.IntVar(value=self.data["crazy_min"])
        crazy_m = tk.Menu(opts, tearoff=0)
        for label, mins in CRAZY_PRESETS:
            crazy_m.add_radiobutton(label=label, value=mins, variable=self.v_crazy,
                                    command=lambda m_=mins: self.set_crazy(m_))
        crazy_m.add_separator()
        crazy_m.add_command(label="Crise de folie maintenant !", command=self.act_crazy)
        opts.add_cascade(label="Mode FOU", menu=crazy_m)

        self.v_flies = tk.IntVar(value=self.data["flies_min"])
        flies_m = tk.Menu(opts, tearoff=0)
        for label, mins in FLY_PRESETS:
            flies_m.add_radiobutton(label=label, value=mins, variable=self.v_flies,
                                    command=lambda m_=mins: self.set_flies(m_))
        flies_m.add_separator()
        flies_m.add_command(label="Lâcher des mouches maintenant",
                            command=lambda: self.spawn_flies(manual=True))
        opts.add_cascade(label="Mouches", menu=flies_m)
        opts.add_separator()
        if SERVER_URL:            # options inutiles sans serveur (voir local_config.example.py)
            self.v_remote = tk.BooleanVar(value=self.data["remote_messages"])
            self.v_update = tk.BooleanVar(value=self.data["auto_update"])
            self.v_rset = tk.BooleanVar(value=self.data["remote_settings"])
            opts.add_checkbutton(label="Recevoir des messages à distance", variable=self.v_remote,
                                 command=lambda: self.set_remote_opt("remote_messages",
                                                                     self.v_remote.get()))
            opts.add_checkbutton(label="Mises à jour automatiques", variable=self.v_update,
                                 command=lambda: self.set_remote_opt("auto_update",
                                                                     self.v_update.get()))
            opts.add_checkbutton(label="Autoriser les réglages à distance", variable=self.v_rset,
                                 command=lambda: self.set_remote_opt("remote_settings",
                                                                     self.v_rset.get()))
        opts.add_command(label=f"Version {APP_VERSION}", state="disabled")
        opts.add_separator()
        opts.add_checkbutton(label="Toujours au premier plan", variable=self.v_top,
                             command=self.toggle_topmost)
        opts.add_checkbutton(label=desktop.STARTUP_LABEL, variable=self.v_start,
                             command=lambda: desktop.set_startup(self.v_start.get()))
        sizes = tk.Menu(opts, tearoff=0)
        for label in SIZES:
            sizes.add_radiobutton(label=label, value=label, variable=self.v_size,
                                  command=self.change_size)
        opts.add_cascade(label="Taille", menu=sizes)
        m.add_cascade(label="Options", menu=opts)
        m.add_separator()
        m.add_command(label="Quitter", command=self.quit)
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

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
        self.data["topmost"] = self.v_top.get()
        self.root.attributes("-topmost", self.data["topmost"])
        self.save()

    def change_size(self):
        self.data["size"] = self.v_size.get()
        self.apply_size()
        self.save()
