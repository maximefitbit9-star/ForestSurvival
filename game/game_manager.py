"""Central game-state orchestrator. Engine-agnostic: the Panda3D layer calls into this."""
import random

from .inventory import Inventory
from .crafting import CraftingBench, Grinder
from .campfire import Campfire
from .day_night import DayNightCycle
from .weather import WeatherSystem
from .farming import FarmManager
from .resource_system import LootRoller, TreeHarvest
from .worldgen import WorldGen, SeededRNG
from .npc_manager import NPCManager
from .animal_ai import AnimalAI
from .threat_ai import ThreatAI
from .player import PlayerState
from .class_system import ClassSystem
from .diamonds import compute_diamonds


class GameManager:
    def __init__(self, gamedata, seed=None, class_id="camper", profile=None):
        self.gd = gamedata
        self.profile = profile or {"diamonds": 0, "owned_classes": ["camper"]}
        self.class_system = ClassSystem(gamedata, self.profile)
        if class_id not in self.class_system.all_classes():
            class_id = "camper"
        self.class_id = class_id
        passives = self.class_system.passives(class_id)

        self.seed = seed if seed not in (None, "") else random.randint(0, 999999)
        self.rng = SeededRNG(self.seed)
        seed_val = self.rng.seed_val
        self.world = WorldGen(self.seed, gamedata.settings["world"]["size"],
                              gamedata.settings["world"]["height_scale"])
        self.inventory = Inventory(gamedata, 24)
        self.bench = CraftingBench(gamedata, self.inventory)
        self.grinder = Grinder(gamedata, self.inventory)
        self.campfire = Campfire(gamedata)
        self.day_night = DayNightCycle(gamedata.progression)
        self.weather = WeatherSystem(self.seed)
        self.farming = FarmManager(gamedata)
        self.npcs = NPCManager()
        self.npcs.assign_caves(self.world.locations)
        self.animals = AnimalAI(seed_val + 1)
        self.threats = ThreatAI(seed_val + 2)
        self.loot_roller = LootRoller(gamedata, gamedata.loot_tables, self.rng)
        self.player = PlayerState(gamedata.settings, passives)

        self.structures = []
        self.discovered_locations = set()
        self.tree_states = {}
        self._next_structure_id = 0
        self.victory = False
        self.defeat = False
        self.finished = False
        self.run_stats = {"nights_survived": 0, "locations_discovered": 0, "trees_felled": 0}

        for item_id, qty in self.class_system.starting_items(class_id).items():
            self.inventory.add(item_id, qty)
        if not any(s.item_id == "old_axe" for s in self.inventory.slots):
            self.inventory.add("old_axe", 1)
        # Verified reference feature: a guaranteed coal pile and logs near the
        # starting campfire are enough to reach campfire level 2 on day one.
        self.inventory.add("log", 6)
        self.inventory.add("coal", 1)
        self.animals.populate_near(0, 0, 60, "forest", 8)

    # ------------------------------------------------------------------ time

    def tick(self, dt):
        """Advances the whole simulation. Returns a list of event dicts."""
        if self.finished:
            return []
        events = []
        dn_events = self.day_night.tick(dt)
        is_night = self.day_night.is_night()
        for ev in dn_events:
            if ev == "night_start":
                self.threats.spawn_night_threats(self.day_night.day, self.campfire.safe_radius,
                                                 (self.player.x, self.player.y))
                events.append({"type": "night_start", "night": self.day_night.day})
            elif ev == "new_day":
                self.weather.on_new_day()
                self.run_stats["nights_survived"] = self.day_night.day - 1
                self.animals.populate_near(self.player.x, self.player.y, 70, "forest", 4)
                events.append({"type": "new_day", "day": self.day_night.day})
                if self.day_night.day > 99:
                    self.victory = True
                    self._finish()
                    events.append({"type": "victory"})
        self.weather.tick(dt, self._biome_at_player())
        cf_event = self.campfire.tick(dt, is_night, self.weather.fuel_multiplier)
        if cf_event["event"] == "out":
            events.append({"type": "campfire_out"})
        elif cf_event["event"] == "critical":
            events.append({"type": "fuel_critical", "fraction": cf_event["fraction"]})
        elif cf_event["event"] == "low":
            events.append({"type": "fuel_low", "fraction": cf_event["fraction"]})

        player_safe = self.campfire.in_safe_zone(self._dist_to_campfire())
        warn = self.player.tick(dt, self.player.sprinting, player_safe, self.campfire.lit)
        for w in warn:
            events.append({"type": w})
        if not self.player.alive:
            self.defeat = True
            self._finish()
            events.append({"type": "defeat"})

        self.farming.tick(dt / self.day_night.cycle_length, self.weather.is_wet)
        self.npcs.update(dt, (0, 0), self.campfire.safe_radius)
        self.animals.update(dt, (self.player.x, self.player.y), is_night)
        threat_events = self.threats.update(dt, (self.player.x, self.player.y), player_safe,
                                            (0, 0), self.campfire.safe_radius, is_night)
        for te in threat_events:
            if te.get("type") == "attack":
                self.player.damage(te["damage"])
                if not self.player.alive:
                    self.defeat = True
                    self._finish()
                    events.append({"type": "defeat"})
            events.append(te)
        self._check_discoveries()
        return events

    def _finish(self):
        self.finished = True
        self.run_stats["nights_survived"] = max(0, self.day_night.day - 1)
        self.run_stats["locations_discovered"] = len(self.discovered_locations)
        self.earned_diamonds = compute_diamonds(
            self.gd.progression, self.run_stats["nights_survived"],
            self.npcs.rescued_count(), self.run_stats["locations_discovered"],
            self.campfire.level, self.victory)
        self.profile["diamonds"] += self.earned_diamonds
        self.profile["runs"] = self.profile.get("runs", 0) + 1
        self.profile["best_day"] = max(self.profile.get("best_day", 0), self.day_night.day)
        if self.victory:
            self.profile["wins"] = self.profile.get("wins", 0) + 1

    def _biome_at_player(self):
        return self.world.biome_at(int(self.player.x), int(self.player.y))

    def _dist_to_campfire(self):
        import math
        return math.hypot(self.player.x, self.player.y)

    def _check_discoveries(self):
        import math
        for loc in self.world.locations:
            if not loc.get("discovered"):
                if math.hypot(loc["x"] - self.player.x, loc["y"] - self.player.y) < 18:
                    loc["discovered"] = True
                    self.discovered_locations.add(loc["id"])
                    self.run_stats["locations_discovered"] = len(self.discovered_locations)

    # ------------------------------------------------------------- interactions

    def add_fuel(self, item_id, quantity=1):
        if not self.gd.fuel_value(item_id):
            return False
        if self.inventory.count(item_id) < quantity:
            return False
        self.inventory.remove(item_id, quantity)
        self.campfire.add_fuel(item_id, quantity)
        return True

    def chop_tree(self, tree_index, tool_id):
        """Hits a tree once. Returns the hit result plus whether it fell."""
        tree = self.world.trees[tree_index]
        if tree.get("removed"):
            return {"fell": False, "damage": 0.0, "drops": {}}
        key = str(tree_index)
        if key not in self.tree_states:
            self.tree_states[key] = TreeHarvest(self.gd, tree["type"], self.rng)
        harvest = self.tree_states[key]
        result = harvest.hit(tool_id, wood_bonus=self.player.wood_bonus)
        if result.get("fell"):
            tree["removed"] = True
            self.run_stats["trees_felled"] += 1
            for item_id, qty in result.get("drops", {}).items():
                self.inventory.add(item_id, qty)
        return result

    def interactor_loot(self, location_id):
        """Loots a discovered location once."""
        loc = next((l for l in self.world.locations if l["id"] == location_id), None)
        if loc is None or loc.get("looted") or not loc.get("discovered"):
            return {}
        loc["looted"] = True
        loot = self.loot_roller.roll_location(loc["type"], self.player.loot_bonus)
        for item_id, qty in loot.items():
            self.inventory.add(item_id, qty)
        return loot

    def rescue_child(self, child_id):
        if not self.npcs.can_rescue(child_id, self.campfire.level):
            return False
        if not self.npcs.rescue(child_id, self.campfire.level):
            return False
        self.day_night.day += 0
        return True

    def grind(self, item_id, quantity=1):
        return self.grinder.process(item_id, quantity, self.player.grind_bonus)

    def craft(self, recipe_id):
        ok, result = self.bench.craft(recipe_id, self.player.craft_discount)
        if not ok:
            return False, None
        recipe = self.bench.all_known_recipes()[recipe_id]
        if recipe["type"] == "bench_upgrade":
            self.bench.upgrade(self.player.craft_discount)
            return True, "bench"
        if recipe["type"] == "item" and recipe_id == "map":
            self.has_map = True
        return True, recipe_id

    def upgrade_bench(self):
        return self.bench.upgrade(self.player.craft_discount)

    def place_structure(self, structure_id, x, y, rotation=0):
        """Places a crafted structure. Collision checked against existing ones."""
        min_dist = 3.0
        for s in self.structures:
            if (s["id"] == structure_id and s.get("farm")) is True:
                pass
            if abs(s["x"] - x) < min_dist and abs(s["y"] - y) < min_dist:
                return None
        if self._dist(x, y) < 3.0:
            return None
        struct = {"id": self._next_structure_id, "type": structure_id, "x": x, "y": y,
                  "rotation": rotation, "day": self.day_night.day}
        self._next_structure_id += 1
        self.structures.append(struct)
        if self.gd.structure_def(structure_id).get("farm"):
            self.farming.add_plot(x, y)
        return struct

    def _dist(self, x, y):
        import math
        return math.hypot(x, y)

    def plant_crop(self, plot_id, seeds_item_id):
        plot = self.farming.plots.get(plot_id)
        if plot is None or self.inventory.count(seeds_item_id) < 1:
            return False
        if not plot.plant(seeds_item_id):
            return False
        self.inventory.remove(seeds_item_id, 1)
        return True

    def harvest_plot(self, plot_id):
        plot = self.farming.plots.get(plot_id)
        if plot is None:
            return {}
        crop, qty, seeds, seed_qty = plot.harvest(self.rng)
        if crop is None:
            return {}
        self.inventory.add(crop, qty)
        if seeds:
            self.inventory.add(seeds, seed_qty)
        return {"crop": crop, "qty": qty, "seeds": seeds, "seed_qty": seed_qty}

    def cook(self, recipe_id):
        cooking = self.gd.recipes["cooking"].get(recipe_id)
        if cooking is None or not self.inventory.consume(cooking["cost"]):
            return False
        self.inventory.add(recipe_id, 1 + (1 if self.player.food_bonus >= 0.5 else 0))
        return True

    def cook_on_fire(self):
        """Cook raw meat directly on the campfire."""
        if self.campfire.fuel <= 0 or not self.campfire.lit:
            return False
        if self.inventory.count("raw_meat") < 1:
            return False
        self.inventory.remove("raw_meat", 1)
        self.inventory.add("cooked_meat", 1)
        return True

    def use_bed(self, structure_type):
        days = self.gd.structure_def(structure_type).get("skip_days", 1)
        self.day_night.skip_days(days)
        return days

    def stun_threats(self):
        self.threats.stun()

    # ----------------------------------------------------------------- saving

    def to_dict(self):
        return {
            "seed": self.seed,
            "class": self.class_id,
            "day": self.day_night.day,
            "time": self.day_night.time,
            "player": self.player.to_dict(),
            "inventory": self.inventory.to_dict(),
            "bench_level": self.bench.level,
            "campfire": self.campfire.to_dict(),
            "weather": self.weather.to_dict(),
            "structures": self.structures,
            "next_structure_id": self._next_structure_id,
            "farm": self.farming.to_dict(),
            "children": self.npcs.to_dict(),
            "locations": [{"id": l["id"], "discovered": l["discovered"], "looted": l.get("looted", False)}
                         for l in self.world.locations],
            "removed_trees": [i for i, t in enumerate(self.world.trees) if t.get("removed")],
            "stats": self.run_stats,
        }

    def load_dict(self, data):
        self.class_id = data.get("class", "camper")
        passives = self.class_system.passives(self.class_id)
        self.player = PlayerState(self.gd.settings, passives)
        self.player.from_dict(data.get("player", {}))
        self.inventory.from_dict(data.get("inventory", []))
        self.bench.level = int(data.get("bench_level", 1))
        self.campfire.from_dict(data.get("campfire", {}))
        self.day_night.from_dict({"day": data.get("day", 1), "time": data.get("time", 0)})
        self.weather.from_dict(data.get("weather", {}))
        self.structures = data.get("structures", [])
        self._next_structure_id = int(data.get("next_structure_id", len(self.structures)))
        self.farming.from_dict(data.get("farm", []))
        self.npcs.from_dict(data.get("children", {}))
        for loc_save in data.get("locations", []):
            loc = next((l for l in self.world.locations if l["id"] == loc_save["id"]), None)
            if loc:
                loc["discovered"] = loc_save.get("discovered", False)
                if loc_save.get("looted"):
                    loc["looted"] = True
                if loc.get("discovered"):
                    self.discovered_locations.add(loc["id"])
        for idx in data.get("removed_trees", []):
            if 0 <= idx < len(self.world.trees):
                self.world.trees[idx]["removed"] = True
        self.run_stats = data.get("stats", self.run_stats)
