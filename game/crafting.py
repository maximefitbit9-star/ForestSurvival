"""Crafting bench logic: tiers, upgrades, recipes and the Grinder."""
from collections import OrderedDict


class CraftingBench:
    def __init__(self, gamedata, inventory):
        self.gd = gamedata
        self.inventory = inventory
        self.level = 1
        self.max_level = len(self.gd.recipes["bench_levels"])

    def recipes_for_level(self, level=None):
        level = level or self.level
        return OrderedDict(self.gd.recipes["bench_levels"][str(level)]["recipes"])

    def all_known_recipes(self):
        known = OrderedDict()
        for lvl in range(1, self.level + 1):
            known.update(self.recipes_for_level(lvl))
        return known

    def next_upgrade_id(self):
        if self.level >= self.max_level:
            return None
        return "bench_upgrade_%d" % (self.level + 1)

    def next_upgrade_cost(self):
        nxt = self.next_upgrade_id()
        if nxt is None:
            return None
        return self.recipes_for_level()[nxt]["cost"]

    def can_upgrade(self, discount=0.0):
        nxt = self.next_upgrade_id()
        if nxt is None:
            return False
        cost = self.scaled_cost(self.recipes_for_level()[nxt]["cost"], discount)
        return self.inventory.has(cost)

    def upgrade(self, discount=0.0):
        if not self.can_upgrade(discount):
            return False
        cost = self.scaled_cost(self.recipes_for_level()[self.next_upgrade_id()]["cost"], discount)
        self.inventory.consume(cost)
        self.level += 1
        return True

    def scaled_cost(self, cost, discount):
        if discount <= 0:
            return cost
        return {i: max(1, int(round(q * (1 - discount)))) for i, q in cost.items()}

    def missing_materials(self, recipe_id, discount=0.0):
        recipe = self.all_known_recipes().get(recipe_id)
        if recipe is None:
            return {}
        cost = self.scaled_cost(recipe["cost"], discount)
        return {i: q - self.inventory.count(i) for i, q in cost.items() if self.inventory.count(i) < q}

    def can_craft(self, recipe_id, discount=0.0):
        recipe = self.all_known_recipes().get(recipe_id)
        if recipe is None:
            return False
        return self.inventory.has(self.scaled_cost(recipe["cost"], discount))

    def craft(self, recipe_id, discount=0.0):
        """Crafts the recipe, consuming materials. Returns (success, result_id)."""
        recipe = self.all_known_recipes().get(recipe_id)
        if recipe is None or recipe_id == self.next_upgrade_id():
            return False, None
        cost = self.scaled_cost(recipe["cost"], discount)
        if not self.inventory.consume(cost):
            return False, None
        return True, recipe_id


class Grinder:
    def __init__(self, gamedata, inventory):
        self.gd = gamedata
        self.inventory = inventory

    def can_process(self, item_id):
        return self.gd.grinder_output(item_id)[0] is not None

    def process(self, item_id, quantity=1, bonus=0.0):
        """Grinds items into their output material. Returns (output_id, amount) or (None, 0)."""
        out_id, per_item = self.gd.grinder_output(item_id)
        if out_id is None:
            return None, 0
        have = self.inventory.count(item_id)
        qty = min(quantity, have)
        if qty <= 0:
            return None, 0
        self.inventory.remove(item_id, qty)
        amount = int(qty * per_item * (1 + bonus))
        amount = max(1, amount)
        added = self.inventory.add(out_id, amount)
        return out_id, added
