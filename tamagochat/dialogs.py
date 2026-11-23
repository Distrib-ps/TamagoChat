"""Fenêtres annexes : état, renommer, phrases, fréquence des phrases, message à envoyer."""
import tkinter as tk
from tkinter import messagebox, ttk

from . import desktop
from .config import ICON_FILE, STATS, STAT_COLORS, STAT_LABELS
from .phrases import PHRASE_CATEGORIES


class DialogsMixin:
    def open_stats(self):
        if self.stats_win and self.stats_win.winfo_exists():
            self.stats_win.lift()
            return
        w = self.stats_win = tk.Toplevel(self.root)
        w.title(f"{self.data['name']} : état")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        w.configure(bg="#fff8ef")
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        d = self.dpi
        width, height = int(300 * d), int(205 * d)
        c = tk.Canvas(w, width=width, height=height, bg="#fff8ef", highlightthickness=0)
        c.pack(padx=int(10 * d), pady=int(10 * d))
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - width // 2)}+{max(0, y - height - int(60 * d))}")

        def refresh():
            if not w.winfo_exists():
                return
            c.delete("all")
            c.create_text(0, 0, anchor="nw", text=self.data["name"],
                          font=desktop.font(14, "bold"), fill="#3b2a22")
            for i, k in enumerate(STATS):
                top = int((38 + i * 34) * d)
                v = self.stats[k]
                c.create_text(0, top, anchor="nw", text=STAT_LABELS[k],
                              font=desktop.font(10), fill="#3b2a22")
                bx, bw, bh = int(100 * d), int(160 * d), int(16 * d)
                c.create_rectangle(bx, top + 2, bx + bw, top + 2 + bh,
                                   fill="#eee2d4", outline="#3b2a22", width=2)
                if v > 0.5:
                    c.create_rectangle(bx + 2, top + 4, bx + 2 + (bw - 4) * v / 100,
                                       top + bh, fill=STAT_COLORS[k], outline="")
                c.create_text(bx + bw + int(6 * d), top, anchor="nw", text=f"{v:.0f}",
                              font=desktop.font(10), fill="#3b2a22")
            avg = sum(self.stats.values()) / 4
            mood = ("Aux anges" if avg > 85 else "Content" if avg > 65 else "Ça va"
                    if avg > 45 else "Grognon" if avg > 25 else "Malheureux")
            if self.state == "sleep":
                mood += " (il dort)"
            c.create_text(0, int(178 * d), anchor="nw", text=f"Humeur : {mood}",
                          font=desktop.font(10, "italic"), fill="#3b2a22")
            w.after(500, refresh)

        refresh()

    def open_rename(self):
        w = tk.Toplevel(self.root)
        w.title("Renommer")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        tk.Label(w, text="Nouveau nom :", font=desktop.font(10)).pack(padx=12, pady=(12, 4))
        v = tk.StringVar(value=self.data["name"])
        ent = tk.Entry(w, textvariable=v, font=desktop.font(11), width=22)
        ent.pack(padx=12)
        ent.select_range(0, "end")

        def ok(_=None):
            name = v.get().strip()[:24]
            if name:
                self.data["name"] = name
                self.save()
                self.say("renamed")
            w.destroy()

        tk.Button(w, text="OK", width=10, command=ok).pack(pady=10)
        ent.bind("<Return>", ok)
        ent.bind("<Escape>", lambda _: w.destroy())
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 100)}+{max(0, y - 150)}")
        w.after(50, lambda: (w.focus_force(), ent.focus_set()))

    def open_phrases(self):
        if self.phrases_win and self.phrases_win.winfo_exists():
            self.phrases_win.lift()
            return
        w = self.phrases_win = tk.Toplevel(self.root)
        w.title(f"Les phrases de {self.data['name']}")
        w.attributes("-topmost", True)
        w.minsize(480, 380)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        ui_font = desktop.font(10)
        frm = ttk.Frame(w, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        frm.rowconfigure(1, weight=1)

        labels = [label for _, label in PHRASE_CATEGORIES]
        key_of = {label: key for key, label in PHRASE_CATEGORIES}
        v_cat = tk.StringVar(value=labels[0])
        ttk.Label(frm, text="Situation :", font=ui_font).grid(row=0, column=0, sticky="w")
        combo = ttk.Combobox(frm, values=labels, textvariable=v_cat, state="readonly",
                             font=ui_font, height=20)
        combo.grid(row=0, column=1, columnspan=4, sticky="we", pady=(0, 8), padx=(6, 0))

        lb = tk.Listbox(frm, font=ui_font, activestyle="none", exportselection=False, height=12)
        sb = ttk.Scrollbar(frm, orient="vertical", command=lb.yview)
        lb.config(yscrollcommand=sb.set)
        lb.grid(row=1, column=0, columnspan=4, sticky="nsew")
        sb.grid(row=1, column=4, sticky="ns")

        v_text = tk.StringVar()
        ent = ttk.Entry(frm, textvariable=v_text, font=ui_font)
        ent.grid(row=2, column=0, columnspan=5, sticky="we", pady=8)

        status = ttk.Label(frm, font=desktop.font(9), foreground="#6b5a4e")

        def key():
            return key_of[v_cat.get()]

        def current():
            return list(self.phrases(key()))

        def store(lst, select=None):
            self.data["phrases"][key()] = lst
            self.phrases_rev += 1
            self.save()
            refresh(select)

        def refresh(select=None):
            lst = current()
            lb.delete(0, "end")
            for p in lst:
                lb.insert("end", p)
            if select is not None and lst:
                select = max(0, min(select, len(lst) - 1))
                lb.selection_set(select)
                lb.see(select)
            perso = key() in self.data["phrases"]
            n = len(lst)
            txt = f"{n} phrase{'s' if n > 1 else ''}"
            txt += " (personnalisées)" if perso else " (celles d'origine)"
            if n == 0:
                txt += " : il ne dira rien dans cette situation"
            status.config(text=txt)

        def selected():
            sel = lb.curselection()
            return sel[0] if sel else None

        def on_select(_=None):
            i = selected()
            if i is not None:
                v_text.set(lb.get(i))

        def add(_=None):
            text = v_text.get().strip()[:200]
            if not text:
                return
            lst = current() + [text]
            store(lst, len(lst) - 1)
            v_text.set("")
            ent.focus_set()

        def modify():
            i, text = selected(), v_text.get().strip()[:200]
            if i is None or not text:
                return
            lst = current()
            lst[i] = text
            store(lst, i)

        def delete():
            i = selected()
            if i is None:
                return
            lst = current()
            del lst[i]
            store(lst, i)
            v_text.set("")

        def test():
            i = selected()
            text = v_text.get().strip() or (lb.get(i) if i is not None else "")
            if text:
                if self.state == "sleep":
                    self.set_state("idle")
                self.say_text(text)

        def reset():
            if key() not in self.data["phrases"]:
                return
            if messagebox.askyesno("Rétablir", "Remettre les phrases d'origine pour cette "
                                   "situation ?\nTes phrases perso de cette situation seront "
                                   "effacées.", parent=w):
                self.data["phrases"].pop(key(), None)
                self.phrases_rev += 1
                self.save()
                refresh()

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=5, sticky="we")
        ttk.Button(btns, text="Ajouter", command=add).pack(side="left")
        ttk.Button(btns, text="Modifier", command=modify).pack(side="left", padx=4)
        ttk.Button(btns, text="Supprimer", command=delete).pack(side="left")
        ttk.Button(btns, text="Lui faire dire", command=test).pack(side="left", padx=4)
        ttk.Button(btns, text="Rétablir l'origine", command=reset).pack(side="right")

        status.grid(row=4, column=0, columnspan=5, sticky="w", pady=(8, 0))
        ttk.Label(frm, text="Astuce : écris {name} pour qu'il dise son propre nom. "
                  "Sélectionne une phrase pour la modifier.",
                  font=desktop.font(9), foreground="#6b5a4e").grid(
            row=5, column=0, columnspan=5, sticky="w")

        combo.bind("<<ComboboxSelected>>", lambda _: (v_text.set(""), refresh()))
        lb.bind("<<ListboxSelect>>", on_select)
        for seq in desktop.DELETE_KEYS:
            lb.bind(seq, lambda _: delete())
        ent.bind("<Return>", add)

        refresh()
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 260)}+{max(0, y - 480)}")
        w.after(50, lambda: (w.focus_force(), ent.focus_set()))

    def open_chatter_custom(self):
        w = tk.Toplevel(self.root)
        w.title("Fréquence des phrases")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        ui_font = desktop.font(10)
        frm = ttk.Frame(w, padding=14)
        frm.pack()
        ttk.Label(frm, text=f"{self.data['name']} dit une phrase spontanée environ toutes les :",
                  font=ui_font).grid(row=0, column=0, columnspan=2, sticky="w")
        cur = self.data["chatter_s"] or 180
        v = tk.StringVar(value=f"{cur / 60:g}")
        spin = ttk.Spinbox(frm, from_=0.5, to=240, increment=0.5, textvariable=v,
                           width=7, font=ui_font)
        spin.grid(row=1, column=0, sticky="w", pady=8)
        ttk.Label(frm, text="minutes", font=ui_font).grid(row=1, column=1, sticky="w", padx=6)
        ttk.Label(frm, text="Les réponses à tes actions (caresses, repas...) ne sont pas concernées.",
                  font=desktop.font(9), foreground="#6b5a4e").grid(row=2, column=0, columnspan=2,
                                                                   sticky="w")

        def ok(_=None):
            try:
                mins = float(v.get().replace(",", "."))
            except ValueError:
                return
            self.set_chatter(max(15, min(mins * 60, 24 * 3600)))
            w.destroy()

        ttk.Button(frm, text="OK", command=ok).grid(row=3, column=0, columnspan=2, pady=(10, 0))
        spin.bind("<Return>", ok)
        w.bind("<Escape>", lambda _: w.destroy())
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 200)}+{max(0, y - 200)}")
        w.after(50, lambda: (w.focus_force(), spin.focus_set(), spin.selection_range(0, "end")))

    def open_reply(self):
        if self.reply_win and self.reply_win.winfo_exists():
            self.reply_win.lift()
            return
        w = self.reply_win = tk.Toplevel(self.root)
        w.title("Envoyer un message")
        w.resizable(False, False)
        w.attributes("-topmost", True)
        try:
            w.iconbitmap(ICON_FILE)
        except Exception:
            pass
        frm = ttk.Frame(w, padding=14)
        frm.pack()
        to = f"à {self.last_sender}" if self.last_sender else "à la personne qui t'envoie des messages"
        ttk.Label(frm, text=f"Ton message sera envoyé {to} :",
                  font=desktop.font(10)).pack(anchor="w")
        txt = tk.Text(frm, width=46, height=4, font=desktop.font(10), wrap="word")
        txt.pack(pady=8)

        def send(_=None):
            text = txt.get("1.0", "end").strip()[:500]
            if text:
                self.remote.send_reply(text)
                w.destroy()
            return "break"

        ttk.Button(frm, text="Envoyer", command=send).pack(anchor="e")
        for seq in desktop.SEND_KEYS:
            txt.bind(seq, send)
        w.bind("<Escape>", lambda _: w.destroy())
        x, y = self.root.winfo_pointerxy()
        w.geometry(f"+{max(0, x - 220)}+{max(0, y - 220)}")
        w.after(50, lambda: (w.focus_force(), txt.focus_set()))
