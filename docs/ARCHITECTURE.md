# Tomorrow Is Gone Architecture

## Current Architecture Phases

Platform target: **PlayStation 5 exclusive**.

### Phase 1 — Foundation (Implemented)
Phase 1 provides engine-independent prototype rules in `prototypes/core` and data-driven JSON content in `data/`.

Implemented baseline systems:
- Player stats and progression (`PlayerStats`)
- Inventory and item stacking
- Item and loot data loading
- Weapon durability prototype behavior
- Zombie state-machine prototype
- Save/load JSON snapshot contract
- Foundational tests for the above systems

### Phase 1.5 — Multiplayer World Architecture (Designed + Minimal Contracts)
Phase 1.5 defines long-term architecture boundaries and data contracts for multiplayer world-scale development without implementing full gameplay systems.

Implementation level in this phase:
- Added architecture contracts module: `prototypes/core/phase15_contracts.py`
- Added architecture-level contract tests: `tests/test_phase15_architecture_contracts.py`
- Added design document: `docs/PHASE_1_5_MULTIPLAYER_WORLD_ARCHITECTURE.md`
- Hardened contract boundaries for cure-gated form transitions, zombie sanity bands, finite vertical world partitioning, loot container-tier eligibility mapping, and server-authoritative client-intent flows

Not implemented in this phase:
- Full gameplay logic for new systems
- Unity runtime implementation
- Networking transport implementation
- Database/back-end implementation
- Phase 1.6 authoritative runtime slice (implemented in the next phase)

### Phase 1.6 — Authoritative Multiplayer Slice (Implemented)
Phase 1.6 adds a runnable authoritative prototype runtime on top of the Phase 1.5 contracts.

Implementation level in this phase:
- Added runtime implementation: `prototypes/core/phase16_authoritative_runtime.py`
- Added Unity adapter implementation: `unity/phase16_unity_adapter.py`
- Added runtime validation tests: `tests/test_phase16_authoritative_slice.py`
- Added phase documentation: `docs/PHASE_1_6_AUTHORITATIVE_MULTIPLAYER_SLICE.md`
- Validated authoritative command-intent flow, chunk interest management, tiered loot, partitioned persistence, missions, and combat replication

### Phase 2 — Core Gameplay Runtime Expansion (Implemented)
Phase 2 extends the Phase 1.6 runtime into an authoritative survival simulation while preserving engine-independent boundaries.

Implementation level in this phase:
- Expanded authoritative runtime models for human survival, zombie survival, inventory/equipment, crafting/workbenches, gathering, gardening, construction, destruction, infection, animals/taming, hordes, progression, missions, economy, and power abstraction
- Added data-driven Phase 2 definition loading from `data/phase2_definitions.json`
- Expanded persistence partitions for new gameplay domains (equipment/progression/economy/missions/world entities)
- Expanded chunk-aware authoritative snapshots for inventory/equipment, animals, structures, resources, gardens, power, economy, missions, and NPC foundation records
- Expanded deterministic test world with representative entities for core gameplay systems
- Added comprehensive Phase 2 runtime tests in `tests/test_phase2_core_gameplay_runtime.py`

### Phase 3 — AI and Encounter Expansion (Implemented)
Phase 3 extends the authoritative runtime with engine-independent AI encounter systems while preserving server authority and Phase 2 stability.

Implementation level in this phase:
- Added engine-independent AI/navigation contracts and deterministic navigation provider in `prototypes/core/phase3_ai.py`
- Added data-driven AI balancing configuration in `data/phase3_ai_definitions.json`
- Extended authoritative runtime with zombie perception (vision/hearing/memory), deterministic target scoring/selection/switching, pursuit abandonment, and dynamic horde grouping/splitting
- Added player-zombie recruitment catalyst behavior for meaningful hostile encounters (without auto-follow from proximity alone)
- Added human NPC encounter foundations for threat detection, flee/combat response, and investigate/wander behavior
- Added chunk-aware AI filtering and required NPC AI persistence state
- Extended Unity adapter projection to include NPC AI state and perception events
- Added focused Phase 3 deterministic tests in `tests/test_phase3_ai_encounter_expansion.py`

## Phase 1.5 Layering Model

- **Engine-independent contracts (now):**
  - Data models and interfaces under `prototypes/core/phase15_contracts.py`
  - Persistent domain separation contracts
  - Server configuration and world-grid/chunking contracts
- **Future Unity-specific adapters:**
  - Scene/prefab streaming orchestration
  - MonoBehaviour wrappers and Netcode transport bindings
  - Client-side interpolation/prediction presentation layers
- **Future server/runtime implementations:**
  - Authority logic and synchronization runtime
  - Persistent storage repositories
  - Mission/economy/weather/npc runtime controllers

## System Responsibilities and Dependencies (Phase 1.5)

The complete per-system breakdown for all 20 required systems is documented in:
- `docs/PHASE_1_5_MULTIPLAYER_WORLD_ARCHITECTURE.md`

At a high level:
1. Server architecture owns session authority and system orchestration.
2. Server configuration injects rules into all gameplay systems.
3. Player state is unified across human/infected/zombie forms.
4. Transformation and zombie sanity extend player state rather than forking architecture, and human reversion is cure-gated.
5. Zombie sanity behavior consequences remain data-driven via sanity bands.
6. Animal state and abilities are data-driven and shared across normal/infected/tamed variants.
7. World region/chunk architecture is required for 1:1-scale streaming and persistence with configurable finite vertical range comparable to large Minecraft-style finite limits.
8. Building/destruction persist deltas, not full scene state.
9. Loot architecture distinguishes container -> container tier -> eligible loot pools before runtime randomization.
10. Loot/crafting/durability/vehicles/NPC/missions/economy/weather all depend on server config + persistence contracts.
11. Multiplayer authority/sync defines write ownership and replicated topics, with clients submitting command intents.
12. Unity integration remains an adapter layer over contract-defined systems.

## Data-Driven Expansion Strategy

Phase 1.5 architecture expands the contract surface to support:
- Server configs and custom rules
- Zombie tiers and sanity bands
- Animal infection/taming/abilities
- Chunked world regions and persistent world edits across configurable finite vertical layers (surface, underground, underwater, above-ground construction)
- Structures and destruction records
- Loot tiers, container tiers, and container eligibility contracts
- Recipes and workbench requirements
- Durability state
- Vehicles, NPCs, missions, economy, weather
- Explicit persistence-domain partitioning

These are contract-first definitions and are intentionally implementation-light.

## Unity Integration Direction

Unity remains an integration shell around engine-independent rules:
1. Load contract-driven data from `data/` and server configuration payloads.
2. Stream world chunks/regions based on server authoritative interest management.
3. Render and animate entities from replicated state topics.
4. Keep gameplay decisions in server/core logic rather than scene scripts.

## Recommended Next Phase

**Phase 4 — Combat and Equipment Runtime**
- Expand modular combat depth and equipment balancing over the new encounter AI layer.
- Continue PS5-first runtime progression while preserving server-authoritative boundaries.
- Stage production networking/platform concerns for later phases.
