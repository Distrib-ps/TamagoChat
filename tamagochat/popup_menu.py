"""Menu contextuel dessiné, au style de theme.py (le menu natif de Tk ne se stylise pas sur Mac).

Chaque niveau (menu, sous-menu) est une petite fenêtre transparente, comme la bulle.
"""
import tkinter as tk
import tkinter.font as tkfont
from dataclasses import dataclass
from typing import Callable, Optional

from . import desktop
from . import theme as th
from .bubble import round_rect
from .icons import RUNS, SIZE as ICON_SIZE
from .render import draw_runs

SEPARATOR = None


@dataclass
class Item:
    label: str
    command: Optional[Callable] = None
    icon: Optional[str] = None
    check: Optional[bool] = None      # case à cocher : cochée ou non
    radio: Optional[bool] = None      # un choix parmi plusieurs : choisi ou non
    enabled: bool = True
    items: Optional[list] = None      # sous-menu


class PopupMenu:
    def __init__(self, root, items, scale=1.0, on_close=None):
        self.root, self.items, self.on_close = root, items, on_close
        self.scale = scale
        self.font = tkfont.Font(root, font=desktop.font(th.FONT_SIZE))
        self.levels = []
        self.closed = False
        self.armed = False
        self.watch_id = None

    def px(self, value):
        return max(1, round(value * self.scale))

    def area(self, x, y):
        return desktop.work_area_at(x, y) or (0, 0, self.root.winfo_screenwidth(),
                                              self.root.winfo_screenheight())

    def show(self, x, y):
        level = _Level(self, self.items)
        L, T, R, B = self.area(x, y)
        lx = x if x + level.width <= R else x - level.width
        ly = y if y + level.height <= B else y - level.height
        level.place(max(L, min(lx, R - level.width)), max(T, min(ly, B - level.height)))
        level.win.focus_force()
        self.watch()

    def watch(self):
        """Ferme le menu au premier clic en dehors (attend d'abord le relâchement du clic droit)."""
        if self.closed:
            return
        if not desktop.mouse_buttons_down():
            self.armed = True
        elif self.armed and not any(level.contains(*self.root.winfo_pointerxy())
                                    for level in self.levels):
            self.close()
            return
        self.watch_id = self.root.after(40, self.watch)

    def run(self, item):
        self.close()
        if item.command:
            item.command()

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.watch_id:
            self.root.after_cancel(self.watch_id)
        for level in reversed(self.levels):
            level.destroy()
        self.levels = []
        if self.on_close:
            self.on_close()


