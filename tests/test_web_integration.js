// Integration test: verifies the HTML shell and JS wiring are consistent.
// Run: node tests/test_web_integration.js
"use strict";
const fs = require("fs");
const path = require("path");

const WEB = path.join(__dirname, "..", "web");
let passed = 0, failed = 0;
function check(name, fn) {
  try { fn(); passed++; }
  catch (e) { failed++; console.log("FAIL: " + name + " -> " + e.message); }
}
function assert(cond, msg) { if (!cond) throw new Error(msg || "assertion failed"); }

const html = fs.readFileSync(path.join(WEB, "index.html"), "utf8");
const jsFiles = ["config.js", "logic.js", "audio.js", "render.js", "controls.js", "ui.js", "main.js"];

check("all script files exist and are referenced", () => {
  for (const f of jsFiles) {
    assert(html.includes('src="js/' + f + '"'), "index.html must reference js/" + f);
    assert(fs.existsSync(path.join(WEB, "js", f)), "js/" + f + " must exist");
  }
  assert(html.includes('src="vendor/three.min.js"'), "must vendor three.js");
  assert(fs.existsSync(path.join(WEB, "vendor", "three.min.js")), "three.min.js must exist");
  assert(fs.existsSync(path.join(WEB, "vendor", "THREE-LICENSE.txt")), "three.js licence must be recorded");
  assert(html.includes('href="css/style.css"'), "must reference the stylesheet");
  assert(fs.existsSync(path.join(WEB, "css", "style.css")), "stylesheet must exist");
});

check("every getElementById target exists in the HTML", () => {
  const ids = new Set();
  for (const m of html.matchAll(/id="([^"]+)"/g)) ids.add(m[1]);
  for (const f of jsFiles) {
    const src = fs.readFileSync(path.join(WEB, "js", f), "utf8");
    for (const m of src.matchAll(/getElementById\("([^"]+)"\)/g)) {
      assert(ids.has(m[1]), "js/" + f + " references missing element #" + m[1]);
    }
  }
});

check("data-actions used by the JS exist in the HTML", () => {
  const actions = new Set();
  for (const m of html.matchAll(/data-action="([^"]+)"/g)) actions.add(m[1]);
  const handled = ["continue", "new-game", "load", "classes", "settings", "credits", "exit",
    "classes-back", "classes-confirm", "saves-back", "settings-back", "credits-back",
    "resume", "save", "main-menu", "result-menu", "result-new",
    "inv-close", "craft-close", "map-close"];
  for (const a of handled) {
    assert(actions.has(a) || a === "start-slot", "HTML missing data-action=" + a);
  }
});

check("touch controls are present for mobile", () => {
  for (const id of ["joystick", "joystick-knob", "touch-buttons", "btn-act", "btn-chop",
    "btn-inv", "btn-craft", "btn-map", "btn-sprint", "btn-light", "btn-pause"]) {
    assert(html.includes('id="' + id + '"'), "missing touch element #" + id);
  }
});

check("viewport meta allows mobile play", () => {
  assert(html.includes("user-scalable=no"), "viewport must prevent zoom during play");
});

check("config bundle matches the source JSON configs", () => {
  const { GD } = require(path.join(WEB, "js", "config.js"));
  const items = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "config", "items.json"), "utf8"));
  assert(Object.keys(GD.items.items).length === Object.keys(items.items).length,
    "item counts must match config/items.json");
  const recipes = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "config", "recipes.json"), "utf8"));
  assert(Object.keys(GD.recipes.bench_levels).length === 5, "five bench tiers");
  const t1 = GD.recipes.bench_levels["1"].recipes.map;
  assert(t1.cost.wood === 3, "verified Map cost 3 wood");
  assert(GD.recipes.bench_levels["5"].recipes.weather_machine.cost.forest_gem === 1,
    "verified weather machine cost");
});

check("no external network URLs in game code", () => {
  for (const f of jsFiles) {
    const src = fs.readFileSync(path.join(WEB, "js", f), "utf8");
    assert(!/https?:\/\//.test(src), "js/" + f + " must not load external resources (fully offline)");
  }
});

console.log("\n" + passed + " passed, " + failed + " failed");
if (failed > 0) process.exit(1);
