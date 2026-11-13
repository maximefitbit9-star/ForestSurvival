// Headless end-to-end smoke test: runs the real app code (main.js, ui.js,
// render.js, logic.js) against minimal DOM and THREE stubs.
// Run: node tests/test_web_smoke.js
"use strict";
const path = require("path");
const fs = require("fs");
const vm = require("vm");

const WEB = path.join(__dirname, "..", "web");
let passed = 0, failed = 0;
function check(name, fn) {
  try { fn(); passed++; }
  catch (e) { failed++; console.log("FAIL: " + name + " -> " + (e && e.stack ? e.stack.split("\n").slice(0, 3).join("\n") : e)); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || "assertion failed"); }

// ---------------------------------------------------------------- DOM stub

class StyleObj { constructor() { this.props = {}; } }
class ClassList {
  constructor() { this.set = new Set(); }
  add(...c) { c.forEach((x) => this.set.add(x)); }
  remove(...c) { c.forEach((x) => this.set.delete(x)); }
  contains(c) { return this.set.has(c); }
  toggle(c, force) {
    const on = force === undefined ? !this.set.has(c) : force;
    if (on) this.set.add(c); else this.set.delete(c);
    return on;
  }
}
class StubElement {
  constructor(tag) {
    this.tagName = (tag || "div").toUpperCase();
    this.children = [];
    this.classList = new ClassList();
    this.style = new StyleObj();
    this.dataset = {};
    this.textContent = "";
    this.innerHTML = "";
    this.title = "";
    this.value = "0";
    this.checked = false;
    this.offsetWidth = 100;
    this._listeners = {};
    this._timer = null;
  }
  addEventListener(type, fn) { (this._listeners[type] = this._listeners[type] || []).push(fn); }
  dispatch(type, event) { (this._listeners[type] || []).forEach((fn) => fn(event || { preventDefault() {}, stopPropagation() {} })); }
  appendChild(child) { this.children.push(child); return child; }
  removeChild(child) { const i = this.children.indexOf(child); if (i >= 0) this.children.splice(i, 1); }
  remove() {}
  getBoundingClientRect() { return { left: 0, top: 0, width: 100, height: 100 }; }
  querySelector() { return new StubElement("input"); }
  querySelectorAll() { return []; }
  getContext() { return null; }
  requestPointerLock() {}
  setAttribute() {}
}

const elements = {};
function getEl(id) {
  if (!elements[id]) elements[id] = new StubElement("div");
  return elements[id];
}

const storage = {};
const documentStub = {
  getElementById: getEl,
  createElement: (tag) => new StubElement(tag),
  querySelectorAll: () => [],
  addEventListener: () => {},
  pointerLockElement: null,
  documentElement: new StubElement("html"),
  body: new StubElement("body"),
};
const windowListeners = {};
let rafCallbacks = [];
const windowStub = {
  innerWidth: 1280, innerHeight: 720, devicePixelRatio: 1,
  addEventListener: (t, fn) => { (windowListeners[t] = windowListeners[t] || []).push(fn); },
  dispatchKey: (key, type) => (windowListeners[type || "keydown"] || []).forEach((fn) => fn({ key, preventDefault() {} })),
  dispatch: (type, event) => (windowListeners[type] || []).forEach((fn) => fn(event || {})),
  localStorage: {
    getItem: (k) => (k in storage ? storage[k] : null),
    setItem: (k, v) => { storage[k] = String(v); },
    removeItem: (k) => { delete storage[k]; },
  },
  requestAnimationFrame: (fn) => { rafCallbacks.push(fn); return rafCallbacks.length; },
  alert: () => {},
  close: () => {},
};

// --------------------------------------------------------------- THREE stub

class V3 { constructor(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; }
  set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
  setScalar(s) { this.x = s; this.y = s; this.z = s; return this; } }
