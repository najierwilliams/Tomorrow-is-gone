# Phase 1.5 — Multiplayer World Architecture

This phase defines architecture and contracts required to safely scale toward a persistent multiplayer open world (including 1:1-scale city maps) without prematurely implementing full gameplay systems.

Platform target: **PlayStation 5 exclusive**.

## Architectural Principles
- Contract-first, implementation-light.
- Engine-independent core models and interfaces.
- Data-driven configuration for content and balancing.
- Server-authoritative writes for persistent world state.
- Region/chunk/cell partitioning for world-scale streaming.
- Delta persistence for modifications/destruction/building.
- Loose coupling via explicit interfaces and payload contracts.

## Implemented in Code (Architecture Contracts Only)
- `prototypes/core/phase15_contracts.py`
  - Core data models (player form, server config, animals, world/chunks, structure/destruction, loot/crafting/workbench, durability, vehicles, NPC, missions, economy, weather, persistence, replication)
  - Key protocol interfaces (`ServerConfigurationProvider`, `PersistentStateRepository`, `WorldChunkStream`, `UnityIntegrationPort`)
- `tests/test_phase15_architecture_contracts.py`
  - Minimal tests validating critical contract invariants

---

## 1) Server Architecture
- **Responsibility:** authoritative simulation orchestration and write control.
- **Core data:** `ServerConfiguration`, `ReplicationRule`, persistence layout.
- **Interfaces/contracts:** server configuration provider + persistence repository.
- **Engine-independent:** simulation orchestration contracts.
- **Unity-specific:** client transport endpoints and scene synchronization hooks.
- **Dependencies:** configuration, authority/sync, persistence, world chunking.

## 2) Server Configuration
- **Responsibility:** centralized runtime policy input (public/private/custom/creative/rules/difficulty/missions/map).
- **Core data:** `ServerRuleSet`, `ServerConfiguration`.
- **Interfaces/contracts:** configuration provider.
- **Engine-independent:** full model.
- **Unity-specific:** settings UI/editor pipelines.
- **Dependencies:** missions, economy, weather, NPC, loot, world rules.

## 3) Player State Architecture
- **Responsibility:** unified player representation for human/infected/zombie.
- **Core data:** `PlayerStateModel`, `PlayerForm`.
- **Interfaces/contracts:** player persistence payloads (future implementation).
- **Engine-independent:** full model and transitions.
- **Unity-specific:** avatar presentation, animation layers, VFX/audio.
- **Dependencies:** transformation, sanity, missions, inventory, persistence.

## 4) Human/Zombie Transformation Architecture
- **Responsibility:** progression/cure state machine without splitting player model.
- **Core data:** `PlayerForm`, `infection_progress` in `PlayerStateModel`.
- **Interfaces/contracts:** `is_valid_form_transition(...)`.
- **Engine-independent:** transition rules with cure-gated return to `HUMAN` from `INFECTED_HUMAN` and `ZOMBIE`.
- **Unity-specific:** cinematic and visual transformation effects.
- **Dependencies:** player state, sanity, cure mission/economy systems.

## 5) Zombie Sanity Architecture
- **Responsibility:** zombie mental-state resource affecting behavior tuning.
- **Core data:** `ZombieSanityState`, `ZombieTierDefinition`, `ZombieSanityBandDefinition`.
- **Interfaces/contracts:** sanity delta application + sanity-band resolution.
- **Engine-independent:** value constraints, tier metadata, and data-driven sanity-band consequence metadata (coexistence, hostility, cure eligibility, mission availability, behavior tags).
- **Unity-specific:** post-processing, audio distortion, feedback FX.
- **Dependencies:** transformation, missions, feeding/combat systems.

## 6) Animal/Infection/Taming Architecture
- **Responsibility:** single model for wild/tamed/pet/infected/underwater variants.
- **Core data:** `AnimalStateModel`, `InfectionState`, `TameState`, `AnimalHabitat`, `AnimalAbilityDefinition`.
- **Interfaces/contracts:** ability IDs reference external data tables.
- **Engine-independent:** model + ability domain structure.
- **Unity-specific:** movement controllers, animation rigs, behavior trees.
- **Dependencies:** missions, crafting/building bonuses, persistence.

