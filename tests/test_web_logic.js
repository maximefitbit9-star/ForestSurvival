// Logic tests for the web build. Run: node tests/test_web_logic.js
"use strict";
const path = require("path");
const L = require(path.join(__dirname, "..", "web", "js", "logic.js"));
const { GD } = require(path.join(__dirname, "..", "web", "js", "config.js"));

let passed = 0, failed = 0;
function check(name, fn) {
  try { fn(); passed++; }
  catch (e) { failed++; console.log("FAIL: " + name + " -> " + e.message); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || "assertion failed"); }
function eq(a, b, msg) { if (a !== b) throw new Error((msg || "") + " expected " + b + " got " + a); }

// ---------------------------------------------------------------- inventory

check("inventory basics", () => {
  const inv = new L.Inventory(GD, 8);
  eq(inv.add("log", 5), 5);
  eq(inv.count("log"), 5);
  eq(inv.add("log", 20), 20, "fills stack then spills");
  eq(inv.count("log"), 25);
  assert(inv.remove("log", 7) === 7 && inv.count("log") === 18);
  assert(!inv.consume({ scrap: 5 }));
  inv.add("scrap", 5);
  assert(inv.consume({ scrap: 5}) && inv.count("scrap") === 0);
  assert(inv.split(0) !== null);
  eq(inv.count("log"), 18);
  assert(inv.move(0, 1) === true);
  assert(inv.use(0) === null, "logs are not consumable");
});

check("inventory stacking and moving", () => {
  const inv = new L.Inventory(GD, 6);
  inv.add("coal", 30);
  eq(inv.freeSlots(), 4, "coal stacks of 20 across two slots");
  const other = new L.Inventory(GD, 4);
  other.add("log", 3); other.add("wood", 2);
  other.move(0, 1);
  assert(other.slots[0].id === "wood" || other.slots[1].id === "log", "swap happened");
});

// ---------------------------------------------------------------- crafting

check("crafting bench tiers", () => {
  const inv = new L.Inventory(GD);
  const bench = new L.CraftingBench(GD, inv);
  inv.add("wood", 300); inv.add("scrap", 300);
  inv.add("cultist_gem", 5); inv.add("forest_gem", 2);
  eq(bench.level, 1);
  assert(bench.canCraft("map"));
  assert(bench.craft("map"));
  eq(inv.count("wood"), 297);
  assert(!bench.canCraft("farm_plot"));
  assert(bench.upgrade());
  eq(bench.level, 2);
  assert(bench.canCraft("farm_plot"));
  assert(bench.craft("farm_plot"));
  while (bench.level < 5) assert(bench.upgrade(), "should reach level 5");
  eq(bench.nextUpgradeId(), null);
  assert(bench.canCraft("weather_machine"));
  const empty = new L.CraftingBench(GD, new L.Inventory(GD));
  const missing = empty.missing("map");
  eq(missing.wood, 3);
});

check("grinder", () => {
  const inv = new L.Inventory(GD);
  inv.add("bolt", 4); inv.add("log", 10);
  let [out, amount] = L.grind(GD, inv, "bolt", 2);
  eq(out, "scrap"); eq(amount, 2);
  [out, amount] = L.grind(GD, inv, "log", 3);
  eq(out, "wood"); eq(amount, 6);
  const [o2, a2] = L.grind(GD, inv, "coal", 1);
  eq(o2, null); eq(a2, 0);
});

// ---------------------------------------------------------------- campfire

check("campfire levels and fuel", () => {
  const cf = new L.Campfire(GD);
  eq(cf.level, 1); eq(cf.safeRadius, 12);
  assert(cf.addFuel("log", 10) > 0);
  const before = cf.fuel;
  assert(cf.addFuel("coal", 10) >= before);
  for (let i = 0; i < 200; i++) cf.addFuel("coal", 10);
  eq(cf.level, 6, "stocking fuel reaches level 6");
  assert(cf.inSafeZone(5) && !cf.inSafeZone(500));
  const cf2 = new L.Campfire(GD);
  cf2.fuel = 1;
  assert(["out", "critical"].includes(cf2.tick(10, true, 2.0).event));
  const cf3 = new L.Campfire(GD);
  cf3.tick(10000, true, 1.0);
  assert(!cf3.lit);
});

// --------------------------------------------------------------- day/night

check("day night cycle", () => {
  const dn = new L.DayNight(GD);
  eq(dn.dayLength, 180); eq(dn.nightLength, 90);
  let newDays = 0, nights = 0;
  dn.onNewDay = () => newDays++;
  dn.onNightStart = () => nights++;
  eq(dn.phase(), "dawn");
  dn.tick(100);
  eq(dn.phase(), "day");
  let evs = dn.tick(80);
  assert(evs.includes("night_start") && dn.isNight());
  eq(nights, 1);
  evs = dn.tick(90);
  assert(evs.includes("new_day") && dn.day === 2);
  eq(newDays, 1);
  dn.skipDays(3);
  eq(dn.day, 5);
  eq(dn.secondsUntilNight(), 180);
});

