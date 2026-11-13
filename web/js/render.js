// Three.js world renderer for the Wildwood. All geometry is generated original code.
"use strict";

const PHASES = {
  dawn: { sky: 0x8c738c, ambient: 0x736a70, sun: 0.35, fog: 0xb29ea6 },
  day: { sky: 0x73b2f2, ambient: 0x8c8c8c, sun: 1.0, fog: 0xc0d2eb },
  dusk: { sky: 0xd97340, ambient: 0x73594c, sun: 0.5, fog: 0xd99a73 },
  night: { sky: 0x050810, ambient: 0x1a1e33, sun: 0.05, fog: 0x070a12 },
};

const TREE_SPECS = {
  small: { radius: 0.35, height: 3, crown: 1.0, colour: 0x1f6116 },
  normal: { radius: 0.55, height: 6, crown: 1.2, colour: 0x1f6116 },
  big: { radius: 0.9, height: 10, crown: 1.8, colour: 0x175c10 },
  snow_pine: { radius: 0.5, height: 7, crown: 1.1, colour: 0x26593a },
  ancient: { radius: 1.2, height: 13, crown: 2.2, colour: 0x33512e },
};

const LOCATION_COLOURS = {
  cabin: 0x73543a, house: 0x80664d, grocery_store: 0x8c8c80, clinic: 0xccccd9,
  mechanical_building: 0x666673, warehouse: 0x806b59, campsite: 0x4d4d4d,
  ruins: 0x8c8473, cave: 0x4d4d52, chest: 0x805926, cultist_outpost: 0x402633,
  red_cave: 0x59595f, blue_cave: 0x59595f, yellow_cave: 0x59595f, grey_cave: 0x59595f,
};