class Euler {
  constructor() { this._x = 0; this._y = 0; this._z = 0; this.order = "XYZ"; }
  get x() { return this._x; } set x(v) { this._x = v; }
  get y() { return this._y; } set y(v) { this._y = v; }
  get z() { return this._z; } set z(v) { this._z = v; }
  set(x, y, z) { this._x = x; this._y = y; this._z = z; return this; }
}
class Color {
  constructor(hex) { this.hex = hex || 0; }
  setHex(h) { this.hex = h; return this; }
  setRGB(r, g, b) { this.r = r; this.g = g; this.b = b; return this; }
  get r() { return ((this.hex >> 16) & 255) / 255; }
  get g() { return ((this.hex >> 8) & 255) / 255; }
  get b() { return (this.hex & 255) / 255; }
}
class Object3D {
  constructor() {
    this.position = new V3(); this.rotation = new Euler(); this.scale = new V3(1, 1, 1);
    this.visible = true; this.children = []; this.matrix = { elements: [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1] };
    this.material = null; this.geometry = null; this.userData = {};
    this.castShadow = false; this.frustumCulled = true;
  }
  add(c) { this.children.push(c); return c; }
  remove(c) { const i = this.children.indexOf(c); if (i >= 0) this.children.splice(i, 1); }
  setScale(s) { this.scale.set(s, s, s); }
  updateMatrix() {}
  rotateX() {} set_pos() {}
}
class BufferAttribute {
  constructor(arr, size) { this.array = arr; this.itemSize = size; this.count = arr.length / size; this.needsUpdate = false; }
  getX(i) { return this.array[i * this.itemSize]; }
  getY(i) { return this.array[i * this.itemSize + 1]; }
  getZ(i) { return this.array[i * this.itemSize + 2]; }
  setY(i, v) { this.array[i * this.itemSize + 1] = v; }
}
class BufferGeometry {
  constructor() { this.attributes = {}; this.children = []; }
  setAttribute(name, attr) { this.attributes[name] = attr; }
  rotateX() { return this; }
  computeVertexNormals() {}
}
class PlaneGeometry extends BufferGeometry {
  constructor(w, h, ws, hs) {
    super();
    const n = (ws + 1) * (hs + 1);
    this.attributes.position = new BufferAttribute(new Float32Array(n * 3), 3);
  }
}
class SimpleGeo extends BufferGeometry {}
const geoFactory = (name) => class extends SimpleGeo {};
class Material {
  constructor(opts) { Object.assign(this, opts || {}); this.color = new Color((opts && opts.color) || 0xffffff); }
  clone() { const m = new Material(this); m.color = new Color(this.color.hex); return m; }
}
class Mesh extends Object3D {
  constructor(geo, mat) { super(); this.geometry = geo; this.material = mat; }
}
class Group extends Object3D {}
class InstancedMesh extends Mesh {
  constructor(geo, mat, count) { super(geo, mat); this.count = count; this.instanceMatrix = { needsUpdate: false }; }
  setMatrixAt() {}
}
class Scene extends Object3D { constructor() { super(); this.background = new Color(0); this.fog = null; } }
class PerspectiveCamera extends Object3D {
  constructor(fov, aspect, near, far) { super(); this.fov = fov; this.aspect = aspect; }
  updateProjectionMatrix() {}
}
class Renderer {
  constructor() { this.shadowMap = { enabled: false, type: null }; this._pixel = 1; }
  setSize() {} setPixelRatio(p) { this._pixel = p; } render() {} dispose() {}
}
class Light extends Object3D { constructor(col, i) { super(); this.color = new Color(col); this.intensity = i == null ? 1 : i; } }
class AmbientLight extends Light {}
class DirectionalLight extends Light {
  constructor(c, i) { super(c, i); this.castShadow = false; this.shadow = { mapSize: { set() {} }, camera: {} }; }
}
class PointLight extends Light {}
class Fog { constructor(col, near, far) { this.color = new Color(col); this.near = near; this.far = far; } }
class Points extends Object3D {}
class PointsMaterial extends Material {}
class MeshBasicMaterial extends Material {}
class MeshLambertMaterial extends Material {}
class CylinderGeometry extends SimpleGeo { constructor() { super(); } }
class ConeGeometry extends SimpleGeo {}
class SphereGeometry extends SimpleGeo {}
class BoxGeometry extends SimpleGeo {}

const THREEstub = {
  Scene, PerspectiveCamera, WebGLRenderer: Renderer, AmbientLight, DirectionalLight,
  PointLight, Fog, PlaneGeometry, BufferGeometry, BufferAttribute, Mesh, Group,
  InstancedMesh, Object3D, Color, Points, PointsMaterial, MeshBasicMaterial,
  MeshLambertMaterial, CylinderGeometry, ConeGeometry, SphereGeometry, BoxGeometry,
  PCFSoftShadowMap: 1,
};

