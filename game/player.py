"""Player survival stats and movement state (logic only; the renderer drives it)."""
import math


class PlayerState:
    def __init__(self, settings, passives=None):
        p = settings["player"]
        self.x = 0.0
        self.y = 0.0
        self.z = 0.0
        self.heading = 0.0
        self.max_health = p["max_health"] + (passives or {}).get("health_bonus", 0)
        self.max_hunger = p["max_hunger"]
        self.max_stamina = p["max_stamina"]
        self.health = self.max_health
        self.hunger = self.max_hunger
        self.stamina = self.max_stamina
        self.speed_bonus = (passives or {}).get("speed_bonus", 0)
        self.damage_bonus = (passives or {}).get("damage_bonus", 0)
        self.hunger_rate = p["hunger_rate"] * (passives or {}).get("hunger_rate", 1.0)
        self.health_regen = (passives or {}).get("health_regen", 0.0)
        self.wood_bonus = (passives or {}).get("wood_bonus", 0)
        self.loot_bonus = (passives or {}).get("loot_bonus", 0.0)
        self.food_bonus = (passives or {}).get("food_bonus", 0.0)
        self.grind_bonus = (passives or {}).get("grind_bonus", 0.0)
        self.craft_discount = (passives or {}).get("craft_discount", 0.0)
        self.alive = True
        self.moving = False
        self.sprinting = False
        self.crouching = False

    @property
    def walk_speed(self):
        return 6.0 + self.speed_bonus

    def heal(self, amount):
        self.health = min(self.max_health, self.health + amount)

    def eat(self, hunger, health=0, stamina=0):
        self.hunger = min(self.max_hunger, self.hunger + hunger)
        self.heal(health)
        self.stamina = min(self.max_stamina, self.stamina + stamina)

    def damage(self, amount):
        self.health = max(0, self.health - amount)
        if self.health <= 0:
            self.alive = False
        return not self.alive

    def respawn(self):
        self.health = self.max_health * 0.5
        self.hunger = max(30, self.hunger)
        self.alive = True

    def move(self, dx, dy, dt, speed=None):
        speed = speed if speed is not None else self.walk_speed
        dist = speed * dt
        d = math.hypot(dx, dy)
        if d > 0:
            self.x += dx / d * dist
            self.y += dy / d * dist
            self.heading = math.degrees(math.atan2(-dx, dy))
            self.moving = True
        else:
            self.moving = False

    def tick(self, dt, sprinting, in_safe_zone, campfire_lit):
        """Survival drain per second. Returns a list of warning events."""
        events = []
        if sprinting and self.stamina > 0:
            self.stamina = max(0, self.stamina - 12.0 * dt)
            self.sprinting = True
        else:
            self.sprinting = False
            self.stamina = min(self.max_stamina, self.stamina + 8.0 * dt)
        self.hunger = max(0, self.hunger - self.hunger_rate * dt)
        if self.hunger <= 0:
            self.damage(1.0 * dt)
            events.append("starving")
        elif self.hunger < 25:
            events.append("hungry")
        if in_safe_zone and campfire_lit:
            self.heal(0.5 * dt)
        if self.health_regen:
            self.heal(self.health_regen * dt)
        if self.health < 25:
            events.append("low_health")
        return events

    def to_dict(self):
        return {"x": self.x, "y": self.y, "z": self.z, "heading": self.heading,
                "health": self.health, "hunger": self.hunger, "stamina": self.stamina, "alive": self.alive}

    def from_dict(self, data):
        self.x = float(data.get("x", 0))
        self.y = float(data.get("y", 0))
        self.z = float(data.get("z", 0))
        self.heading = float(data.get("heading", 0))
        self.health = float(data.get("health", self.max_health))
        self.hunger = float(data.get("hunger", self.max_hunger))
        self.stamina = float(data.get("stamina", self.max_stamina))
        self.alive = bool(data.get("alive", True))
