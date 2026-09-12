# Tomorrow Is Gone — Phase 1 Architecture

## Goal
Phase 1 establishes a modular, engine-independent game foundation that can be integrated into Unity later.

## Repository Structure
- `/docs` — architecture and integration documentation
- `/design` — high-level design notes and balancing references
- `/systems` — future long-term gameplay systems (engine-level implementations)
- `/data` — data-driven definitions (items, loot, balancing values)
- `/assets` — placeholder and production assets
- `/tools` — development utilities and content pipelines
- `/prototypes` — Phase 1 executable prototypes (engine-independent)
- `/unity` — Unity-specific adapters and integration scripts
- `/tests` — focused prototype validation tests

## Layering Model
- **Engine-independent**: `prototypes/core/*` and `data/*`
- **Unity-specific**: future adapters under `unity/`
- **Prototype-only**: current runtime wiring and simplified tuning values in `prototypes/`

## Core System Design (Phase 1)
### Player System
- `PlayerStats` stores health, stamina, hunger, thirst, XP, and level.
- Keeps survival/stat logic centralized and deterministic.

### Zombie System
- `ZombieEntity` uses explicit states and transitions.
- Base state model supports extension for future zombie types without rewriting shared logic.

### Inventory System
- Slot + stack based inventory with add/remove operations.
- Item handling remains data-driven through item definition IDs.

### Item System
- `ItemDefinition` and `ItemCategory` define item metadata and classification.
- Loaded from JSON to avoid hard-coded item behavior.

### Weapon System
- `WeaponDefinition` + `WeaponInstance` split static data from runtime durability.
- Supports future weapon variants and balancing via data.

### Health / Damage System
- `PlayerStats.apply_damage()` and `heal()` define current baseline damage loop.
- Designed for expansion into armor, status effects, limb damage, and resistances.

### Survival System
- Hunger/thirst tracked independently from health.
- Prototype keeps effects simple and isolated for easier balancing later.

### Loot System
- `LootTable` rolls deterministic drops when supplied with seeded RNG.
- Enables location-specific tables and rarity tiers in later phases.

### NPC System
- Not implemented yet in code.
- Planned architecture mirrors zombie state-machine approach with role-specific AI modules.

### Quest System
- Not implemented yet in code.
- Planned as data-defined objectives + progression triggers, decoupled from UI/engine.

### World System
- Not implemented yet in code.
- Planned as data-driven zones, encounter tables, safe/danger metadata, and world events.

### Save / Load System
- `GameSnapshot` serializes player + inventory structures to JSON.
- Baseline contract for later Unity persistence and migration logic.

### Progression System
- XP thresholds and leveling implemented in `PlayerStats.add_experience()`.
- Minimal formula now, can migrate to configurable progression tables later.

### Future Multiplayer Considerations
- Keep game rules deterministic and state payloads serializable.
- Separate authority-sensitive logic (combat, inventory changes) from presentation.
- Avoid direct engine calls inside core rule modules.

## Zombie State Architecture
Implemented states:
- Idle
- Wander
- Investigate
- Detect Player
- Chase
- Attack
- Search
- Lose Target
- Return to Wandering

Extension strategy:
- Keep shared base transitions in core zombie entity.
- Add per-zombie-type behavior profiles (speed, perception, aggression, armor).
- Add new state handlers instead of branching the entire AI system.

## Unity Integration Strategy
1. Keep `prototypes/core` as authoritative gameplay rule reference.
2. Build Unity-side adapters in `/unity`:
   - ScriptableObject loaders for `/data`
   - MonoBehaviour wrappers for player/zombie/inventory runtime events
   - Save adapters around `GameSnapshot`-compatible schema
3. Replace prototype event loops with Unity update/tick orchestration while preserving rules.
4. Add visual/audio/animation layers without moving core business logic into presentation code.
