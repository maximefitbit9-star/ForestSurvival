# Ninety-Nine Nights in the Wildwood

An original single-player 3D forest survival game inspired by the gameplay systems of
Roblox's *99 Nights in the Forest*. Survive 99 nights, keep the campfire burning,
rescue four missing children and develop your camp.

Built with **Python 3.11+** and **Panda3D**. Fully offline. Single-player only.
All models, textures and audio in this game are procedurally generated originals —
nothing is copied from any other game.

## Installation (Windows)

1. Install Python 3.11 or newer from <https://www.python.org/downloads/> and tick
   "Add python.exe to PATH" during installation.
2. Open a command prompt in this folder and run:

   ```
   pip install -r requirements.txt
   ```

3. Double-click **`launch.bat`** to play, or run `python main.py`.

Recommended for the listed hardware (i5-14100F / RTX 3050): the **High** preset runs
at 1080p with shadows and a 240 m render distance at a smooth frame rate.

## Controls

| Key | Action |
| --- | --- |
| W A S D / arrows | Move |
| Mouse | Look |
| Shift | Sprint |
| Ctrl | Crouch |
| Left click | Chop the nearest tree with your best axe |
| E | Interact (add fuel, scavenge, rescue, plant/harvest, sleep, open bench) |
| I | Inventory (click to select, click again to split, click two slots to move) |
| C | Crafting bench (Craft / Grinder / Build tabs) |
| B | Build mode: R rotates, right click places, B cancels |
| M | Map |
| F | Flashlight (stuns nearby night hunters) |
| F5 | Save |
| Esc | Pause / close panels |

## Graphics settings

Open **Settings** on the main menu (also reachable from the pause menu):

- **Presets**: Low, Medium, High, Ultra.
- **Individual options**: resolution, fullscreen, VSync, render distance, shadows,
  sound volume, music volume. Changes are saved to `config/settings.json`
  (`user_settings` block) and can be hand-edited there too.

## Saves

- Three save slots, shown on **Load Game**. The game auto-saves every new day and
  on F5.
- Diamonds, owned classes, best day and wins are stored permanently in
  `saves/profile.json` and persist between runs, even after a defeat.

## Configuration

Everything important is data-driven in `config/`:

| File | Contents |
| --- | --- |
| `items.json` | The item database (names, categories, rarity, stacks, food effects) |
| `recipes.json` | Crafting bench tiers 1-5, all recipe costs, structure definitions, cooking |
| `classes.json` | Classes, verified diamond prices, starting items, passive perks |
| `loot_tables.json` | Per-location-type loot tables and rarity weights |
| `progression.json` | Day/night timing, campfire levels and fuel values, tools, trees, farming, grinder, diamond rewards |
| `settings.json` | Graphics presets, user settings, world size, player stats |

## Testing

```
python tests/test_logic.py
```

19 logic tests cover the inventory, crafting bench and upgrades, grinder, campfire
fuel and levels, day/night cycle, weather, farming, tree harvesting per tool,
world generation, children rescue, animals, threats, player stats, classes,
diamond rewards, the save system, victory/defeat and a full game-manager
integration scenario.

## Implemented features

- Main menu, credits, class selection (8 classes with verified diamond prices),
  settings with four graphics presets, save-slot selection, pause menu.
- Seeded procedural world: hills, water, four biomes (forest, dense woodland,
  snowy, magical), ~60 locations (cabins, houses, grocery stores, clinics,
  mechanical buildings, warehouses, campsites, ruins, caves, cultist outposts,
  chests), colour-coded children caves.
- Verified day/night cycle (3-minute day, 90-second night) with sunrise, sunset,
  stars, moonlit fog and per-phase lighting.
- Campfire with six levels, animated flames and smoke, fuel meter, safe zone,
  low-fuel warnings, weather-sensitive burn rate, per-level visual changes.
- Fuels: logs, coal, biofuel, fuel canisters, oil barrels (configurable values).
- Tree chopping: five tree sizes, five axes with verified hit counts
  (Old Axe 5 hits, Strong Axe 1 hit / 35 on big trees, Chainsaw 2 / 38),
  progressive visible damage, falling animation, log and sapling drops.
- Inventory with stacking, moving, splitting, item use, rarity colours.
- Crafting bench with five verified tiers and all verified recipe costs;
  grinder (items -> wood/scrap/biofuel); cooking (campfire + Crock Pot stew).
- Building placement with transparent preview, rotation and collision checks;
  structures render at the camp (beds, walls, farm plots, storage, utilities).
- Farming: four crops, weather-influenced growth, harvest with seed drops.
- Four missing children (Dino, Squid, Kraken, Koala Kid) with personalities,
  dialogue and campfire-level rescue gates; rescued children wander the camp.
- Wildlife (bunnies, deer, birds) with wander/flee AI; night hunters with
  distinct AI: The Deer (patrol/search/chase, fears the campfire), The Owl
  (swoops) and The Ram (line-charge that knocks down trees). Night one is safe.
- Weather: clear, rain, fog, storm, snow; affects visibility, fuel burn and crops.
- Procedurally synthesised audio (ambience, night, rain, thunder, chopping,
  falling trees, crafting, building, collecting, warnings, victory, defeat).
- Victory screen at day 99, defeat screen, run statistics, configurable diamond
  rewards that persist forever.
- Robust saving: atomic writes, corruption quarantine, three slots, world seed
  and world changes (looted buildings, felled trees, placed structures).

## Incomplete or simplified features

- Caves are rendered as cave-mouth structures rather than fully explorable
  interiors. (Technical limitation: full interiors would need a second scene
  graph per cave; the rescue gameplay loop is complete without them.)
- Animal models are simple low-poly primitives; there are no skeletal animations.
- The minimap is not implemented; the full map (M) is.
- Class level progression (levels I-III per class in the original) is not
  implemented; classes have fixed perks, documented in `config/classes.json`.
- Teleporters are placeable and saved but do not yet link two pads for travel.
- 3D spatial audio is approximated by distance-based volume falloff.
- Multiplayer features of the reference game are intentionally absent
  (single-player only).

## Documentation

- `docs/research.md` — reference research: verified mechanics, values and
  sources, plus identified uncertain information.
- `docs/devlog.md` — development log and stage-by-stage status.

## Licence and credits

Original code and assets (procedurally generated at runtime). Inspired by the
systems of *99 Nights in the Forest* (Grandma's Favourite Games); no assets,
code, maps or audio from that game are used. Built with the Panda3D engine.
