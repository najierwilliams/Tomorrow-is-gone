# Tomorrow Is Gone

A modular zombie survival/horror game foundation intended for future Unity development.

## Current Development Phase
**Phase 1.5 — Multiplayer World Architecture**

This repository now contains:
- Implemented Phase 1 core prototypes
- Phase 1.5 architecture contracts for long-term multiplayer world systems
- Documentation for engine-independent boundaries and future Unity integration

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

## Implemented Systems (Phase 1)
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

## Designed Systems (Phase 1.5, architecture-level)
- Server architecture/configuration contracts
- Unified player state for human/infected/zombie
- Transformation and zombie sanity contracts
- Animal infection/taming/ability contracts
- Region/chunk/streaming world contracts
- Building/destruction persistence contracts
- Loot tier/container contracts
- Crafting/workbench contracts
- Item durability general contracts
- Vehicle, NPC, mission, economy, weather contracts
- Save/persistence domain partitioning contracts
- Multiplayer authority/replication contracts
- Unity integration port contracts

See:
- `docs/ARCHITECTURE.md`
- `docs/PHASE_1_5_MULTIPLAYER_WORLD_ARCHITECTURE.md`
- `prototypes/core/phase15_contracts.py`

## Run Prototypes and Tests
From repository root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## What Is Not Implemented Yet
- Full gameplay implementation for Phase 1.5 systems
- Full server runtime, transport, and persistence backend
- Unity gameplay implementation and world streaming runtime
- Full content authoring for all long-term game datasets

## Recommended Next Step
**Phase 1.6 — Authoritative Multiplayer Slice**
- Build a minimal server-authoritative runtime using Phase 1.5 contracts.
- Validate chunk streaming + persistence on a limited world slice.
- Connect initial replicated state flows into Unity adapter prototypes.
