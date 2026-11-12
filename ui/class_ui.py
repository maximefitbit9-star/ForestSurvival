"""Class selection: purchases with persistent diamonds, starting gear and perks."""
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton

from .widgets import THEME, make_label, make_panel


class ClassUI:
    def __init__(self, base, app):
        self.base = base
        self.app = app
        self.visible = False
        self.root = DirectFrame(frameColor=(0, 0, 0, 0.6))
        self.root.set_transparency(True)
        self.root.hide()
        self.panel = make_panel(self.root, (0, 0, 0), (-0.95, 0.95, -0.85, 0.85))
        self.title = make_label("Class Selection", self.panel, (0, 0, 0.75), scale=0.07)
        self.diamonds_label = make_label("", self.panel, (0, 0, 0.65), scale=0.05)
        self.info = make_label("", self.panel, (0, 0, -0.7), scale=0.035)
        self.info["text_align"] = TextNode.ACenter
        self.rows = []
        self.selected_class = None

    def refresh(self):
        for row in self.rows:
            row.destroy()
        self.rows = []
        app = self.app
        classes = app.gamedata.classes["classes"]
        self.diamonds_label["text"] = "Diamonds: %d" % app.profile.get("diamonds", 0)
        y = 0.5
        for class_id, cdef in classes.items():
            owned = class_id in app.profile.get("owned_classes", ["camper"])
            price = cdef["price"]
            state = "OWNED" if owned else ("%d diamonds" % price)
            can_buy = not owned and app.profile.get("diamonds", 0) >= price
            colour = (0.35, 0.65, 0.35, 1) if can_buy else ((0.2, 0.3, 0.5, 1) if owned else (0.25, 0.25, 0.25, 1))
            btn = DirectButton(parent=self.panel, pos=(-0.5, 0, y), scale=0.045,
                               text="%s - %s | %s" % (cdef["name"], cdef["description"][:60], state),
                               text_scale=0.8, text_fg=THEME["text"], text_align=DirectGuiGlobals.ALeft,
                               frameColor=colour, frameSize=(-0.05, 3.4, -0.9, 1.0),
                               command=self._select, extraArgs=[class_id])
            self.rows.append(btn)
            y -= 0.075

    def _select(self, class_id):
        app = self.app
        cs = app.class_system
        if cs.is_owned(class_id):
            self.selected_class = class_id
            cdef = app.gamedata.class_data(class_id)
            items = ", ".join("%d %s" % (q, app.gamedata.item_name(i))
                              for i, q in cdef.get("starting_items", {}).items())
            perks = ", ".join("%s: %s" % (k, v) for k, v in cdef.get("passives", {}).items())
            self.info["text"] = "Selected: %s | Starts with: %s | Perks: %s" % (
                cdef["name"], items or "nothing extra", perks or "none")
        elif cs.buy(class_id):
            self.app.save_profile()
            self.refresh()
            self.info["text"] = "Purchased %s!" % app.gamedata.class_data(class_id)["name"]
        else:
            self.info["text"] = "Not enough diamonds. Survive more nights to earn diamonds."

    def show(self):
        self.visible = True
        self.refresh()
        self.root.show()

    def hide(self):
        self.visible = False
        self.root.hide()
