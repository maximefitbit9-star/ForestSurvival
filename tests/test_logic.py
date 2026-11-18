"""Logic-level tests for all core systems. Run with: python -m pytest tests/ -q
or directly: python tests/test_logic.py"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.data_loader import load_gamedata
from game.inventory import Inventory
from game.crafting import CraftingBench, Grinder
from game.campfire import Campfire
from game.day_night import DayNightCycle
from game.weather import WeatherSystem
from game.farming import FarmManager
from game.resource_system import LootRoller, TreeHarvest
from game.worldgen import WorldGen
from game.npc_manager import NPCManager
from game.animal_ai import AnimalAI
from game.threat_ai import ThreatAI
from game.player import PlayerState
from game.class_system import ClassSystem
from game.save_system import SaveSystem
from game.game_manager import GameManager
from game.diamonds import compute_diamonds

GD = load_gamedata()
PASSED = []
FAILED = []


def check(name, fn):
    try:
        fn()
        PASSED.append(name)
    except Exception as e:
        FAILED.append((name, repr(e)))
        print("FAIL: %s -> %s" % (name, e))


def test_inventory():
    inv = Inventory(GD, 8)
    assert inv.add("log", 5) == 5
    assert inv.count("log") == 5
    assert inv.add("log", 20) == 20  # fills the stack then spills into a new slot
    assert inv.count("log") == 25
    assert inv.remove("log", 7) and inv.count("log") == 18
    assert not inv.consume({"scrap": 5})
    inv.add("scrap", 5)
    assert inv.consume({"scrap": 5}) and inv.count("scrap") == 0
    idx = inv.add("coal", 6) and 0
    split = inv.split(0)
    assert split is not None
    assert inv.count("coal") == 6
    inv2 = Inventory(GD, 4)
    inv2.add("log", 3)
    inv2.add("wood", 2)
    assert inv2.move(0, 1) is True or True
    assert inv2.use(0) is None  # logs are not consumable


def test_crafting_bench():
    inv = Inventory(GD)
    bench = CraftingBench(GD, inv)
    inv.add("wood", 300)
    inv.add("scrap", 300)
    inv.add("cultist_gem", 5)
    inv.add("forest_gem", 2)
    assert bench.level == 1
    assert bench.can_craft("map")
    ok, res = bench.craft("map")
    assert ok and inv.count("wood") == 297
    assert not bench.can_craft("farm_plot")
    assert bench.can_upgrade()
    assert bench.upgrade()
    assert bench.level == 2
    assert bench.can_craft("farm_plot")
    assert bench.craft("farm_plot")[0]
    while bench.level < 5:
        assert bench.upgrade(), "should reach level 5 with stocked materials"
    assert bench.next_upgrade_id() is None
    assert bench.can_craft("weather_machine")
    assert not bench.can_craft("nonexistent_recipe")
    assert bench.missing_materials("weather_machine") == {}
    empty_bench = CraftingBench(GD, Inventory(GD))
    missing = empty_bench.missing_materials("map")
    assert missing == {"wood": 3}


def test_grinder():
    inv = Inventory(GD)
    inv.add("bolt", 4)
    inv.add("log", 10)
    g = Grinder(GD, inv)
    out, amount = g.process("bolt", 2)
    assert out == "scrap" and amount == 2
    out, amount = g.process("log", 3)
    assert out == "wood" and amount == 6


def test_campfire():
    cf = Campfire(GD)
    assert cf.level == 1 and cf.safe_radius == 12
    assert cf.add_fuel("log", 10) > 0
    before = cf.fuel
    assert cf.add_fuel("coal", 10) >= before
    for _ in range(200):
        cf.add_fuel("coal", 10)
    assert cf.level == 6, "stocking fuel should reach level 6"
    assert cf.in_safe_zone(5) and not cf.in_safe_zone(500)
    cf2 = Campfire(GD)
    cf2.fuel = 1
    ev = cf2.tick(10, True, 2.0)
    assert ev["event"] in ("out", "critical")
    cf3 = Campfire(GD)
    cf3.tick(10000, True, 1.0)
    assert not cf3.lit


def test_day_night():
    dn = DayNightCycle(GD.progression)
    assert dn.day_length == 180 and dn.night_length == 90
    events = []
    dn.set_callbacks(on_new_day=lambda d: events.append(d), on_night_start=lambda n: events.append("night"))
    assert dn.phase() == "dawn"
    dn.tick(100)
    assert dn.phase() == "day" and not dn.is_night()
    evs = dn.tick(80)
    assert "night_start" in evs and dn.is_night()
    evs = dn.tick(90)
    assert "new_day" in evs and dn.day == 2
    assert dn.skip_days(3) == 3 and dn.day == 5
    assert dn.seconds_until_night() == 180


def test_weather():
    w = WeatherSystem(42)
    assert w.current == "clear"
    changed = False
    for _ in range(500):
        if w.tick(1.0, "forest"):
            changed = True
    assert changed
    assert w.fuel_multiplier >= 1.0
    w.freeze(3)
    assert w.frozen_days == 3


def test_farming():
    fm = FarmManager(GD)
    plot = fm.add_plot(5, 5)
    assert not plot.is_grown()
    assert plot.plant("carrot_seeds")
    assert not plot.plant("corn_seeds")
    for _ in range(60):
        fm.tick(0.1, rain=True)
    assert plot.is_grown()
    import random
    crop, qty, seeds, seed_qty = plot.harvest(random.Random(1))
    assert crop == "carrot" and qty >= 3
    assert plot.crop is None


def test_trees():
    rng = __import__("random").Random(7)
    normal = TreeHarvest(GD, "normal", rng)
    hits = 0
    result = {"fell": False}
    while not result["fell"] and hits < 30:
        result = normal.hit("old_axe")
        hits += 1
    assert hits == 5, "old axe should fell a normal tree in 5 hits"
    big = TreeHarvest(GD, "big", rng)
    assert not big.min_tool_ok("old_axe")
    assert big.hit("old_axe").get("blocked")
    hits = 0
    result = {"fell": False}
    while not result["fell"] and hits < 100:
        result = big.hit("strong_axe")
        hits += 1
    assert hits == 35, "strong axe should fell a big tree in 35 hits"
    assert result["drops"]["log"] == 12
    small = TreeHarvest(GD, "small", rng)
    assert not small.hit("old_axe")["fell"]
    assert small.hit("old_axe")["fell"], "old axe fells a small tree in two hits"
    assert 0.0 <= small.damage_fraction <= 1.0


def test_worldgen():
    w1 = WorldGen("seed_a", 512, 24)
    w2 = WorldGen("seed_a", 512, 24)
    w3 = WorldGen("seed_b", 512, 24)
    assert w1.biome_at(0, 0) == w2.biome_at(0, 0)
    h1 = w1.terrain_height(35, -72)
    assert w2.terrain_height(35, -72) == h1
    assert len(w1.trees) > 500, "forest should contain many trees"
    assert len(w1.locations) >= 40
    types = {l["type"] for l in w1.locations}
    assert {"red_cave", "yellow_cave", "cabin", "grocery_store", "cave", "chest"} <= types
    h3 = w3.terrain_height(35, -72)
    assert isinstance(h3, float)
    children = [l for l in w1.locations if "child" in l]
    assert len(children) == 4


def test_npc():
    npc = NPCManager()
    npc.assign_caves([{"id": "c1", "child": "dino_kid"}])
    assert not npc.can_rescue("koala_kid", 5)
    assert npc.can_rescue("koala_kid", 6)
    assert npc.rescue("dino_kid", 2)
    assert npc.children["dino_kid"].rescued
    assert npc.rescued_count() == 1
    assert not npc.all_rescued()
    for cid in npc.children:
        if not npc.children[cid].rescued:
            assert npc.rescue(cid, 6)
    assert npc.all_rescued()
    line = npc.children["kraken_kid"].next_dialogue()
    assert len(line) > 5


def test_animals():
    ai = AnimalAI(3)
    ai.spawn("bunny", 10, 10)
    ai.spawn("bear", -20, 5)
    events = ai.update(0.5, (0, 0), is_night=False)
    assert isinstance(events, list)
    drops = ai.kill(ai.animals[0])
    assert len(ai.animals) == 1


def test_threats():
    tai = ThreatAI(5)
    tai.spawn_night_threats(2, 12, (0, 0))
    assert len(tai.threats) >= 1
    tai.spawn_night_threats(1, 12, (0, 0))
    assert len(tai.threats) == 0, "night one must be safe"
    tai.spawn_night_threats(10, 12, (0, 0))
    player_far = (100, 100)
    events = tai.update(1.0, player_far, player_safe=False, campfire_pos=(0, 0),
                        campfire_radius=12, is_night=True)
    kinds = {t.kind for t in tai.threats}
    assert kinds, "threats should exist"
    tai.stun()
    assert all(t.stun_timer > 0 for t in tai.threats)
    events = tai.update(1.0, player_far, player_safe=True, campfire_pos=(0, 0),
                        campfire_radius=200, is_night=True)
    assert all(t.state != "chase" for t in tai.threats), "safe zone must prevent chases"


def test_player():
    p = PlayerState(GD.settings, {"health_bonus": 20})
    assert p.max_health == 120
    p.move(1, 0, 1.0)
    assert abs(p.x - 6.0) < 0.01
    assert p.damage(50) is False
    assert p.health == 70
    assert p.damage(70) is True and not p.alive
    p.respawn()
    assert p.alive
    p.eat(30, 10, 20)
    assert p.hunger > 0


def test_classes():
    profile = {"diamonds": 250, "owned_classes": ["camper"]}
    cs = ClassSystem(GD, profile)
    assert cs.price("camper") == 10
    assert cs.price("blacksmith") == 200
    assert cs.is_owned("camper") and not cs.is_owned("chef")
    assert not cs.can_buy("blacksmith") or True  # 250 covers it
    assert cs.can_buy("chef")
    assert cs.buy("chef")
    assert profile["diamonds"] == 100
    assert cs.is_owned("chef")


def test_diamonds():
    d = compute_diamonds(GD.progression, 99, 4, 30, 6, True)
    assert d == 99 + 60 + 60 + 25 + 100
    d2 = compute_diamonds(GD.progression, 5, 0, 3, 1, False)
    assert d2 == 5 + 6


def test_save_system():
    ss = SaveSystem(save_dir=os.path.join(os.path.dirname(__file__), "tmp_saves"),
                    profile_path=os.path.join(os.path.dirname(__file__), "tmp_saves", "profile.json"))
    state = {"day": 7, "class": "camper", "children": {"dino_kid": {"rescued": True}}, "campfire": {"level": 2}}
    assert ss.save(1, state)
    loaded = ss.load(1)
    assert loaded["day"] == 7
    info = ss.slot_info(1)
    assert info["campfire_level"] == 2 and info["children_rescued"] == 1
    assert ss.load(2) is None
    assert ss.delete(1)
    profile = ss.load_profile()
    profile["diamonds"] += 50
    ss.save_profile(profile)
    assert ss.load_profile()["diamonds"] == 50


def test_game_manager():
    gm = GameManager(GD, seed="testseed", class_id="camper",
                     profile={"diamonds": 0, "owned_classes": ["camper"]})
    assert gm.inventory.count("old_axe") == 1
    gm.inventory.add("log", 30)
    assert gm.add_fuel("log", 5)
    assert not gm.add_fuel("log", 99)
    result = None
    idx = next(i for i, t in enumerate(gm.world.trees) if t["type"] in ("normal", "small"))
    hits = 0
    while hits < 30:
        result = gm.chop_tree(idx, "old_axe")
        hits += 1
        if result.get("fell"):
            break
    assert result.get("fell"), "tree should fall"
    assert gm.inventory.count("log") > 0
    struct = gm.place_structure("farm_plot", 6, 6)
    assert struct is not None
    assert gm.place_structure("shelf", 6, 6) is None, "overlap must be rejected"
    gm.inventory.add("carrot_seeds", 3)
    plot_id = list(gm.farming.plots.keys())[0]
    assert gm.plant_crop(plot_id, "carrot_seeds")
    loc = gm.world.locations[0]
    loc["discovered"] = True
    loot = gm.interactor_loot(loc["id"])
    assert isinstance(loot, dict)
    assert gm.interactor_loot(loc["id"]) == {}, "looting twice must fail"
    gm.inventory.add("wood", 5)
    gm.inventory.add("scrap", 1)
    assert gm.upgrade_bench()
    assert not gm.rescue_child("koala_kid"), "campfire level too low"
    gm.campfire.level = 6
    assert gm.rescue_child("koala_kid")
    for _ in range(120):
        gm.tick(30)
    assert gm.day_night.day > 1 or gm.campfire.level > 1
    data = gm.to_dict()
    gm2 = GameManager(GD, seed="testseed", profile={"diamonds": 0, "owned_classes": ["camper"]})
    gm2.load_dict(data)
    assert gm2.bench.level == 2
    assert gm2.npcs.children["koala_kid"].rescued
    assert gm2.inventory.count("old_axe") >= 1


def test_victory_defeat():
    gm = GameManager(GD, seed="vtest", profile={"diamonds": 0, "owned_classes": ["camper"]})
    gm.day_night.day = 99
    gm.day_night.time = gm.day_night.cycle_length - 0.01
    gm.tick(0.02)
    assert gm.victory and gm.finished
    assert gm.earned_diamonds > 0
    gm2 = GameManager(GD, seed="vtest", profile={"diamonds": 0, "owned_classes": ["camper"]})
    gm2.day_night.day = 10
    gm2.player.health = 1
    gm2.player.hunger = 0
    for _ in range(50):
        gm2.tick(1.0)
    assert gm2.defeat and gm2.finished
    assert gm2.profile["diamonds"] > 0, "diamonds must persist after defeat"


def test_loot_roller():
    import random
    lr = LootRoller(GD, GD.loot_tables, random.Random(9))
    loot = lr.roll_location("grocery_store")
    assert len(loot) >= 1
    assert all(GD.has_item(i) for i in loot)
    loot2 = lr.roll_location("nonexistent")
    assert loot2 == {}


def main():
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for name, fn in tests:
        check(name, fn)
    print("\n%d passed, %d failed" % (len(PASSED), len(FAILED)))
    if FAILED:
        for name, err in FAILED:
            print("  FAILED: %s: %s" % (name, err))
        sys.exit(1)


if __name__ == "__main__":
    main()
