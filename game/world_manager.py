"""Renders the world: terrain, chunked trees with distance culling, locations,
campfire visuals, lighting, sky, stars and weather particles."""
import math
from panda3d.core import ClockObject
import os
import random

from panda3d.core import (
    GeoMipTerrain, Filename, PNMImage, CardMaker, AmbientLight, DirectionalLight,
    PointLight, Texture, TransparencyAttrib, Fog, LVector3f, NodePath, VBase4)

from .assets_gen import ensure_all_textures
from .day_night_phases import PHASES
from .geometry import make_cylinder, make_cone, make_box, make_sphere

TERRAIN_SIZE = 256


def _colour(c, a=1.0):
    return VBase4(c[0], c[1], c[2], a)


class WorldRenderer:
    """Builds and updates all 3D world visuals from a GameManager state."""

    def __init__(self, base, gm, settings):
        self.base = base
        self.gm = gm
        self.settings = settings
        self.render_distance = settings.get("render_distance", 240)
        self.root = NodePath("world")
        self.root.reparentTo(self.base.render)
        self.textures = ensure_all_textures()
        self.tree_nodes = {}
        self.location_nodes = {}
        self.falling_trees = {}
        self._rng = random.Random(7)
        self._models = {}
        self._rendered_fire_level = None
        self._build_sky()
        self._build_lights()
        self._build_terrain()
        self._build_water()
        self._build_campfire()
        self._build_tree_models()
        self._build_all_trees()
        self._build_locations()
        self._build_stars()
        self._build_weather_particles()

    # ------------------------------------------------------------ sky & light

    def _build_sky(self):
        cm = CardMaker("sky")
        cm.set_frame(-800, 800, -800, 800)
        self.sky_card = self.root.attachNewNode(cm.generate())
        self.sky_card.set_p(-90)
        self.sky_card.set_z(180)
        self.sky_card.set_light_off()
        self.sky_card.set_bin("background", 0)
        self.sky_card.set_depth_write(False)
        self.sky_card.set_compass()

    def _build_stars(self):
        cm = CardMaker("star")
        cm.set_frame(-0.05, 0.05, -0.05, 0.05)
        self.stars = self.root.attachNewNode("stars")
        self.stars.set_light_off()
        self.stars.set_compass()
        rng = random.Random(42)
        for _ in range(300):
            star = self.stars.attachNewNode(cm.generate())
            theta = rng.uniform(0, 2 * math.pi)
            phi = rng.uniform(5, 80)
            r = 700
            star.set_pos(r * math.cos(theta) * math.cos(math.radians(phi)),
                         r * math.sin(theta) * math.cos(math.radians(phi)),
                         r * math.sin(math.radians(phi)))
            star.set_billboard_point_eye()
            star.set_scale(rng.uniform(2, 6))
            star.set_color(1, 1, 1, rng.uniform(0.4, 1.0))
        self.stars.set_transparency(TransparencyAttrib.MAlpha)
        self.stars.hide()

    def _build_lights(self):
        self.ambient = AmbientLight("ambient")
        self.ambient_node = self.root.attachNewNode(self.ambient)
        self.root.set_light(self.ambient_node)
        self.sun = DirectionalLight("sun")
        self.sun_node = self.root.attachNewNode(self.sun)
        self.sun_node.set_hpr(45, -60, 0)
        self.root.set_light(self.sun_node)
        if self.settings.get("shadows", True):
            self.sun.set_shadow_caster(True, self.settings.get("shadow_resolution", 1024),
                                        self.settings.get("shadow_resolution", 1024))
            self.sun.get_lens().set_near_far(10, 500)
            self.sun.get_lens().set_film_size(160, 160)
        self.fire_light = PointLight("fire")
        self.fire_light.set_color((1.0, 0.6, 0.3, 1))
        self.fire_light.set_attenuation((1, 0.005, 0.0002))
        self.fire_node = self.root.attachNewNode(self.fire_light)
        self.fire_node.set_pos(0, 0, 2)
        self.root.set_light(self.fire_node)
        self.fog = Fog("fog")
        self.fog.set_color(0.7, 0.8, 0.85)
        self.fog.set_linear_range(60, self.render_distance)
        self.base.render.set_fog(self.fog)

    # --------------------------------------------------------------- terrain

    def _build_terrain(self):
        world = self.gm.world
        img = PNMImage(TERRAIN_SIZE, TERRAIN_SIZE)
        scale = world.size / TERRAIN_SIZE
        for x in range(TERRAIN_SIZE):
            for y in range(TERRAIN_SIZE):
                wx = (x - TERRAIN_SIZE / 2) * scale
                wy = (y - TERRAIN_SIZE / 2) * scale
                h = world.terrain_height(wx, wy)
                img.set_xel(x, y, max(0.0, min(1.0, (h + 30) / 90.0)))
        fname = Filename.from_os_specific(os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets", "textures", "heightfield.png"))
        os.makedirs(os.path.dirname(str(fname)), exist_ok=True)
        img.write(fname)
        self.terrain = GeoMipTerrain("terrain")
        self.terrain.setHeightfield(fname)
        self.terrain.setBlockSize(64)
        self.terrain.setNearFar(self.render_distance * 0.35, self.render_distance)
        self.z_scale = world.height_scale * 3.4
        terrain_root = self.terrain.getRoot()
        terrain_root.set_scale(world.size / TERRAIN_SIZE, world.size / TERRAIN_SIZE, self.z_scale)
        terrain_root.set_pos(-world.size / 2, -world.size / 2, 0)
        terrain_root.reparentTo(self.root)
        grass = self.base.loader.loadTexture(self.textures["grass"])
        grass.set_wrap_u(Texture.WMRepeat)
        grass.set_wrap_v(Texture.WMRepeat)
        terrain_root.set_texture(grass)
        for stage in terrain_root.find_all_texture_stages():
            terrain_root.set_tex_scale(stage, 48)
        self.terrain.generate()
        if self.base.camera is not None:
            self.terrain.set_focal_point(self.base.camera.get_pos(self.base.render).xy)

    def get_height(self, x, y):
        size = self.gm.world.size
        fx = (x + size / 2) / size * TERRAIN_SIZE
        fy = (y + size / 2) / size * TERRAIN_SIZE
        fx = max(0, min(TERRAIN_SIZE - 1, fx))
        fy = max(0, min(TERRAIN_SIZE - 1, fy))
        return self.terrain.get_elevation(fx, fy) * self.z_scale

    def _build_water(self):
        half = self.gm.world.size / 2
        cm = CardMaker("water")
        cm.set_frame(-half, half, -half, half)
        self.water = self.root.attachNewNode(cm.generate())
        self.water.set_p(-90)
        self.water.set_z(1.2)
        self.water.set_color(0.15, 0.3, 0.5, 0.6)
        self.water.set_transparency(TransparencyAttrib.MAlpha)

    # -------------------------------------------------------------- campfire

    def _build_campfire(self):
        self.campfire_np = self.root.attachNewNode("campfire")
        self.campfire_np.attach_new_node(make_cylinder(1.6, 0.35, (0.25, 0.2, 0.15)))
        for i in range(5):
            log = self.campfire_np.attach_new_node(make_cylinder(0.12, 2.2, (0.4, 0.28, 0.16)))
            log.set_hpr(i * 72, 90, 20)
            log.set_z(0.3)
        cm = CardMaker("flame")
        cm.set_frame(-0.5, 0.5, 0, 1.6)
        self.flames = []
        rng = random.Random(5)
        for _ in range(6):
            flame = self.campfire_np.attachNewNode(cm.generate())
            flame.set_pos(rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0.4)
            flame.set_billboard_point_eye()
            flame.set_transparency(TransparencyAttrib.MAlpha)
            flame.set_color(1.0, rng.uniform(0.3, 0.7), 0.1, 0.9)
            flame.set_scale(rng.uniform(0.7, 1.3))
            self.flames.append(flame)
        self.smoke = []
        for _ in range(3):
            puff = self.campfire_np.attachNewNode(cm.generate())
            puff.set_pos(0, 0, 2.0)
            puff.set_billboard_point_eye()
            puff.set_transparency(TransparencyAttrib.MAlpha)
            puff.set_color(0.4, 0.4, 0.4, 0.3)
            self.smoke.append(puff)
        self.campfire_decor = self.campfire_np.attachNewNode("decor")
        self._rendered_fire_level = 0
        self._update_campfire_level()

    def _update_campfire_level(self):
        level = self.gm.campfire.level
        self.campfire_decor.remove_node()
        self.campfire_decor = self.campfire_np.attachNewNode("decor")
        if level >= 2:
            for i in range(3):
                bench = self.campfire_decor.attach_new_node(make_cylinder(0.25, 2.4, (0.4, 0.3, 0.18)))
                ang = i * 120 + 30
                bench.set_pos(math.cos(math.radians(ang)) * 3, math.sin(math.radians(ang)) * 3, 0.25)
                bench.set_hpr(ang, 90, 0)
        if level >= 3:
            rocks = 6 if level == 3 else 12
            for i in range(rocks):
                rock = self.campfire_decor.attach_new_node(make_sphere(0.45, (0.45, 0.45, 0.48)))
                ang = i * (360 / rocks)
                rock.set_pos(math.cos(math.radians(ang)) * 2.2, math.sin(math.radians(ang)) * 2.2, 0.3)
        if level >= 5:
            for i in range(8):
                stone = self.campfire_decor.attach_new_node(make_box(1.2, 1.2, 0.5, (0.5, 0.5, 0.52)))
                ang = i * 45
                stone.set_pos(math.cos(math.radians(ang)) * 4.5, math.sin(math.radians(ang)) * 4.5, 0.25)
        if level >= 6:
            pillar = self.campfire_decor.attach_new_node(make_cylinder(0.6, 3.0, (0.55, 0.5, 0.45)))
            pillar.set_pos(5.5, 0, 1.5)

    # ---------------------------------------------------------------- trees

    def _build_tree_models(self):
        specs = {"small": (0.35, 3, 1.0), "normal": (0.55, 6, 1.2), "big": (0.9, 10, 1.8),
                 "snow_pine": (0.5, 7, 1.1), "ancient": (1.2, 13, 2.2)}
        for tree_type, (radius, height, crown) in specs.items():
            model = NodePath("tree_" + tree_type)
            model.attach_new_node(make_cylinder(radius, height, (0.32, 0.22, 0.13)))
            if tree_type == "snow_pine":
                for i in range(3):
                    cone = model.attach_new_node(make_cone(radius * (2.2 - i * 0.6), height * 0.35,
                                                           (0.15, 0.35, 0.22), z0=height * (0.4 + i * 0.2)))
            else:
                green = (0.12, 0.38, 0.14) if tree_type != "ancient" else (0.2, 0.3, 0.25)
                model.attach_new_node(make_sphere(radius * 2.2 * crown, green, segments=10)) \
                    .set_pos(0, 0, height + radius * 0.8)
            self._models[tree_type] = model

    def _build_all_trees(self):
        for idx, tree in enumerate(self.gm.world.trees):
            if tree.get("removed"):
                continue
            model = self._models[tree["type"]]
            np = self.root.attachNewNode("tree_%d" % idx)
            np.set_pos(tree["x"], tree["y"], self.get_height(tree["x"], tree["y"]))
            np.set_scale(tree.get("scale", 1.0))
            model.instance_to(np)
            self.tree_nodes[idx] = np

    def _build_locations(self):
        for loc in self.gm.world.locations:
            node = self.root.attachNewNode(loc["id"])
            x, y = loc["x"], loc["y"]
            node.set_pos(x, y, self.get_height(x, y))
            loc_type = loc["type"]
            if loc_type.endswith("_cave"):
                node.attach_new_node(make_box(6, 6, 3.5, (0.3, 0.3, 0.32)))
                node.attach_new_node(make_box(2, 0.5, 2.5, (0.12, 0.12, 0.12))).set_pos(3, 0, 0)
                label_colour = {"red_cave": (0.8, 0.2, 0.2), "blue_cave": (0.2, 0.4, 0.8),
                                "yellow_cave": (0.85, 0.8, 0.2), "grey_cave": (0.5, 0.5, 0.5)}.get(loc_type)
                if label_colour:
                    node.attach_new_node(make_sphere(0.6, label_colour)).set_pos(0, 0, 4.2)
            elif loc_type == "chest":
                node.attach_new_node(make_box(1.2, 0.8, 1.0, (0.5, 0.35, 0.15)))
            else:
                colours = {"cabin": (0.45, 0.33, 0.22), "house": (0.5, 0.4, 0.3),
                           "grocery_store": (0.55, 0.55, 0.5), "clinic": (0.8, 0.8, 0.85),
                           "mechanical_building": (0.4, 0.4, 0.45), "warehouse": (0.5, 0.42, 0.35),
                           "campsite": (0.3, 0.3, 0.3), "ruins": (0.55, 0.52, 0.45),
                           "cave": (0.3, 0.3, 0.32), "cultist_outpost": (0.25, 0.15, 0.2)}
                colour = colours.get(loc_type, (0.5, 0.5, 0.5))
                height = 3.0 if loc_type not in ("campsite", "ruins") else 1.5
                node.attach_new_node(make_box(6, 5, height, colour))
                node.attach_new_node(make_box(7, 6, 0.5, (0.3, 0.2, 0.15))).set_pos(0, 0, height)
            self.location_nodes[loc["id"]] = node

    # --------------------------------------------------------------- weather

    def _build_weather_particles(self):
        self.rain_root = self.root.attachNewNode("rain")
        cm = CardMaker("drop")
        cm.set_frame(-0.02, 0.02, -0.4, 0.02)
        rng = random.Random(3)
        self.rain_particles = []
        for _ in range(200):
            drop = self.rain_root.attachNewNode(cm.generate())
            drop.set_pos(rng.uniform(-40, 40), rng.uniform(-40, 40), rng.uniform(0, 30))
            drop.set_color(0.6, 0.7, 1.0, 0.6)
            drop.set_transparency(TransparencyAttrib.MAlpha)
            self.rain_particles.append(drop)
        self.rain_root.set_compass()
        self.rain_root.hide()

    # ---------------------------------------------------------------- update

    def update(self, dt, camera_pos):
        frame = globalClock.frame_count
        phase = self.gm.day_night.phase()
        p = PHASES[phase]
        self.sky_card.set_color(_colour(p["sky"]))
        self.ambient.set_color(_colour(p["ambient"]))
        if phase == "night":
            self.sun.set_color((0.15, 0.18, 0.3, 1))
        else:
            s = p["sun"]
            self.sun.set_color((s, s * 0.95, s * 0.85, 1))
        self.fog.set_color(*p["fog"])
        vis = self.gm.weather.visibility
        base_far = self.render_distance * vis
        self.fog.set_linear_range(base_far * 0.25, base_far)
        if phase == "night":
            self.stars.show()
        else:
            self.stars.hide()

        fire_frac = self.gm.campfire.fuel_fraction()
        if self.gm.campfire.lit:
            flicker = 0.85 + 0.15 * math.sin(frame * 0.7)
            scale = (0.4 + fire_frac) * flicker
            for i, flame in enumerate(self.flames):
                flame.set_sx(scale * (1 + 0.1 * math.sin(frame * 0.9 + i)))
                flame.set_sz(scale * 1.4)
                flame.set_alpha_scale(0.4 + fire_frac * 0.6)
            for i, puff in enumerate(self.smoke):
                cycle = (frame * 0.01 + i / 3) % 1
                puff.set_z(2 + cycle * 4)
                puff.set_alpha_scale(0.35 * (1 - cycle))
            self.fire_node.set_color((1.0, 0.6 + 0.2 * flicker, 0.3, 1))
        else:
            for flame in self.flames:
                flame.set_alpha_scale(0.0)
            for puff in self.smoke:
                puff.set_alpha_scale(0.0)
            self.fire_node.set_color((0.1, 0.1, 0.1, 1))

        if self.gm.campfire.level != self._rendered_fire_level:
            self._rendered_fire_level = self.gm.campfire.level
            self._update_campfire_level()

        if self.gm.weather.is_wet:
            self.rain_root.show()
            for drop in self.rain_particles:
                z = drop.get_z() - dt * 25
                if z < 0:
                    z = 30
                drop.set_z(z)
        else:
            self.rain_root.hide()

        self._update_falling_trees(dt)
        self.terrain.update()

    def update_tree_visibility(self, camera_pos):
        rd = self.render_distance
        for idx, node in self.tree_nodes.items():
            tree = self.gm.world.trees[idx]
            if tree.get("removed") and idx not in self.falling_trees:
                node.hide()
                continue
            d = math.hypot(tree["x"] - camera_pos.x, tree["y"] - camera_pos.y)
            if d > rd:
                node.hide()
            else:
                node.show()

    def animate_tree_fall(self, idx, direction_degrees):
        """Starts a believable fall: the tree pivots around its base away from the chopper."""
        node = self.tree_nodes.get(idx)
        if node is None or idx in self.falling_trees:
            return
        rad = math.radians(direction_degrees)
        self.falling_trees[idx] = {"node": node, "progress": 0.0,
                                   "dir_x": math.sin(rad), "dir_y": -math.cos(rad)}

    def _update_falling_trees(self, dt):
        done = []
        for idx, fall in self.falling_trees.items():
            fall["progress"] = min(1.0, fall["progress"] + dt * 0.7)
            t = fall["progress"]
            angle = 90 * t * t
            node = fall["node"]
            node.set_p(-angle * fall["dir_x"])
            node.set_r(angle * fall["dir_y"])
            if t >= 1.0:
                done.append(idx)
        for idx in done:
            node = self.falling_trees.pop(idx)["node"]
            node.hide()

    def show_tree_damage(self, idx, damage_fraction):
        node = self.tree_nodes.get(idx)
        if node is None:
            return
        node.set_scale(node.get_scale()[0] * 1.0)
        tilt = damage_fraction * 4
        node.set_r(tilt)