// ---------------------------------------------------------------- weather

check("weather", () => {
  const w = new L.Weather(42);
  eq(w.current, "clear");
  let changed = false;
  for (let i = 0; i < 500; i++) if (w.tick(1, "forest")) changed = true;
  assert(changed);
  assert(w.fuelMultiplier >= 1.0);
  w.freeze(3);
  eq(w.frozenDays, 3);
});

// ----------------------------------------------------------------- farming

check("farming", () => {
  const plot = new L.FarmPlot(GD, "p", 5, 5);
  assert(!plot.isGrown());
  assert(plot.plant("carrot_seeds"));
  assert(!plot.plant("corn_seeds"));
  for (let i = 0; i < 60; i++) plot.tick(0.1, true);
  assert(plot.isGrown());
  const result = plot.harvest(L.makeRng("h"));
  eq(result.crop, "carrot");
  assert(result.qty >= 3);
  eq(plot.crop, null);
});

// ------------------------------------------------------------------- trees

check("tree harvesting per tool", () => {
  const rng = L.makeRng("t7");
  const normal = new L.TreeHarvest(GD, "normal", rng);
  let hits = 0, r = { fell: false };
  while (!r.fell && hits < 30) { r = normal.hit("old_axe"); hits++; }
  eq(hits, 5, "old axe fells normal tree in 5 hits");
  const big = new L.TreeHarvest(GD, "big", rng);
  assert(big.hit("old_axe").blocked, "old axe cannot fell big trees");
  hits = 0; r = { fell: false };
  while (!r.fell && hits < 100) { r = big.hit("strong_axe"); hits++; }
  eq(hits, 35, "strong axe fells big tree in 35 hits");
  eq(r.drops.log, 12);
  eq(r.drops.sapling >= 3 && r.drops.sapling <= 4, true, "big tree saplings 3-4");
  const small = new L.TreeHarvest(GD, "small", rng);
  assert(!small.hit("old_axe").fell);
  assert(small.hit("old_axe").fell, "small tree falls in two old-axe hits");
});

// ---------------------------------------------------------------- worldgen

check("world generation", () => {
  const w1 = L.generateWorld(GD, "seed_a", 512, 24);
  const w2 = L.generateWorld(GD, "seed_a", 512, 24);
  eq(w1.biomeAt(0, 0), w2.biomeAt(0, 0));
  eq(w1.height(35, -72), w2.height(35, -72), "same seed same terrain");
  assert(w1.trees.length > 500, "forest contains many trees");
  assert(w1.locations.length >= 40);
  const types = new Set(w1.locations.map((l) => l.type));
  for (const t of ["red_cave", "yellow_cave", "cabin", "grocery_store", "cave", "chest"]) {
    assert(types.has(t), "location type " + t);
  }
  eq(w1.locations.filter((l) => l.child).length, 4, "four child caves");
});

// -------------------------------------------------------------------- loot

check("loot rolls", () => {
  const rng = L.makeRng("loot9");
  const loot = L.rollLoot(GD, rng, "grocery_store", 0);
  assert(Object.keys(loot).length >= 1);
  for (const id of Object.keys(loot)) assert(GD.items.items[id], "loot item exists");
  eq(Object.keys(L.rollLoot(GD, rng, "nonexistent", 0)).length, 0);
});

// ------------------------------------------------------------------ threats

check("threats", () => {
  const rng = L.makeRng("th5");
  eq(L.spawnNightThreats(rng, 1, 12, [0, 0]).length, 0, "night one is safe");
  const threats = L.spawnNightThreats(rng, 10, 12, [0, 0]);
  assert(threats.length >= 1);
  let evs = L.updateThreats(rng, 1, threats, [100, 100], false, 12, true);
  assert(Array.isArray(evs));
  for (const t of threats) t.stun = 5;
  evs = L.updateThreats(rng, 1, threats, [100, 100], true, 200, true);
  assert(threats.every((t) => t.state !== "chase"), "safe zone prevents chases");
});

// ------------------------------------------------------------------ animals

check("animals", () => {
  const rng = L.makeRng("an3");
  const animals = [
    { id: "a", species: "bunny", x: 3, y: 3, state: "idle", stateTimer: 1, tx: 0, ty: 0 },
    { id: "b", species: "deer", x: -20, y: 5, state: "idle", stateTimer: 1, tx: 0, ty: 0 },
  ];
  L.updateAnimals(rng, 0.5, animals, [0, 0], false);
  assert(animals[0].state === "flee", "bunny flees when player is close");
  assert(animals[1].state === "idle" || animals[1].state === "walk", "distant deer stays calm");
});

