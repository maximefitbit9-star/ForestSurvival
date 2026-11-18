# Reference Research — 99 Nights in the Forest

This document records what was verified from public wiki sources about the
reference game, what is uncertain, and how it maps onto this original game.
The primary wiki (99-nights-in-the-forest.fandom.com) blocked automated access,
so research used the game's independent wiki mirror (99nightsintheforest.wiki),
the Miraheze mirror, and cross-checked guides (GamesRadar, IGN). Sources were
cross-verified where possible.

## Verified mechanics and values

### Day/night cycle
- Each day lasts **3 minutes**, each night **1 minute 30 seconds**; a full cycle
  is 4 minutes 30 seconds. (Multiple concordant sources.)
- The Deer does not attack on the first night.
- Beds rescue-time: rescuing children and crafting beds raises the day counter
  multiplier (up to 9 days per night in the original). Adapted here as bed
  sleep-to-skip and per-child bonuses.
- A Sun Dial (bench tier 2) shows the time until day/night.

### Campfire
- Levels **1 to 6**. Level ups by filling a fuel bar with flammable items.
- Each level increases the explorable map size and the safe-zone radius.
- Higher levels resist rain and snow; level 6 depletes slower.
- Tier visuals (verified descriptions): T1 basic logs; T2 three log benches;
  T3 six rocks; T4 twelve rocks; T5 stone base built around the fire.
- Fuels: Logs, Coal, Fuel Canisters, Biofuel, Oil Barrels. Coal burns about
  4x longer than wood; at level 4+ a log adds less than 1%.
- A guaranteed coal pile / 6-log pile near spawn reaches fire level 2 on day one.
- If the fire goes out at night, players must hide (e.g. in a cabin, on a shelf)
  until morning.

### Crafting bench (all costs verified against the wiki's tables)
- Tier 1: Map (3 Wood), Old Bed (20 Wood), Bunny Trap (5 Wood),
  Bench 2 (5 Wood, 1 Scrap).
- Tier 2: Sun Dial (5 Scrap), Regular Bed (5 Scrap), Compass (3 Scrap),
  Freezer (4 Scrap), Farm Plot (10 Wood), Wood Rain Storage (5 Scrap),
  Shelf (2 Scrap), Log Wall (12 Wood), Bear Trap (3 Scrap),
  Bench 3 (15 Wood, 15 Scrap).
- Tier 3: Crock Pot (15 Wood, 10 Scrap), Radar (15 Wood, 10 Scrap),
  Boost Pad (15 Wood, 10 Scrap), Biofuel Processor (12 Wood, 12 Scrap),
  Torch (6 Wood, 6 Scrap), Good Bed (10 Wood, 10 Scrap), Lightning Rod (8 Scrap),
  Bench 4 (30 Wood, 20 Scrap, 2 Cultist Gems).
- Tier 4: Ammo Crate (20 Wood, 30 Scrap, 1 Cultist Gem), Oil Drill
  (25 Wood, 35 Scrap, 1 Cultist Gem), Giant Bed (20 Wood, 30 Scrap,
  1 Cultist Gem), Teleporter (15 Wood, 25 Scrap, 1 Cultist Gem),
  Bench 5 (50 Wood, 50 Scrap, 1 Gem of the Forest).
- Tier 5: Respawn Capsule, Time Accelerator, Weather Machine (each 50 Wood,
  50 Scrap, 1 Gem of the Forest).
- Total materials to reach bench level 5: 81 Scrap, 100 Wood, 2 Cultist Gems,
  1 Gem of the Forest (IGN cross-check).

### Trees and axes
- Big trees give **12 logs and 3-4 saplings**; normal trees give **3 logs and
  0-1 saplings**.
- Strong Axe: **1 hit** per normal tree, **35 hits** per big tree.
- Chainsaw: **2 hits** normal, **38 hits** big.
- Ice Axe: **5 hits** normal.
- Saplings can be replanted; trees are finite but very numerous.

### Grinder
- Located by the campfire (east side / left of the bench).
- Converts items into materials (e.g. bolts into scrap, chairs/tires into
  wood/scrap, crops into biofuel). Exact per-item quantities are not published.

### Children (verified structure)
- Four missing children: Dino Kid, Squid Kid, Kraken Kid, Koala Kid.
- Held in colour-coded caves guarded by wolves (Dino) or bears; Kraken Kid
  requires campfire level 5 and a yellow key; Koala Kid requires campfire
  level 6 and is guarded by six bears.
- After rescue they settle within the campfire radius.

### Threats (verified behaviours)
- The Deer: main antagonist; hunts at night; fears the campfire's light;
  cannot reach players inside the safe zone; more aggressive on later nights;
  can be briefly stunned by a flashlight.
- The Owl and The Ram: additional night threats. The Ram charges in a line and
  knocks down trees.
- Camps are raided by cultists every few nights in the original.

### Classes (verified diamond prices)
- Camper 10, Scavenger 25, Medic 40, Fisherman 50, Lumberjack 70,
  Berserker 100, Chef 150, Blacksmith 200. Higher tiers exist (Assassin 500;
  Cyborg / Pyromaniac / Big Game Hunter / Necromancer / Vampire at 600).
- Classes are bought with Diamonds earned from badges, chests and long runs.
- Lumberjack gets extra wood; Blacksmith gets grinder scrap bonuses and craft
  discounts (verified).

### Diamonds
- Earned from badges, diamond chests in the Cultist Stronghold, and surviving
  50 or 99 nights. Persist between games.

## Uncertain, contradictory or unavailable information

- **Exact campfire fuel amounts per level**: wiki figures are ranges that vary
  with player count ("275-350+ logs" etc.) and are not reliable for a
  single-player adaptation. This game uses configurable thresholds in
  `config/progression.json` instead, with the verified relative fuel values.
- **Grinder output quantities**: not published; original values used.
- **Old/Good axe hit counts**: the wiki documents Strong, Ice and Chainsaw
  precisely but not the starter axes; 5 and 3 hits are original adaptations.
- **Class level progression (I-III)**: verified to exist, but the per-level perk
  details are inconsistent between sources; not implemented.
- **The original day-counter multiplier (beds + children)**: verified in
  spirit; exact stacking rules are unclear; simplified to sleep-to-skip.
- **Cultist raids**: verified for the multiplayer original; replaced here by
  the Deer/Owl/Ram night pressure plus cultist outposts as loot locations.

## Adaptation policy

Where a value could not be verified, the configuration files carry a `note`
field marking it as an original adaptation. Nothing unverified is presented as
a wiki fact. No assets, code, maps, models, textures or audio from the
reference game are used; all content here is procedurally generated originals.
