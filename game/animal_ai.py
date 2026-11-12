"""Wildlife AI: idle, wander, flee, and day/night behaviour differences."""
import math
import random

SPECIES = {
    "bunny": {"speed": 3.0, "flee_radius": 6, "active": "day", "drops": {"bunny_foot": 0.3, "pelt": 0.4}},
    "deer": {"speed": 4.0, "flee_radius": 10, "active": "day", "drops": {"pelt": 0.8, "raw_meat": 1}},
    "wolf": {"speed": 6.5, "flee_radius": 0, "active": "any", "drops": {"wolf_pelt": 0.9, "raw_meat": 1}},
    "bear": {"speed": 5.0, "flee_radius": 0, "active": "any", "drops": {"pelt": 1.0, "raw_meat": 2}},
    "bird": {"speed": 5.0, "flee_radius": 8, "active": "day", "drops": {}},
}


class Animal:
    def __init__(self, animal_id, species, x, y):
        self.id = animal_id
        self.species = species
        self.x = x
        self.y = y
        self.state = "idle"
        self.state_timer = random.uniform(1, 4)
        self.target_x, self.target_y = x, y
        self.hp = 30 if species in ("wolf", "bear") else 10


class AnimalAI:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.animals = []
        self._next_id = 0

    def spawn(self, species, x, y):
        animal = Animal("%s_%d" % (species, self._next_id), species, x, y)
        self._next_id += 1
        self.animals.append(animal)
        return animal

    def populate_near(self, player_x, player_y, radius, biome, count=6):
        """Spawns a mix of ambient wildlife around a position (guards excluded)."""
        for _ in range(count):
            ang = self.rng.uniform(0, 2 * math.pi)
            d = self.rng.uniform(15, radius)
            x, y = player_x + math.cos(ang) * d, player_y + math.sin(ang) * d
            species = self.rng.choice(["bunny", "bunny", "deer", "bird"])
            self.spawn(species, x, y)

    def update(self, dt, player_pos, is_night):
        events = []
        for a in self.animals:
            spec = SPECIES[a.species]
            if spec["active"] == "day" and is_night and a.species != "wolf":
                a.state = "sleep"
                continue
            dist = math.hypot(player_pos[0] - a.x, player_pos[1] - a.y)
            flee_r = spec["flee_radius"]
            if flee_r and dist < flee_r and a.state != "flee":
                a.state = "flee"
                a.state_timer = 2.0
                ang = math.atan2(a.y - player_pos[1], a.x - player_pos[0])
                a.target_x = a.x + math.cos(ang) * 25
                a.target_y = a.y + math.sin(ang) * 25
                events.append({"type": "flee", "species": a.species})
            if a.state == "flee":
                a.state_timer -= dt
                self._move(a, dt, 1.5)
                if a.state_timer <= 0:
                    a.state = "idle"
                    a.state_timer = self.rng.uniform(1, 3)
            elif a.state == "walk":
                a.state_timer -= dt
                self._move(a, dt, 0.6)
                if a.state_timer <= 0 or math.hypot(a.target_x - a.x, a.target_y - a.y) < 1:
                    a.state = "idle"
                    a.state_timer = self.rng.uniform(1, 5)
            else:
                a.state_timer -= dt
                if a.state_timer <= 0:
                    a.state = "walk"
                    a.state_timer = self.rng.uniform(2, 5)
                    a.target_x = a.x + self.rng.uniform(-15, 15)
                    a.target_y = a.y + self.rng.uniform(-15, 15)
        return events

    def _move(self, animal, dt, speed_scale):
        spec = SPECIES[animal.species]
        dx, dy = animal.target_x - animal.x, animal.target_y - animal.y
        d = math.hypot(dx, dy)
        if d < 0.05:
            return
        step = spec["speed"] * speed_scale * dt
        animal.x += dx / d * step
        animal.y += dy / d * step

    def kill(self, animal):
        """Removes an animal and returns its drops (quantity dict)."""
        if animal not in self.animals:
            return {}
        self.animals.remove(animal)
        drops = {}
        for item_id, qty in SPECIES[animal.species]["drops"].items():
            if self.rng.random() < 0.9:
                drops[item_id] = max(1, int(qty))
        return drops
