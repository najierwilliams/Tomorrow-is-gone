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

- **Phase 1.6 — Authoritative Multiplayer Slice (Recommended Next)**
  - Not implemented yet in this architecture-hardening pass
  - Implement a thin server-authoritative runtime over Phase 1.5 contracts
  - Implement chunk interest management and persistence for a limited map district
  - Implement one human and one zombie mission end-to-end
  - Integrate replicated state snapshots into Unity adapter prototypes

- **Phase 2 — Core Gameplay Runtime Expansion**
  - Expand movement, interactions, scavenging, survival loops on top of authority model

- **Phase 3 — AI and Encounter Expansion**
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