class _Level:
    def __init__(self, menu, items, parent=None):
        self.menu, self.items, self.parent = menu, items, parent
        self.child = self.child_row = None
        self.hover = None
        self.pressed = False
        self.timer = None
        self.layout()
        w = self.win = tk.Toplevel(menu.root)
        w.overrideredirect(True)
        desktop.make_transparent(w)
        w.attributes("-topmost", True)
        c = self.c = tk.Canvas(w, bg=desktop.BG, highlightthickness=0, bd=0,
                               width=self.width, height=self.height)
        c.pack()
        self.draw()
        c.bind("<Motion>", lambda e: self.set_hover(self.row_at(e.y)))
        c.bind("<Leave>", self.on_leave)
        c.bind("<ButtonPress>", self.on_press)
        c.bind("<ButtonRelease>", self.on_release)
        w.bind("<Escape>", lambda e: menu.close())
        menu.levels.append(self)

    def layout(self):
        m, px = self.menu, self.menu.px
        self.pad, self.gap = px(th.PADDING), px(th.GAP)
        self.icon_px = px(th.ICON_PIXEL)
        has_col = any(i and (i.icon or i.check is not None or i.radio is not None)
                      for i in self.items)
        self.col = ICON_SIZE * self.icon_px if has_col else 0
        has_sub = any(i and i.items for i in self.items)
        self.text_x = self.pad + self.gap + (self.col + self.gap if self.col else 0)
        text_w = max((m.font.measure(i.label) for i in self.items if i), default=0)
        arrow = 2 * self.gap if has_sub else 0
        self.w = max(self.text_x + text_w + arrow + self.gap + self.pad, px(th.MIN_WIDTH))
        self.rows, y = [], self.pad
        for item in self.items:
            h = px(th.ROW_HEIGHT) if item else px(th.SEPARATOR_HEIGHT)
            self.rows.append((y, y + h, item))
            y += h
        self.h = y + self.pad
        shadow = px(th.SHADOW_OFFSET)
        self.width, self.height = self.w + shadow, self.h + shadow

    def place(self, x, y):
        self.x, self.y = x, y
        self.win.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.win.update_idletasks()           # sur Mac, le premier plan ne tient qu'une fois affiché
        desktop.make_tool_window(self.win)
        desktop.keep_on_top([self.win])

    def contains(self, x, y):
        return self.x <= x < self.x + self.width and self.y <= y < self.y + self.height

    def draw(self):
        c, px, w, h = self.c, self.menu.px, self.w, self.h
        s = px(th.SHADOW_OFFSET)
        r = px(th.RADIUS)
        round_rect(c, 1 + s, 1 + s, w - 1 + s, h - 1 + s, r, fill=th.SHADOW, outline="")
        self.body = round_rect(c, 1, 1, w - 1, h - 1, r, fill=th.PAPER, outline=th.INK,
                               width=px(th.BORDER))
        for top, bottom, item in self.rows:
            mid = (top + bottom) // 2
            if item is None:
                c.create_line(self.pad + self.gap, mid, w - self.pad - self.gap, mid,
                              fill=th.SHADOW, width=px(1))
                continue
            self.draw_mark(item, self.pad + self.gap + self.col // 2, mid)
            c.create_text(self.text_x, mid, anchor="w", text=item.label, font=self.menu.font,
                          fill=th.INK if item.enabled else th.MUTED)
            if item.items:
                ax, d = w - self.pad - self.gap, px(4)
                c.create_line(ax - d, mid - d, ax, mid, ax - d, mid + d, fill=th.INK,
                              width=px(2), capstyle="round", joinstyle="round")

    def draw_mark(self, item, cx, cy):
        c, px = self.c, self.menu.px
        if item.icon:
            half = self.col // 2
            draw_runs(c, RUNS[item.icon], self.icon_px, cx - half, cy - half)
            return
        r = px(6)
        if item.check is not None:
            round_rect(c, cx - r, cy - r, cx + r, cy + r, px(4), outline=th.INK, width=px(2),
                       fill=th.ACCENT if item.check else th.PAPER)
            if item.check:
                c.create_line(cx - px(3), cy, cx - px(1), cy + px(3), cx + px(3), cy - px(3),
                              fill=th.PAPER, width=px(2), capstyle="round", joinstyle="round")
        elif item.radio is not None:
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=th.INK, width=px(2),
                          fill=th.ACCENT if item.radio else th.PAPER)

    def row_at(self, y):
        for i, (top, bottom, item) in enumerate(self.rows):
            if top <= y < bottom:
                return i if item and item.enabled else None
        return None

    def set_hover(self, index):
        if index == self.hover:
            return
        self.hover = index
        self.c.delete("hover")
        if index is not None:
            top, bottom, _ = self.rows[index]
            px = self.menu.px
            round_rect(self.c, self.pad, top + px(1), self.w - self.pad, bottom - px(1), px(8),
                       fill=th.HOVER, outline="", tags="hover")
            self.c.tag_raise("hover", self.body)
        if self.timer:
            self.c.after_cancel(self.timer)
        self.timer = self.c.after(th.SUBMENU_DELAY_MS, self.sync_child)

    def sync_child(self):
        self.timer = None
        if self.hover is None or self.hover == self.child_row:
            return
        self.close_child()
        if self.rows[self.hover][2].items:
            self.open_child(self.hover)

    def open_child(self, index):
        top, _, item = self.rows[index]
        child = _Level(self.menu, item.items, parent=self)
        L, T, R, B = self.menu.area(self.x, self.y)
        x = self.x + self.w - self.pad
        if x + child.width > R:
            x = self.x - child.width + self.pad
        y = max(T, min(self.y + top - self.pad, B - child.height))
        child.place(max(L, x), y)
        self.child, self.child_row = child, index

    def close_child(self):
        if self.child:
            self.child.destroy()
            self.child = self.child_row = None

    def on_leave(self, e):
        if self.hover != self.child_row:      # vers le sous-menu ouvert : la ligne reste en évidence
            self.set_hover(None)

    def on_press(self, e):
        self.pressed = True

    def on_release(self, e):
        if not self.pressed:
            return
        self.pressed = False
        index = self.row_at(e.y)
        if index is None:
            return
        item = self.rows[index][2]
        if item.items:
            if self.timer:
                self.c.after_cancel(self.timer)
                self.timer = None
            if index != self.child_row:
                self.close_child()
                self.open_child(index)
        else:
            self.menu.run(item)

    def destroy(self):
        if self.timer:
            self.c.after_cancel(self.timer)
            self.timer = None
        self.close_child()
        if self in self.menu.levels:
            self.menu.levels.remove(self)
        try:
            self.win.destroy()
        except tk.TclError:
            pass