## 7) Persistent World Architecture
- **Responsibility:** durable representation of world modifications.
- **Core data:** `StructureRecord`, `DestructionRecord`, persistence categories.
- **Interfaces/contracts:** persistent state repository.
- **Engine-independent:** event/state contracts.
- **Unity-specific:** mesh regeneration and scene object realization.
- **Dependencies:** chunking, building/destruction, save architecture.

## 8) World Region/Chunk/Streaming Architecture
- **Responsibility:** scalable world partitioning for large maps.
- **Core data:** `WorldCoordinate`, `ChunkAddress`, `WorldGridConfig`.
- **Interfaces/contracts:** `WorldChunkStream.required_chunks_for_player`.
- **Engine-independent:** coordinate partitioning and interest contracts, including configurable finite vertical world bounds (not unlimited) comparable to large Minecraft-style finite limits, with above-ground, underground, and underwater layering support.
- **Unity-specific:** additive scene streaming, LOD object activation.
- **Dependencies:** persistence, authority/sync, vehicles, NPC spawning.

## 9) Building/Destruction Architecture
- **Responsibility:** player-built and destructible structures represented as persistent deltas.
- **Core data:** `StructureRecord`, `DestructionRecord`.
- **Interfaces/contracts:** structure/destruction state persistence operations.
- **Engine-independent:** records and invariants.
- **Unity-specific:** construction previews, destruction visuals, debris simulation.
- **Dependencies:** chunking, persistence, authority/sync, crafting.

## 10) Loot and Container Tier Architecture
- **Responsibility:** controlled randomized loot by container/tier and region rules.
- **Core data:** `LootTierDefinition`, `LootContainerDefinition`.
- **Interfaces/contracts:** loot generation service contract (future runtime) over `container -> container tier -> eligible loot pools`.
- **Engine-independent:** tier/container schema including eligible categories and quality-level boundaries per tier.
- **Unity-specific:** container interactables and loot UI.
- **Dependencies:** economy balance, persistence, server config.

## 11) Crafting/Workbench Architecture
- **Responsibility:** data-driven crafting with station gating.
- **Core data:** `RecipeDefinition`, `WorkbenchDefinition`.
- **Interfaces/contracts:** recipe resolution and validation service (future runtime).
- **Engine-independent:** recipe/workbench schema.
- **Unity-specific:** crafting panels and placement interactions.
- **Dependencies:** inventory/items, structure/electricity, missions.

## 12) Item Durability Architecture
- **Responsibility:** generic wear model shared by weapons/tools/vehicles.
- **Core data:** `DurabilityState`.
- **Interfaces/contracts:** `apply_wear` contract.
- **Engine-independent:** full model.
- **Unity-specific:** durability HUD and FX.
- **Dependencies:** combat, crafting repair, economy.

## 13) Vehicle Architecture
- **Responsibility:** shared vehicle state for cars/boats/planes.
- **Core data:** `VehicleDefinition`, `VehicleStateModel`, `VehicleType`.
- **Interfaces/contracts:** vehicle persistence and replication topics.
- **Engine-independent:** vehicle schema.
- **Unity-specific:** physics controllers and input adapters.
- **Dependencies:** world chunking, authority/sync, fuel/economy.

## 14) NPC Architecture
- **Responsibility:** human settlement and zombie horde actor metadata.
- **Core data:** `NpcDefinition`, `NpcFaction`.
- **Interfaces/contracts:** behavior profile + mission/shop linking.
- **Engine-independent:** NPC metadata and references.
- **Unity-specific:** navmesh agents, dialogue presentation.
- **Dependencies:** missions, economy, world streaming, persistence.

