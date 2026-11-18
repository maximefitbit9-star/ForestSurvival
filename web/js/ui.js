// DOM UI: menus, HUD, inventory, crafting, map, saves (localStorage).
"use strict";

const RARITY_COLOURS = {
  common: "#e8f0e5", uncommon: "#4ec94e", rare: "#4e9be0", very_rare: "#b04ee0", special: "#e0b74e",
};

const ITEM_ICONS = {
  log: "\u{1FAB5}", wood: "\u{1FA72}", sapling: "\u{1F331}", coal: "\u{26CF}", scrap: "\u{1F529}",
  bolt: "\u{1F529}", sheet_metal: "\u{1F6E0}", tire: "\u{1F3CE}", chair: "\u{1F6BA}", radio: "\u{1F4FB}",
  broken_machinery: "\u2699", fuel_canister: "\u{1F6E8}", biofuel: "\u{1F7E9}", oil_barrel: "\u{1F6B1}",
  carrot: "\u{1F955}", corn: "\u{1F33D}", pumpkin: "\u{1F383}", chili: "\u{1F336}", berries: "\u{1FAD0}",
  apple: "\u{1F34E}", raw_meat: "\u{1F357}", cooked_meat: "\u{1F356}", fish: "\u{1F41F}",
  hearty_stew: "\u{1F372}", bandage: "\u{1FA79}", medkit: "\u{1F691}", carrot_seeds: "\u{1F33F}",
  corn_seeds: "\u{1F33F}", pumpkin_seeds: "\u{1F33F}", chili_seeds: "\u{1F33F}", bunny_foot: "\u{1F407}",
  pelt: "\u{1F9F4}", wolf_pelt: "\u{1F43A}", cultist_gem: "\u{1F48E}", forest_gem_fragment: "\u{1F48E}",
  forest_gem: "\u{1F48E}", red_key: "\u{1F5DD}", yellow_key: "\u{1F5DD}", grey_key: "\u{1F5DD}",
  blue_key: "\u{1F5DD}", old_axe: "\u{1FA03}", good_axe: "\u{1FA03}", strong_axe: "\u{1FA03}",
  ice_axe: "\u2744", chainsaw: "\u{1F6E0}", flashlight: "\u{1F526}",
};

