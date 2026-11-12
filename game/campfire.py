"""Campfire logic: fuel, levels, safe area and warnings."""


class Campfire:
    def __init__(self, gamedata):
        self.gd = gamedata
        prog = self.gd.progression["campfire"]
        self.max_level = prog["max_level"]
        self.thresholds = prog["level_up_thresholds"]
        self.level = 1
        self.fuel = 50.0
        self.total_fuel_burned_towards_level = 50.0
        self.lit = True

    def _level_def(self, level=None):
        return self.gd.campfire_level_def(level or self.level)

    @property
    def capacity(self):
        return self._level_def()["fuel_capacity"]

    @property
    def safe_radius(self):
        return self._level_def()["safe_radius"]

    @property
    def unlock_radius(self):
        return self._level_def()["unlock_radius"]

    def fuel_fraction(self):
        return max(0.0, min(1.0, self.fuel / self.capacity))

    def add_fuel(self, item_id, quantity=1):
        """Adds a burnable item. Returns the fuel added (0 if the item is not fuel)."""
        value = self.gd.fuel_value(item_id)
        if value <= 0:
            return 0.0
        amount = value * quantity
        self.fuel = min(self.capacity, self.fuel + amount)
        self.total_fuel_burned_towards_level += amount
        self.lit = True
        self._check_level_up()
        return amount

    def _check_level_up(self):
        while self.level < self.max_level and self.total_fuel_burned_towards_level >= self.thresholds[self.level - 1]:
            self.level += 1

    def tick(self, dt, is_night, weather_multiplier=1.0):
        """Consumes fuel over time. Returns a state dict for the view/HUD."""
        if not self.lit:
            return {"event": "out"}
        prog = self.gd.progression["campfire"]
        level_defs = prog["levels"]
        ld = level_defs[str(self.level)]
        rate = ld["burn_rate_night"] if is_night else ld["burn_rate_day"]
        rate *= 1.0 - ld["weather_resistance"] * (weather_multiplier - 1.0) if weather_multiplier > 1 else rate
        self.fuel -= rate * dt
        self.total_fuel_burned_towards_level = max(self.total_fuel_burned_towards_level - rate * dt, 0.0)
        if self.fuel <= 0:
            self.fuel = 0
            self.lit = False
            return {"event": "out"}
        frac = self.fuel_fraction()
        if frac < 0.15:
            return {"event": "critical", "fraction": frac}
        if frac < 0.35:
            return {"event": "low", "fraction": frac}
        return {"event": "ok", "fraction": frac}

    def in_safe_zone(self, distance):
        return self.lit and distance <= self.safe_radius

    def to_dict(self):
        return {"level": self.level, "fuel": round(self.fuel, 2),
                "progress": round(self.total_fuel_burned_towards_level, 2), "lit": self.lit}

    def from_dict(self, data):
        self.level = int(data.get("level", 1))
        self.fuel = float(data.get("fuel", 50.0))
        self.total_fuel_burned_towards_level = float(data.get("progress", self.fuel))
        self.lit = bool(data.get("lit", True))
