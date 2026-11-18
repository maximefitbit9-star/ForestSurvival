# Ninety-Nine Nights in the Wildwood

An original single-player forest survival game inspired by the gameplay systems of *99 Nights in the Forest*, built with HTML, CSS and Three.js. Runs entirely in your browser, fully offline, with desktop **and** mobile touch controls.

> **Original work:** all models, textures and audio in this game are procedurally generated originals. Nothing from *99 Nights in the Forest* is copied or extracted; only publicly documented gameplay systems were referenced during design.

## Quick start

Option A - just open it (most reliable):
1. Download or clone this repository.
2. Double-click **`web/standalone.html`** - the entire game (code, styles, Three.js, data) in one self-contained file. It works wherever you copy or open it, no folder structure required.

Option A2 - the modular version:
2b. Double-click **`web/index.html`** (keep it inside the `web/` folder with its `css/`, `js/` and `vendor/` siblings).

Option B - serve it (best for mobile testing):
```
cd web
python -m http.server 8000
```
Then open **http://localhost:8000** on your computer - or, from a phone on the same Wi-Fi, `http://<your-PC's-LAN-IP>:8000`. Touch controls appear automatically.

## How to play

You are the last camper to return from the Wildwood. Keep the campfire alive for **99 nights**, rescue the four lost children, and survive the things that come out after dark.

- **Chop trees** for logs - thin trees fall in a few hits, big trees need a stronger axe, and old axes bounce off ancient trunks.
- **Fuel the campfire** with logs and coal. Its level (1-6) grows the safe zone and unlocks deeper rescues.
- **Explore** cabins, houses, stores, caves and ruins for loot; stalk camps of cultists for gems.
- **Craft** at the bench (five tiers, thousands of possible upgrades per run): axes, maps, structures, machines.
- **Rescue the four children**, each lost in a far cave the reputation of your fire must open.
- Reach day 99 - or die trying. Diamonds earned across runs buy classes.

### Controls - desktop

| Key | Action |
|---|---|
| W A S D | Move |
| Mouse | Look (click the window to capture the cursor) |
| Shift | Sprint |
| Left click | Chop / place |
| E | Interact (fuel, loot, rescue, sleep, plant) |
| I | Inventory |
| C | Crafting bench |
| M | Map |
| B | Rotate a structure being placed |
| F | Flashlight (repels night threats) |
| Esc | Pause |

### Controls - mobile

- **Left stick** - move
- **Drag the world** - look around
- **CHOP / ACT / RUN / LIGHT** buttons - main actions
- **INV / CRAFT / MAP / II** buttons - menus and pause

## Features

- Seeded, procedurally generated world with four biomes (forest, dense woodland, snowy, magical) and ~60 locations
- Day/night cycle (3-minute day, 90-second night) and weather (rain, fog, thunderstorms, snow) that eats campfire fuel faster
- Six-level campfire with fuel management, safe-zone radius and on-fire cooking
- Interactive tree chopping: progressive damage, tool requirements per tree size, saplings from felled trees
- Inventory with stacking, moving and splitting; five-tier crafting bench with 46 items; grinder; farming and cooking
- Building placement: farm plots, sheds, beds (sleep to skip a day), torches and more
- The four lost children, each behind a campfire-level gate, each with their own rescue and dialogue
- Wildlife (bunnies, deer, birds) by day; three distinct night hunters - the Deer that circles and chases, the Owl that swoops, the Ram that telegraphs then charges
- Eight purchasable classes (Camper, Hunter, Chef, Lumberjack, Doctor, Engineer, Scout, Blacksmith) with permanent diamond prices
- Persistent diamonds earned per run; three save slots with atomic writes; victory and defeat screens with run statistics
- Procedurally generated textures (ground, bark, leaves) and fully synthesised audio (Web Audio API) - zero media files

## Verified reference data

Publicly documented values from *99 Nights in the Forest* are preserved (see `docs/research.md` for the full audit):
- 3-minute day / 90-second night, ~15-minute session loops
- Campfire levels 1-6
- All five crafting bench tiers with the exact known upgrade costs
- Tree species that need stronger axes; approximate hit counts per axe
- The four named children and their campfire-level rescue gates
- Class prices (Camper 10 ... Blacksmith 200)

Unverified values are marked in `config/*.json` `note` fields as original adaptations.

## Tech & architecture

```
web/
  index.html        - document shell and UI layer
  css/style.css     - responsive theme, HUD, menus, touch controls
  js/config.js      - bundled game data (generated from config/*.json)
  js/logic.js       - DOM-free game logic (runs in browser AND Node for tests)
  js/render.js      - Three.js world renderer, procedural textures
  js/controls.js    - keyboard/mouse + virtual joystick + touch buttons
  js/ui.js          - menus, HUD, inventory, crafting, map, saves
  js/main.js        - app bootstrap and the game loop
  vendor/           - Three.js r128 and its MIT licence (fully offline)
config/             - the authoritative JSON data (items, recipes, classes, loot, progression, settings)
```

All gameplay data lives in `config/*.json` and is bundled into the browser by `tools/gen_web_config.py`:
```
python tools/gen_web_config.py
```

Three.js r128 is MIT-licensed and vendored locally so the game needs zero network access.

## Tests

```
node tests/test_web_logic.js         # 18 logic tests (inventory, crafting, campfire, trees, threats, saves...)
node tests/test_web_integration.js   # 7 wiring tests (HTML/JS consistency, config parity, offline enforcement)
node tests/test_web_smoke.js         # 13 end-to-end tests: menu -> game -> move -> chop -> fuel -> night ->
                                      loot -> rescue -> save/reload -> victory -> defeat -> crafting -> mobile
```

All 38 tests pass. The smoke suite runs the *real* app code headlessly against DOM/THREE stubs - during development it caught two genuine bugs (a wrong campfire method name and an inverted movement vector), both fixed before delivery.

Requires Node.js for the tests only - the game itself needs nothing but a browser.

## Saves

Saved to your browser's `localStorage` (three slots plus a persistent profile with diamonds and classes). Clearing your browser data clears your saves.

## Known limitations

- Terrain is heightmapped; tree crowns are stylised primitives rather than modelled foliage
- Characters are simple stylised figures, not skeletal-animated
- Cave interiors are represented by their entrances, not explorable rooms
- Agents can walk through standing trees
- Touch devices are supported, but the game is tuned for screens 5 inches and up

## Licence and credits

- All original game code, data and generated assets: see this repository's commit history
- Three.js (vendored in `web/vendor/`): MIT licence - see `web/vendor/THREE-LICENSE.txt`
- Gameplay inspiration: *99 Nights in the Forest* (no assets, code or data from that game are used)

See `docs/` for the research audit and the full development log.
