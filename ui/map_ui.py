"""World map: fog of war, discovered locations, landmarks and player position."""
import math

from direct.gui import DirectGuiGlobals
from direct.gui.DirectFrame import DirectFrame
from direct.gui.DirectLabel import DirectLabel

from .widgets import THEME, make_label, make_panel

LOCATION_LABELS = {
    "cabin": "Cabin", "house": "House", "grocery_store": "Store", "clinic": "Clinic",
    "mechanical_building": "Workshop", "warehouse": "Warehouse", "campsite": "Campsite",
    "ruins": "Ruins", "cave": "Cave", "chest": "Chest", "cultist_outpost": "Outpost",
    "red_cave": "Red Cave", "blue_cave": "Blue Cave", "yellow_cave": "Yellow Cave",
    "grey_cave": "Grey Cave",
}


class MapUI:
    def __init__(self, base, gm):
        self.base = base
        self.gm = gm
        self.visible = False
        self.root = DirectFrame(frameColor=(0, 0, 0, 0.6))
        self.root.set_transparency(True)
        self.root.hide()
        self.panel = make_panel(self.root, (0, 0, 0), (-0.85, 0.85, -0.85, 0.85))
        self.title = make_label("World Map", self.panel, (0, 0, 0.78), scale=0.06)
        self.markers = []
        self.player_marker = None

    def refresh(self):
        for m in self.markers:
            m.destroy()
        self.markers = []
        gm = self.gm
        has_map = any(s["type"] == "map" for s in gm.structures) or getattr(gm, "has_map", False)
        size = gm.world.size
        def to_panel(x, y):
            return (x / size * 1.5, y / size * 1.5)
        for loc in gm.world.locations:
            if not loc.get("discovered") and not has_map:
                continue
            px, py = to_panel(loc["x"], loc["y"])
            label = LOCATION_LABELS.get(loc["type"], loc["type"])
            colour = (0.9, 0.8, 0.3, 1) if loc.get("discovered") else (0.4, 0.4, 0.4, 0.6)
            if "child" in loc:
                child = gm.npcs.children[loc["child"]]
                colour = (0.3, 0.9, 0.3, 1) if child.rescued else (0.9, 0.3, 0.3, 1)
            marker = DirectLabel(parent=self.panel, pos=(px, 0, py), scale=0.045,
                                 text=label[:1], text_fg=colour, frameColor=(0, 0, 0, 0))
            self.markers.append(marker)
        if self.player_marker:
            self.player_marker.destroy()
        px, py = to_panel(gm.player.x, gm.player.y)
        self.player_marker = DirectLabel(parent=self.panel, pos=(px, 0, py), scale=0.05,
                                         text="You", text_fg=(0.3, 0.8, 1.0, 1), frameColor=(0, 0, 0, 0))

    def show(self):
        self.visible = True
        self.refresh()
        self.root.show()

    def hide(self):
        self.visible = False
        self.root.hide()
