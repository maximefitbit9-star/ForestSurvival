"""Seeded procedural world generation: terrain heights, biomes, locations, trees.

Pure data: the renderer turns this into Panda3D geometry. All positions are in
world units (metres), origin at the camp.
"""
import hashlib
import math
import random

BIOMES = {
    "forest": {"ground": (0.30, 0.50, 0.22), "trees": ["normal", "small"], "density": 1.0, "fog": (0.65, 0.75, 0.70)},
    "dense_woodland": {"ground": (0.18, 0.36, 0.16), "trees": ["normal", "big"], "density": 1.8, "fog": (0.45, 0.58, 0.45)},
    "snowy": {"ground": (0.85, 0.88, 0.92), "trees": ["snow_pine", "normal"], "density": 0.7, "fog": (0.80, 0.85, 0.90)},
    "magical": {"ground": (0.25, 0.35, 0.30), "trees": ["normal", "ancient"], "density": 0.8, "fog": (0.45, 0.40, 0.60)},
}


def _noise_2d(rng, x, y):
    """Cheap deterministic value noise from a per-world random table."""
    xi, yi = int(math.floor(x)), int(math.floor(y))
    xf, yf = x - xi, y - yi
    s = lambda a, b: (rng.seed_val * 7919 + a * 104729 + b * 1299709) % 1000 / 1000.0

    def interp(a, b, t):
        t = t * t * (3 - 2 * t)
        return a + (b - a) * t

    v00, v10 = s(xi, yi), s(xi + 1, yi)
    v01, v11 = s(xi, yi + 1), s(xi + 1, yi + 1)
    return interp(interp(v00, v10, xf), interp(v01, v11, xf), yf)


class SeededRNG(random.Random):
    def __init__(self, seed):
        self.seed_val = int(hashlib.md5(str(seed).encode()).hexdigest()[:8], 16)
        super().__init__(self.seed_val)


class WorldGen:
    def __init__(self, seed, size=512, height_scale=24):
        self.seed = seed
        self.size = size
        self.height_scale = height_scale
        self.rng = SeededRNG(seed)
        self.locations = []
        self.trees = []
        self.generate()

    def terrain_height(self, x, y):
        h = 0.0
        h += _noise_2d(self.rng, x / 120.0, y / 120.0) * 1.0
        h += _noise_2d(self.rng, x / 60.0, y / 60.0) * 0.4
        h += _noise_2d(self.rng, x / 25.0, y / 25.0) * 0.12
        d = math.sqrt(x * x + y * y)
        h -= max(0.0, (d - 200) / 400.0) * 0.3
        return h * self.height_scale

    def biome_at(self, x, y):
        n = _noise_2d(self.rng, x / 180.0 + 500, y / 180.0 + 500)
        d = math.sqrt(x * x + y * y)
        if d < 120:
            return "forest"
        if n < 0.30:
            return "dense_woodland"
        if n > 0.72:
            return "magical"
        if x < -self.size * 0.22 or y > self.size * 0.22:
            return "snowy"
        return "forest"

    def _rand_pos(self, rmin, rmax):
        ang = self.rng.uniform(0, 2 * math.pi)
        r = self.rng.uniform(rmin, rmax)
        return int(r * math.cos(ang)), int(r * math.sin(ang))

    def generate(self):
        rng = self.rng
        half = self.size // 2
        child_defs = [
            ("dino_kid", "red_cave", 90), ("squid_kid", "blue_cave", 130),
            ("kraken_kid", "yellow_cave", 180), ("koala_kid", "grey_cave", 220),
        ]
        for child_id, loc_type, r in child_defs:
            x, y = self._rand_pos(r, r + 40)
            self.locations.append({
                "id": "%s_%d" % (loc_type, len(self.locations)), "type": loc_type, "x": x, "y": y,
                "discovered": False, "child": child_id, "guard": "bears" if child_id != "dino_kid" else "wolves",
            })
        others = [
            ("cabin", 5), ("house", 4), ("grocery_store", 2), ("clinic", 2),
            ("mechanical_building", 3), ("warehouse", 2), ("campsite", 6), ("ruins", 4),
            ("cave", 5), ("cultist_outpost", 3),
        ]
        for loc_type, count in others:
            for _ in range(count):
                x, y = self._rand_pos(70, half - 30)
                self.locations.append({"id": "%s_%d" % (loc_type, len(self.locations)),
                                       "type": loc_type, "x": x, "y": y, "discovered": False})
        for i in range(14):
            x, y = self._rand_pos(60, half - 40)
            self.locations.append({"id": "chest_%d" % i, "type": "chest", "x": x, "y": y, "discovered": False})
        for i in range(4):
            x, y = self._rand_pos(150, half - 40)
            self.locations.append({"id": "gem_shrine_%d" % i, "type": "ruins", "x": x, "y": y,
                                   "discovered": False, "gem_fragment": True})
        self._generate_trees()

    def _generate_trees(self):
        half = self.size // 2
        step = 8
        for x in range(-half, half, step):
            for y in range(-half, half, step):
                jx, jy = x + self.rng.randint(-3, 3), y + self.rng.randint(-3, 3)
                d = math.sqrt(jx * jx + jy * jy)
                if d < 14:
                    continue
                biome = BIOMES[self.biome_at(jx, jy)]
                chance = 0.24 * biome["density"]
                if self.rng.random() > chance:
                    continue
                tree_type = self.rng.choice(biome["trees"])
                if tree_type == "big" and self.rng.random() > 0.25:
                    tree_type = "normal"
                if tree_type == "ancient" and self.rng.random() > 0.15:
                    tree_type = "normal"
                self.trees.append({"x": jx, "y": jy, "type": tree_type, "scale": self.rng.uniform(0.85, 1.3)})

    def to_dict(self):
        return {"seed": self.seed, "size": self.size,
                "locations": [{"id": l["id"], "discovered": l["discovered"]} for l in self.locations],
                "removed_trees": [t.get("id", i) for i, t in enumerate(self.trees) if t.get("removed")]}
