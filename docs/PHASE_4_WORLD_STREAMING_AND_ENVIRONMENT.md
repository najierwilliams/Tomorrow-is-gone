# Phase 4 — World, Streaming & Environment

## Scope
Phase 4 delivers the engine-independent authoritative world foundation for large finite coordinates, chunk/region streaming, persistent world deltas, and environment contracts. Unity remains an adapter.

## World Coordinate System
- Implemented in `prototypes/core/phase4_world.py` via `WorldCoordinateMapper`.
- Supports world -> region -> chunk -> local conversion and reverse conversion.
- Uses integer/fixed authoritative coordinates (`WorldPosition`, `ChunkCoordinate`, `RegionCoordinate`).
- Enforces finite world bounds with explicit validation.

## Chunk Lifecycle and Region Architecture
- Chunk lifecycle states: `unloaded`, `loading`, `active`, `unloading`, `failed`.
- Runtime tracks lifecycle metadata per chunk in `WorldChunkRuntime`.
- Deterministic chunk identity and baseline metadata are retained independent of Unity.

## Streaming and Interest Management
- Data-driven radii loaded from `data/phase4_world_definitions.json`:
  - simulation radius
  - replication radius
  - persistence activation radius
  - AI interest radius
  - vertical radius
- Server computes relevant chunks from player chunk position; clients do not force chunk loads.

## Persistence and Static/Dynamic Separation
- Baseline world data is deterministic (seed + chunk + generation version).
- Persistent changes are modeled as deltas (`ChunkPersistentDelta`) for destroyed structures, harvested nodes, modified containers, and persistent entities.
- Unload/reload preserves structure/resource/container state through authoritative persistence.

## Deterministic Generation
- `DeterministicWorldGenerator` provides deterministic terrain/resource/POI/spawn baselines per chunk.
- Baseline generation never directly overwrites persisted deltas.

## World Objects, Resources, Structures, Containers
- Engine-independent persistent object contracts include stable IDs, object type, chunk ownership, and persistence classification.
- Resource nodes and structures are chunk-owned in runtime snapshots/persistence.
- Resource gather and structure destruction remain server-authoritative.
- Container looted state and generated loot remain persistent and chunk-scoped.

## POIs, Biomes, Spawning
- Data-driven biome and POI contracts support future city/region realism.
- Data-driven spawn rule contracts support biome gating, distance checks, and active limits.
- Persistent/semi-persistent/transient despawn distinctions are defined.

## AI and Navigation Integration
- Phase 3 AI remains intact and chunk-aware.
- AI relevance continues to be filtered by chunk proximity.
- Navigation remains replaceable and chunk/tile aware through existing abstraction boundaries.

## Replication
- Authoritative replication remains interest-based.
- Runtime snapshots now include chunk lifecycle metadata and environment-state projection.
- Clients receive relevant chunks/entities only and cannot authoritatively mutate world state.

## Environment, Seasons/Weather, Underwater Foundation
- Added contracts and data definitions for:
  - biome environmental modifiers
  - season definitions and weather weighting
  - regional environment state
  - underwater-capable biome/state representation
- No final weather simulation or final rendering is implemented in this phase.

## Unity Adapter Integration Points
- `unity/phase16_unity_adapter.py` now projects:
  - chunk metadata
  - environment state by region
  - existing world entities/containers/resources
- Unity remains presentation-only; authoritative state stays in core runtime.

## External Repository Decisions
- No external repositories or third-party components were integrated in Phase 4.
- Referenced external projects remain research-only due to architecture and authority constraints.

## Known Limitations
- World generation is intentionally simple and deterministic, not production terrain quality.
- Runtime still uses a prototype in-process transport and JSON persistence.
- Navigation invalidation from structural destruction is contract-ready but not full production mesh rebuilding.

## Future Unity Integration
- Unity can consume replicated chunk/environment metadata for streaming visualization.
- Future work can layer final terrain, weather visuals, city art, and underwater rendering without changing authority contracts.
