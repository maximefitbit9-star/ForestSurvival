"""Seeded loot generation and tree harvest logic."""
import random


class LootRoller:
    def __init__(self, gamedata, loot_tables, rng):
        self.gd = gamedata
        self.loot_tables = loot_tables
        self.rng = rng

    def roll_location(self, location_type, loot_bonus=0.0):
        """Returns a dict of item_id -> quantity for a discovered location."""
        table = self.loot_tables["locations"].get(location_type)
        if table is None:
            return {}
        lo, hi = table["rolls"]
        rolls = self.rng.randint(lo, hi) + (1 if loot_bonus >= 0.5 and self.rng.random() < loot_bonus else 0)
        loot = {}
        entries = list(table["loot"].items())
        total_weight = sum(w for _, w in entries)
        for _ in range(rolls):
            pick = self.rng.uniform(0, total_weight)
            acc = 0.0
            for item_id, weight in entries:
                acc += weight
                if pick <= acc:
                    qty = self.rng.randint(1, 3)
                    if self.gd.has_item(item_id) and self.gd.item(item_id).get("stack", 1) == 1:
                        qty = 1
                    loot[item_id] = loot.get(item_id, 0) + qty
                    break
        return loot


class TreeHarvest:
    """Progressive tree damage: trees accumulate visible damage before falling."""

    def __init__(self, gamedata, tree_type, rng):
        self.gd = gamedata
        self.tree_type = tree_type
        self.rng = rng
        self.defn = gamedata.tree_def(tree_type)
        self.max_hp = max(1, self.defn["hits"])
        self.hp = self.max_hp
        self.fallen = False
        self.fall_direction = rng.uniform(0, 360)

    @property
    def damage_fraction(self):
        return 1.0 - (self.hp / self.max_hp)

    def min_tool_ok(self, tool_id):
        tool = self.gd.tool_def(tool_id)
        if tool is None:
            return False
        order = ["old_axe", "good_axe", "strong_axe", "ice_axe", "chainsaw"]
        min_tool = self.defn.get("min_tool", "old_axe")
        return order.index(tool_id) >= order.index(min_tool)

    def hits_with(self, tool_id):
        """How many hits of this tool are needed in total (progressive damage per hit)."""
        tool = self.gd.tool_def(tool_id)
        if tool is None:
            return None
        if not self.min_tool_ok(tool_id):
            return None
        if self.tree_type == "big":
            return tool["hits_big_tree"]
        if self.tree_type == "small":
            return max(1, tool["hits_normal_tree"] // 2)
        return tool["hits_normal_tree"]

    def hit(self, tool_id, damage_bonus=0.0, wood_bonus=0):
        """Applies one hit. Returns a result dict: fell, damage, drops."""
        if self.fallen:
            return {"fell": False, "damage": 0.0, "drops": {}}
        total_hits = self.hits_with(tool_id)
        if total_hits is None:
            return {"fell": False, "damage": 0.0, "drops": {}, "blocked": True}
        per_hit = self.max_hp / max(1, total_hits)
        self.hp -= per_hit
        self.damage = self.damage_fraction
        if self.hp <= 0:
            self.fallen = True
            lo, hi = self.defn["saplings"]
            drops = {
                "log": self.defn["logs"] + wood_bonus,
                "sapling": self.rng.randint(lo, hi),
            }
            return {"fell": True, "damage": 1.0, "drops": drops, "direction": self.fall_direction}
        return {"fell": False, "damage": self.damage_fraction, "drops": {}}
