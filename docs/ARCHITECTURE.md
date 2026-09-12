# Tomorrow Is Gone Architecture

## Current Architecture Phases

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

Not implemented in this phase:
- Full gameplay logic for new systems
- Unity runtime implementation
- Networking transport implementation
- Database/back-end implementation

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
4. Transformation and zombie sanity extend player state rather than forking architecture.
5. Animal state and abilities are data-driven and shared across normal/infected/tamed variants.
6. World region/chunk architecture is required for 1:1-scale streaming and persistence.
7. Building/destruction persist deltas, not full scene state.
8. Loot/crafting/durability/vehicles/NPC/missions/economy/weather all depend on server config + persistence contracts.
9. Multiplayer authority/sync defines write ownership and replicated topics.
10. Unity integration remains an adapter layer over contract-defined systems.

## Data-Driven Expansion Strategy

Phase 1.5 architecture expands the contract surface to support:
- Server configs and custom rules
- Zombie tiers and sanity
- Animal infection/taming/abilities
- Chunked world regions and persistent world edits
- Structures and destruction records
- Loot tiers and containers
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

**Phase 1.6 — Multiplayer Runtime Vertical Slice**
- Implement a minimal authoritative server loop over selected Phase 1.5 contracts.
- Implement chunk interest management + persistence for a limited test map.
- Implement one end-to-end mission path for both human and zombie audiences.
- Implement Unity adapters for replicated player/world snapshots.
