"""Weather system: clear, rain, fog, storm, snow. Affects fuel burn and crops."""
import random

WEATHERS = {
    "clear": {"name": "Clear", "fuel_multiplier": 1.0, "visibility": 1.0},
    "rain": {"name": "Rain", "fuel_multiplier": 1.6, "visibility": 0.75},
    "fog": {"name": "Fog", "fuel_multiplier": 1.1, "visibility": 0.4},
    "storm": {"name": "Storm", "fuel_multiplier": 2.2, "visibility": 0.6},
    "snow": {"name": "Snow", "fuel_multiplier": 1.4, "visibility": 0.55},
}


class WeatherSystem:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.current = "clear"
        self.time_left = 120.0
        self.frozen_days = 0

    def _pick(self, biome):
        roll = self.rng.random()
        if biome == "snowy":
            return "snow" if roll < 0.6 else ("fog" if roll < 0.8 else "clear")
        if roll < 0.55:
            return "clear"
        if roll < 0.75:
            return "rain"
        if roll < 0.88:
            return "fog"
        return "storm"

    def set_weather(self, weather, duration):
        if weather in WEATHERS:
            self.current = weather
            self.time_left = duration

    def freeze(self, days=3):
        """Weather Machine: stops rain and storms for several days."""
        self.frozen_days = days
        self.set_weather("clear", days * 300)

    def tick(self, dt, biome="forest"):
        if self.frozen_days > 0 and self.current in ("rain", "storm"):
            self.current = "clear"
        if self.time_left > 0:
            self.time_left -= dt
            if self.time_left > 0:
                return False
        duration = self.rng.uniform(90, 240)
        self.current = self._pick(biome)
        self.time_left = duration
        return True

    def on_new_day(self):
        if self.frozen_days > 0:
            self.frozen_days -= 1

    @property
    def fuel_multiplier(self):
        return WEATHERS[self.current]["fuel_multiplier"]

    @property
    def visibility(self):
        return WEATHERS[self.current]["visibility"]

    @property
    def is_wet(self):
        return self.current in ("rain", "storm")

    def to_dict(self):
        return {"current": self.current, "time_left": round(self.time_left, 1), "frozen_days": self.frozen_days}

    def from_dict(self, data):
        self.current = data.get("current", "clear")
        self.time_left = float(data.get("time_left", 120))
        self.frozen_days = int(data.get("frozen_days", 0))
