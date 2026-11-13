"""Loads all JSON configuration files from the config directory."""
import json
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")


def _load(name):
    with open(os.path.join(CONFIG_DIR, name), "r", encoding="utf-8") as f:
        return json.load(f)


class GameData:
    def __init__(self, config_dir=None):
        self.config_dir = config_dir or CONFIG_DIR
        self.items = self._load_file("items.json")
        self.recipes = self._load_file("recipes.json")
        self.classes = self._load_file("classes.json")
        self.loot_tables = self._load_file("loot_tables.json")
        self.progression = self._load_file("progression.json")
        self.settings = self._load_file("settings.json")

    def _load_file(self, name):
        with open(os.path.join(self.config_dir, name), "r", encoding="utf-8") as f:
            return json.load(f)

    def item(self, item_id):
        return self.items["items"][item_id]

    def item_name(self, item_id):
        return self.item(item_id).get("name", item_id)

    def has_item(self, item_id):
        return item_id in self.items["items"]

    def rarity_colour(self, rarity):
        return self.items["rarities"].get(rarity, "#ffffff")

    def class_data(self, class_id):
        return self.classes["classes"][class_id]

    def structure_def(self, struct_id):
        return self.recipes["structure_items"].get(struct_id, {"name": struct_id, "description": ""})

    def fuel_value(self, item_id):
        return self.progression["fuel_values"].get(item_id, {}).get("value", 0.0)

    def tree_def(self, tree_type):
        return self.progression["trees"][tree_type]

    def tool_def(self, tool_id):
        return self.progression["tools"].get(tool_id)

    def crop_def(self, crop_id):
        return self.progression["farming"]["crops"][crop_id]

    def grinder_output(self, item_id):
        entry = self.progression["grinder"]["recipes"].get(item_id)
        if entry:
            return entry["output"], entry["amount"]
        return None, 0

    def campfire_level_def(self, level):
        return self.progression["campfire"]["levels"][str(level)]


def load_gamedata(config_dir=None):
    return GameData(config_dir)
