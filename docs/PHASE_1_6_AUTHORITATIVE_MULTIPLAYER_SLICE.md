# Phase 1.6 — Authoritative Multiplayer Slice

## Purpose of Phase 1.6
Phase 1.6 proves a runnable, server-authoritative multiplayer slice on top of the Phase 1.5 contracts. The goal is validation of architecture and data flow, not delivery of the full production game.

Platform direction remains **PS5-first**, with PC as a later expansion phase.

## Architecture Being Proven
- Contract-driven multiplayer runtime progression from Phase 1.5 into executable server logic.
- Server-authoritative write ownership for player/world state.
- Client command-intent ingestion with server-side validation/mutation.
- Replicated snapshot output suitable for Unity adapter consumption.
- Partitioned persistence domains for recoverable state.

## Authoritative Server Runtime
`AuthoritativeServerRuntime` (`prototypes/core/phase16_authoritative_runtime.py`) owns:
- Player lifecycle and authoritative state mutation.
- World/chunk runtime state and active chunk refresh.
- Mission state and command result tracking.
- Snapshot replication per player audience.
- Save/load persistence boundaries for core runtime domains.

## Client Command Intent Flow
The runtime implements a strict flow:
1. Client submits `ClientCommandIntent`.
2. Server routes by topic and validates payload/rules.
3. Server applies authoritative mutation only when accepted.
4. Server records command results and replicates snapshots.

This covers movement, interaction, infection/form changes, zombie feed, inventory actions, and mission commands.

## Player Forms and Cure Gating
Implemented form transitions follow `PlayerForm` contracts:
- `HUMAN -> INFECTED_HUMAN`
- `INFECTED_HUMAN -> ZOMBIE`
- `INFECTED_HUMAN -> HUMAN` only when cure-gated
- `ZOMBIE -> HUMAN` only when cure-gated

Rejected transitions remain authoritative server rejections.

## Human Runtime State
`HumanRuntimeState` currently tracks:
- Core human `PlayerStats`
- Authoritative world `position`
- Movement state marker

Human state is server-owned and replicated through snapshots.

## Zombie Runtime State
`ZombieRuntimeState` currently tracks:
- Feeding state
- Zombie sanity state
- Zombie tier id
- Mission eligibility
- Zombie health value

Zombie feed updates sanity/health authoritatively and can progress zombie mission state.

## Chunk Interest Management
Runtime chunk interest logic:
- Computes required chunks per player based on configured radius.
- Activates required chunks and deactivates unneeded chunks.
- Replicates active chunk keys and visible player/container data scoped to interest.

This validates the server-authoritative world visibility boundary.

## Tiered Authoritative Loot
Tiered container loot is generated server-side through `TieredLootGenerator`:
- Container tier weights resolve to an eligible loot tier.
- Tier selects only eligible loot pools.
- Generated loot is applied to inventory authoritatively.
- Looted container state is enforced and replicated.

Clients do not author loot outcomes.

## Persistence Domains
File-backed partitioned persistence is validated with:
- `players`
- `inventories`
- `world`
- `loot`
- `server_config`

This is a prototype persistence slice, aligned with larger domain-partition goals from Phase 1.5.

## Human and Zombie Missions
Runtime includes mission definitions and authoritative progression for:
- One human mission (`mission_human_retrieve_item`)
- One zombie mission (`mission_zombie_feed_target`)

Audience constraints and objective completion are server-validated.

## Local Multiplayer Simulation
`InProcessTransport` enables local multi-player command submission and snapshot replication to validate end-to-end authority behavior in tests without production networking infrastructure.

## Authoritative Combat Replication
Zombie-to-human attack interaction is server-resolved and then replicated through authoritative player snapshot payloads, validating server ownership of combat outcome state.

## Unity Adapter Boundary
`Phase16UnityAdapter` remains a boundary adapter:
- Receives server snapshots by topic/payload.
- Projects player/world view data for Unity-side representation.
- Queues and forwards command intents.

Gameplay authority remains in server/core runtime, not Unity presentation.

## Tests and Validation
Phase 1.6 behavior is covered by `tests/test_phase16_authoritative_slice.py`, including:
- Authoritative player creation
- Accepted/rejected command flow
- Form transitions with cure gating
- Chunk interest activation/deactivation
- Tiered loot eligibility
- Persistence restore behavior
- Human/zombie mission progression
- Authoritative combat replication and Unity adapter projection

Repository suite currently validates 24 passing tests.

## What This Phase Intentionally Does NOT Implement
- Production networking stack, transport hardening, or server browser.
- Full live persistence backend and deployment infrastructure.
- Full PS5 platform integration/runtime packaging.
- Complete open-world city content and all gameplay systems.
- Finalized AI/content/economy/weather/vehicle/construction production loops.
- Full game release scope.

## Known Prototype Limitations
- Local in-process transport instead of production network transport.
- File-backed JSON persistence rather than scalable backend storage.
- Narrow mission/content breadth (representative slice only).
- Simplified runtime behaviors for validation-focused coverage.
- Unity integration remains adapter-level, not full gameplay runtime.

## How This Prepares the Project for Phase 2
Phase 1.6 establishes a validated authority spine for Phase 2:
- A working server-authoritative command/mutation/replication loop exists.
- Runtime state ownership boundaries are enforced in code and tests.
- Prototype persistence and chunk interest patterns are proven.
- Human/zombie mission and combat replication paths are in place for expansion.

Recommended next phase: **Phase 2 — Core Gameplay Runtime Expansion**.