## 15) Mission Architecture
- **Responsibility:** mission graph for human/zombie/custom server missions.
- **Core data:** `MissionDefinition`, `MissionAudience`.
- **Interfaces/contracts:** mission evaluator and progression persistence (future runtime).
- **Engine-independent:** mission contract shape.
- **Unity-specific:** mission UI, journal flows, objective markers.
- **Dependencies:** player state, NPC, economy, server config.

## 16) Economy Architecture
- **Responsibility:** currency and dynamic pricing policy boundaries.
- **Core data:** `EconomyConfig`.
- **Interfaces/contracts:** shop pricing and ledger service contracts (future runtime).
- **Engine-independent:** price policy contracts.
- **Unity-specific:** shop UX and transaction feedback.
- **Dependencies:** missions, loot, crafting, server config.

## 17) Weather/Regional Climate Architecture
- **Responsibility:** region-bound seasonal weather/hazard policy.
- **Core data:** `WeatherPreset`, `RegionalClimateProfile`.
- **Interfaces/contracts:** climate selection service (future runtime).
- **Engine-independent:** weather/climate schema.
- **Unity-specific:** visual weather effects, audio, terrain shader responses.
- **Dependencies:** world regions, server config, survival effects.

## 18) Save/Persistence Architecture
- **Responsibility:** explicit partitioning of durable state domains.
- **Core data:** `PersistenceLayout` categories:
  - player
  - world
  - inventory
  - structure
  - destruction
  - vehicle
  - npc
  - loot
  - server configuration
- **Interfaces/contracts:** `PersistentStateRepository`.
- **Engine-independent:** persistence boundaries and payload contracts.
- **Unity-specific:** save trigger integration and local cache behavior.
- **Dependencies:** all persistent systems.

## 19) Multiplayer Authority/Synchronization Architecture
- **Responsibility:** define who can write what and what replicates.
- **Core data:** `AuthorityRole`, `ReplicationRule`, `ClientCommandIntent`.
- **Interfaces/contracts:** replicated topic channels, authority checks, and client command-intent ingestion.
- **Engine-independent:** server-authoritative state policy with client-intent command flow.
- **Unity-specific:** transport serialization, interpolation, prediction UX.
- **Dependencies:** server architecture, chunk streaming, entity systems.

## 20) Unity Integration Architecture
- **Responsibility:** adapter boundary between contract layer and Unity runtime.
- **Core data:** payload dictionaries keyed by topic.
- **Interfaces/contracts:** `UnityIntegrationPort`.
- **Engine-independent:** interface definitions only.
- **Unity-specific:** all MonoBehaviour and scene/prefab execution.
- **Dependencies:** every implemented runtime system.

---

## Dependency Graph (Condensed)
- Server Architecture -> Authority/Synchronization, Persistence, World Chunking
- Server Configuration -> Missions, Economy, Loot, Weather, NPC, Rules
- Player State -> Transformation, Zombie Sanity, Missions, Persistence
- Animal System -> Missions, Crafting/Building Bonuses, Persistence
- World Chunking -> Building/Destruction, Vehicles, NPC Streaming, Persistence
- Building/Destruction -> Persistence, Authority, Crafting/Blueprints
- Loot/Crafting/Economy/Missions -> shared data contracts and server rules
- Unity Integration -> consumes replicated/persistent contract payloads only

## What This Phase Intentionally Does Not Implement
- Full world simulation runtime
- Full multiplayer networking stack
- Unity gameplay scenes and loops
- Full content pipelines for all required data sets
- Large-scale city map assets and streaming assets
- Phase 1.6 gameplay/runtime implementation

## Recommended Next Development Phase
**Phase 1.6 — Authoritative Multiplayer Slice**
1. Implement minimal authoritative server runtime using these contracts.
2. Implement chunk interest management + persistence for one representative city district.
3. Implement unified player transformation loop (human -> infected -> zombie -> cure).
4. Implement one human mission + one zombie mission end-to-end.
5. Implement Unity adapter prototype consuming replicated chunk/player snapshots.
