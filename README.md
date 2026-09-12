# Tomorrow Is Gone

A modular zombie survival/horror game foundation intended for future Unity development.

PlayStation 5 is the exclusive target platform for all future architecture and runtime implementation.

## Current Development Phase
**Phase 3 (implemented) — AI & Encounter Expansion**

This repository now contains:
- Implemented Phase 1 core prototypes
- Implemented Phase 1.5 architecture contracts for long-term multiplayer world systems
- Implemented Phase 1.6 authoritative multiplayer runtime slice
- Implemented Phase 2 core gameplay runtime expansion systems
- Implemented Phase 3 server-authoritative AI/navigation/perception/encounter expansion systems
- Documentation for engine-independent boundaries and future Unity integration
- PS5-focused architecture constraints for large persistent multiplayer worlds

## Repository Structure
- `/docs` — architecture and Unity integration documentation
- `/design` — design references
- `/systems` — future production systems
- `/data` — data-driven definitions and future schema sources
- `/assets` — game assets (placeholder/production)
- `/tools` — utility scripts and pipelines
- `/prototypes` — executable Phase 1 prototypes + Phase 1.5 architecture contracts
- `/unity` — Unity-specific adapters (future runtime integration)
- `/tests` — focused foundational and contract tests

## Implemented Prototype Systems (Phases 1, 1.5, and 1.6)
- Player stats (health/stamina/hunger/thirst)
- Health and damage handling
- Stamina spending/recovery
- Inventory operations (stacking and slot capacity)
- Data-driven item definitions
- Weapon durability/damage behavior
- Zombie entities with modular state transitions
- Loot table rolling
- Experience/level progression
- Save/load data structures (JSON snapshot)
- Phase 1.5 engine-independent multiplayer architecture contracts
- Authoritative server runtime loop with server-owned player/world state
- Client intent -> server validation -> authoritative mutation command flow
- HUMAN -> INFECTED_HUMAN -> ZOMBIE transitions with cure-gated reversal
- HumanRuntimeState and ZombieRuntimeState runtime models
- Chunk/world interest management for replicated snapshots
- Server-authoritative tiered container loot generation
- File-backed partitioned persistence for player/inventory/world/loot/server config
- Human and zombie mission acceptance/progression runtime paths
- Local multiplayer simulation via in-process transport
- Authoritative zombie-to-human combat replication
- Unity boundary adapter (`Phase16UnityAdapter`) for snapshot projection
- Human survival runtime depletion/recovery/death loops
- Zombie feeding/sanity/sleep-healing/tier progression runtime
- Server-authoritative item use, equipment, crafting, gathering, gardening, construction, destruction, and economy mutation flows
- Data-driven definitions for food, medicine, weapons, armor, recipes, workbenches, resource nodes, crops, structures, animal abilities, zombie tiers, missions, and progression
- Persistent world domains for structures, destruction, animals, gardens, power state, hordes, missions, progression, and economy
- Multiplayer-authoritative infection interactions for humans and animals
- Expanded chunk-aware replicated snapshots for inventory/equipment, animals, structures, world resources, missions, economy, and power
- Engine-independent AI core contracts and deterministic chunk navigation abstraction (`prototypes/core/phase3_ai.py`)
- Server-authoritative zombie perception (vision/hearing/memory), target scoring/switching, pursuit abandonment, recruitment, and dynamic horde splitting
- Human NPC encounter behavior foundation (threat detection, flee/combat response, investigation/wander)
- Chunk-aware AI evaluation and persisted NPC AI memory/state with Unity adapter projection support

See:
- `docs/ARCHITECTURE.md`
- `docs/PHASE_1_5_MULTIPLAYER_WORLD_ARCHITECTURE.md`
- `docs/PHASE_1_6_AUTHORITATIVE_MULTIPLAYER_SLICE.md`
- `docs/PHASE_2_CORE_GAMEPLAY_RUNTIME_EXPANSION.md`
- `docs/PHASE_3_AI_AND_ENCOUNTER_EXPANSION.md`
- `prototypes/core/phase15_contracts.py`
- `prototypes/core/phase16_authoritative_runtime.py`

## Run Prototypes and Tests
From repository root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## What Is Not Implemented Yet
- Production networking stack and live service infrastructure
- PS5 platform integration/runtime packaging
- Full open-world city content and complete gameplay feature set
- Production-grade server browser, matchmaking, and deployment tooling
- Full Unity gameplay implementation and large-scale world streaming content
- Future late-phase PC expansion and mod/community platform support

## Recommended Next Step
**Phase 4 — Combat and Equipment Runtime**
- Expand combat depth and balancing over the now-established authoritative encounter AI layer.
- Continue platform/transport productionization while preserving core engine independence.
