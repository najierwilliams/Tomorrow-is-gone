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

- **Phase 3 — AI and Encounter Expansion (Recommended Next)**
  - Extend zombie and NPC runtime behaviors with data-driven profiles

- **Phase 4 — Combat and Equipment Runtime**
  - Implement modular combat resolution, durability interactions, and balancing

- **Phase 5 — World and Content Scale-Out**
  - Expand region streaming, mission content, weather profiles, and economy depth

- **Phase 6 — Unity Multiplayer Integration**
  - Productionize Unity-side adapters, transport, prediction/interpolation, and content streaming

- **Phase 7 — Playable Alpha**
  - Stable multiplayer vertical slice with persistence and progression

- **Phase 8 — Public Early Build**
  - External testing, balancing passes, and iterative systems hardening

- **Phase 9 — Live Expansion**
  - Content growth, optimization, and post-launch systems evolution
