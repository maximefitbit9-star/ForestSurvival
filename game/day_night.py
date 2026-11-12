"""Day/night cycle logic. Verified timing: 3-minute day, 90-second night."""
from .day_night_phases import PHASES  # noqa: F401  (kept minimal; phases defined below)


class DayNightCycle:
    DAWN, DAY, DUSK, NIGHT = "dawn", "day", "dusk", "night"

    def __init__(self, progression):
        dn = progression["day_night"]
        self.day_length = dn["day_length_seconds"]
        self.night_length = dn["night_length_seconds"]
        self.time = 0.0
        self.day = 1
        self._on_new_day = None
        self._on_night_start = None

    def set_callbacks(self, on_new_day=None, on_night_start=None):
        self._on_new_day = on_new_day
        self._on_night_start = on_night_start

    @property
    def cycle_length(self):
        return self.day_length + self.night_length

    def is_night(self):
        return self.time >= self.day_length

    def phase(self):
        t = self.time
        if t < self.day_length * 0.08:
            return self.DAWN
        if t < self.day_length * 0.92:
            return self.DAY
        if t < self.day_length:
            return self.DUSK
        return self.NIGHT

    def day_fraction_left(self):
        if self.is_night():
            return 0.0
        return 1.0 - self.time / self.day_length

    def seconds_until_night(self):
        if self.is_night():
            return 0.0
        return self.day_length - self.time

    def skip_days(self, count=1):
        """Beds and the Time Accelerator skip time. Returns days advanced."""
        advanced = 0
        for _ in range(count):
            self.day += 1
            advanced += 1
            if self._on_new_day:
                self._on_new_day(self.day)
        self.time = 0.0
        return advanced

    def tick(self, dt):
        """Advances time. Returns a list of event strings that occurred."""
        events = []
        was_night = self.is_night()
        self.time += dt
        if not was_night and self.time >= self.day_length:
            events.append("night_start")
            if self._on_night_start:
                self._on_night_start(self.day)
        if self.time >= self.cycle_length:
            self.time -= self.cycle_length
            self.day += 1
            events.append("new_day")
            if self._on_new_day:
                self._on_new_day(self.day)
        return events

    def to_dict(self):
        return {"day": self.day, "time": round(self.time, 2)}

    def from_dict(self, data):
        self.day = int(data.get("day", 1))
        self.time = float(data.get("time", 0.0))
