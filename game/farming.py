"""Farming logic: plots, planting, growth affected by weather, harvesting."""
import random


class FarmPlot:
    def __init__(self, gamedata, plot_id, x, y):
        self.gd = gamedata
        self.id = plot_id
        self.x = x
        self.y = y
        self.crop = None
        self.growth = 0.0
        self.watered = False

    def plant(self, seeds_item_id):
        crop = self.gd.item(seeds_item_id).get("crop")
        if self.crop is not None or crop is None:
            return False
        self.crop = crop
        self.growth = 0.0
        return True

    def is_grown(self):
        return self.crop is not None and self.growth >= 1.0

    def tick(self, dt_days, rain=False):
        """dt_days: fraction of a day elapsed. Rain speeds growth."""
        if self.crop is None or self.is_grown():
            return
        grow_days = self.gd.crop_def(self.crop)["grow_days"]
        speed = 1.0
        if rain:
            speed += self.gd.progression["farming"]["rain_growth_bonus"]
        self.growth = min(1.0, self.growth + (dt_days / grow_days) * speed)

    def harvest(self, rng):
        """Returns (crop_id, quantity, seeds_item_id, seed_qty)."""
        if not self.is_grown():
            return None, 0, None, 0
        crop = self.crop
        self.crop = None
        self.growth = 0.0
        cdef = self.gd.crop_def(crop)
        qty = rng.randint(*cdef["yield"])
        seeds = "%s_seeds" % crop
        seed_qty = 1 if rng.random() < cdef["seed_drop_chance"] else 0
        return crop, qty, seeds, seed_qty

    def to_dict(self):
        return {"crop": self.crop, "growth": round(self.growth, 3), "x": self.x, "y": self.y}

    def from_dict(self, data):
        self.crop = data.get("crop")
        self.growth = float(data.get("growth", 0.0))


class FarmManager:
    def __init__(self, gamedata):
        self.gd = gamedata
        self.plots = {}

    def add_plot(self, x, y):
        plot_id = "plot_%d" % len(self.plots)
        plot = FarmPlot(self.gd, plot_id, x, y)
        self.plots[plot_id] = plot
        return plot

    def tick(self, dt_days, rain=False):
        for plot in self.plots.values():
            plot.tick(dt_days, rain)

    def to_dict(self):
        return [p.to_dict() for p in self.plots.values()]

    def from_dict(self, data):
        self.plots = {}
        for entry in data:
            plot = FarmPlot(self.gd, entry.get("id", "plot"), entry["x"], entry["y"])
            plot.from_dict(entry)
            self.plots[plot.id] = plot