// Seed initial element state to match index.html (all screens hidden except the menu).
for (const id of ["screen-classes", "screen-saves", "screen-settings", "screen-credits",
  "screen-pause", "screen-result", "hud", "screen-inventory", "screen-crafting",
  "screen-map", "touch-controls"]) {
  getEl(id).classList.add("hidden");
}

// ------------------------------------------------------------- load scripts

function load(file) {
  const src = fs.readFileSync(path.join(WEB, file), "utf8");
  vm.runInThisContext(src, { filename: file });
}

global.window = windowStub;
global.document = documentStub;
Object.defineProperty(global, "navigator", { value: { userAgent: "node-test" }, writable: true, configurable: true });
global.localStorage = windowStub.localStorage;
global.requestAnimationFrame = windowStub.requestAnimationFrame;
global.alert = windowStub.alert;
global.THREE = THREEstub;
global.clearTimeout = clearTimeout;
global.setTimeout = () => 0; // warnings use timers; keep text until cleared like a real browser

load("js/config.js");
load("js/logic.js");
load("js/audio.js");
load("js/render.js");
load("js/controls.js");
load("js/ui.js");
load("js/main.js");

// --------------------------------------------------------------- helpers

let now = 0;
function pump(frames, stepMs) {
  stepMs = stepMs || 1000;
  for (let i = 0; i < frames; i++) {
    now += stepMs;
    const cbs = rafCallbacks;
    rafCallbacks = [];
    cbs.forEach((fn) => fn(now));
  }
}

function visible(id) { return !getEl(id).classList.contains("hidden"); }

// ------------------------------------------------------------------ tests

check("app boots to the main menu", () => {
  windowStub.dispatch("load");
  pump(2, 16);
  assert(visible("screen-menu"), "menu must be visible");
  assert(!visible("hud"), "hud must be hidden before a game starts");
  assert(typeof App !== "undefined" && App.profile, "profile loaded");
});

check("new game starts and the loop runs", () => {
  App.onAction("new-game");
  pump(5, 16);
  assert(App.game, "game exists");
  assert(visible("hud"), "hud shown");
  assert(App.world, "renderer created");
  assert(App.game.inv.count("old_axe") === 1, "starts with an axe");
  pump(30, 1000); // 30 simulated seconds
  assert(!App.game.finished, "game still running");
});

check("keyboard movement moves the player forward", () => {
  const g = App.game;
  const y0 = g.player.y;
  windowStub.dispatchKey("w", "keydown");
  pump(10, 100);
  windowStub.dispatchKey("w", "keyup");
  assert(g.player.y < y0 - 1, "player moved forward (y decreased), y0=" + y0 + " y=" + g.player.y);
});

check("chopping fells the nearest tree and yields logs", () => {
  const g = App.game;
  const idx = g.world.trees.findIndex((t) => !t.removed && (t.type === "normal" || t.type === "small"));
  const tree = g.world.trees[idx];
  g.player.x = tree.x; g.player.y = tree.y;
  const logs0 = g.inv.count("log");
  let fell = false;
  for (let i = 0; i < 30 && !fell; i++) { App.chop(); fell = g.world.trees[idx].removed; }
  assert(fell, "tree fell");
  assert(g.inv.count("log") > logs0, "logs collected");
  assert(g.stats.trees_felled >= 1, "stat tracked");
});

check("campfire interaction adds fuel", () => {
  const g = App.game;
  g.player.x = 0; g.player.y = 0;
  const fuel0 = g.campfire.fuel;
  App.interact();
  assert(g.campfire.fuel > fuel0, "fuel added from inventory");
});

check("night falls, threats spawn, and the safe zone protects", () => {
  const g = App.game;
  g.dayNight.time = g.dayNight.dayLength - 0.01;
  pump(3, 100);
  assert(g.dayNight.isNight(), "night started");
  // Night 1 is safe; force a later night to check threats.
  g.dayNight.day = 5;
  g.dayNight.time = g.dayNight.dayLength - 0.01;
  pump(3, 100);
  assert(g.threats.length >= 1, "threats spawned on a later night");
  g.player.x = 0; g.player.y = 0;
  pump(20, 500);
  assert(g.threats.every((t) => t.state !== "chase"), "safe zone prevents chases");
});

