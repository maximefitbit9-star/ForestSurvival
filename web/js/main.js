// Main application: bootstrap, game loop, interactions and events.
"use strict";

const SaveStore = {
  KEY: "wildwood_",
  available() {
    try { localStorage.setItem("__t", "1"); localStorage.removeItem("__t"); return true; }
    catch (e) { return false; }
  },
  read(key, fallback) {
    try {
      const raw = localStorage.getItem(this.KEY + key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) { return fallback; }
  },
  write(key, value) {
    try {
      localStorage.setItem(this.KEY + key, JSON.stringify(value));
      return true;
    } catch (e) { return false; }
  },
  slotInfo(slot) {
    const data = this.read("slot_" + slot, null);
    if (!data) return null;
    const children = Object.values(data.children || {}).filter((c) => c && c.rescued).length;
    return { day: data.day || 1, campfireLevel: (data.campfire || {}).level || 1, childrenRescued: children };
  },
};

const App = {
  isMobile: false,
  game: null,
  world: null,       // WorldRender
  controls: null,
  profile: null,
  userSettings: null,
  selectedClass: "camper",
  currentSlot: 0,
  paused: false,
  craftingOpen: false,
  inventoryOpen: false,
  mapOpen: false,
  placingPreview: null,
  lastTime: 0,
  elapsed: 0,
  saveTimer: 0,

  detectMobile() {
    return /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(navigator.userAgent) ||
      ("ontouchstart" in window && window.innerWidth < 900);
  },

  start() {
    this.isMobile = this.detectMobile();
    AudioSys.init();
    this.profile = SaveStore.read("profile", null) || {
      diamonds: 0, owned_classes: ["camper"], best_day: 0, wins: 0, runs: 0,
    };
    const defaultPreset = this.isMobile ? "low" : "high";
    this.userSettings = SaveStore.read("settings", null) ||
      Object.assign({ preset: defaultPreset }, GD.settings.graphics_presets[defaultPreset]);
    if (!SaveStore.available()) {
      alert("Private browsing detected: saves will not persist between sessions.");
    }
    UI.init();
    UI.hideAllScreens();
    UI.show("screen-menu");
    this.controls = new Controls(document.getElementById("game-canvas"), this.isMobile);
    if (this.isMobile) {
      this.controls.setSprintButton(document.getElementById("btn-sprint"));
      this._bindTouchButtons();
    }
    this._bindKeys();
    requestAnimationFrame((t) => this.loop(t));
  },

  // ------------------------------------------------------------- settings

  applyPreset(name) {
    const preset = GD.settings.graphics_presets[name];
    if (!preset || !this.world) return;
    this.userSettings = Object.assign({ preset: name }, preset);
    this.world.renderDistance = preset.render_distance;
    this.world.renderer.shadowMap.enabled = !!preset.shadows && !this.isMobile;
    this.saveSettings();
    UI.refreshSettings();
    AudioSys.play("menu_click");
  },

  toggleFullscreen(on) {
    try {
      if (on && document.documentElement.requestFullscreen) document.documentElement.requestFullscreen();
      else if (!on && document.exitFullscreen) document.exitFullscreen();
      this.userSettings.fullscreen = on;
      this.saveSettings();
    } catch (e) { /* user gesture required on some browsers */ }
  },

  saveSettings() {
    AudioSys.setVolumes(this.userSettings.sound_volume, this.userSettings.music_volume);
    SaveStore.write("settings", this.userSettings);
  },

  saveProfile() { SaveStore.write("profile", this.profile); },

  // ------------------------------------------------------------ menu actions

  onAction(action, btn, arg) {
    switch (action) {
      case "continue": this.continueGame(); break;
      case "new-game": this.startGame(null); break;
      case "load": UI.refreshSaves(); UI.hideAllScreens(); UI.show("screen-saves"); break;
      case "start-slot": this.startGame(arg); break;
      case "classes": UI.refreshClasses(); UI.hideAllScreens(); UI.show("screen-classes"); break;
      case "classes-back": UI.hideAllScreens(); UI.show("screen-menu"); break;
      case "classes-confirm": this.startGame(null, this.selectedClass); break;
      case "settings": UI.refreshSettings(); UI.hideAllScreens(); UI.show("screen-settings"); break;
      case "settings-back":
        UI.hideAllScreens();
        if (this.game && this.paused) UI.show("screen-pause");
        else if (!this.game) UI.show("screen-menu");
        break;
      case "credits": UI.hideAllScreens(); UI.show("screen-credits"); break;
      case "credits-back": UI.hideAllScreens(); UI.show("screen-menu"); break;
      case "exit": window.close(); UI.warning("Close this browser tab to exit the game."); break;
      case "resume": this.togglePause(); break;
      case "save": this.saveGame(); break;
      case "main-menu": this.returnToMenu(); break;
      case "result-menu": this.returnToMenu(); break;
      case "result-new": this.startGame(null, this.selectedClass); break;
      case "inv-close": this.toggleInventory(); break;
      case "craft-close": this.toggleCrafting(); break;
      case "map-close": this.toggleMap(); break;
    }
  },

  continueGame() {
    for (let slot = 0; slot < 3; slot++) {
      if (SaveStore.slotInfo(slot)) { this.startGame(slot); return; }
    }
    this.startGame(null);
  },

  returnToMenu() {
    this.saveProfile();
    this.game = null;
    if (this.world) { this.world.renderer.dispose(); this.world = null; }
    UI.hideAllScreens();
    UI.hud(false);
    UI.show("screen-menu");
    this.paused = false;
    AudioSys.setAmbience("day");
  },

  // ------------------------------------------------------------- game setup

  startGame(slot, classId) {
    AudioSys.resume();
    UI.hideAllScreens();
    this.game = new Game(GD, null, classId || this.selectedClass, this.profile);
    if (slot != null) {
      const data = SaveStore.read("slot_" + slot, null);
      if (data) this.game.load(data);
    }
    this.currentSlot = slot == null ? 0 : slot;
    if (!this.world) {
      this.world = new WorldRender(this.game, this.userSettings, this.isMobile);
    } else {
      // Rebuild the scene for the new world.
      this.world.renderer.dispose();
      this.world = new WorldRender(this.game, this.userSettings, this.isMobile);
    }
    this.controls.heading = 0;
    this.controls.pitch = 0;
    this.controls.enabled = true;
    UI.game = this.game;
    if (this.game.structures.length) this.rebuildStructures();
    UI.hud(true);
    UI.hide("screen-pause");
    this.paused = false;
    this.saveTimer = 0;
    AudioSys.setAmbience("day");
  },

  // ---------------------------------------------------------------- input

  _bindKeys() {
    window.addEventListener("keydown", (e) => {
      const k = e.key.toLowerCase();
      if (!this.game) return;
      if (k === "i") this.toggleInventory();
      else if (k === "c") this.toggleCrafting();
      else if (k === "m") this.toggleMap();
      else if (k === "e") this.interact();
      else if (k === "f") this.useFlashlight();
      else if (k === "b") this.rotatePlacing();
      else if (k === "escape") this.onEscape();
      else if (k === "enter" && this.placingPreview) this.confirmPlacement();
    });
    if (!this.isMobile) {
      document.getElementById("game-canvas").addEventListener("mousedown", (e) => {
        if (!this.game || this.paused || this.inventoryOpen || this.craftingOpen || this.mapOpen) return;
        if (e.button === 0) this.chop();
        else if (e.button === 2) this.confirmPlacement();
      });
      document.getElementById("game-canvas").addEventListener("contextmenu", (e) => e.preventDefault());
    }
  },

  _bindTouchButtons() {
    const bind = (id, fn) => {
      const btn = document.getElementById(id);
      btn.addEventListener("touchstart", (e) => { e.preventDefault(); fn(); }, { passive: false });
      btn.addEventListener("click", (e) => { e.stopPropagation(); }); // prevent double-fire
    };
    bind("btn-act", () => this.interact());
    bind("btn-chop", () => this.chop());
    bind("btn-inv", () => this.toggleInventory());
    bind("btn-craft", () => this.toggleCrafting());
    bind("btn-map", () => this.toggleMap());
    bind("btn-light", () => this.useFlashlight());
    bind("btn-pause", () => this.onEscape());
    // Long-press the chop button rotates a placement preview.
    let rotateFired = false;
    const chopBtn = document.getElementById("btn-chop");
    chopBtn.addEventListener("touchstart", () => {
      rotateFired = false;
      this._chopHoldTimer = setTimeout(() => { if (UI.placingStructure) { this.rotatePlacing(); rotateFired = true; } }, 400);
    });
    chopBtn.addEventListener("touchend", () => clearTimeout(this._chopHoldTimer));
  },

  onEscape() {
    if (!this.game) return;
    if (this.inventoryOpen) return this.toggleInventory();
    if (this.craftingOpen) return this.toggleCrafting();
    if (this.mapOpen) return this.toggleMap();
    this.togglePause();
  },

  togglePause() {
    this.paused = !this.paused;
    this.controls.enabled = !this.paused;
    UI.hideAllScreens();
    if (this.paused) UI.show("screen-pause");
  },

  toggleInventory() {
    if (!this.game) return;
    this.inventoryOpen = !this.inventoryOpen;
    this.craftingOpen = false;
    this.mapOpen = false;
    UI.hide("screen-crafting"); UI.hide("screen-map");
    if (this.inventoryOpen) { UI.refreshInventory(); UI.show("screen-inventory"); }
    else UI.hide("screen-inventory");
  },

  toggleCrafting() {
    if (!this.game) return;
    this.craftingOpen = !this.craftingOpen;
    this.inventoryOpen = false;
    this.mapOpen = false;
    UI.hide("screen-inventory"); UI.hide("screen-map");
    if (this.craftingOpen) { UI.refreshCrafting(); UI.show("screen-crafting"); }
    else UI.hide("screen-crafting");
  },

  toggleMap() {
    if (!this.game) return;
    this.mapOpen = !this.mapOpen;
    this.inventoryOpen = false;
    this.craftingOpen = false;
    UI.hide("screen-inventory"); UI.hide("screen-crafting");
    if (this.mapOpen) { UI.drawMap(); UI.show("screen-map"); }
    else UI.hide("screen-map");
  },

  // ----------------------------------------------------------- interactions

  bestAxe() {
    for (const axe of ["old_axe", "good_axe", "strong_axe", "ice_axe", "chainsaw"]) {
      if (this.game.inv.count(axe) > 0) return axe;
    }
    return null;
  },

  chop() {
    if (!this.game || this.paused || this.inventoryOpen || this.craftingOpen || this.mapOpen) return;
    if (UI.placingStructure) { this.confirmPlacement(); return; }
    const axe = this.bestAxe();
    if (!axe) { UI.warning("You need an axe to chop trees."); return; }
    const player = this.game.player;
    let best = -1, bestDist = 5.0;
    this.game.world.trees.forEach((tree, index) => {
      if (tree.removed) return;
      const d = Math.hypot(tree.x - player.x, tree.y - player.y);
      if (d < bestDist) { best = index; bestDist = d; }
    });
    if (best < 0) return;
    const result = this.game.chopTree(best, axe);
    AudioSys.play("chop");
    if (result.blocked) {
      UI.warning("This tree is too thick for the " + GD.items.items[axe].name + ".");
      return;
    }
    if (result.fell) {
      this.world.animateTreeFall(best, result.direction);
      AudioSys.play("tree_fall");
      const drops = Object.entries(result.drops)
        .map(([id, q]) => q + " " + GD.items.items[id].name).join(", ");
      UI.warning("Tree felled: " + drops);
    } else {
      this.world.showTreeDamage(best, result.damage);
    }
  },

  chooseFuel() {
    let best = null, bestValue = 0;
    for (const id of ["log", "coal", "biofuel", "fuel_canister", "oil_barrel"]) {
      const value = GD.progression.fuel_values[id] ? GD.progression.fuel_values[id].value : 0;
      if (this.game.inv.count(id) > 0 && value > bestValue) { best = id; bestValue = value; }
    }
    return best;
  },

  findInteraction() {
    const g = this.game;
    const player = g.player;
    if (Math.hypot(player.x, player.y) < 5) return { kind: "campfire" };
    if (Math.hypot(player.x, player.y - 5) < 4) return { kind: "bench" };
    for (const loc of g.world.locations) {
      const d = Math.hypot(loc.x - player.x, loc.y - player.y);
      if (d < 7 && loc.discovered) {
        if (loc.child && !g.children[loc.child].rescued) return { kind: "child", id: loc.child };
        if (!loc.looted) return { kind: "location", id: loc.id };
      }
    }
    for (const struct of g.structures) {
      const d = Math.hypot(struct.x - player.x, struct.y - player.y);
      if (d < 3) {
        const def = GD.recipes.structure_items[struct.type];
        if (def && def.skip_days) return { kind: "bed", id: struct.type };
        if (def && def.farm) {
          const plot = g.plots.find((p) => Math.abs(p.x - struct.x) < 0.1 && Math.abs(p.y - struct.y) < 0.1);
          if (plot) return { kind: "plot", id: plot.id };
        }
      }
    }
    return null;
  },

  interact() {
    if (!this.game || this.paused || this.inventoryOpen || this.craftingOpen || this.mapOpen) return;
    const target = this.findInteraction();
    if (!target) return;
    const g = this.game;
    if (target.kind === "campfire") {
      const fuel = this.chooseFuel();
      if (fuel) { g.addFuel(fuel, 1); AudioSys.play("collect"); }
      else UI.warning("No fuel items in your inventory.");
    } else if (target.kind === "bench") {
      this.toggleCrafting();
    } else if (target.kind === "location") {
      const loot = g.loot(target.id);
      if (loot) {
        AudioSys.play("collect");
        UI.warning("Found: " + Object.entries(loot)
          .map(([id, q]) => q + " " + GD.items.items[id].name).join(", "));
      } else UI.warning("Already looted.");
    } else if (target.kind === "child") {
      const childId = target.id;
      if (g.rescueChild(childId)) {
        AudioSys.play("rescue");
        const child = g.children[childId];
        UI.warning("Rescued " + CHILDREN[childId].name + '! "' +
          CHILDREN[childId].dialogue[child.dialogueIndex++ % CHILDREN[childId].dialogue.length] + '"', 6);
      } else {
        const need = CHILDREN[childId].rescue_requirement;
        UI.warning(CHILDREN[childId].name + " is too deep in the forest. Upgrade the campfire to level " + need + " first.");
      }
    } else if (target.kind === "plot") {
      const plot = g.plots.find((p) => p.id === target.id);
      if (plot.isGrown()) {
        const result = g.harvestPlot(plot.id);
        AudioSys.play("collect");
        UI.warning("Harvested " + result.qty + " " + GD.items.items[result.crop].name);
      } else if (!plot.crop) {
        const seeds = ["carrot_seeds", "corn_seeds", "pumpkin_seeds", "chili_seeds"]
          .find((s) => g.inv.count(s) > 0);
        if (seeds) {
          g.plant(plot.id, seeds);
          AudioSys.play("collect");
          UI.warning("Planted " + GD.items.items[seeds].name + ".");
        } else UI.warning("You need seeds to plant here.");
      } else {
        UI.warning("The crop is still growing (" + Math.floor(plot.growth * 100) + "%).");
      }
    } else if (target.kind === "bed") {
      const days = g.useBed(target.id);
      UI.warning("You slept safely. Skipped " + days + " day(s).");
      this.saveGame();
    }
  },

  useFlashlight() {
    if (!this.game) return;
    if (this.game.inv.count("flashlight") < 1) {
      UI.warning("You need a flashlight (found in houses and clinics).");
      return;
    }
    this.game.stunThreats();
    AudioSys.play("warning");
    UI.warning("The hunters flinch away from the light!");
  },

  // ------------------------------------------------------- build placement

  updatePlacingPreview() {
    const g = this.game;
    if (!UI.placingStructure) return;
    if (!this.placingPreview || this.placingPreview.userData.type !== UI.placingStructure) {
      if (this.placingPreview) this.world.scene.remove(this.placingPreview);
      const colour = 0x6aa84f;
      const mesh = new THREE.Mesh(new THREE.BoxGeometry(2, 1.2, 1.5),
        new THREE.MeshLambertMaterial({ color: colour, transparent: true, opacity: 0.5 }));
      this.placingPreview = mesh;
      this.placingPreview.userData.type = UI.placingStructure;
      this.world.scene.add(mesh);
    }
    const player = g.player;
    const fx = player.x + Math.sin(this.controls.heading) * -4;
    const fy = player.y + Math.cos(this.controls.heading) * -4;
    this.placingPreview.position.set(fx, this.world.getGroundHeight(fx, fy) + 0.6, fy);
    this.placingPreview.rotation.y = UI.placingRotation * Math.PI / 180;
    const valid = this.isValidPlacement(fx, fy);
    this.placingPreview.material.opacity = valid ? 0.55 : 0.2;
    this.placingPreview.material.color.setHex(valid ? 0x6aa84f : 0xd94040);
  },

  isValidPlacement(x, y) {
    for (const s of this.game.structures) {
      if (Math.abs(s.x - x) < 3 && Math.abs(s.y - y) < 3) return false;
    }
    return Math.hypot(x, y) >= 3;
  },

  rotatePlacing() {
    if (UI.placingStructure) {
      UI.placingRotation = (UI.placingRotation + 15) % 360;
      AudioSys.play("menu_click");
    }
  },

  confirmPlacement() {
    if (!UI.placingStructure) return;
    const player = this.game.player;
    const fx = player.x + Math.sin(this.controls.heading) * -4;
    const fy = player.y + Math.cos(this.controls.heading) * -4;
    if (!this.isValidPlacement(fx, fy)) {
      UI.warning("Cannot place here - blocked or too close to the fire.");
      return;
    }
    const struct = this.game.placeStructure(UI.placingStructure, fx, fy, UI.placingRotation);
    if (!struct) { UI.warning("Cannot place here."); return; }
    AudioSys.play("build");
    this._addStructureMesh(struct);
    UI.placingStructure = null;
    if (this.placingPreview) { this.world.scene.remove(this.placingPreview); this.placingPreview = null; }
    UI.warning("Placed.");
  },

  _addStructureMesh(struct) {
    const def = GD.recipes.structure_items[struct.type] || {};
    const colour = struct.type.endsWith("bed") ? 0x8c7354 : (def.farm ? 0x59471f : 0x668052);
    const group = new THREE.Group();
    const body = new THREE.Mesh(new THREE.BoxGeometry(def.farm ? 3 : 1.8, def.farm ? 0.3 : 1.2, def.farm ? 3 : 1.4),
      new THREE.MeshLambertMaterial({ color: colour }));
    body.position.y = def.farm ? 0.15 : 0.6;
    group.add(body);
    if (struct.type === "torch") {
      const flame = new THREE.Mesh(new THREE.ConeGeometry(0.25, 0.6, 6),
        new THREE.MeshBasicMaterial({ color: 0xff7722 }));
      flame.position.y = 2.1;
      group.add(flame);
    }
    group.position.set(struct.x, this.world.getGroundHeight(struct.x, struct.y), struct.y);
    group.rotation.y = (struct.rotation || 0) * Math.PI / 180;
    this.world.scene.add(group);
  },

  rebuildStructures() {
    for (const struct of this.game.structures) this._addStructureMesh(struct);
  },

  // ----------------------------------------------------------------- saving

  saveGame() {
    if (!this.game) return;
    SaveStore.write("slot_" + this.currentSlot, this.game.toSave());
    this.saveProfile();
    UI.warning("Game saved to slot " + (this.currentSlot + 1) + ".");
  },

  // ------------------------------------------------------------- game loop

  loop(now) {
    requestAnimationFrame((t) => this.loop(t));
    const dt = Math.min((now - (this.lastTime || now)) / 1000, 0.1);
    this.lastTime = now;
    if (!this.game || !this.world) { if (this.world) this.world.render(); return; }
    this.elapsed += dt;
    const g = this.game;
    const uiBlocking = this.paused || this.inventoryOpen || this.craftingOpen || this.mapOpen;

    if (!uiBlocking && !g.finished) {
      // Movement.
      const player = g.player;
      const move = this.controls.moveVector();
      const sprinting = this.controls.isSprinting() && player.stamina > 1;
      const crouching = this.controls.isCrouching();
      let speed = 6.0 + player.speedBonus;
      if (sprinting) speed *= 1.75;
      if (crouching) speed *= 0.5;
      if (move.x || move.y) {
        // Camera forward is (-sin h, -cos h); right is (cos h, -sin h).
        const h = this.controls.heading;
        const dirX = -Math.sin(h) * move.y + Math.cos(h) * move.x;
        const dirY = -Math.cos(h) * move.y - Math.sin(h) * move.x;
        player.x += dirX * speed * dt;
        player.y += dirY * speed * dt;
      }
      player.sprinting = sprinting;
      const half = g.world.size / 2 - 5;
      player.x = Math.max(-half, Math.min(half, player.x));
      player.y = Math.max(-half, Math.min(half, player.y));

      // Simulation.
      const events = g.tick(dt);
      for (const ev of events) this.handleEvent(ev);
    }

    // Camera.
    const player = g.player;
    const groundY = this.world.getGroundHeight(player.x, player.y);
    const eye = crouchingEye(this.controls, player);
    this.world.camera.position.set(player.x, groundY + eye, player.y);
    this.world.camera.rotation.order = "YXZ";
    this.world.camera.rotation.y = this.controls.heading;
    this.world.camera.rotation.x = this.controls.pitch;

    // Views.
    this.world.update(dt, this.elapsed);
    this.updatePlacingPreview();
    this.world.render();

    // HUD + ambience.
    UI.updateHud();
    const promptTarget = (!uiBlocking && !g.finished) ? this.findInteraction() : null;
    const prompts = {
      campfire: "Interact: Add fuel (" + (this.chooseFuel() ? GD.items.items[this.chooseFuel()].name : "none left!") + ")",
      bench: "Interact: Open Crafting Bench",
      location: "Interact: Scavenge",
      child: "Interact: Rescue child",
      plot: "Interact: Plant / harvest crop",
      bed: "Interact: Sleep (skip a day)",
    };
    UI.prompt(promptTarget ? prompts[promptTarget.kind] : "");
    if (g.dayNight.isNight()) AudioSys.setAmbience(g.weather.isWet ? "rain" : "night");
    else AudioSys.setAmbience(g.weather.isWet ? "rain" : "day");

    // Autosave once per game day.
    this.saveTimer += dt;
    if (this.saveTimer > 30) { this.saveTimer = 0; if (!g.finished) SaveStore.write("slot_" + this.currentSlot, g.toSave()); }

    if (g.finished && !this._resultShown) {
      this._resultShown = true;
      UI.showResult(g);
      this.saveProfile();
      AudioSys.play(g.victory ? "victory" : "defeat");
    }
    if (!g.finished) this._resultShown = false;
  },

  handleEvent(ev) {
    switch (ev.type) {
      case "night_start":
        UI.warning("Night " + ev.night + " falls. Stay within the campfire's light!", 5);
        AudioSys.play("growl");
        break;
      case "new_day": UI.warning("Day " + ev.day + " begins."); break;
      case "fuel_low": UI.warning("The campfire is running low on fuel!"); break;
      case "fuel_critical": UI.warning("The fire is about to go out!"); break;
      case "campfire_out": UI.warning("The campfire has gone out! Relight it with fuel!"); AudioSys.play("warning"); break;
      case "starving": UI.warning("You are starving. Eat something!"); break;
      case "hungry": UI.warning("You are getting hungry."); break;
      case "spotted": UI.warning("Something has spotted you..."); AudioSys.play("growl"); break;
      case "attack": UI.warning("You were attacked! Get to the campfire!", 2); AudioSys.play("warning"); break;
      case "ram_charge": UI.warning("The Ram is charging!"); break;
      case "thunder": AudioSys.play("thunder"); break;
    }
  },
};

function crouchingEye(controls, player) {
  return controls.isCrouching() ? 0.95 : 1.7;
}

window.addEventListener("load", () => App.start());
