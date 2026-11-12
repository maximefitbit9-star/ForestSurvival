"""Crafting bench interface: tiers, upgrades, recipes, missing materials, the
Grinder, cooking and the build menu."""
from panda3d.core import TextNode
from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectButton import DirectButton

from .widgets import THEME, make_label, make_panel


class CraftingUI:
    def __init__(self, base, gm, audio, on_craft=None, on_build=None):
        self.base = base
        self.gm = gm
        self.audio = audio
        self.on_craft = on_craft
        self.on_build = on_build
        self.visible = False
        self.root = DirectFrame(frameColor=(0, 0, 0, 0.6))
        self.root.set_transparency(True)
        self.root.hide()
        self.panel = make_panel(self.root, (0, 0, 0), (-0.95, 0.95, -0.8, 0.8))
        self.title = make_label("Crafting Bench - Tier %d" % gm.bench.level, self.panel,
                               (0, 0, 0.7), scale=0.07)
        self.info = make_label("", self.panel, (0, 0, -0.7), scale=0.035)
        self.info["text_align"] = TextNode.ACenter
        self.recipe_buttons = []
        self.tab = "craft"
        self._build_tabs()

    def _build_tabs(self):
        self.tab_craft = DirectButton(parent=self.panel, pos=(-0.7, 0, 0.58), scale=0.05,
                                      text="Craft", frameColor=THEME["accent"], text_fg=THEME["text"],
                                      command=self._set_tab, extraArgs=["craft"])
        self.tab_grind = DirectButton(parent=self.panel, pos=(-0.5, 0, 0.58), scale=0.05,
                                      text="Grinder", frameColor=(0.2, 0.2, 0.2, 1), text_fg=THEME["text"],
                                      command=self._set_tab, extraArgs=["grind"])
        self.tab_build = DirectButton(parent=self.panel, pos=(-0.28, 0, 0.58), scale=0.05,
                                       text="Build", frameColor=(0.2, 0.2, 0.2, 1), text_fg=THEME["text"],
                                       command=self._set_tab, extraArgs=["build"])

    def _set_tab(self, tab):
        self.tab = tab
        self.refresh()

    def _clear_buttons(self):
        for btn in self.recipe_buttons:
            btn.destroy()
        self.recipe_buttons = []

    def refresh(self):
        self._clear_buttons()
        self.title["text"] = "Crafting Bench - Tier %d" % self.gm.bench.level
        gm = self.gm
        if self.tab == "craft":
            recipes = gm.bench.all_known_recipes()
            nxt = gm.bench.next_upgrade_id()
            self._add_recipe_row(nxt, "Upgrade bench to Tier %d" % (gm.bench.level + 1),
                                  gm.bench.next_upgrade_cost(), can=gm.bench.can_upgrade(gm.player.craft_discount),
                                  is_upgrade=True)
            for recipe_id, recipe in recipes.items():
                if recipe_id == nxt:
                    continue
                struct = gm.gd.structure_def(recipe_id)
                name = struct.get("name", gm.gd.item_name(recipe_id) if gm.gd.has_item(recipe_id) else recipe_id)
                can = gm.bench.can_craft(recipe_id, gm.player.craft_discount)
                self._add_recipe_row(recipe_id, name, recipe["cost"], can=can)
        elif self.tab == "grind":
            inv = gm.inventory
            row = 0
            for i, slot in enumerate(inv.slots):
                if slot.is_empty():
                    continue
                out, amount = gm.gd.grinder_output(slot.item_id)
                if out is None:
                    continue
                self._add_grind_row(slot.item_id, out, amount, row)
                row += 1
            if row == 0:
                self.info["text"] = "Place wooden objects, mechanical junk or crops into the grinder."
        else:
            built = set(s["type"] for s in gm.structures)
            for recipe_id in gm.bench.all_known_recipes():
                struct = gm.gd.structure_def(recipe_id)
                if not struct:
                    continue
                count = sum(1 for s in gm.structures if s["type"] == recipe_id)
                self._add_build_row(recipe_id, struct.get("name", recipe_id), count)

    def _row_pos(self, row):
        return (-0.6, 0, 0.45 - row * 0.095)

    def _add_recipe_row(self, recipe_id, name, cost, can, is_upgrade=False):
        if len(self.recipe_buttons) >= 11:
            return
        row = len(self.recipe_buttons)
        pos = self._row_pos(row)
        cost_text = ", ".join("%d %s" % (q, self.gm.gd.item_name(i)) for i, q in cost.items())
        colour = THEME["accent"] if can else (0.25, 0.25, 0.25, 1)
        btn = DirectButton(parent=self.panel, pos=pos, scale=0.045,
                           text="%s  [%s]" % (name, cost_text), text_scale=0.8,
                           text_fg=THEME["text"], text_align=DirectGuiGlobals.ALeft,
                           frameColor=colour, frameSize=(-0.05, 3.2, -0.9, 1.0),
                           command=self._craft, extraArgs=[recipe_id, is_upgrade],
                           textMayChange=0)
        self.recipe_buttons.append(btn)

    def _add_grind_row(self, item_id, out_id, amount, row):
        pos = (-0.6, 0, 0.45 - row * 0.095)
        btn = DirectButton(parent=self.panel, pos=pos, scale=0.045,
                           text="Grind %s -> %d %s" % (self.gm.gd.item_name(item_id), amount,
                                                       self.gm.gd.item_name(out_id)),
                           text_scale=0.8, text_fg=THEME["text"], text_align=DirectGuiGlobals.ALeft,
                           frameColor=THEME["accent"], frameSize=(-0.05, 3.2, -0.9, 1.0),
                           command=self._grind, extraArgs=[item_id])
        self.recipe_buttons.append(btn)

    def _add_build_row(self, recipe_id, name, count):
        pos = self._row_pos(len(self.recipe_buttons))
        btn = DirectButton(parent=self.panel, pos=pos, scale=0.045,
                           text="Place %s (%d placed)" % (name, count),
                           text_scale=0.8, text_fg=THEME["text"], text_align=DirectGuiGlobals.ALeft,
                           frameColor=(0.3, 0.5, 0.3, 1), frameSize=(-0.05, 3.2, -0.9, 1.0),
                           command=self._start_build, extraArgs=[recipe_id])
        self.recipe_buttons.append(btn)

    def _craft(self, recipe_id, is_upgrade):
        gm = self.gm
        if is_upgrade:
            if gm.upgrade_bench():
                if self.audio:
                    self.audio.play("craft")
                self.refresh()
            else:
                self.info["text"] = "Not enough materials to upgrade."
            return
        ok, result = gm.craft(recipe_id)
        if ok:
            if self.audio:
                self.audio.play("craft")
            struct = gm.gd.structure_def(recipe_id)
            name = struct.get("name", recipe_id)
            self.info["text"] = "Crafted %s. Use the Build tab to place structures." % name
        else:
            missing = gm.bench.missing_materials(recipe_id, gm.player.craft_discount)
            self.info["text"] = "Missing: " + ", ".join(
                "%d %s" % (q, gm.gd.item_name(i)) for i, q in missing.items())
        self.refresh()

    def _grind(self, item_id):
        out, amount = self.gm.grind(item_id, 1)
        if out and self.audio:
            self.audio.play("craft")
        self.refresh()

    def _start_build(self, recipe_id):
        owned = any(s["type"] == recipe_id for s in self.gm.structures)
        if not owned:
            self.info["text"] = "Craft the structure first on the Craft tab."
            self.refresh()
            return
        if self.on_build:
            self.on_build(recipe_id)
        self.hide()

    def show(self):
        self.visible = True
        self.refresh()
        self.root.show()

    def hide(self):
        self.visible = False
        self.root.hide()
