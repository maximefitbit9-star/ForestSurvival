"""Procedurally generated original textures (no external assets, fully offline)."""
import math
import os
import random

from panda3d.core import PNMImage, Filename

TEX_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "textures", "generated")


def _valid_png(path):
    if not os.path.exists(path):
        return False
    img = PNMImage()
    return img.read(Filename.from_os_specific(path))


def _noise_tex(name, size, base, variation, seed=1, blotches=12):
    path = os.path.join(TEX_DIR, name)
    if _valid_png(path):
        return path
    rng = random.Random(seed)
    img = PNMImage(size, size)
    br, bg, bb = base
    for x in range(size):
        for y in range(size):
            n = rng.uniform(-variation, variation)
            r = max(0, min(255, int((br + n) * 255)))
            g = max(0, min(255, int((bg + n) * 255)))
            b = max(0, min(255, int((bb + n) * 255)))
            img.set_xel(x, y, r / 255.0, g / 255.0, b / 255.0)
    for _ in range(blotches):
        cx, cy = rng.randint(0, size - 1), rng.randint(0, size - 1)
        rad = rng.randint(size // 12, size // 5)
        shade = rng.uniform(-0.08, 0.08)
        for x in range(max(0, cx - rad), min(size, cx + rad)):
            for y in range(max(0, cy - rad), min(size, cy + rad)):
                d = math.hypot(x - cx, y - cy)
                if d <= rad:
                    c = img.get_xel(x, y)
                    f = 1 - (d / rad) * 0.6
                    img.set_xel(x, y, max(0.0, c[0] + shade * f),
                                max(0.0, c[1] + shade * f),
                                max(0.0, c[2] + shade * f))
    if not img.write(Filename.from_os_specific(path)):
        raise IOError("Could not write generated texture: %s" % path)
    return path


def ensure_all_textures():
    os.makedirs(TEX_DIR, exist_ok=True)
    tex = {}
    tex["grass"] = _noise_tex("grass.png", 128, (0.30, 0.48, 0.20), 0.05, seed=11, blotches=20)
    tex["dirt"] = _noise_tex("dirt.png", 128, (0.38, 0.30, 0.20), 0.05, seed=12, blotches=18)
    tex["snow"] = _noise_tex("snow.png", 128, (0.88, 0.90, 0.94), 0.03, seed=13, blotches=10)
    tex["magical"] = _noise_tex("magical.png", 128, (0.24, 0.34, 0.30), 0.07, seed=14, blotches=25)
    tex["bark"] = _noise_tex("bark.png", 64, (0.30, 0.22, 0.14), 0.06, seed=15, blotches=8)
    return tex
