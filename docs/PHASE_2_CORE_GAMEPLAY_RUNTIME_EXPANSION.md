# Phase 2 — Core Gameplay Runtime Expansion

## Objectives
Phase 2 expands the Phase 1.6 authoritative runtime into a functional core survival simulation while preserving server authority, modularity, chunk-aware world integration, and Unity adapter boundaries.

## Systems Implemented
- Human survival runtime: hunger/thirst depletion, stamina recovery, starvation/dehydration damage, healing, death state
- Zombie survival runtime: feeding requirements, no water requirement, sleep healing, sanity bands, tier progression hooks, death
- Unified infection flow: human infection progression and authoritative form transitions; zombie infection of humans; zombie infection of animals
- Inventory/item usage: authoritative add/remove, stack handling, item use validation, food/medicine consumption
- Equipment runtime: weapon/armor equip state, durability, attack resolution, armor mitigation, unusable condition
- Crafting/workbenches: data-driven recipes, material validation, workbench compatibility and power checks
- Resource gathering: authoritative node depletion/respawn and inventory grant
- Gardening: planting, watering, growth, harvest, plant health persistence
- Construction/destruction: human build permissions, zombie build denial, structure health/state, authoritative destruction records
- Power foundation: grouped source/device power generation/consumption with insufficient-power behavior
- Animals: persistent animal entities, habitat categories, infection state, tame state, ownership
- Infected animal abilities: data-driven ability domains (combat/crafting/gardening/building/gathering)
- Horde foundation: zombie-only membership, leader references, join/leave persistence
- Missions/progression/economy: audience-gated missions, objective progression, XP/level progression, zombie tier progression hooks, currency earn/spend
- NPC foundation: persistent NPC human/zombie settlement/shop references

## Architecture
- Core runtime remains in `prototypes/core/phase16_authoritative_runtime.py`
- Contracts remain engine-independent in `prototypes/core/phase15_contracts.py`
- Definitions are loaded from `data/phase2_definitions.json`
- Runtime separates player/world/equipment/progression/economy/missions domains for persistence and testing

## Authoritative Command Flow
All gameplay actions follow:
`CLIENT INTENT -> SERVER VALIDATION -> SERVER MUTATION -> PERSISTENCE -> REPLICATION`

Implemented representative command topics:
- `player.move`
- `player.interact`
- `player.infect`
- `zombie.feed`
- `zombie.sleep`
- `player.inventory_action`
- `player.use_item`
- `player.equip`
- `crafting.start`
- `gather.resource`
- `garden.action`
- `structure.build`
- `structure.damage`
- `animal.tame`
- `animal.use_ability`
- `horde.membership`
- `economy.mutate`
- `power.source_toggle`
- `mission.accept`
- `mission.progress`

## Data-Driven Systems
`data/phase2_definitions.json` now drives:
- Items
- Food
- Medicine
- Weapons
- Armor
- Recipes
- Workbenches
- Loot tiers
- Resource nodes
- Crops
- Structures
- Animals
- Animal abilities
- Zombie tiers
- Zombie sanity bands
- Missions
- Progression
- Power source/device definitions
- Economy config
- Survival config

## Persistence Domains
Runtime now persists partitioned keys for:
- `players`
- `inventories`
- `equipment`
- `progression`
- `economy`
- `missions`
- `world` (chunks, resources, gardens, structures, destruction, animals, hordes, power, NPCs, workbenches)
- `loot`

## Multiplayer and Chunk Integration
- Chunk interest remains authoritative and scoped per player
- Replicated snapshots include only chunk-relevant world entities
- Snapshot payloads expanded for inventory/equipment, animals, structures, resources, gardens, power, missions, economy, hordes, and NPC foundations

## Unity Boundary
`unity/phase16_unity_adapter.py` was expanded to project representative authoritative snapshots for:
- Player state
- Inventory/equipment
- Missions
- Animals
- Structures
- World/chunk entities and power state

## Testing
- Existing Phase 1/1.5/1.6 tests remain
- Added `tests/test_phase2_core_gameplay_runtime.py` with targeted runtime coverage across human, zombie, animals, shared authority, persistence, and multiplayer interactions

## Limitations and Deferred Scope
Phase 2 intentionally does not implement:
- Advanced zombie AI
- Advanced NPC AI
- Vehicle simulation
- Full underwater gameplay systems
- Dynamic weather/seasons
- Final UI/graphics/audio/animation
- Production networking stack and PS5 SDK integration

## Preparation for Phase 3
Phase 2 establishes persistent, data-driven, server-authoritative runtime contracts that Phase 3 can extend with richer AI and encounter behavior without moving gameplay rules into Unity.
