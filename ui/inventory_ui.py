"""Inventory screen: stacking, moving, splitting, using and descriptions."""
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton

from .widgets import THEME, make_label, make_panel


class InventoryUI:
    def __init__(self, base, gm, audio):
        self.base = base
        self.gm = gm
        self.audio = audio
        self.visible = False
        self.root = DirectFrame(frameColor=(0, 0, 0, 0.6))
        self.root.set_transparency(True)
        self.root.hide()
        self.panel = make_panel(self.root, (-0.05, 0, 0), (-0.7, 0.7, -0.75, 0.75))
        self.title = make_label("Inventory", self.panel, (0, 0, 0.68), scale=0.07)
        self.detail = make_label("", self.panel, (0, 0, -0.55), scale=0.035)
        self.detail["text_align"] = TextNode.ACenter
        self.slot_buttons = []
        self.selected = None
        self._build_slots()

    def _build_slots(self):
        for btn in self.slot_buttons:
            btn.destroy()
        self.slot_buttons = []
        inv = self.gm.inventory
        cols, rows = 6, 4
        for i in range(cols * rows):
            x = -0.55 + (i % cols) * 0.22
            y = 0.5 - (i // cols) * 0.24
            btn = DirectButton(parent=self.panel, pos=(x, 0, y), scale=0.09,
                               frameColor=(0.12, 0.16, 0.12, 0.95),
                               text="", text_scale=0.35, text_pos=(0, -0.9),
                               text_fg=THEME["text"], pressEffect=1,
                               command=self._on_click, extraArgs=[i],
                               frameSize=(-1.1, 1.1, -1.1, 1.1))
            self.slot_buttons.append(btn)

    def _on_click(self, index):
        if self.selected is None:
            self.selected = index
        elif self.selected == index:
            new_idx = self.gm.inventory.split(index)
            self.selected = None
            if new_idx is not None and self.audio:
                self.audio.play("collect")
        else:
            self.gm.inventory.move(self.selected, index)
            self.selected = None
            if self.audio:
                self.audio.play("collect")
        self.refresh()

    def use_selected(self, index):
        effects = self.gm.inventory.use(index)
        if effects and self.gm:
            p = self.gm.player
            p.eat(effects.get("hunger", 0), effects.get("health", 0), effects.get("stamina", 0))
            if self.audio:
                self.audio.play("collect")
        self.refresh()

    def refresh(self):
        inv = self.gm.inventory
        for i, btn in enumerate(self.slot_buttons):
            slot = inv.slots[i]
            if slot.is_empty():
                btn["text"] = ""
                btn["text_fg"] = THEME["text"]
                btn["frameColor"] = (0.12, 0.16, 0.12, 0.95)
            else:
                btn["text"] = "%s\n%d" % (self.gm.gd.item_name(slot.item_id)[:9], slot.quantity)
                rarity = self.gm.gd.item(slot.item_id).get("rarity", "common")
                btn["text_fg"] = self.gm.gd.rarity_colour(rarity)
                sel = (0.35, 0.65, 0.35, 0.9) if self.selected == i else (0.12, 0.16, 0.12, 0.95)
                btn["frameColor"] = sel

    def set_detail(self, index):
        slot = self.gm.inventory.slots[index]
        if slot.is_empty():
            self.detail["text"] = ""
            return
        item = self.gm.gd.item(slot.item_id)
        self.detail["text"] = "%s - %s" % (self.gd_name(slot), item.get("description", ""))

    def gd_name(self, slot):
        return self.gm.gd.item_name(slot.item_id)

    def show(self):
        self.visible = True
        self.refresh()
        self.root.show()

    def hide(self):
        self.visible = False
        self.selected = None
        self.root.hide()
