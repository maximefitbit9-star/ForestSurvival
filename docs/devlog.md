# Development Log

## Stage 1 — Foundation (complete)
- Project structure, Panda3D configuration, windowed app, main menu, credits,
  pause menu, settings with four presets, save-slot selection.
- Player controller: WASD, mouse look, sprint, crouch, terrain-following camera.

## Stage 2 — Environment (complete)
- Seeded procedural terrain (GeoMipTerrain from a generated heightfield),
  procedural grass texture, water plane, four biomes with distinct tree sets,
  fog, day/night cycle with the verified 3-minute day / 90-second night timing,
  stars, per-phase lighting, weather (clear/rain/fog/storm/snow) with rain
  particles and visibility effects.

## Stage 3 — Survival (complete)
- Health, hunger, stamina with safe-zone regeneration; inventory with stacking,
  moving, splitting and item use; tree chopping with progressive visible
  damage, per-tool hit counts (verified values), falling animation, log and
  sapling drops; campfire with six levels, animated flames/smoke, fuel meter,
  warnings and weather-sensitive burn rate; five fuel types.

## Stage 4 — Progression (complete)
- Crafting bench with five tiers and all verified recipe costs; upgrades;
  grinder (items into wood/scrap/biofuel); cooking on the campfire and in the
  Crock Pot; class perks (Blacksmith discount, Lumberjack wood bonus, etc.).

## Stage 5 — Base development (complete)
- Building placement with transparent preview, rotation (R), right-click to
  place, collision checks, per-structure visuals; farm plots with four crops,
  weather-influenced growth and seed drops; storage structures.

## Stage 6 — World exploration (complete)
- ~60 seeded locations across ten types, each with a data-driven loot table
  and rarity weights; discovery tracking; map screen with fog of war and
  full reveal once the Map is crafted.

## Stage 7 — Characters and AI (complete)
- Four children with personalities, dialogue and campfire-level rescue gates;
  rescued children wander the camp; wildlife (bunnies, deer, birds) with
  wander/flee AI; night hunters with distinct state machines (Deer: patrol /
  search / chase / safe-zone circling; Owl: swoop; Ram: line-charge that
  knocks down trees). Night one is safe, verified faithful.

## Stage 8 — Complete game (complete)
- Class selection with diamond purchases (verified prices), diamonds earned
  per run with a configurable formula, persistent profile, victory at day 99,
  defeat on death or a burnt-out fire, result screens, robust three-slot saves
  with atomic writes and corruption quarantine.

## Stage 9 — Polish (complete for this release)
- Procedurally synthesised audio set (18 files), distance-attenuated sounds,
  day/night/rain ambience switching, campfire flicker, smoke, tree-fall
  animation, LOD via distance culling of trees, configurable render distance
  and shadows, 19 passing logic tests plus a headless end-to-end smoke test
  (menu -> game -> night -> save -> chop -> rescue -> victory -> diamonds).

## Known limitations
- Cave interiors are represented by cave-mouth structures (see README).
- No skeletal animation; characters and animals are stylised low-poly shapes.
- Teleporters do not yet link for travel; flashlight stuns rather than wards.
- 3D audio is approximated by distance volume falloff.

## Backup policy
- Before any major change, copy the working tree to a sibling folder
  `ForestSurvival_backup_YYYYMMDD` (or commit a git tag).

## Stage 10 - Browser edition (complete)

- Full HTML/Three.js remake in `web/`, reusing the verified JSON configs
  (bundled into `js/config.js` by `tools/gen_web_config.py`).
- Same feature set as the Python edition: seeded world with four biomes,
  verified day/night timing, six-level campfire, five-tier crafting bench with
  verified costs, grinder, farming, building placement, four children,
  Deer/Owl/Ram night AI, weather, eight classes, persistent diamonds,
  localStorage saves, victory/defeat screens.
- Mobile support: virtual joystick, drag-to-look, touch buttons for every
  action, Low preset auto-selected on phones, reduced particle counts.
- Fully offline: Three.js r128 vendored locally (MIT licence recorded), audio
  synthesised via Web Audio, no network requests (enforced by test).
- Testing: 18 logic tests (Node port of the Python suite), 7 integration tests
  (HTML/JS wiring, offline enforcement, config parity), 13 end-to-end smoke
  tests running the real app code against DOM/THREE stubs. The smoke test
  caught two real bugs (Campfire.fraction naming, inverted movement vector),
  both fixed. Total: 38 web tests + 19 Python tests, all passing.
