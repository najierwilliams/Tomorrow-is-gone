# Phase 5 — Final Core Systems & Unity Integration Preparation

Phase 5 completes the remaining engine-independent gameplay and integration contracts required before Unity implementation work.

## Final Core Architecture

```
GAME CORE
  -> AUTHORITATIVE SERVER
  -> PERSISTENCE / REPLICATION
  -> UNITY ADAPTER
  -> UNITY PRESENTATION
```

Unity is a consumer of authoritative state and a producer of validated client intents. Unity never owns gameplay authority.

## Player Lifecycle and State

- Server-authoritative human/infected/zombie lifecycle remains enforced through transition validation and cure gating.
- Runtime player snapshots now include role, health/stamina/hunger/thirst, infection progress, zombie state, inventory, equipment durability, progression, economy, mission state, position, and chunk key.
- Authoritative respawn contracts are available for human and zombie forms.

## Animal Systems

- Wild/tamed/infected animals remain server-authoritative.
- Ability usage remains data-driven and ownership validated.
- Animal infection and taming emit authoritative events.

## Crafting, Construction, Utilities, Vehicles

- Crafting remains transactional with recipe/workbench/tag/power checks and output-capacity prevalidation.
- Structure placement and damage remain server-authoritative with ownership validation, persistence deltas, and event emission.
- Utility definitions are data-driven in `data/phase5_definitions.json`.
- Vehicle foundation now includes authoritative enter/exit/move intents, ownership/passenger state, persistence, replication payloads, and Unity projection support.

## Missions, Economy, NPCs

- Missions continue to progress only from server-side gameplay events.
- Client mission self-complete intents are explicitly rejected.
- Economy remains transaction-id based for spends; direct client minting remains rejected.
- NPC state, AI state, and sensory memory persistence remain active and replicated.

## Multiplayer Authority, Permissions, and Security

- Runtime intent handlers explicitly separate permitted client intents from server-only state mutation paths.
- Rejections are explicit for forged mission completion, world time mutation, environment mutation, and event injection.
- Vehicle control is owner-authorized; forged ownership in payloads is ignored.
- Creative/private/public rule categories are represented by Phase 5 server rule definitions.

## Replication and Unity Adapter Contract

Replication now includes:

- player state and visible players
- chunk/world metadata and environment state
- structures/resources/animals/NPCs/vehicles/power/mission/economy views
- world time/day-night state
- authoritative event stream
- explicit Unity-allowed intent topic list
- real-world provider contract metadata

Unity adapter projections include vehicles, world time, event stream, and allowed intents in addition to prior Phase 1–4 projections.

## Persistence Finalization

Persistence covers:

- players, inventories, equipment, progression, economy, missions
- world chunks/resources/gardens/structures/destruction
- animals/hordes/NPCs/workbenches/power
- vehicles
- world time state

Round-trip persistence tests cover vehicles alongside existing structure/NPC/animal persistence coverage.

## World Time and Environment Hooks

- Deterministic world-time runtime state tracks tick/day/day-night and elapsed time.
- Day-night transitions emit authoritative environment-change events.
- Hook definitions for zombie/NPC/farming/weather/lighting integration are data-driven in Phase 5 definitions.

## Real-World City Provider Abstraction

`prototypes/core/phase5_contracts.py` defines replaceable provider protocols:

- `RealWorldCityDataProvider`
- `RealWorldBuildingProvider`
- `RealWorldRoadProvider`
- `RealWorldPOIProvider`

No external geographic dataset or Open City Model dependency is added in Phase 5.

## Event System

Authoritative event stream includes server-generated events such as:

- `structure_created`, `structure_damaged`, `structure_destroyed`
- `item_crafted`
- `animal_tamed`, `animal_infected`
- `mission_updated`
- `vehicle_entered`, `vehicle_exited`, `vehicle_moved`
- `player_respawned`
- `environment_changed`

Clients cannot inject authoritative events.

## Data Validation

`prototypes/core/phase5_validation.py` validates:

- `items.json`
- `loot_tables.json`
- `phase2_definitions.json`
- `phase3_ai_definitions.json`
- `phase4_world_definitions.json`
- `phase5_definitions.json`

Invalid definitions fail with explicit validation errors.

## Known Limitations (Intentionally Out of Scope)

- Final Unity graphics, terrain, lighting, animation, and production physics
- Final vehicle flight/driving simulation
- Full weather simulation and rendering
- External real-world city dataset integration and licensing decisions
- Full faction/civilization simulation
- Marketplace/mod download/purchase systems

## Unity Integration Entry Points

- Runtime authoritative snapshots (`transport.push_snapshot`) for Unity consumption
- Unity adapter projection (`unity/phase16_unity_adapter.py`)
- Client intent queue (`queue_input_command` -> runtime `ClientCommandIntent`)
- Explicit allowlist of gameplay intent topics in replicated payloads
