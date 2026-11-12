"""The four missing children and rescued-child camp NPCs.

Verified reference details: four missing children (Dino, Squid, Kraken and
Koala Kid) are held in colour-coded caves guarded by wolves or bears; rescues
are gated behind campfire levels (Kraken Kid at level 5, Koala Kid at level 6);
after rescue they settle within the campfire radius. Personalities, dialogue
and backstories below are original writing.
"""
import math

CHILDREN = {
    "dino_kid": {
        "name": "Dino Kid", "colour": (0.85, 0.25, 0.20), "hat": "dino",
        "personality": "Boisterous and brave, even when shivering.",
        "backstory": "Wore his dinosaur costume on the school trip and got separated chasing a 'dragon' he swears he saw.",
        "rescue_requirement": 2, "guard": "wolves", "location_type": "red_cave",
        "dialogue": ["That dragon was THIS big, honest!", "Can I keep the axe? Please?", "I wasn't scared. Much."],
    },
    "squid_kid": {
        "name": "Squid Kid", "colour": (0.25, 0.45, 0.85), "hat": "squid",
        "personality": "Quiet, observant, draws maps on scraps of bark.",
        "backstory": "Lost while sketching the river bend; her squid hat was a gift from her brother, who is also out there somewhere.",
        "rescue_requirement": 3, "guard": "bears", "location_type": "blue_cave",
        "dialogue": ["I marked the way on this bark. See?", "The cave hummed at night. Did you hear it?", "Thank you. Truly."],
    },
    "kraken_kid": {
        "name": "Kraken Kid", "colour": (0.90, 0.80, 0.20), "hat": "kraken",
        "personality": "Joke-cracker, hides fear behind laughter.",
        "backstory": "Followed a yellow light into the deep cave and found the thing making it was not friendly.",
        "rescue_requirement": 5, "guard": "bears", "location_type": "yellow_cave",
        "dialogue": ["A kraken? In a forest? I know, right!", "You took your time, haha!", "Six bears. SIX. Count them next time."],
    },
    "koala_kid": {
        "name": "Koala Kid", "colour": (0.55, 0.55, 0.55), "hat": "koala",
        "personality": "Sleepy, gentle, hums old lullabies to stay calm.",
        "backstory": "The youngest of the group; fell asleep in a hollow tree and woke to find everyone gone.",
        "rescue_requirement": 6, "guard": "bears", "location_type": "grey_cave",
        "dialogue": ["I knew someone would come. Eventually.", "Is the fire warm? I like warm.", "The grey cave was cold. And loud."],
    },
}


class ChildNPC:
    def __init__(self, child_id):
        self.id = child_id
        self.defn = CHILDREN[child_id]
        self.rescued = False
        self.cave_location_id = None
        self.x = 0.0
        self.y = 0.0
        self.wander_timer = 0.0
        self.dialogue_index = 0

    def next_dialogue(self):
        line = self.defn["dialogue"][self.dialogue_index % len(self.defn["dialogue"])]
        self.dialogue_index += 1
        return line


class NPCManager:
    def __init__(self):
        self.children = {cid: ChildNPC(cid) for cid in CHILDREN}

    def assign_caves(self, locations):
        for loc in locations:
            if "child" in loc:
                self.children[loc["child"]].cave_location_id = loc["id"]

    def can_rescue(self, child_id, campfire_level):
        return campfire_level >= CHILDREN[child_id]["rescue_requirement"]

    def rescue(self, child_id, campfire_level):
        child = self.children[child_id]
        if child.rescued or not self.can_rescue(child_id, campfire_level):
            return False
        child.rescued = True
        return True

    def rescued_count(self):
        return sum(1 for c in self.children.values() if c.rescued)

    def all_rescued(self):
        return self.rescued_count() == len(self.children)

    def update(self, dt, campfire_pos, campfire_radius):
        """Rescued children wander around inside the camp's safe zone."""
        import random as _r
        for child in self.children.values():
            if not child.rescued:
                continue
            child.wander_timer -= dt
            if child.wander_timer <= 0:
                ang = _r.uniform(0, 2 * math.pi)
                r = _r.uniform(2, max(4, campfire_radius * 0.6))
                child.x = campfire_pos[0] + math.cos(ang) * r
                child.y = campfire_pos[1] + math.sin(ang) * r
                child.wander_timer = _r.uniform(4, 10)

    def to_dict(self):
        return {cid: {"rescued": c.rescued} for cid, c in self.children.items()}

    def from_dict(self, data):
        for cid, entry in data.items():
            if cid in self.children:
                self.children[cid].rescued = bool(entry.get("rescued", False))
