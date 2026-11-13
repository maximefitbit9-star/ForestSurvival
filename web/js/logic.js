// Engine-agnostic game logic for the web build.
// Direct port of the tested Python logic modules (game/*.py). No DOM, no THREE -
// this file runs in both the browser and Node (for the test suite).
"use strict";

function makeRng(seed) {
  // Deterministic PRNG (mulberry32) so world generation is reproducible per seed.
  let h = 1779033703 ^ seed.length;
  for (let i = 0; i < seed.length; i++) {
    h = Math.imul(h ^ seed.charCodeAt(i), 3432918353);
    h = (h << 13) | (h >>> 19);
  }
  let a = h >>> 0;
  function next() {
    a |= 0; a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  const rng = {
    next,
    int(lo, hi) { return lo + Math.floor(next() * (hi - lo + 1)); },
    range(lo, hi) { return lo + next() * (hi - lo); },
    pick(arr) { return arr[Math.floor(next() * arr.length)]; },
  };
  return rng;
}

// ---------------------------------------------------------------- world gen

const BIOMES = {
  forest: { ground: [0.30, 0.50, 0.22], trees: ["normal", "small"], density: 1.0 },
  dense_woodland: { ground: [0.18, 0.36, 0.16], trees: ["normal", "big"], density: 1.8 },
  snowy: { ground: [0.85, 0.88, 0.92], trees: ["snow_pine", "normal"], density: 0.7 },
  magical: { ground: [0.25, 0.35, 0.30], trees: ["normal", "ancient"], density: 0.8 },
};

function valueNoise2d(rng, x, y) {
  const xi = Math.floor(x), yi = Math.floor(y);
  const xf = x - xi, yf = y - yi;
  const s = (a, b) => rng.next();
  const v00 = s(xi, yi), v10 = s(xi + 1, yi), v01 = s(xi, yi + 1), v11 = s(xi + 1, yi + 1);
  const interp = (a, b, t) => { t = t * t * (3 - 2 * t); return a + (b - a) * t; };
  return interp(interp(v00, v10, xf), interp(v01, v11, xf), yf);
}

function generateWorld(GD, seed, size, heightScale) {
  const rng = makeRng(String(seed));
  const world = { seed, size, heightScale, rng, locations: [], trees: [] };
  world.height = (x, y) => {
    let h = valueNoise2d(rng, x / 120, y / 120) * 1.0;
    h += valueNoise2d(rng, x / 60, y / 60) * 0.4;
    h += valueNoise2d(rng, x / 25, y / 25) * 0.12;
    const d = Math.sqrt(x * x + y * y);
    h -= Math.max(0, (d - 200) / 400) * 0.3;
    return h * heightScale;
  };
  const randPos = (rmin, rmax) => {
    const ang = rng.range(0, Math.PI * 2);
    const r = rng.range(rmin, rmax);
    return [Math.round(r * Math.cos(ang)), Math.round(r * Math.sin(ang))];
  };
  world.biomeAt = (x, y) => {
    const n = valueNoise2d(rng, x / 180 + 500, y / 180 + 500);
    const d = Math.sqrt(x * x + y * y);
    if (d < 120) return "forest";
    if (n < 0.30) return "dense_woodland";
    if (n > 0.72) return "magical";
    if (x < -size * 0.22 || y > size * 0.22) return "snowy";
    return "forest";
  };
  const childDefs = [
    ["dino_kid", "red_cave", 90], ["squid_kid", "blue_cave", 130],
    ["kraken_kid", "yellow_cave", 180], ["koala_kid", "grey_cave", 220],
  ];
  childDefs.forEach(([child, type, r], i) => {
    const [x, y] = randPos(r, r + 40);
    world.locations.push({
      id: type + "_" + world.locations.length, type, x, y, discovered: false,
      child, guard: child === "dino_kid" ? "wolves" : "bears",
    });
  });
  const others = [["cabin", 5], ["house", 4], ["grocery_store", 2], ["clinic", 2],
    ["mechanical_building", 3], ["warehouse", 2], ["campsite", 6], ["ruins", 4],
    ["cave", 5], ["cultist_outpost", 3]];
  others.forEach(([type, count]) => {
    for (let i = 0; i < count; i++) {
      const [x, y] = randPos(70, size / 2 - 30);
      world.locations.push({ id: type + "_" + world.locations.length, type, x, y, discovered: false });
    }
  });
  for (let i = 0; i < 14; i++) {
    const [x, y] = randPos(60, size / 2 - 40);
    world.locations.push({ id: "chest_" + i, type: "chest", x, y, discovered: false });
  }
  for (let i = 0; i < 4; i++) {
    const [x, y] = randPos(150, size / 2 - 40);
    world.locations.push({ id: "gem_shrine_" + i, type: "ruins", x, y, discovered: false, gem_fragment: true });
  }
  const half = size / 2, step = 8;
  for (let x = -half; x < half; x += step) {
    for (let y = -half; y < half; y += step) {
      const jx = x + rng.int(-3, 3), jy = y + rng.int(-3, 3);
      const d = Math.sqrt(jx * jx + jy * jy);
      if (d < 14) continue;
      const biome = BIOMES[world.biomeAt(jx, jy)];
      if (rng.next() > 0.24 * biome.density) continue;
      let type = rng.pick(biome.trees);
      if (type === "big" && rng.next() > 0.25) type = "normal";
      if (type === "ancient" && rng.next() > 0.15) type = "normal";
      world.trees.push({ x: jx, y: jy, type, scale: rng.range(0.85, 1.3), removed: false });
    }
  }
  return world;
}

// --------------------------------------------------------------- inventory

class Inventory {
  constructor(GD, size) {
    this.GD = GD;
    this.size = size || 24;
    this.slots = Array.from({ length: this.size }, () => ({ id: null, qty: 0 }));
  }
  stackLimit(id) {
    const item = this.GD.items.items[id];
    return item ? (item.stack || 1) : 1;
  }
  count(id) { return this.slots.reduce((a, s) => a + (s.id === id ? s.qty : 0), 0); }
  freeSlots() { return this.slots.filter((s) => !s.id || s.qty <= 0).length; }
  add(id, qty) {
    qty = qty || 1;
    if (qty <= 0 || !this.GD.items.items[id]) return 0;
    let added = 0;
    const limit = this.stackLimit(id);
    for (const s of this.slots) {
      if (s.id === id && s.qty < limit) {
        const take = Math.min(limit - s.qty, qty - added);
        s.qty += take; added += take;
        if (added >= qty) return added;
      }
    }
    for (const s of this.slots) {
      if (!s.id || s.qty <= 0) {
        const take = Math.min(limit, qty - added);
        s.id = id; s.qty = take; added += take;
        if (added >= qty) return added;
      }
    }
    return added;
  }
  remove(id, qty) {
    qty = qty || 1;
    if (this.count(id) < qty) return 0;
    let remaining = qty;
    for (const s of this.slots) {
      if (s.id === id) {
        const take = Math.min(s.qty, remaining);
        s.qty -= take; remaining -= take;
        if (s.qty <= 0) s.id = null;
        if (remaining <= 0) break;
      }
    }
    return qty - remaining;
  }
  has(reqs) { return Object.entries(reqs).every(([id, q]) => this.count(id) >= q); }
  consume(reqs) {
    if (!this.has(reqs)) return false;
    for (const [id, qty] of Object.entries(reqs)) this.remove(id, qty);
    return true;
  }
  move(from, to) {
    if (from === to || from < 0 || to < 0 || from >= this.size || to >= this.size) return false;
    const src = this.slots[from], dst = this.slots[to];
    if (!dst.id || dst.qty <= 0) {
      this.slots[from] = dst; this.slots[to] = src; return true;
    }
    if (src.id === dst.id) {
      const limit = this.stackLimit(src.id);
      const take = Math.min(limit - dst.qty, src.qty);
      if (take <= 0) return false;
      dst.qty += take; src.qty -= take;
      if (src.qty <= 0) src.id = null;
      return true;
    }
    this.slots[from] = dst; this.slots[to] = src; return true;
  }
  split(index) {
    const s = this.slots[index];
    if (!s.id || s.qty < 2) return null;
    const half = Math.floor(s.qty / 2);
    for (let i = 0; i < this.size; i++) {
      const o = this.slots[i];
      if (!o.id || o.qty <= 0) {
        o.id = s.id; o.qty = half; s.qty -= half; return i;
      }
    }
    return null;
  }
  use(index) {
    const s = this.slots[index];
    if (!s.id) return null;
    const item = this.GD.items.items[s.id];
    const effects = item && (item.food || item.use);
    if (!effects) return null;
    this.remove(s.id, 1);
    return Object.assign({}, effects);
  }
  toSave() { return this.slots.map((s) => ({ id: s.id, qty: s.qty })); }
  load(data) {
    this.slots = Array.from({ length: this.size }, (_, i) => {
      const e = data && data[i];
      return e ? { id: e.id, qty: e.qty || 0 } : { id: null, qty: 0 };
    });
  }
}

// ---------------------------------------------------------- crafting bench

class CraftingBench {
  constructor(GD, inv) {
    this.GD = GD; this.inv = inv; this.level = 1;
    this.maxLevel = Object.keys(GD.recipes.bench_levels).length;
  }
  recipesFor(level) { return this.GD.recipes.bench_levels[String(level || this.level)].recipes; }
  allKnown() {
    const known = {};
    for (let l = 1; l <= this.level; l++) Object.assign(known, this.recipesFor(l));
    return known;
  }
  nextUpgradeId() { return this.level >= this.maxLevel ? null : "bench_upgrade_" + (this.level + 1); }
  scaledCost(cost, discount) {
    if (!discount) return cost;
    const out = {};
    for (const [id, q] of Object.entries(cost)) out[id] = Math.max(1, Math.round(q * (1 - discount)));
    return out;
  }
  canUpgrade(discount) {
    const nxt = this.nextUpgradeId();
    if (!nxt) return false;
    return this.inv.has(this.scaledCost(this.recipesFor()[nxt].cost, discount));
  }
  upgrade(discount) {
    const nxt = this.nextUpgradeId();
    if (!nxt || !this.canUpgrade(discount)) return false;
    this.inv.consume(this.scaledCost(this.recipesFor()[nxt].cost, discount));
    this.level += 1;
    return true;
  }
  missing(recipeId, discount) {
    const recipe = this.allKnown()[recipeId];
    if (!recipe) return {};
    const cost = this.scaledCost(recipe.cost, discount);
    const out = {};
    for (const [id, q] of Object.entries(cost)) {
      const have = this.inv.count(id);
      if (have < q) out[id] = q - have;
    }
    return out;
  }
  canCraft(recipeId, discount) {
    const recipe = this.allKnown()[recipeId];
    return !!recipe && this.inv.has(this.scaledCost(recipe.cost, discount));
  }
  craft(recipeId, discount) {
    const recipe = this.allKnown()[recipeId];
    if (!recipe || recipeId === this.nextUpgradeId()) return false;
    if (!this.inv.consume(this.scaledCost(recipe.cost, discount))) return false;
    return true;
  }
}

function grind(GD, inv, itemId, qty, bonus) {
  const entry = GD.progression.grinder.recipes[itemId];
  if (!entry) return [null, 0];
  const have = inv.count(itemId);
  const n = Math.min(qty || 1, have);
  if (n <= 0) return [null, 0];
  inv.remove(itemId, n);
  const amount = Math.max(1, Math.round(n * entry.amount * (1 + (bonus || 0))));
  const added = inv.add(entry.output, amount);
  return [entry.output, added];
}

// ---------------------------------------------------------------- campfire

class Campfire {
  constructor(GD) {
    this.GD = GD;
    this.level = 1;
    this.fuel = 50;
    this.progress = 50;
    this.lit = true;
  }
  def() { return this.GD.progression.campfire.levels[String(this.level)]; }
  get capacity() { return this.def().fuel_capacity; }
  get safeRadius() { return this.def().safe_radius; }
  fraction() { return Math.max(0, Math.min(1, this.fuel / this.capacity)); }
  addFuel(itemId, qty) {
    const value = this.GD.progression.fuel_values[itemId];
    if (!value || value.value <= 0) return 0;
    const amount = value.value * (qty || 1);
    this.fuel = Math.min(this.capacity, this.fuel + amount);
    this.progress += amount;
    this.lit = true;
    this._levelUp();
    return amount;
  }
  _levelUp() {
    const th = this.GD.progression.campfire.level_up_thresholds;
    while (this.level < this.GD.progression.campfire.max_level && this.progress >= th[this.level - 1]) {
      this.level += 1;
    }
  }
  tick(dt, isNight, weatherMult) {
    if (!this.lit) return { event: "out" };
    const ld = this.def();
    let rate = isNight ? ld.burn_rate_night : ld.burn_rate_day;
    if ((weatherMult || 1) > 1) rate *= 1 - ld.weather_resistance * (weatherMult - 1);
    this.fuel -= rate * dt;
    this.progress = Math.max(0, this.progress - rate * dt);
    if (this.fuel <= 0) { this.fuel = 0; this.lit = false; return { event: "out" }; }
    const f = this.fraction();
    if (f < 0.15) return { event: "critical", fraction: f };
    if (f < 0.35) return { event: "low", fraction: f };
    return { event: "ok", fraction: f };
  }
  inSafeZone(dist) { return this.lit && dist <= this.safeRadius; }
  toSave() { return { level: this.level, fuel: +this.fuel.toFixed(2), progress: +this.progress.toFixed(2), lit: this.lit }; }
  load(d) { this.level = d.level || 1; this.fuel = d.fuel != null ? d.fuel : 50; this.progress = d.progress != null ? d.progress : this.fuel; this.lit = d.lit !== false; }
}

// --------------------------------------------------------------- day/night

class DayNight {
  constructor(GD) {
    const dn = GD.progression.day_night;
    this.dayLength = dn.day_length_seconds;
    this.nightLength = dn.night_length_seconds;
    this.time = 0; this.day = 1;
    this.onNewDay = null; this.onNightStart = null;
  }
  get cycleLength() { return this.dayLength + this.nightLength; }
  isNight() { return this.time >= this.dayLength; }
  phase() {
    if (this.time < this.dayLength * 0.08) return "dawn";
    if (this.time < this.dayLength * 0.92) return "day";
    if (this.time < this.dayLength) return "dusk";
    return "night";
  }
  secondsUntilNight() { return this.isNight() ? 0 : this.dayLength - this.time; }
  skipDays(count) {
    for (let i = 0; i < (count || 1); i++) {
      this.day += 1;
      if (this.onNewDay) this.onNewDay(this.day);
    }
    this.time = 0;
  }
  tick(dt) {
    const events = [];
    const wasNight = this.isNight();
    this.time += dt;
    if (!wasNight && this.time >= this.dayLength) {
      events.push("night_start");
      if (this.onNightStart) this.onNightStart(this.day);
    }
    if (this.time >= this.cycleLength) {
      this.time -= this.cycleLength;
      this.day += 1;
      events.push("new_day");
      if (this.onNewDay) this.onNewDay(this.day);
    }
    return events;
  }
  toSave() { return { day: this.day, time: +this.time.toFixed(2) }; }
  load(d) { this.day = d.day || 1; this.time = d.time || 0; }
}

// ------------------------------------------------------------------ weather

const WEATHERS = {
  clear: { fuel: 1.0, visibility: 1.0 },
  rain: { fuel: 1.6, visibility: 0.75 },
  fog: { fuel: 1.1, visibility: 0.4 },
  storm: { fuel: 2.2, visibility: 0.6 },
  snow: { fuel: 1.4, visibility: 0.55 },
};

class Weather {
  constructor(seed) {
    this.rng = makeRng("weather" + seed);
    this.current = "clear";
    this.timeLeft = 120;
    this.frozenDays = 0;
  }
  _pick(biome) {
    const roll = this.rng.next();
    if (biome === "snowy") return roll < 0.6 ? "snow" : (roll < 0.8 ? "fog" : "clear");
    if (roll < 0.55) return "clear";
    if (roll < 0.75) return "rain";
    if (roll < 0.88) return "fog";
    return "storm";
  }
  freeze(days) { this.frozenDays = days || 3; this.current = "clear"; this.timeLeft = (days || 3) * 300; }
  tick(dt, biome) {
    if (this.frozenDays > 0 && (this.current === "rain" || this.current === "storm")) this.current = "clear";
    if (this.timeLeft > 0) {
      this.timeLeft -= dt;
      if (this.timeLeft > 0) return false;
    }
    this.current = this._pick(biome || "forest");
    this.timeLeft = this.rng.range(90, 240);
    return true;
  }
  onNewDay() { if (this.frozenDays > 0) this.frozenDays -= 1; }
  get fuelMultiplier() { return WEATHERS[this.current].fuel; }
  get visibility() { return WEATHERS[this.current].visibility; }
  get isWet() { return this.current === "rain" || this.current === "storm"; }
  toSave() { return { current: this.current, timeLeft: +this.timeLeft.toFixed(1), frozenDays: this.frozenDays }; }
  load(d) { this.current = d.current || "clear"; this.timeLeft = d.timeLeft != null ? d.timeLeft : 120; this.frozenDays = d.frozenDays || 0; }
}

// ------------------------------------------------------------------ farming

class FarmPlot {
  constructor(GD, id, x, y) {
    this.GD = GD; this.id = id; this.x = x; this.y = y;
    this.crop = null; this.growth = 0;
  }
  plant(seedsId) {
    const item = this.GD.items.items[seedsId];
    if (this.crop || !item || !item.crop) return false;
    this.crop = item.crop; this.growth = 0;
    return true;
  }
  isGrown() { return !!this.crop && this.growth >= 1; }
  tick(dtDays, rain) {
    if (!this.crop || this.isGrown()) return;
    const growDays = this.GD.progression.farming.crops[this.crop].grow_days;
    let speed = 1;
    if (rain) speed += this.GD.progression.farming.rain_growth_bonus;
    this.growth = Math.min(1, this.growth + (dtDays / growDays) * speed);
  }
  harvest(rng) {
    if (!this.isGrown()) return null;
    const crop = this.crop;
    this.crop = null; this.growth = 0;
    const def = this.GD.progression.farming.crops[crop];
    const qty = rng.int(def.yield[0], def.yield[1]);
    const seedQty = rng.next() < def.seed_drop_chance ? 1 : 0;
    return { crop, qty, seeds: crop + "_seeds", seedQty };
  }
  toSave() { return { id: this.id, x: this.x, y: this.y, crop: this.crop, growth: +this.growth.toFixed(3) }; }
  load(d) { this.crop = d.crop || null; this.growth = d.growth || 0; }
}

// -------------------------------------------------------------------- trees

class TreeHarvest {
  constructor(GD, type, rng) {
    this.GD = GD; this.rng = rng;
    this.def = GD.progression.trees[type];
    this.type = type;
    this.maxHp = Math.max(1, this.def.hits);
    this.hp = this.maxHp;
    this.fallen = false;
    this.direction = rng.range(0, 360);
  }
  minToolOk(toolId) {
    const order = ["old_axe", "good_axe", "strong_axe", "ice_axe", "chainsaw"];
    return order.indexOf(toolId) >= order.indexOf(this.def.min_tool || "old_axe");
  }
  hitsWith(toolId) {
    const tool = this.GD.progression.tools[toolId];
    if (!tool || !this.minToolOk(toolId)) return null;
    if (this.type === "big") return tool.hits_big_tree;
    if (this.type === "small") return Math.max(1, Math.floor(tool.hits_normal_tree / 2));
    return tool.hits_normal_tree;
  }
  hit(toolId, woodBonus) {
    if (this.fallen) return { fell: false, damage: 0, drops: {} };
    const total = this.hitsWith(toolId);
    if (total == null) return { fell: false, damage: 0, drops: {}, blocked: true };
    this.hp -= this.maxHp / total;
    if (this.hp <= 0) {
      this.fallen = true;
      return {
        fell: true, damage: 1, direction: this.direction,
        drops: { log: this.def.logs + (woodBonus || 0), sapling: this.rng.int(this.def.saplings[0], this.def.saplings[1]) },
      };
    }
    return { fell: false, damage: 1 - this.hp / this.maxHp, drops: {} };
  }
}

// --------------------------------------------------------------------- loot

function rollLoot(GD, rng, locationType, lootBonus) {
  const table = GD.loot_tables.locations[locationType];
  if (!table) return {};
  let rolls = rng.int(table.rolls[0], table.rolls[1]);
  if (lootBonus >= 0.5 && rng.next() < lootBonus) rolls += 1;
  const entries = Object.entries(table.loot);
  const total = entries.reduce((a, [, w]) => a + w, 0);
  const loot = {};
  for (let i = 0; i < rolls; i++) {
    let pick = rng.next() * total, acc = 0;
    for (const [id, w] of entries) {
      acc += w;
      if (pick <= acc) {
        const item = GD.items.items[id];
        const qty = item && item.stack === 1 ? 1 : rng.int(1, 3);
        loot[id] = (loot[id] || 0) + qty;
        break;
      }
    }
  }
  return loot;
}

// ------------------------------------------------------------------ threats

function spawnNightThreats(rng, night, safeRadius, playerPos) {
  if (night <= 1) return [];
  const count = Math.min(1 + Math.floor(night / 20), 3);
  const threats = [];
  for (let i = 0; i < count; i++) {
    const kind = night >= 5 ? rng.pick(["deer", "deer", "owl", "ram"]) : "deer";
    const ang = rng.range(0, Math.PI * 2);
    const dist = safeRadius + 25 + rng.range(0, 30);
    const x = playerPos[0] + Math.cos(ang) * dist;
    const y = playerPos[1] + Math.sin(ang) * dist;
    const speed = kind === "deer" ? 6.5 + Math.min(2.5, night * 0.03) : (kind === "owl" ? 7.5 : 5.5);
    threats.push({
      id: kind + "_" + i, kind, x, y, speed,
      detect: kind === "owl" ? 45 : (kind === "ram" ? 35 : 40),
      attackRange: kind === "ram" ? 3 : 2,
      state: "patrol", stateTimer: 0, tx: x, ty: y,
      chargeDir: 0, stun: 0, cooldown: 0,
    });
  }
  return threats;
}

function updateThreats(rng, dt, threats, playerPos, playerSafe, campRadius, isNight) {
  const events = [];
  const dist = (a, b, c, d) => Math.hypot(a - c, b - d);
  for (const t of threats) {
    if (t.stun > 0) { t.stun -= dt; continue; }
    if (t.cooldown > 0) t.cooldown -= dt;
    if (!isNight) { t.state = "retreat"; t.x += 100 * dt; t.y += 100 * dt; continue; }
    const dp = dist(t.x, t.y, playerPos[0], playerPos[1]);
    const inSafe = dist(playerPos[0], playerPos[1], 0, 0) <= campRadius;
    if (t.kind === "deer") {
      if (playerSafe || inSafe) {
        t.state = "circle";
        t.x += Math.cos(Date.now() * 0.001 + t.speed) * 2 * dt;
        t.y += Math.sin(Date.now() * 0.001) * 2 * dt;
      } else if (t.state !== "chase" && dp < t.detect) {
        t.state = "chase";
        events.push({ type: "spotted", threat: t.kind });
      } else if (t.state === "chase") {
        if (dp > t.detect * 1.6) { t.state = "search"; t.stateTimer = 4; events.push({ type: "lost", threat: t.kind }); }
        else {
          const d = Math.max(0.01, dp);
          t.x += (playerPos[0] - t.x) / d * t.speed * dt;
          t.y += (playerPos[1] - t.y) / d * t.speed * dt;
          if (dp < t.attackRange && t.cooldown <= 0) { t.cooldown = 2; events.push({ type: "attack", threat: t.kind, damage: 25 }); }
        }
      } else if (t.state === "search") {
        t.stateTimer -= dt;
        if (t.stateTimer <= 0) t.state = "patrol";
      } else {
        t.stateTimer -= dt;
        if (t.stateTimer <= 0) { t.tx = rng.range(-60, 60); t.ty = rng.range(-60, 60); t.stateTimer = rng.range(5, 10); }
        const d = Math.max(0.01, Math.hypot(t.tx - t.x, t.ty - t.y));
        t.x += (t.tx - t.x) / d * t.speed * 0.4 * dt;
        t.y += (t.ty - t.y) / d * t.speed * 0.4 * dt;
      }
    } else if (t.kind === "owl") {
      if (playerSafe || inSafe) { t.state = "circle"; }
      else if (dp < t.detect) {
        t.state = "swoop";
        const d = Math.max(0.01, dp);
        t.x += (playerPos[0] - t.x) / d * t.speed * 1.2 * dt;
        t.y += (playerPos[1] - t.y) / d * t.speed * 1.2 * dt;
        if (dp < t.attackRange && t.cooldown <= 0) { t.cooldown = 3; events.push({ type: "attack", threat: "owl", damage: 15 }); }
      } else { t.state = "patrol"; }
    } else if (t.kind === "ram") {
      if (t.state === "charge_up") {
        t.stateTimer -= dt;
        if (t.stateTimer <= 0) {
          t.state = "charging"; t.stateTimer = 1.2;
          t.chargeDir = Math.atan2(playerPos[1] - t.y, playerPos[0] - t.x);
          events.push({ type: "ram_charge", threat: "ram" });
        }
      } else if (t.state === "charging") {
        t.stateTimer -= dt;
        t.x += Math.cos(t.chargeDir) * t.speed * 3.2 * dt;
        t.y += Math.sin(t.chargeDir) * t.speed * 3.2 * dt;
        if (t.stateTimer <= 0) { t.state = "search"; t.stateTimer = 3; }
      } else if (playerSafe || inSafe) {
        t.state = "circle";
      } else if (dp < t.detect && t.cooldown <= 0) {
        t.state = "charge_up"; t.stateTimer = 1;
        events.push({ type: "spotted", threat: "ram" });
      } else if (t.stateTimer > 0) {
        t.stateTimer -= dt;
      }
    }
  }
  return events;
}

// ------------------------------------------------------------------ animals

const SPECIES = {
  bunny: { speed: 3.0, flee: 6 },
  deer: { speed: 4.0, flee: 10 },
  bird: { speed: 5.0, flee: 8 },
};

function updateAnimals(rng, dt, animals, playerPos, isNight) {
  for (const a of animals) {
    const spec = SPECIES[a.species];
    if (!spec) continue;
    if (isNight && a.species !== "wolf") { a.state = "sleep"; continue; }
    const d = Math.hypot(a.x - playerPos[0], a.y - playerPos[1]);
    if (spec.flee && d < spec.flee && a.state !== "flee") {
      a.state = "flee"; a.stateTimer = 2;
      const ang = Math.atan2(a.y - playerPos[1], a.x - playerPos[0]);
      a.tx = a.x + Math.cos(ang) * 25;
      a.ty = a.y + Math.sin(ang) * 25;
    }
    if (a.state === "flee") {
      a.stateTimer -= dt;
      const dd = Math.max(0.01, Math.hypot(a.tx - a.x, a.ty - a.y));
      a.x += (a.tx - a.x) / dd * spec.speed * 1.5 * dt;
      a.y += (a.ty - a.y) / dd * spec.speed * 1.5 * dt;
      if (a.stateTimer <= 0) { a.state = "idle"; a.stateTimer = rng.range(1, 3); }
    } else if (a.state === "walk") {
      a.stateTimer -= dt;
      const dd = Math.max(0.01, Math.hypot(a.tx - a.x, a.ty - a.y));
      a.x += (a.tx - a.x) / dd * spec.speed * 0.6 * dt;
      a.y += (a.ty - a.y) / dd * spec.speed * 0.6 * dt;
      if (a.stateTimer <= 0 || dd < 1) { a.state = "idle"; a.stateTimer = rng.range(1, 5); }
    } else {
      a.stateTimer -= dt;
      if (a.stateTimer <= 0) {
        a.state = "walk"; a.stateTimer = rng.range(2, 5);
        a.tx = a.x + rng.range(-15, 15);
        a.ty = a.y + rng.range(-15, 15);
      }
    }
  }
}

// ------------------------------------------------------------------ player

class PlayerState {
  constructor(GD, passives) {
    passives = passives || {};
    const p = GD.settings.player;
    this.x = 0; this.y = 0; this.heading = 0;
    this.maxHealth = p.max_health + (passives.health_bonus || 0);
    this.maxHunger = p.max_hunger;
    this.maxStamina = p.max_stamina;
    this.health = this.maxHealth;
    this.hunger = this.maxHunger;
    this.stamina = this.maxStamina;
    this.speedBonus = passives.speed_bonus || 0;
    this.hungerRate = p.hunger_rate * (passives.hunger_rate || 1);
    this.healthRegen = passives.health_regen || 0;
    this.woodBonus = passives.wood_bonus || 0;
    this.lootBonus = passives.loot_bonus || 0;
    this.foodBonus = passives.food_bonus || 0;
    this.grindBonus = passives.grind_bonus || 0;
    this.craftDiscount = passives.craft_discount || 0;
    this.alive = true;
    this.sprinting = false;
  }
  heal(a) { this.health = Math.min(this.maxHealth, this.health + a); }
  eat(hunger, health, stamina) {
    this.hunger = Math.min(this.maxHunger, this.hunger + hunger);
    this.heal(health || 0);
    this.stamina = Math.min(this.maxStamina, this.stamina + (stamina || 0));
  }
  damage(a) {
    this.health = Math.max(0, this.health - a);
    if (this.health <= 0) this.alive = false;
    return !this.alive;
  }
  tick(dt, sprinting, inSafeZone, fireLit) {
    const events = [];
    if (sprinting && this.stamina > 0) {
      this.stamina = Math.max(0, this.stamina - 12 * dt);
      this.sprinting = true;
    } else {
      this.sprinting = false;
      this.stamina = Math.min(this.maxStamina, this.stamina + 8 * dt);
    }
    this.hunger = Math.max(0, this.hunger - this.hungerRate * dt);
    if (this.hunger <= 0) { this.damage(1 * dt); events.push("starving"); }
    else if (this.hunger < 25) events.push("hungry");
    if (inSafeZone && fireLit) this.heal(0.5 * dt);
    if (this.healthRegen) this.heal(this.healthRegen * dt);
    if (this.health < 25) events.push("low_health");
    return events;
  }
  toSave() { return { x: this.x, y: this.y, health: this.health, hunger: this.hunger, stamina: this.stamina, alive: this.alive }; }
  load(d) {
    this.x = d.x || 0; this.y = d.y || 0;
    this.health = d.health != null ? d.health : this.maxHealth;
    this.hunger = d.hunger != null ? d.hunger : this.maxHunger;
    this.stamina = d.stamina != null ? d.stamina : this.maxStamina;
    this.alive = d.alive !== false;
  }
}

// ----------------------------------------------------------------- children

const CHILDREN = {
  dino_kid: { name: "Dino Kid", colour: "#d94033", rescue_requirement: 2, guard: "wolves",
    personality: "Boisterous and brave, even when shivering.",
    dialogue: ["That dragon was THIS big, honest!", "Can I keep the axe? Please?", "I wasn't scared. Much."] },
  squid_kid: { name: "Squid Kid", colour: "#4073d9", rescue_requirement: 3, guard: "bears",
    personality: "Quiet, observant, draws maps on scraps of bark.",
    dialogue: ["I marked the way on this bark. See?", "The cave hummed at night. Did you hear it?", "Thank you. Truly."] },
  kraken_kid: { name: "Kraken Kid", colour: "#e6cc33", rescue_requirement: 5, guard: "bears",
    personality: "Joke-cracker, hides fear behind laughter.",
    dialogue: ["A kraken? In a forest? I know, right!", "You took your time, haha!", "Six bears. SIX. Count them next time."] },
  koala_kid: { name: "Koala Kid", colour: "#8c8c8c", rescue_requirement: 6, guard: "bears",
    personality: "Sleepy, gentle, hums old lullabies to stay calm.",
    dialogue: ["I knew someone would come. Eventually.", "Is the fire warm? I like warm.", "The grey cave was cold. And loud."] },
};

// -------------------------------------------------------------- game manager

class Game {
  constructor(GD, seed, classId, profile) {
    this.GD = GD;
    this.profile = profile || { diamonds: 0, owned_classes: ["camper"], best_day: 0, wins: 0, runs: 0 };
    const classes = GD.classes.classes;
    this.classId = classes[classId] ? classId : "camper";
    const passives = (classes[this.classId].passives) || {};
    this.seed = seed != null && seed !== "" ? seed : Math.floor(Math.random() * 999999);
    this.rng = makeRng(String(this.seed));
    this.world = generateWorld(GD, this.seed, GD.settings.world.size, GD.settings.world.height_scale);
    this.inv = new Inventory(GD, 24);
    this.bench = new CraftingBench(GD, this.inv);
    this.campfire = new Campfire(GD);
    this.dayNight = new DayNight(GD);
    this.weather = new Weather(this.seed);
    this.plots = [];
    this.children = {};
    for (const id of Object.keys(CHILDREN)) this.children[id] = { rescued: false, x: 0, y: 0, wanderTimer: 0, dialogueIndex: 0 };
    this.animals = [];
    this.threats = [];
    this.player = new PlayerState(GD, passives);
    this.structures = [];
    this.discovered = new Set();
    this.treeStates = {};
    this.nextStructureId = 0;
    this.victory = false;
    this.defeat = false;
    this.finished = false;
    this.earnedDiamonds = 0;
    this.hasMap = false;
    this.stats = { nights_survived: 0, locations_discovered: 0, trees_felled: 0 };
    for (const [id, qty] of Object.entries(classes[this.classId].starting_items || {})) this.inv.add(id, qty);
    if (this.inv.count("old_axe") === 0) this.inv.add("old_axe", 1);
    this.inv.add("log", 6);
    this.inv.add("coal", 1);
    this._populateAnimals(0, 0, 60, 8);
  }
  _populateAnimals(x, y, radius, count) {
    for (let i = 0; i < count; i++) {
      const ang = this.rng.range(0, Math.PI * 2);
      const d = this.rng.range(15, radius);
      this.animals.push({
        id: "animal_" + this.animals.length,
        species: this.rng.pick(["bunny", "bunny", "deer", "bird"]),
        x: x + Math.cos(ang) * d, y: y + Math.sin(ang) * d,
        state: "idle", stateTimer: this.rng.range(1, 4), tx: 0, ty: 0,
      });
    }
  }
  _distToCamp() { return Math.hypot(this.player.x, this.player.y); }
  _biomeAtPlayer() { return this.world.biomeAt(Math.floor(this.player.x), Math.floor(this.player.y)); }

  tick(dt) {
    if (this.finished) return [];
    const events = [];
    for (const ev of this.dayNight.tick(dt)) {
      if (ev === "night_start") {
        this.threats = spawnNightThreats(this.rng, this.dayNight.day, this.campfire.safeRadius, [this.player.x, this.player.y]);
        events.push({ type: "night_start", night: this.dayNight.day });
      } else if (ev === "new_day") {
        this.weather.onNewDay();
        this.stats.nights_survived = this.dayNight.day - 1;
        this._populateAnimals(this.player.x, this.player.y, 70, 4);
        events.push({ type: "new_day", day: this.dayNight.day });
        if (this.dayNight.day > 99) { this.victory = true; this._finish(); events.push({ type: "victory" }); }
      }
    }
    this.weather.tick(dt, this._biomeAtPlayer());
    const isNight = this.dayNight.isNight();
    const cf = this.campfire.tick(dt, isNight, this.weather.fuelMultiplier);
    if (cf.event === "out") events.push({ type: "campfire_out" });
    else if (cf.event === "critical") events.push({ type: "fuel_critical", fraction: cf.fraction });
    else if (cf.event === "low") events.push({ type: "fuel_low", fraction: cf.fraction });

    const playerSafe = this.campfire.inSafeZone(this._distToCamp());
    for (const w of this.player.tick(dt, this.player.sprinting, playerSafe, this.campfire.lit)) {
      events.push({ type: w });
    }
    if (!this.player.alive) { this.defeat = true; this._finish(); events.push({ type: "defeat" }); }

    for (const plot of this.plots) plot.tick(dt / this.dayNight.cycleLength, this.weather.isWet);
    this._updateChildren(dt);
    updateAnimals(this.rng, dt, this.animals, [this.player.x, this.player.y], isNight);
    for (const te of updateThreats(this.rng, dt, this.threats, [this.player.x, this.player.y], playerSafe, this.campfire.safeRadius, isNight)) {
      if (te.type === "attack") {
        this.player.damage(te.damage);
        if (!this.player.alive) { this.defeat = true; this._finish(); events.push({ type: "defeat" }); }
      }
      events.push(te);
    }
    this._checkDiscoveries();
    return events;
  }
  _updateChildren(dt) {
    for (const id of Object.keys(this.children)) {
      const c = this.children[id];
      if (!c.rescued) continue;
      c.wanderTimer -= dt;
      if (c.wanderTimer <= 0) {
        const ang = this.rng.range(0, Math.PI * 2);
        const r = this.rng.range(2, Math.max(4, this.campfire.safeRadius * 0.6));
        c.x = Math.cos(ang) * r;
        c.y = Math.sin(ang) * r;
        c.wanderTimer = this.rng.range(4, 10);
      }
    }
  }
  _checkDiscoveries() {
    for (const loc of this.world.locations) {
      if (!loc.discovered && Math.hypot(loc.x - this.player.x, loc.y - this.player.y) < 18) {
        loc.discovered = true;
        this.discovered.add(loc.id);
        this.stats.locations_discovered = this.discovered.size;
      }
    }
  }
  _finish() {
    this.finished = true;
    this.stats.nights_survived = Math.max(0, this.dayNight.day - 1);
    this.stats.locations_discovered = this.discovered.size;
    const cfg = this.GD.progression.diamonds;
    let d = this.stats.nights_survived * cfg.per_night_survived;
    d += this.rescuedCount() * cfg.per_child_rescued;
    d += this.stats.locations_discovered * cfg.per_location_discovered;
    d += (this.campfire.level - 1) * cfg.campfire_level_bonus;
    if (this.victory) d += cfg.victory_bonus;
    this.earnedDiamonds = Math.floor(d);
    this.profile.diamonds += this.earnedDiamonds;
    this.profile.runs = (this.profile.runs || 0) + 1;
    this.profile.best_day = Math.max(this.profile.best_day || 0, this.dayNight.day);
    if (this.victory) this.profile.wins = (this.profile.wins || 0) + 1;
  }
  rescuedCount() { return Object.values(this.children).filter((c) => c.rescued).length; }

  addFuel(itemId, qty) {
    if (!this.GD.progression.fuel_values[itemId]) return false;
    if (this.inv.count(itemId) < (qty || 1)) return false;
    this.inv.remove(itemId, qty || 1);
    this.campfire.addFuel(itemId, qty || 1);
    return true;
  }
  chopTree(index, toolId) {
    const tree = this.world.trees[index];
    if (!tree || tree.removed) return { fell: false, damage: 0, drops: {} };
    if (!this.treeStates[index]) this.treeStates[index] = new TreeHarvest(this.GD, tree.type, this.rng);
    const result = this.treeStates[index].hit(toolId, this.player.woodBonus);
    if (result.fell) {
      tree.removed = true;
      this.stats.trees_felled += 1;
      for (const [id, qty] of Object.entries(result.drops)) this.inv.add(id, qty);
    }
    return result;
  }
  loot(locationId) {
    const loc = this.world.locations.find((l) => l.id === locationId);
    if (!loc || loc.looted || !loc.discovered) return null;
    loc.looted = true;
    const loot = rollLoot(this.GD, this.rng, loc.type, this.player.lootBonus);
    for (const [id, qty] of Object.entries(loot)) this.inv.add(id, qty);
    return loot;
  }
  canRescue(childId) { return this.campfire.level >= CHILDREN[childId].rescue_requirement; }
  rescueChild(childId) {
    if (!this.canRescue(childId) || this.children[childId].rescued) return false;
    this.children[childId].rescued = true;
    return true;
  }
  doGrind(itemId, qty) { return grind(this.GD, this.inv, itemId, qty, this.player.grindBonus); }
  craft(recipeId) {
    if (!this.bench.craft(recipeId, this.player.craftDiscount)) return false;
    if (recipeId === "map") this.hasMap = true;
    return true;
  }
  upgradeBench() { return this.bench.upgrade(this.player.craftDiscount); }
  placeStructure(type, x, y, rotation) {
    for (const s of this.structures) {
      if (Math.abs(s.x - x) < 3 && Math.abs(s.y - y) < 3) return null;
    }
    if (Math.hypot(x, y) < 3) return null;
    const struct = { id: this.nextStructureId++, type, x, y, rotation: rotation || 0 };
    this.structures.push(struct);
    const def = this.GD.recipes.structure_items[type];
    if (def && def.farm) {
      const plot = new FarmPlot(this.GD, "plot_" + this.plots.length, x, y);
      this.plots.push(plot);
    }
    return struct;
  }
  plant(plotId, seedsId) {
    const plot = this.plots.find((p) => p.id === plotId);
    if (!plot || this.inv.count(seedsId) < 1 || !plot.plant(seedsId)) return false;
    this.inv.remove(seedsId, 1);
    return true;
  }
  harvestPlot(plotId) {
    const plot = this.plots.find((p) => p.id === plotId);
    if (!plot) return null;
    const result = plot.harvest(this.rng);
    if (!result) return null;
    this.inv.add(result.crop, result.qty);
    if (result.seedQty > 0) this.inv.add(result.seeds, result.seedQty);
    return result;
  }
  cook(recipeId) {
    const recipe = this.GD.recipes.cooking[recipeId];
    if (!recipe || !this.inv.consume(recipe.cost)) return false;
    this.inv.add(recipeId, 1 + (this.player.foodBonus >= 0.5 ? 1 : 0));
    return true;
  }
  cookOnFire() {
    if (!this.campfire.lit || this.inv.count("raw_meat") < 1) return false;
    this.inv.remove("raw_meat", 1);
    this.inv.add("cooked_meat", 1);
    return true;
  }
  useBed(type) {
    const def = this.GD.recipes.structure_items[type];
    const days = (def && def.skip_days) || 1;
    this.dayNight.skipDays(days);
    return days;
  }
  stunThreats() { for (const t of this.threats) t.stun = Math.max(t.stun, 4 * this.rng.range(0.5, 1)); }

  toSave() {
    return {
      seed: this.seed, class: this.classId,
      day: this.dayNight.day, time: this.dayNight.time,
      player: this.player.toSave(), inventory: this.inv.toSave(),
      bench_level: this.bench.level, campfire: this.campfire.toSave(),
      weather: this.weather.toSave(), structures: this.structures,
      plots: this.plots.map((p) => p.toSave()),
      children: Object.fromEntries(Object.entries(this.children).map(([id, c]) => [id, { rescued: c.rescued }])),
      locations: this.world.locations.map((l) => ({ id: l.id, discovered: l.discovered, looted: !!l.looted })),
      removed_trees: this.world.trees.map((t, i) => (t.removed ? i : -1)).filter((i) => i >= 0),
      stats: this.stats, hasMap: this.hasMap,
    };
  }
  load(data) {
    this.classId = data.class || "camper";
    const passives = (this.GD.classes.classes[this.classId] && this.GD.classes.classes[this.classId].passives) || {};
    this.player = new PlayerState(this.GD, passives);
    this.player.load(data.player || {});
    this.inv.load(data.inventory || []);
    this.bench.level = data.bench_level || 1;
    this.campfire.load(data.campfire || {});
    this.dayNight.load({ day: data.day || 1, time: data.time || 0 });
    this.weather.load(data.weather || {});
    this.structures = data.structures || [];
    this.nextStructureId = this.structures.length;
    this.plots = (data.plots || []).map((p) => {
      const plot = new FarmPlot(this.GD, p.id, p.x, p.y);
      plot.load(p);
      return plot;
    });
    for (const [id, c] of Object.entries(data.children || {})) {
      if (this.children[id]) this.children[id].rescued = !!c.rescued;
    }
    for (const locSave of data.locations || []) {
      const loc = this.world.locations.find((l) => l.id === locSave.id);
      if (loc) {
        loc.discovered = !!locSave.discovered;
        loc.looted = !!locSave.looted;
        if (loc.discovered) this.discovered.add(loc.id);
      }
    }
    for (const idx of data.removed_trees || []) {
      if (this.world.trees[idx]) this.world.trees[idx].removed = true;
    }
    this.stats = data.stats || this.stats;
    this.hasMap = !!data.hasMap;
  }
}

// ----------------------------------------------------------- class purchases

function canBuyClass(GD, profile, classId) {
  return !profile.owned_classes.includes(classId) && profile.diamonds >= GD.classes.classes[classId].price;
}

function buyClass(GD, profile, classId) {
  if (!canBuyClass(GD, profile, classId)) return false;
  profile.diamonds -= GD.classes.classes[classId].price;
  profile.owned_classes.push(classId);
  return true;
}

// ------------------------------------------------------------------ exports

if (typeof module !== "undefined") {
  module.exports = {
    makeRng, generateWorld, BIOMES, Inventory, CraftingBench, grind, Campfire,
    DayNight, Weather, FarmPlot, TreeHarvest, rollLoot, spawnNightThreats,
    updateThreats, updateAnimals, SPECIES, PlayerState, CHILDREN, Game,
    canBuyClass, buyClass, WEATHERS,
  };
}