check("looting a discovered building yields items", () => {
  const g = App.game;
  const loc = g.world.locations.find((l) => GD.loot_tables.locations[l.type]);
  g.player.x = loc.x; g.player.y = loc.y;
  loc.discovered = true;
  pump(2, 100);
  const inv0 = g.inv.usedCount ? g.inv.usedCount() : 0;
  const loot = App.game.loot(loc.id);
  assert(loot && Object.keys(loot).length >= 1, "loot found");
});

check("child rescue is gated by campfire level and then works", () => {
  const g = App.game;
  g.dayNight.time = 10; // daytime
  g.campfire.level = 1;
  const cave = g.world.locations.find((l) => l.child === "dino_kid");
  g.player.x = cave.x; g.player.y = cave.y;
  cave.discovered = true; // walking within 18m discovers it in normal play
  App.interact();
  assert(!g.children.dino_kid.rescued, "rescue must fail at campfire level 1");
  g.campfire.level = 2;
  App.interact();
  assert(g.children.dino_kid.rescued, "dino kid rescued at campfire level 2");
  pump(10, 500);
  assert(getEl("hud-warning").textContent.includes("Rescued"), "rescue message shown");
});

check("saving writes to localStorage and reload restores state", () => {
  App.saveGame();
  assert(storage["wildwood_slot_0"], "slot saved");
  const day = App.game.dayNight.day;
  const data = JSON.parse(storage["wildwood_slot_0"]);
  assert(data.day === day, "day persisted");
  App.onAction("main-menu");
  assert(visible("screen-menu"), "back at menu");
  App.startGame(0);
  assert(App.game.dayNight.day === day, "loaded save restores the day");
  assert(App.game.children.dino_kid.rescued, "loaded save restores rescues");
});

check("victory at day 99 shows the result screen and awards diamonds", () => {
  const g = App.game;
  const d0 = App.profile.diamonds;
  g.dayNight.day = 99;
  g.dayNight.time = g.dayNight.cycleLength - 0.01;
  pump(3, 100);
  assert(g.finished && g.victory, "victory triggered");
  assert(visible("screen-result"), "result screen shown");
  assert(App.profile.diamonds > d0, "diamonds awarded");
  assert(JSON.parse(storage["wildwood_profile"]).diamonds === App.profile.diamonds, "profile persisted");
  assert(getEl("result-title").textContent.includes("Survived"), "victory title shown");
});

check("defeat also grants diamonds and shows the screen", () => {
  App.onAction("result-new");
  const g = App.game;
  const d0 = App.profile.diamonds;
  g.dayNight.day = 10;
  g.player.health = 0.5;
  g.player.hunger = 0;
  pump(30, 1000);
  assert(g.finished && g.defeat, "defeat triggered");
  assert(App.profile.diamonds > d0, "diamonds persist after defeat");
  assert(getEl("result-title").textContent.includes("Forest"), "defeat title shown");
});

check("crafting: bench upgrade consumes materials and unlocks recipes", () => {
  App.onAction("result-new");
  const g = App.game;
  g.inv.add("wood", 300); g.inv.add("scrap", 300);
  g.inv.add("cultist_gem", 5); g.inv.add("forest_gem", 2);
  const wood0 = g.inv.count("wood");
  assert(g.upgradeBench(), "upgrade to tier 2");
  assert(g.inv.count("wood") === wood0 - 5, "upgrade cost consumed (5 wood)");
  assert(g.bench.canCraft("farm_plot"), "tier 2 recipes unlocked");
  while (g.bench.level < 5) assert(g.upgradeBench(), "reach tier 5");
  assert(g.bench.canCraft("weather_machine"), "tier 5 recipes unlocked");
});

check("mobile mode: joystick input drives movement", () => {
  App.onAction("result-new");
  const g = App.game;
  assert(g, "game restarted");
  App.controls.isMobile = true;
  App.controls.moveInput.x = 0;
  App.controls.moveInput.y = 1; // full forward on the virtual stick
  const y0 = g.player.y;
  pump(10, 100);
  App.controls.moveInput.y = 0;
  assert(g.player.y < y0 - 1, "joystick forward moved the player, y0=" + y0 + " y=" + g.player.y);
  App.controls.isMobile = false;
});

console.log("\n" + passed + " passed, " + failed + " failed");
if (failed > 0) process.exit(1);
