"""Building placement: transparent preview, rotation, collision-checked placement."""
import math

from panda3d.core import TransparencyAttrib

from .geometry import make_box, make_cylinder


STRUCTURE_COLOURS = {
    "old_bed": (0.55, 0.45, 0.3), "regular_bed": (0.5, 0.5, 0.55), "good_bed": (0.4, 0.5, 0.6),
    "giant_bed": (0.6, 0.4, 0.5), "sun_dial": (0.7, 0.65, 0.5), "bunny_trap": (0.5, 0.4, 0.25),
    "bear_trap": (0.45, 0.45, 0.5), "freezer": (0.75, 0.8, 0.85), "farm_plot": (0.35, 0.28, 0.15),
    "wood_rain_storage": (0.45, 0.35, 0.2), "shelf": (0.5, 0.4, 0.25), "log_wall": (0.4, 0.28, 0.15),
    "crock_pot": (0.6, 0.3, 0.2), "radar": (0.35, 0.35, 0.4), "boost_pad": (0.3, 0.6, 0.4),
    "biofuel_processor": (0.4, 0.5, 0.3), "torch": (0.7, 0.5, 0.2), "lightning_rod": (0.6, 0.6, 0.65),
    "ammo_crate": (0.35, 0.4, 0.3), "oil_drill": (0.4, 0.35, 0.3), "teleporter": (0.5, 0.3, 0.6),
    "respawn_capsule": (0.3, 0.6, 0.6), "time_accelerator": (0.4, 0.4, 0.7),
    "weather_machine": (0.5, 0.6, 0.5),
}


class BuildingSystem:
    def __init__(self, base, gm, renderer):
        self.base = base
        self.gm = gm
        self.renderer = renderer
        self.placing = None
        self.rotation = 0
        self.preview = None
        self.placed_nodes = {}
        self._rebuild_all()

    def _make_structure_np(self, structure_id, parent, x, y, rotation, preview=False):
        colour = STRUCTURE_COLOURS.get(structure_id, (0.5, 0.5, 0.5))
        node = parent.attachNewNode("struct_%s" % structure_id)
        node.set_pos(x, y, self.renderer.get_height(x, y))
        node.set_h(rotation)
        if structure_id.endswith("bed"):
            node.attach_new_node(make_box(2.0, 1.0, 0.5, colour))
            node.attach_new_node(make_box(0.2, 1.0, 0.8, colour)).set_pos(-0.9, 0, 0)
        elif structure_id == "log_wall":
            for i in range(3):
                log = node.attach_new_node(make_cylinder(0.3, 3.0, colour))
                log.set_hpr(0, 90, 0)
                log.set_pos(-1 + i, 0, 0.3 + i * 0.0)
        elif structure_id == "farm_plot":
            node.attach_new_node(make_box(3.0, 3.0, 0.3, colour))
        elif structure_id == "torch":
            node.attach_new_node(make_cylinder(0.1, 2.0, (0.4, 0.3, 0.2)))
            node.attach_new_node(make_box(0.3, 0.3, 0.3, (0.9, 0.6, 0.2))).set_pos(0, 0, 2.0)
        else:
            node.attach_new_node(make_box(1.6, 1.2, 1.2, colour))
        if preview:
            node.set_transparency(TransparencyAttrib.MAlpha)
            node.set_alpha_scale(0.5)
        return node

    def _rebuild_all(self):
        for node in self.placed_nodes.values():
            node.remove_node()
        self.placed_nodes = {}
        for struct in self.gm.structures:
            node = self._make_structure_np(struct["type"], self.renderer.root,
                                           struct["x"], struct["y"], struct.get("rotation", 0))
            self.placed_nodes[struct["id"]] = node

    def start_placement(self, structure_id):
        self.placing = structure_id
        self.rotation = 0
        if self.preview:
            self.preview.remove_node()
        self.preview = self._make_structure_np(structure_id, self.renderer.root, 0, 0, 0, preview=True)

    def cancel(self):
        self.placing = None
        if self.preview:
            self.preview.remove_node()
            self.preview = None

    def rotate(self, step=15):
        self.rotation = (self.rotation + step) % 360

    def update_preview(self):
        if not self.placing or not self.preview:
            return
        player = self.gm.player
        fx, fy = self._placement_pos(player)
        self.preview.set_pos(fx, fy, self.renderer.get_height(fx, fy))
        self.preview.set_h(self.rotation)
        ok = self._is_valid(fx, fy)
        self.preview.set_alpha_scale(0.6 if ok else 0.2)

    def _placement_pos(self, player):
        heading = math.radians(player.heading) if hasattr(player, "heading") else 0
        return player.x + math.sin(heading) * 4, player.y + math.cos(heading) * 4

    def _is_valid(self, x, y):
        for s in self.gm.structures:
            if abs(s["x"] - x) < 3.0 and abs(s["y"] - y) < 3.0:
                return False
        if math.hypot(x, y) < 3.0:
            return False
        return True

    def confirm(self):
        if not self.placing:
            return False
        player = self.gm.player
        fx, fy = self._placement_pos(player)
        if not self._is_valid(fx, fy):
            return False
        struct = self.gm.place_structure(self.placing, fx, fy, self.rotation)
        if struct is None:
            return False
        node = self._make_structure_np(self.placing, self.renderer.root, fx, fy, self.rotation)
        self.placed_nodes[struct["id"]] = node
        self.placing = None
        if self.preview:
            self.preview.remove_node()
            self.preview = None
        return True

    def refresh(self):
        self._rebuild_all()