const UI = {
  screens: {},
  els: {},
  game: null,
  selectedInvSlot: null,
  craftTab: "craft",
  placingStructure: null,
  placingRotation: 0,

  init() {
    const ids = ["screen-menu", "screen-classes", "screen-saves", "screen-settings",
      "screen-credits", "screen-pause", "screen-result", "hud", "screen-inventory",
      "screen-crafting", "screen-map", "touch-controls"];
    for (const id of ids) this.els[id] = document.getElementById(id);
    document.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        AudioSys.play("menu_click");
        App.onAction(btn.dataset.action, btn);
      });
    });
    document.querySelectorAll("[data-preset]").forEach((btn) => {
      btn.addEventListener("click", () => App.applyPreset(btn.dataset.preset));
    });
    document.querySelectorAll(".craft-tabs .tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        this.craftTab = tab.dataset.tab;
        document.querySelectorAll(".craft-tabs .tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        this.refreshCrafting();
      });
    });
    this.els["screen-settings"].querySelector("#opt-fullscreen").addEventListener("change", (e) => {
      App.toggleFullscreen(e.target.checked);
    });
    this.els["screen-settings"].querySelector("#opt-sound").addEventListener("input", (e) => {
      App.userSettings.sound_volume = parseFloat(e.target.value);
      App.saveSettings();
    });
    this.els["screen-settings"].querySelector("#opt-music").addEventListener("input", (e) => {
      App.userSettings.music_volume = parseFloat(e.target.value);
      App.saveSettings();
    });
    document.getElementById("menu-hint").textContent = App.isMobile
      ? "Left stick moves - drag the view to look - buttons act, chop and open menus"
      : "WASD move - mouse look - click Chop - E interact - I inventory - C craft - M map - F flashlight - Esc pause";
  },

  show(id) { this.els[id].classList.remove("hidden"); },
  hide(id) { this.els[id].classList.add("hidden"); },
  hideAllScreens() {
    for (const id of ["screen-menu", "screen-classes", "screen-saves", "screen-settings",
      "screen-credits", "screen-pause", "screen-result", "screen-inventory",
      "screen-crafting", "screen-map"]) {
      this.hide(id);
    }
  },

  // ------------------------------------------------------------------ HUD

  hud(showIt) {
    this.els["hud"].classList.toggle("hidden", !showIt);
    this.els["touch-controls"].classList.toggle("hidden", !showIt || !App.isMobile);
  },

  updateHud() {
    const g = this.game;
    if (!g) return;
    const day = g.dayNight;
    document.getElementById("hud-day").textContent = "Day " + g.dayNight.day + " / 99";
    let phaseText;
    if (day.isNight()) phaseText = "Night " + day.day + " - stay in the light";
    else {
      const s = day.secondsUntilNight();
      phaseText = "Daytime - " + Math.floor(s / 60) + ":" + String(Math.floor(s % 60)).padStart(2, "0") + " until night";
    }
    document.getElementById("hud-phase").textContent = phaseText;
    document.getElementById("hud-materials").textContent =
      "Logs: " + g.inv.count("log") + "  Wood: " + g.inv.count("wood");
    const setBar = (id, frac) => { document.getElementById(id).style.width = (Math.max(0, Math.min(1, frac)) * 100) + "%"; };
    setBar("bar-health", g.player.health / g.player.maxHealth);
    setBar("bar-hunger", g.player.hunger / g.player.maxHunger);
    setBar("bar-stamina", g.player.stamina / g.player.maxStamina);
    setBar("bar-fire", g.campfire.fraction());
    document.getElementById("bar-fire").style.background = g.campfire.fraction() > 0.35 ? "#e08030" : "#d94040";
    document.getElementById("hud-fire-level").textContent =
      "Level " + g.campfire.level + " - safe zone " + g.campfire.safeRadius + "m";
  },

  warning(text, seconds) {
    const el = document.getElementById("hud-warning");
    el.textContent = text;
    clearTimeout(this._warningTimer);
    this._warningTimer = setTimeout(() => { el.textContent = ""; }, (seconds || 3) * 1000);
  },

  prompt(text) { document.getElementById("hud-prompt").textContent = text; },

  // ------------------------------------------------------------- inventory

  refreshInventory() {
    const grid = document.getElementById("inv-grid");
    grid.innerHTML = "";
    const inv = this.game.inv;
    inv.slots.forEach((slot, index) => {
      const cell = document.createElement("div");
      cell.className = "inv-slot" + (this.selectedInvSlot === index ? " selected" : "");
      if (slot.id) {
        const item = GD.items.items[slot.id];
        cell.innerHTML = '<span class="icon">' + (ITEM_ICONS[slot.id] || "\u{1F4E6}") +
          '</span><span style="color:' + (RARITY_COLOURS[item.rarity] || "#fff") + '">' +
          item.name.slice(0, 9) + '</span><span class="qty">' + slot.qty + "</span>";
        cell.title = item.name + " - " + (item.description || "");
      }
      cell.addEventListener("click", () => this.onInvClick(index));
      grid.appendChild(cell);
    });
  },

  onInvClick(index) {
    const inv = this.game.inv;
    AudioSys.play("menu_click");
    if (this.selectedInvSlot === null) {
      if (inv.slots[index].id) this.selectedInvSlot = index;
    } else if (this.selectedInvSlot === index) {
      const newIdx = inv.split(index);
      this.selectedInvSlot = null;
      if (newIdx !== null) AudioSys.play("collect");
    } else {
      inv.move(this.selectedInvSlot, index);
      this.selectedInvSlot = null;
      AudioSys.play("collect");
    }
    this.refreshInventory();
  },

  useSelectedInSlot(index) {
    const effects = this.game.inv.use(index);
    if (effects) {
      this.game.player.eat(effects.hunger || 0, effects.health || 0, effects.stamina || 0);
      AudioSys.play("collect");
      this.refreshInventory();
    }
  },

  // -------------------------------------------------------------- crafting

  refreshCrafting() {
    const g = this.game;
    const list = document.getElementById("craft-list");
    document.getElementById("craft-title").textContent = "Crafting Bench - Tier " + g.bench.level;
    list.innerHTML = "";
    const mkButton = (text, enabled, onClick) => {
      const btn = document.createElement("button");
      btn.textContent = text;
      btn.disabled = !enabled;
      btn.addEventListener("click", onClick);
      list.appendChild(btn);
    };
    if (this.craftTab === "craft") {
      const nxt = g.bench.nextUpgradeId();
      if (nxt) {
        const cost = g.bench.recipesFor()[nxt].cost;
        const costText = Object.entries(cost).map(([id, q]) => q + " " + GD.items.items[id].name).join(", ");
        mkButton("Upgrade bench to Tier " + (g.bench.level + 1) + "  [" + costText + "]",
          g.bench.canUpgrade(g.player.craftDiscount), () => {
            if (g.upgradeBench()) { AudioSys.play("craft"); this.refreshCrafting(); }
            else document.getElementById("craft-info").textContent = "Not enough materials to upgrade.";
          });
      }
      for (const [recipeId, recipe] of Object.entries(g.bench.allKnown())) {
        if (recipeId === nxt) continue;
        const struct = GD.recipes.structure_items[recipeId];
        const name = struct ? struct.name : (GD.items.items[recipeId] ? GD.items.items[recipeId].name : recipeId);
        const costText = Object.entries(recipe.cost).map(([id, q]) => q + " " + GD.items.items[id].name).join(", ");
        mkButton(name + "  [" + costText + "]", g.bench.canCraft(recipeId, g.player.craftDiscount), () => {
          if (g.craft(recipeId)) {
            AudioSys.play("craft");
            document.getElementById("craft-info").textContent =
              "Crafted " + name + (struct ? ". Place it from the Build tab." : ".");
            this.refreshCrafting();
          } else {
            const missing = g.bench.missing(recipeId, g.player.craftDiscount);
            document.getElementById("craft-info").textContent = "Missing: " +
              Object.entries(missing).map(([id, q]) => q + " " + GD.items.items[id].name).join(", ");
          }
        });
      }
    } else if (this.craftTab === "grind") {
      let any = false;
      for (const slot of g.inv.slots) {
        if (!slot.id) continue;
        const entry = GD.progression.grinder.recipes[slot.id];
        if (!entry) continue;
        any = true;
        mkButton("Grind " + GD.items.items[slot.id].name + " (" + slot.qty + ") -> " +
          entry.amount + " " + GD.items.items[entry.output].name, true, () => {
            g.doGrind(slot.id, 1);
            AudioSys.play("craft");
            this.refreshCrafting();
          });
      }
      if (!any) document.getElementById("craft-info").textContent =
        "Place wooden objects, mechanical junk or crops into the grinder.";
    } else {
      let any = false;
      for (const recipeId of Object.keys(g.bench.allKnown())) {
        const struct = GD.recipes.structure_items[recipeId];
        if (!struct) continue;
        const count = g.structures.filter((s) => s.type === recipeId).length;
        if (count === 0) continue;
        any = true;
        mkButton("Place " + struct.name + " (" + count + " placed)", true, () => {
          this.placingStructure = recipeId;
          this.placingRotation = 0;
          this.hide("screen-crafting");
          App.craftingOpen = false;
          this.warning("Placing " + struct.name + " - look where you want it, then press Place (B rotates).", 4);
        });
      }
      if (!any) document.getElementById("craft-info").textContent =
        "Craft a structure first on the Craft tab.";
    }
  },

  // ------------------------------------------------------------------- map

  drawMap() {
    const canvas = document.getElementById("map-canvas");
    const ctx = canvas.getContext("2d");
    const g = this.game;
    const size = g.world.size;
    ctx.fillStyle = "#0a120c";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    const toXY = (x, y) => [ (x / size + 0.5) * canvas.width, (y / size + 0.5) * canvas.height ];
    const labels = { red_cave: "R", blue_cave: "B", yellow_cave: "Y", grey_cave: "G",
      cabin: "C", house: "H", grocery_store: "S", clinic: "+", mechanical_building: "M",
      warehouse: "W", campsite: "T", ruins: "U", cave: "V", chest: "$", cultist_outpost: "X" };
    for (const loc of g.world.locations) {
      if (!loc.discovered && !g.hasMap) continue;
      const [px, py] = toXY(loc.x, loc.y);
      let colour = loc.discovered ? "#e6cc33" : "rgba(120,120,120,0.5)";
      if (loc.child) {
        const child = g.children[loc.child];
        colour = child.rescued ? "#4ec94e" : "#d94040";
      }
      ctx.fillStyle = colour;
      ctx.font = "bold 13px Georgia";
      ctx.fillText(labels[loc.type] || "?", px - 4, py + 4);
    }
    const [px, py] = toXY(g.player.x, g.player.y);
    ctx.fillStyle = "#4ec3e0";
    ctx.beginPath();
    ctx.arc(px, py, 4, 0, Math.PI * 2);
    ctx.fill();
    // Camp
    const [cx, cy] = toXY(0, 0);
    ctx.fillStyle = "#e08030";
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fill();
  },

  // --------------------------------------------------------------- classes

  refreshClasses() {
    const list = document.getElementById("class-list");
    list.innerHTML = "";
    document.getElementById("class-diamonds").textContent =
      "Diamonds: " + App.profile.diamonds;
    for (const [classId, cdef] of Object.entries(GD.classes.classes)) {
      const owned = App.profile.owned_classes.includes(classId);
      const btn = document.createElement("button");
      const state = owned ? "OWNED" : cdef.price + " diamonds";
      btn.innerHTML = "<b>" + cdef.name + "</b> - " + cdef.description.slice(0, 60) +
        "... <i>(" + state + ")</i>";
      btn.disabled = !owned && !canBuyClass(GD, App.profile, classId);
      btn.addEventListener("click", () => {
        if (owned) {
          App.selectedClass = classId;
          document.getElementById("class-info").textContent =
            "Selected: " + cdef.name + ". Starts with: " +
            Object.entries(cdef.starting_items || {}).map(([id, q]) => q + " " + GD.items.items[id].name).join(", ") + ".";
        } else if (buyClass(GD, App.profile, classId)) {
          App.saveProfile();
          AudioSys.play("craft");
          document.getElementById("class-info").textContent = "Purchased " + cdef.name + "!";
        }
        this.refreshClasses();
      });
      list.appendChild(btn);
    }
  },

  // ----------------------------------------------------------------- saves

  refreshSaves() {
    const list = document.getElementById("save-list");
    list.innerHTML = "";
    for (let slot = 0; slot < 3; slot++) {
      const info = App.saves.slotInfo(slot);
      const btn = document.createElement("button");
      btn.textContent = info
        ? "Slot " + (slot + 1) + ": Day " + info.day + ", Campfire level " + info.campfire_level +
          ", " + info.childrenRescued + " children rescued"
        : "Slot " + (slot + 1) + ": Empty (start a new run)";
      btn.addEventListener("click", () => App.onAction("start-slot", null, slot));
      list.appendChild(btn);
    }
  },

  // --------------------------------------------------------------- results

  showResult(g) {
    document.getElementById("result-title").textContent = g.victory
      ? "You Survived All 99 Nights!" : "The Forest Claimed You";
    document.getElementById("result-title").style.color = g.victory ? "#6ee06e" : "#d94040";
    document.getElementById("result-stats").textContent =
      "Nights survived: " + g.stats.nights_survived +
      "\nChildren rescued: " + g.rescuedCount() + " of 4" +
      "\nLocations discovered: " + g.stats.locations_discovered +
      "\nTrees felled: " + g.stats.trees_felled +
      "\nCampfire level: " + g.campfire.level;
    document.getElementById("result-diamonds").textContent =
      "Diamonds earned: " + g.earnedDiamonds + " (saved forever)";
    this.show("screen-result");
  },

  refreshSettings() {
    const s = App.userSettings;
    document.getElementById("opt-fullscreen").checked = !!s.fullscreen;
    document.getElementById("opt-sound").value = s.sound_volume;
    document.getElementById("opt-music").value = s.music_volume;
    document.getElementById("settings-values").textContent =
      "Preset: " + (s.preset || "custom") + " | Render distance: " + s.render_distance +
      "m | Shadows: " + (s.shadows ? "on" : "off") +
      (App.isMobile ? " | Mobile mode: touch controls" : " | Desktop mode");
  },
};

if (typeof module !== "undefined") module.exports = { UI, ITEM_ICONS, RARITY_COLOURS };