class WorldRender {
  constructor(game, settings, isMobile) {
    this.game = game;
    this.settings = settings;
    this.isMobile = !!isMobile;
    this.renderDistance = settings.render_distance || 240;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x73b2f2);
    this.camera = new THREE.PerspectiveCamera(70, window.innerWidth / window.innerHeight, 0.1, 1200);
    this.renderer = new THREE.WebGLRenderer({ canvas: document.getElementById("game-canvas"), antialias: !isMobile });
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, isMobile ? 1.5 : 2));
    this.renderer.shadowMap.enabled = !!settings.shadows && !isMobile;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this._buildLights();
    this._buildTerrain();
    this._buildWater();
    this._buildCampfire();
    this._buildTrees();
    this._buildLocations();
    this._buildStars();
    this._buildRain();
    this._buildCharacters();
    this._cullTimer = 0;
    this.fallingTrees = [];
    window.addEventListener("resize", () => this._onResize());
  }

  _onResize() {
    this.camera.aspect = window.innerWidth / window.innerHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(window.innerWidth, window.innerHeight);
  }

  _buildLights() {
    this.ambient = new THREE.AmbientLight(0x8c8c8c, 0.7);
    this.scene.add(this.ambient);
    this.sun = new THREE.DirectionalLight(0xfff2dd, 1.0);
    this.sun.position.set(80, 120, 40);
    if (this.renderer.shadowMap.enabled) {
      this.sun.castShadow = true;
      this.sun.shadow.mapSize.set(1024, 1024);
      this.sun.shadow.camera.left = -80;
      this.sun.shadow.camera.right = 80;
      this.sun.shadow.camera.top = 80;
      this.sun.shadow.camera.bottom = -80;
      this.sun.shadow.camera.far = 400;
    }
    this.scene.add(this.sun);
    this.fireLight = new THREE.PointLight(0xff9933, 2.2, 60, 2);
    this.fireLight.position.set(0, 2, 0);
    this.scene.add(this.fireLight);
    this.scene.fog = new THREE.Fog(0xc0d2eb, 40, this.renderDistance);
  }

  _buildTerrain() {
    const world = this.game.world;
    const size = world.size;
    const segs = this.isMobile ? 96 : 160;
    const geo = new THREE.PlaneGeometry(size, size, segs, segs);
    geo.rotateX(-Math.PI / 2);
    const pos = geo.attributes.position;
    const colours = new Float32Array(pos.count * 3);
    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i), z = pos.getZ(i);
      pos.setY(i, world.height(x, z));
      const biome = world.biomeAt(Math.floor(x), Math.floor(z));
      const c = new THREE.Color(
        BIOMES[biome].ground[0], BIOMES[biome].ground[1], BIOMES[biome].ground[2]);
      const tint = 0.9 + 0.1 * Math.sin(x * 0.7) * Math.cos(z * 0.6);
      colours[i * 3] = c.r * tint;
      colours[i * 3 + 1] = c.g * tint;
      colours[i * 3 + 2] = c.b * tint;
    }
    geo.setAttribute("color", new THREE.BufferAttribute(colours, 3));
    geo.computeVertexNormals();
    const mat = new THREE.MeshLambertMaterial({ vertexColors: true });
    this.terrain = new THREE.Mesh(geo, mat);
    this.terrain.receiveShadow = this.renderer.shadowMap.enabled;
    this.scene.add(this.terrain);
  }

  getGroundHeight(x, z) { return this.game.world.height(x, z); }

  _buildWater() {
    const world = this.game.world;
    const geo = new THREE.PlaneGeometry(world.size, world.size);
    geo.rotateX(-Math.PI / 2);
    const mat = new THREE.MeshLambertMaterial({ color: 0x264d80, transparent: true, opacity: 0.55 });
    this.water = new THREE.Mesh(geo, mat);
    this.water.position.y = 1.2;
    this.scene.add(this.water);
  }

  _buildCampfire() {
    this.campfireGroup = new THREE.Group();
    const stoneMat = new THREE.MeshLambertMaterial({ color: 0x40342a });
    const base = new THREE.Mesh(new THREE.CylinderGeometry(1.6, 1.8, 0.35, 10), stoneMat);
    base.position.y = 0.17;
    this.campfireGroup.add(base);
    for (let i = 0; i < 5; i++) {
      const log = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 2.2, 6),
        new THREE.MeshLambertMaterial({ color: 0x664728 }));
      log.rotation.z = Math.PI / 2 - 0.3;
      log.rotation.y = (i / 5) * Math.PI * 2;
      log.position.y = 0.35;
      this.campfireGroup.add(log);
    }
    const flameMat = new THREE.MeshBasicMaterial({ color: 0xff7722, transparent: true, opacity: 0.9 });
    this.flames = [];
    for (let i = 0; i < 6; i++) {
      const flame = new THREE.Mesh(new THREE.ConeGeometry(0.4, 1.6, 6), flameMat.clone());
      flame.position.set((Math.random() - 0.5) * 0.8, 0.9, (Math.random() - 0.5) * 0.8);
      this.campfireGroup.add(flame);
      this.flames.push(flame);
    }
    this.campfireDecor = new THREE.Group();
    this.campfireGroup.add(this.campfireDecor);
    this.scene.add(this.campfireGroup);
    this._renderedFireLevel = 0;
  }

  _updateCampfireLevel(level) {
    while (this.campfireDecor.children.length) {
      this.campfireDecor.remove(this.campfireDecor.children[0]);
    }
    const rockMat = new THREE.MeshLambertMaterial({ color: 0x737377 });
    const woodMat = new THREE.MeshLambertMaterial({ color: 0x664d2e });
    if (level >= 2) {
      for (let i = 0; i < 3; i++) {
        const bench = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.25, 2.4, 6), woodMat);
        const ang = (i * 120 + 30) * Math.PI / 180;
        bench.rotation.z = Math.PI / 2;
        bench.rotation.y = ang;
        bench.position.set(Math.cos(ang) * 3, 0.25, Math.sin(ang) * 3);
        this.campfireDecor.add(bench);
      }
    }
    if (level >= 3) {
      const rocks = level === 3 ? 6 : 12;
      for (let i = 0; i < rocks; i++) {
        const rock = new THREE.Mesh(new THREE.SphereGeometry(0.45, 8, 6), rockMat);
        const ang = (i * 360 / rocks) * Math.PI / 180;
        rock.position.set(Math.cos(ang) * 2.2, 0.3, Math.sin(ang) * 2.2);
        this.campfireDecor.add(rock);
      }
    }
    if (level >= 5) {
      for (let i = 0; i < 8; i++) {
        const stone = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.5, 1.2), rockMat);
        const ang = (i * 45) * Math.PI / 180;
        stone.position.set(Math.cos(ang) * 4.5, 0.25, Math.sin(ang) * 4.5);
        this.campfireDecor.add(stone);
      }
    }
    if (level >= 6) {
      const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.6, 3, 8),
        new THREE.MeshLambertMaterial({ color: 0x8c8073 }));
      pillar.position.set(5.5, 1.5, 0);
      this.campfireDecor.add(pillar);
    }
  }

  _makeTreeGeo(type) {
    const spec = TREE_SPECS[type];
    const group = new THREE.Group();
    const trunk = new THREE.Mesh(new THREE.CylinderGeometry(spec.radius * 0.7, spec.radius, spec.height, 6),
      new THREE.MeshLambertMaterial({ color: 0x52391f }));
    trunk.position.y = spec.height / 2;
    trunk.castShadow = this.renderer.shadowMap.enabled;
    group.add(trunk);
    if (type === "snow_pine") {
      for (let i = 0; i < 3; i++) {
        const cone = new THREE.Mesh(new THREE.ConeGeometry(spec.radius * (2.2 - i * 0.6), spec.height * 0.35, 7),
          new THREE.MeshLambertMaterial({ color: spec.colour }));
        cone.position.y = spec.height * (0.4 + i * 0.2);
        cone.castShadow = this.renderer.shadowMap.enabled;
        group.add(cone);
      }
    } else {
      const crown = new THREE.Mesh(new THREE.SphereGeometry(spec.radius * 2.2 * spec.crown, 8, 6),
        new THREE.MeshLambertMaterial({ color: spec.colour }));
      crown.position.y = spec.height + spec.radius;
      crown.castShadow = this.renderer.shadowMap.enabled;
      group.add(crown);
    }
    return group;
  }

  _buildTrees() {
    // One InstancedMesh per (trunk, crown) pair per tree type for performance.
    this.treeMeshes = {};
    this.treeRecords = [];
    const world = this.game.world;
    const types = {};
    world.trees.forEach((tree, index) => {
      if (!types[tree.type]) types[tree.type] = [];
      types[tree.type].push(index);
    });
    for (const [type, indices] of Object.entries(types)) {
      const spec = TREE_SPECS[type];
      const count = indices.length;
      const trunkGeo = new THREE.CylinderGeometry(spec.radius * 0.7, spec.radius, spec.height, 6);
      const crownGeo = type === "snow_pine"
        ? new THREE.ConeGeometry(spec.radius * 2.2, spec.height * 0.35, 7)
        : new THREE.SphereGeometry(spec.radius * 2.2 * spec.crown, 8, 6);
      const trunkMat = new THREE.MeshLambertMaterial({ color: 0x52391f });
      const crownMat = new THREE.MeshLambertMaterial({ color: spec.colour });
      const trunkMesh = new THREE.InstancedMesh(trunkGeo, trunkMat, count);
      const crownMesh = new THREE.InstancedMesh(crownGeo, crownMat, count);
      trunkMesh.castShadow = crownMesh.castShadow = this.renderer.shadowMap.enabled;
      trunkMesh.frustumCulled = crownMesh.frustumCulled = false;
      this.scene.add(trunkMesh);
      this.scene.add(crownMesh);
      this.treeMeshes[type] = { trunk: trunkMesh, crown: crownMesh, indices };
      indices.forEach((treeIndex, i) => {
        const tree = world.trees[treeIndex];
        this.treeRecords.push({ index: treeIndex, type, slot: i, falling: null });
        this._writeTreeMatrix(type, i, tree, 0);
      });
    }
    this.treeSlotOf = {};
    for (const r of this.treeRecords) this.treeSlotOf[r.index] = r;
  }

  _writeTreeMatrix(type, slot, tree, tiltDeg, fellDeg) {
    const dummy = new THREE.Object3D();
    const y = this.getGroundHeight(tree.x, tree.y);
    dummy.position.set(tree.x, y, tree.y);
    dummy.rotation.set(0, tree.slot * 1.7, 0);
    dummy.scale.setScalar(tree.scale || 1);
    if (tiltDeg) dummy.rotation.x = tiltDeg * Math.PI / 180;
    if (fellDeg) {
      dummy.rotation.x = 0;
      dummy.rotation.z = fellDeg * Math.PI / 180;
      dummy.position.y = y + 0.5;
    }
    dummy.updateMatrix();
    const meshes = this.treeMeshes[type];
    meshes.trunk.setMatrixAt(slot, dummy.matrix);
    meshes.crown.setMatrixAt(slot, dummy.matrix);
  }

  _buildLocations() {
    this.locationMeshes = {};
    const world = this.game.world;
    for (const loc of world.locations) {
      const group = new THREE.Group();
      const colour = LOCATION_COLOURS[loc.type] || 0x808080;
      const mat = new THREE.MeshLambertMaterial({ color: colour });
      if (loc.type.endsWith("_cave")) {
        const body = new THREE.Mesh(new THREE.BoxGeometry(6, 3.5, 6), mat);
        body.position.y = 1.75;
        group.add(body);
        const mouth = new THREE.Mesh(new THREE.BoxGeometry(2, 2.5, 0.5),
          new THREE.MeshLambertMaterial({ color: 0x1f1f1f }));
        mouth.position.set(3, 1.25, 0);
        group.add(mouth);
        const childColours = { red_cave: 0xcc3333, blue_cave: 0x3366cc, yellow_cave: 0xd9cc33, grey_cave: 0x808080 };
        const marker = new THREE.Mesh(new THREE.SphereGeometry(0.6, 8, 6),
          new THREE.MeshBasicMaterial({ color: childColours[loc.type] || 0xffffff }));
        marker.position.y = 4.2;
        group.add(marker);
      } else if (loc.type === "chest") {
        const chest = new THREE.Mesh(new THREE.BoxGeometry(1.2, 1.0, 0.8), mat);
        chest.position.y = 0.5;
        group.add(chest);
      } else {
        const height = (loc.type === "campsite" || loc.type === "ruins") ? 1.5 : 3.0;
        const body = new THREE.Mesh(new THREE.BoxGeometry(6, height, 5), mat);
        body.position.y = height / 2;
        body.castShadow = this.renderer.shadowMap.enabled;
        group.add(body);
        const roof = new THREE.Mesh(new THREE.BoxGeometry(7, 0.5, 6),
          new THREE.MeshLambertMaterial({ color: 0x4d3326 }));
        roof.position.y = height;
        group.add(roof);
      }
      group.position.set(loc.x, this.getGroundHeight(loc.x, loc.y), loc.y);
      this.scene.add(group);
      this.locationMeshes[loc.id] = group;
    }
  }

  _buildStars() {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(300 * 3);
    for (let i = 0; i < 300; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = (5 + Math.random() * 75) * Math.PI / 180;
      const r = 700;
      positions[i * 3] = r * Math.cos(theta) * Math.cos(phi);
      positions[i * 3 + 1] = r * Math.sin(phi);
      positions[i * 3 + 2] = r * Math.sin(theta) * Math.cos(phi);
    }
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    this.stars = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffffff, size: 2, sizeAttenuation: false }));
    this.stars.visible = false;
    this.scene.add(this.stars);
  }

  _buildRain() {
    const geo = new THREE.BufferGeometry();
    const count = this.isMobile ? 400 : 900;
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * 80;
      positions[i * 3 + 1] = Math.random() * 30;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 80;
    }
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    this.rain = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0x99b3e6, size: 0.12, transparent: true, opacity: 0.7 }));
    this.rain.visible = false;
    this.scene.add(this.rain);
  }

  _buildCharacters() {
    this.characterMeshes = {};
    // Children, animals and threats are simple stylised figures.
    const childIds = Object.keys(CHILDREN);
    for (const id of childIds) {
      const group = new THREE.Group();
      const bodyGeo = THREE.CapsuleGeometry
        ? new THREE.CapsuleGeometry(0.3, 0.6, 4, 8)
        : new THREE.CylinderGeometry(0.3, 0.3, 1.2, 8);
      const body = new THREE.Mesh(bodyGeo, new THREE.MeshLambertMaterial({ color: CHILDREN[id].colour }));
      body.position.y = 0.9;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.28, 8, 6),
        new THREE.MeshLambertMaterial({ color: 0xe6c9a8 }));
      head.position.y = 1.7;
      group.add(head);
      group.visible = false;
      this.scene.add(group);
      this.characterMeshes["child_" + id] = group;
    }
    this.animalMeshes = [];
    this.threatMeshes = {};
    this.threatGroup = new THREE.Group();
    this.scene.add(this.threatGroup);
    this.animalGroup = new THREE.Group();
    this.scene.add(this.animalGroup);
  }

  _ensureAnimalMesh(animal) {
    if (this.animalMeshes[animal.id]) return this.animalMeshes[animal.id];
    const colours = { bunny: 0xcccccc, deer: 0x996633, bird: 0x4d668c };
    const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.4, 8, 6),
      new THREE.MeshLambertMaterial({ color: colours[animal.species] || 0x888888 }));
    mesh.scale.set(1, 0.8, 1.4);
    this.animalGroup.add(mesh);
    this.animalMeshes[animal.id] = mesh;
    return mesh;
  }

  _ensureThreatMesh(threat) {
    if (this.threatMeshes[threat.id]) return this.threatMeshes[threat.id];
    const colours = { deer: 0x33261f, owl: 0x3d3d52, ram: 0x26262b };
    const mesh = new THREE.Mesh(
      threat.kind === "owl" ? new THREE.SphereGeometry(0.6, 8, 6) : new THREE.BoxGeometry(1.4, 1.8, 2.2),
      new THREE.MeshLambertMaterial({ color: colours[threat.kind] || 0x222222 }));
    if (threat.kind === "owl") mesh.scale.set(1, 0.7, 1);
    // Glowing eyes so night hunters are readable in the dark.
    const eyeMat = new THREE.MeshBasicMaterial({ color: 0xff2200 });
    for (const sx of [-0.25, 0.25]) {
      const eye = new THREE.Mesh(new THREE.SphereGeometry(0.08, 6, 4), eyeMat);
      eye.position.set(sx, threat.kind === "owl" ? 0.15 : 0.6, threat.kind === "owl" ? 0.5 : 1.12);
      mesh.add(eye);
    }
    this.threatGroup.add(mesh);
    this.threatMeshes[threat.id] = mesh;
    return mesh;
  }

  animateTreeFall(treeIndex, direction) {
    const record = this.treeSlotOf[treeIndex];
    if (!record || record.falling) return;
    record.falling = { progress: 0, direction: direction * Math.PI / 180 };
  }

  showTreeDamage(treeIndex, damage) {
    const record = this.treeSlotOf[treeIndex];
    if (!record || record.falling) return;
    const tree = this.game.world.trees[treeIndex];
    this._writeTreeMatrix(record.type, record.slot, tree, damage * 4);
    const meshes = this.treeMeshes[record.type];
    meshes.trunk.instanceMatrix.needsUpdate = true;
    meshes.crown.instanceMatrix.needsUpdate = true;
  }

  update(dt, elapsed) {
    const g = this.game;
    const phase = PHASES[g.dayNight.phase()];
    this.scene.background.setHex(phase.sky);
    this.ambient.color.setHex(phase.ambient);
    this.sun.intensity = phase.sun;
    this.sun.color.setHex(g.dayNight.isNight() ? 0x26304d : 0xfff2dd);
    const vis = g.weather.visibility;
    const far = this.renderDistance * vis;
    this.scene.fog.color.setHex(phase.fog);
    this.scene.fog.near = far * 0.25;
    this.scene.fog.far = far;
    this.stars.visible = g.dayNight.isNight();

    // Campfire flames flicker with remaining fuel.
    const frac = g.campfire.fraction();
    if (g.campfire.lit) {
      for (let i = 0; i < this.flames.length; i++) {
        const flame = this.flames[i];
        const s = (0.4 + frac) * (0.85 + 0.15 * Math.sin(elapsed * 7 + i * 2));
        flame.scale.set(s, s * 1.3, s);
        flame.material.opacity = 0.4 + frac * 0.6;
      }
      this.fireLight.intensity = 1.2 + frac * 1.8 + 0.3 * Math.sin(elapsed * 9);
    } else {
      this.flames.forEach((f) => (f.material.opacity = 0));
      this.fireLight.intensity = 0.05;
    }
    if (g.campfire.level !== this._renderedFireLevel) {
      this._renderedFireLevel = g.campfire.level;
      this._updateCampfireLevel(g.campfire.level);
    }

    // Rain follows the camera and falls.
    if (g.weather.isWet) {
      this.rain.visible = true;
      const pos = this.rain.geometry.attributes.position;
      for (let i = 0; i < pos.count; i++) {
        let y = pos.getY(i) - dt * 25;
        if (y < 0) y = 30;
        pos.setY(i, y);
      }
      pos.needsUpdate = true;
      this.rain.position.set(this.camera.position.x, 0, this.camera.position.z);
    } else {
      this.rain.visible = false;
    }

    // Falling tree animations.
    let matricesDirty = {};
    for (const record of this.treeRecords) {
      if (!record.falling) continue;
      record.falling.progress = Math.min(1, record.falling.progress + dt * 0.7);
      const t = record.falling.progress;
      const angle = 90 * t * t;
      const tree = g.world.trees[record.index];
      this._writeTreeMatrix(record.type, record.slot, tree, 0, angle * Math.cos(record.falling.direction));
      matricesDirty[record.type] = true;
      if (t >= 1) {
        record.falling = null;
        this._writeTreeMatrix(record.type, record.slot, tree, 0, 0);
        // Hide by scaling to zero once fallen.
        const dummy = new THREE.Object3D();
        dummy.position.set(99999, 0, 99999);
        dummy.scale.setScalar(0.001);
        dummy.updateMatrix();
        const meshes = this.treeMeshes[record.type];
        meshes.trunk.setMatrixAt(record.slot, dummy.matrix);
        meshes.crown.setMatrixAt(record.slot, dummy.matrix);
      }
    }
    // Distance culling: hide trees beyond the render distance (cheap chunk-style LOD).
    this._cullTimer -= dt;
    if (this._cullTimer <= 0) {
      this._cullTimer = 0.5;
      const px = this.camera.position.x, pz = this.camera.position.z;
      const rd = this.renderDistance;
      const dummy = new THREE.Object3D();
      for (const record of this.treeRecords) {
        const tree = g.world.trees[record.index];
        const d = Math.hypot(tree.x - px, tree.y - pz);
        const shouldHide = tree.removed || d > rd;
        if (record.hidden !== shouldHide && !record.falling) {
          record.hidden = shouldHide;
          if (shouldHide) {
            dummy.position.set(99999, 0, 99999);
            dummy.scale.setScalar(0.001);
            dummy.updateMatrix();
            const meshes = this.treeMeshes[record.type];
            meshes.trunk.setMatrixAt(record.slot, dummy.matrix);
            meshes.crown.setMatrixAt(record.slot, dummy.matrix);
          } else {
            this._writeTreeMatrix(record.type, record.slot, tree, 0);
          }
          matricesDirty[record.type] = true;
        }
      }
    }
    for (const [type] of Object.entries(matricesDirty)) {
      const meshes = this.treeMeshes[type];
      meshes.trunk.instanceMatrix.needsUpdate = true;
      meshes.crown.instanceMatrix.needsUpdate = true;
    }

    // Characters: children at camp, animals, threats.
    for (const id of Object.keys(CHILDREN)) {
      const mesh = this.characterMeshes["child_" + id];
      const child = g.children[id];
      mesh.visible = child.rescued;
      if (child.rescued) {
        mesh.position.set(child.x, this.getGroundHeight(child.x, child.y), child.y);
        mesh.rotation.y = Math.sin(elapsed + child.x) * 0.5;
      }
    }
    for (const animal of g.animals) {
      const mesh = this._ensureAnimalMesh(animal);
      mesh.position.set(animal.x, this.getGroundHeight(animal.x, animal.y) + 0.4, animal.y);
      mesh.visible = animal.state !== "sleep" && Math.hypot(animal.x - this.camera.position.x, animal.y - this.camera.position.z) < 80;
    }
    for (const threat of g.threats) {
      const mesh = this._ensureThreatMesh(threat);
      mesh.position.set(threat.x, this.getGroundHeight(threat.x, threat.y) + 1, threat.y);
      mesh.visible = g.dayNight.isNight();
    }
  }

  render() { this.renderer.render(this.scene, this.camera); }
}

if (typeof module !== "undefined") module.exports = { WorldRender, PHASES, TREE_SPECS, LOCATION_COLOURS };
