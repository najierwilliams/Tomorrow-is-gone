# Tomorrow Is Gone

A modular zombie survival/horror game foundation intended for future Unity development.

PlayStation 5 is the exclusive target platform for all future architecture and runtime implementation.

## Current Development Phase
**Phase 2 (next) — Core Gameplay Runtime Expansion**

This repository now contains:
- Implemented Phase 1 core prototypes
- Implemented Phase 1.5 architecture contracts for long-term multiplayer world systems
- Implemented Phase 1.6 authoritative multiplayer runtime slice
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

See:
- `docs/ARCHITECTURE.md`
- `docs/PHASE_1_5_MULTIPLAYER_WORLD_ARCHITECTURE.md`
- `docs/PHASE_1_6_AUTHORITATIVE_MULTIPLAYER_SLICE.md`
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
**Phase 2 — Core Gameplay Runtime Expansion**
- Expand gameplay loops on top of the implemented authoritative runtime slice.
- Extend mission/content depth and progression systems while preserving server authority.
- Continue toward production networking and platform integration in later phases.