// ------------------------------------------------------------------ player

check("player survival", () => {
  const p = new L.PlayerState(GD, { health_bonus: 20 });
  eq(p.maxHealth, 120);
  assert(!p.damage(50));
  eq(p.health, 70);
  assert(p.damage(70) && !p.alive);
  p.eat(30, 10, 20);
  assert(p.hunger > 0);
  const warnings = p.tick(1, true, false, false);
  assert(Array.isArray(warnings));
});

// ----------------------------------------------------------------- children

check("children rescue gates", () => {
  const g = new L.Game(GD, "childtest", "camper", { diamonds: 0, owned_classes: ["camper"] });
  assert(!g.canRescue("koala_kid"), "koala kid needs campfire level 6");
  g.campfire.level = 5;
  assert(!g.canRescue("koala_kid"));
  g.campfire.level = 6;
  assert(g.canRescue("koala_kid"));
  assert(g.rescueChild("koala_kid"));
  assert(!g.rescueChild("koala_kid"), "cannot rescue twice");
  eq(g.rescuedCount(), 1);
});

// ------------------------------------------------------------------- classes

check("class purchases", () => {
  const profile = { diamonds: 250, owned_classes: ["camper"] };
  eq(GD.classes.classes.camper.price, 10);
  eq(GD.classes.classes.blacksmith.price, 200);
  assert(L.canBuyClass(GD, profile, "chef"));
  assert(L.buyClass(GD, profile, "chef"));
  eq(profile.diamonds, 100);
  assert(profile.owned_classes.includes("chef"));
  assert(!L.canBuyClass(GD, profile, "chef"), "cannot buy twice");
});

// ------------------------------------------------------------- game manager

check("game manager integration", () => {
  const g = new L.Game(GD, "gmtest", "camper", { diamonds: 0, owned_classes: ["camper"] });
  eq(g.inv.count("old_axe"), 1);
  eq(g.inv.count("log"), 10, "4 camper logs + 6 guaranteed day-one pile");
  eq(g.inv.count("coal"), 1, "guaranteed day-one coal");
  assert(g.addFuel("log", 5));
  assert(!g.addFuel("log", 99));
  const idx = g.world.trees.findIndex((t) => t.type === "normal" || t.type === "small");
  let hits = 0, r = { fell: false };
  while (hits < 30) { r = g.chopTree(idx, "old_axe"); hits++; if (r.fell) break; }
  assert(r.fell, "tree falls");
  assert(g.inv.count("log") > 0);
  assert(g.placeStructure("farm_plot", 6, 6) !== null);
  eq(g.placeStructure("shelf", 6, 6), null, "overlap rejected");
  g.inv.add("carrot_seeds", 3);
  assert(g.plant("plot_0", "carrot_seeds"));
  const loc = g.world.locations.find((l) => !!GD.loot_tables.locations[l.type]);
  loc.discovered = true;
  const loot = g.loot(loc.id);
  assert(loot && Object.keys(loot).length >= 1, "lootable building yields loot");
  eq(g.loot(loc.id), null, "cannot loot twice");
  g.inv.add("wood", 5); g.inv.add("scrap", 1);
  assert(g.upgradeBench());
  assert(!g.rescueChild("koala_kid"));
  g.campfire.level = 6;
  assert(g.rescueChild("koala_kid"));
  for (let i = 0; i < 120; i++) g.tick(30);
  assert(g.dayNight.day > 1 || g.campfire.level > 1);
  const g2 = new L.Game(GD, "gmtest", "camper", { diamonds: 0, owned_classes: ["camper"] });
  g2.load(g.toSave());
  eq(g2.bench.level, 2);
  assert(g2.children.koala_kid.rescued);
  assert(g2.inv.count("old_axe") >= 1);
});

check("victory and diamonds persist after defeat", () => {
  const g = new L.Game(GD, "vtest", "camper", { diamonds: 0, owned_classes: ["camper"] });
  g.dayNight.day = 99;
  g.dayNight.time = g.dayNight.cycleLength - 0.01;
  g.tick(0.02);
  assert(g.victory && g.finished);
  assert(g.earnedDiamonds > 0);
  const g2 = new L.Game(GD, "vtest", "camper", { diamonds: 0, owned_classes: ["camper"] });
  g2.dayNight.day = 10;
  g2.player.health = 1;
  g2.player.hunger = 0;
  for (let i = 0; i < 50; i++) g2.tick(1);
  assert(g2.defeat && g2.finished);
  assert(g2.profile.diamonds > 0, "diamonds persist after defeat");
});

// --------------------------------------------------------------------- main

console.log("\n" + passed + " passed, " + failed + " failed");
if (failed > 0) process.exit(1);
