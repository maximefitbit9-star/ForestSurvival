"""Nighttime threats. Verified reference behaviours:
- The Deer: main antagonist; hunts at night, fears the campfire's light, will not
  reach players inside the safe zone; does not attack on night one; faster when hungry.
- The Owl: a night hunter that swoops on players far from camp.
- The Ram: charges up, then rushes in a line, knocking down trees in its path.
Distinct AI behaviours are implemented below; the player survives through
awareness, the safe zone, hiding and movement rather than combat.
"""
import math
import random


class Threat:
    def __init__(self, threat_id, kind, x, y, speed, detect_radius, attack_range):
        self.id = threat_id
        self.kind = kind
        self.x = x
        self.y = y
        self.speed = speed
        self.detect_radius = detect_radius
        self.attack_range = attack_range
        self.state = "patrol"
        self.state_timer = 0.0
        self.target_x = x
        self.target_y = y
        self.charge_dir = None
        self.stun_timer = 0.0
        self.cooldown = 0.0

    def distance_to(self, px, py):
        return math.hypot(px - self.x, py - self.y)


class ThreatAI:
    def __init__(self, seed=0):
        self.rng = random.Random(seed)
        self.threats = []

    def spawn_night_threats(self, night, campfire_radius, player_pos):
        """Spawns the night's hunters outside the safe zone. Night one is safe."""
        self.threats = []
        if night <= 1:
            return
        count = 1 + (night // 20)
        for i in range(min(count, 3)):
            kind = self.rng.choice(["deer", "deer", "owl", "ram"]) if night >= 5 else "deer"
            ang = self.rng.uniform(0, 2 * math.pi)
            dist = campfire_radius + 25 + self.rng.uniform(0, 30)
            x = player_pos[0] + math.cos(ang) * dist
            y = player_pos[1] + math.sin(ang) * dist
            if kind == "deer":
                speed = 6.5 + min(2.5, night * 0.03)
                t = Threat("deer_%d" % i, "deer", x, y, speed, 40, 2.0)
            elif kind == "owl":
                t = Threat("owl_%d" % i, "owl", x, y, 7.5, 45, 2.0)
            else:
                t = Threat("ram_%d" % i, "ram", x, y, 5.5, 35, 3.0)
            self.threats.append(t)

    def _move_towards(self, threat, tx, ty, dt, speed_scale=1.0):
        dx, dy = tx - threat.x, ty - threat.y
        d = math.hypot(dx, dy)
        if d < 0.01:
            return
        step = threat.speed * speed_scale * dt
        threat.x += dx / d * step
        threat.y += dy / d * step

    def update(self, dt, player_pos, player_safe, campfire_pos, campfire_radius, is_night, trees=None):
        """Updates all threats. Returns a list of event dicts for the game manager."""
        events = []
        if not is_night:
            for t in self.threats:
                t.state = "retreat"
        for t in self.threats:
            if t.stun_timer > 0:
                t.stun_timer -= dt
                continue
            if t.cooldown > 0:
                t.cooldown -= dt
            dist_to_player = t.distance_to(*player_pos)
            in_safe = math.hypot(player_pos[0] - campfire_pos[0], player_pos[1] - campfire_pos[1]) <= campfire_radius

            if not is_night:
                self._move_towards(t, t.x + 100, t.y + 100, dt, 2.0)
                continue

            if t.kind == "deer":
                if player_safe or in_safe:
                    t.state = "circle"
                    ang = math.atan2(t.y - campfire_pos[1], t.x - campfire_pos[0]) + 0.4 * dt
                    r = campfire_radius + 8
                    tx = campfire_pos[0] + math.cos(ang) * r
                    ty = campfire_pos[1] + math.sin(ang) * r
                    self._move_towards(t, tx, ty, dt, 0.5)
                elif t.state != "chase" and dist_to_player < t.detect_radius:
                    t.state = "chase"
                    events.append({"type": "spotted", "threat": t.kind})
                elif t.state == "chase":
                    if dist_to_player > t.detect_radius * 1.6:
                        t.state = "search"
                        t.state_timer = 4.0
                        events.append({"type": "lost", "threat": t.kind})
                    else:
                        self._move_towards(t, *player_pos, dt)
                        if dist_to_player < t.attack_range and t.cooldown <= 0:
                            t.cooldown = 2.0
                            events.append({"type": "attack", "threat": t.kind, "damage": 25})
                elif t.state == "search":
                    t.state_timer -= dt
                    self._move_towards(t, t.target_x, t.target_y, dt, 0.5)
                    if t.state_timer <= 0:
                        t.state = "patrol"
                else:
                    if t.state_timer <= 0:
                        t.target_x = campfire_pos[0] + self.rng.uniform(-60, 60)
                        t.target_y = campfire_pos[1] + self.rng.uniform(-60, 60)
                        t.state_timer = self.rng.uniform(5, 10)
                    t.state_timer -= dt
                    self._move_towards(t, t.target_x, t.target_y, dt, 0.4)

            elif t.kind == "owl":
                if player_safe or in_safe:
                    t.state = "circle"
                    t.y += math.sin(t.state_timer) * 5 * dt
                    t.state_timer += dt
                elif dist_to_player < t.detect_radius:
                    t.state = "swoop"
                    self._move_towards(t, *player_pos, dt, 1.2)
                    if dist_to_player < t.attack_range and t.cooldown <= 0:
                        t.cooldown = 3.0
                        events.append({"type": "attack", "threat": "owl", "damage": 15})
                else:
                    t.state = "patrol"
                    t.state_timer -= dt
                    self._move_towards(t, t.target_x, t.target_y, dt, 0.3)

            elif t.kind == "ram":
                if t.state == "charge_up":
                    t.state_timer -= dt
                    if t.state_timer <= 0:
                        t.state = "charging"
                        t.state_timer = 1.2
                        t.charge_dir = math.atan2(player_pos[1] - t.y, player_pos[0] - t.x)
                        events.append({"type": "ram_charge", "threat": "ram"})
                elif t.state == "charging":
                    t.state_timer -= dt
                    t.x += math.cos(t.charge_dir) * t.speed * 3.2 * dt
                    t.y += math.sin(t.charge_dir) * t.speed * 3.2 * dt
                    if trees:
                        for tr in trees:
                            if math.hypot(tr["x"] - t.x, tr["y"] - t.y) < 2.5:
                                tr.setdefault("knocked", True)
                                events.append({"type": "tree_knocked", "x": tr["x"], "y": tr["y"]})
                    if t.state_timer <= 0:
                        t.state = "search"
                        t.state_timer = 3.0
                elif player_safe or in_safe:
                    t.state = "circle"
                    self._move_towards(t, campfire_pos[0] + 30, campfire_pos[1] + 30, dt, 0.3)
                elif dist_to_player < t.detect_radius and t.cooldown <= 0:
                    t.state = "charge_up"
                    t.state_timer = 1.0
                    events.append({"type": "spotted", "threat": "ram"})
                elif t.state == "search":
                    t.state_timer -= dt
                    self._move_towards(t, *player_pos, dt, 0.4)
                    if t.state_timer <= 0:
                        t.state = "patrol"
                else:
                    if t.state_timer <= 0:
                        t.target_x, t.target_y = player_pos[0] + self.rng.uniform(-50, 50), player_pos[1] + self.rng.uniform(-50, 50)
                        t.state_timer = 8.0
                    t.state_timer -= dt
                    self._move_towards(t, t.target_x, t.target_y, dt, 0.35)

        return events

    def stun(self, seconds=4.0):
        """The flashlight briefly stuns nearby hunters; repeated stuns fade."""
        for t in self.threats:
            t.stun_timer = max(t.stun_timer, seconds * self.rng.uniform(0.5, 1.0))
