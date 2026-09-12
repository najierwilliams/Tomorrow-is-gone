# Tomorrow Is Gone

A modular zombie survival/horror game foundation intended for future Unity development.

## Current Development Phase
**Phase 1 — Foundation**

This repository currently contains architecture, data schemas, and engine-independent prototypes for core survival systems.

## Repository Structure
- `/docs` — architecture and Unity integration documentation
- `/design` — design references
- `/systems` — future production systems
- `/data` — data-driven item and loot definitions
- `/assets` — game assets (placeholder/production)
- `/tools` — utility scripts and pipelines
- `/prototypes` — executable Phase 1 prototypes
- `/unity` — Unity-specific adapters (future)
- `/tests` — focused foundational tests

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

## Run Prototypes and Tests
From repository root:

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Planned Next Steps
- Expand system depth in Phase 2 while preserving modular boundaries.
- Add richer combat and survival interactions.
- Implement Unity adapters around established data contracts.

## Unity Integration Strategy
Core rules are kept engine-independent under `prototypes/core` and data is stored under `/data`. Unity-specific code will live under `/unity` as adapters/wrappers so gameplay logic can be reused or directly ported without tight engine coupling.
