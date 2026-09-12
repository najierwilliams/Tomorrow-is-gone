# Development Roadmap

- **Platform Target**
  - PlayStation 5 exclusive

- **Phase 1 — Foundation (Implemented)**
  - Establish repository architecture
  - Define core data schemas
  - Implement minimal, testable prototypes for player, survival, inventory, weapons, zombies, loot, progression, and save/load

- **Phase 1.5 — Multiplayer World Architecture (Designed + Contracted)**
  - Define architecture contracts for server configuration and multiplayer authority
  - Define unified human/infected/zombie player-state contracts
  - Define world region/chunk/streaming contracts for very large persistent maps with configurable finite vertical range
  - Define persistence-domain boundaries (player/world/inventory/structures/destruction/vehicles/NPC/loot/server-config)
  - Define zombie sanity bands for data-driven behavioral consequence mapping
  - Define cure-gated human reversion contracts for infected/zombie forms
  - Define contract surfaces for animals, loot tiers, crafting/workbenches, durability, vehicles, NPCs, missions, economy, and weather
  - Document Unity adapter boundaries while keeping gameplay rules engine-independent

- **Phase 1.6 — Authoritative Multiplayer Slice (Implemented)**
  - Implemented a thin server-authoritative runtime over Phase 1.5 contracts
  - Implemented chunk interest management and limited-slice persistence behaviors
  - Implemented one human and one zombie mission end-to-end runtime path
  - Implemented local multiplayer simulation and authoritative combat replication
  - Integrated replicated state snapshots into the Phase16 Unity adapter prototype

- **Phase 2 — Core Gameplay Runtime Expansion (Implemented)**
  - Expanded authoritative survival runtime loops for human and zombie forms
  - Added server-authoritative inventory usage, equipment, crafting, gathering, gardening, construction, destruction, economy, and power foundations
  - Added persistent animals, infected animal abilities, taming, horde foundations, expanded missions/progression, and chunk-aware replication payloads

- **Phase 3 — AI and Encounter Expansion (Implemented)**
  - Added engine-independent navigation abstraction and deterministic provider
  - Added server-authoritative zombie perception, sensory memory, target scoring/switching, pursuit abandonment, and encounter recruitment logic
  - Added dynamic horde member grouping/splitting by individual NPC target decisions
  - Added human NPC encounter response foundation (threat detection, flee/combat, investigate/wander)
  - Added chunk-aware AI evaluation, AI state persistence, and Unity adapter AI/perception projection support

- **Phase 4 — World, Streaming & Environment (Implemented)**
  - Added engine-independent large finite world coordinate contracts and deterministic world addressing
  - Added chunk lifecycle metadata and data-driven streaming/interest radii
  - Added deterministic baseline world generation contracts and static-vs-dynamic persistent delta separation
  - Added biome/POI/spawn/environment/season/weather/underwater data contracts and definitions
  - Extended authoritative runtime + Unity adapter projection for chunk metadata and environment state

- **Phase 5 — Final Core Systems & Unity Integration Preparation (Implemented)**
  - Finalized authoritative contracts for vehicles, world time/day-night, respawn, and event streaming
  - Added Phase 5 data definitions, schema-oriented validation, and custom-content/real-world provider abstractions
  - Extended replication + Unity adapter projection boundaries and authoritative client-intent hardening

- **Phase 6 — Unity Integration**
  - Build Unity presentation and interaction layers against finalized authoritative contracts

- **Phase 7 — World and Content Scale-Out**
  - Expand city/region content density and mission/world-event depth

- **Phase 8 — Unity Multiplayer Integration**
  - Productionize Unity-side adapters, transport, prediction/interpolation, and content streaming

- **Phase 9 — Playable Alpha**
  - Stable multiplayer vertical slice with persistence and progression

- **Phase 10 — Public Early Build**
  - External testing, balancing passes, and iterative systems hardening

- **Phase 11 — Live Expansion**
  - Content growth, optimization, and post-launch systems evolution
