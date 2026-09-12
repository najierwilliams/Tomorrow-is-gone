# Phase 3 — AI & Encounter Expansion

## Summary
Phase 3 extends the existing authoritative runtime with an engine-independent AI core for navigation, perception, target evaluation, recruitment, horde behavior, and human NPC encounter responses.

The authoritative gameplay decision layer remains in `prototypes/core`, while Unity remains an adapter/presentation boundary.

## Engine-Independent AI Architecture
- Core module: `prototypes/core/phase3_ai.py`
- Runtime integration: `prototypes/core/phase16_authoritative_runtime.py`
- Unity projection updates: `unity/phase16_unity_adapter.py`

Key AI contracts:
- `NavigationProvider`
- `NavigationQuery`
- `NavigationPath`
- `NavigationPathStatus`
- `SoundEvent`
- `PerceptionMemory`
- `NpcAiState`
- `Phase3AiConfig`

## Navigation Abstraction
- Runtime now depends on `NavigationProvider` (replaceable)
- Deterministic provider: `DeterministicChunkNavigationProvider`
- Navigation represents:
  - reachable / partial / unreachable / unavailable
  - chunk traversal
  - tile availability and blocked path outcomes
- Chunk keys are first-class in path results

## Recast Integration Boundary
Recast/Detour integration is intentionally isolated behind `NavigationProvider`.

Current status:
- Recast is **not directly embedded** in the game-core model
- The current runtime uses deterministic provider behavior for testability
- A future Unity/Recast adapter can map:
  - runtime `NavigationQuery` -> Recast query
  - Recast output -> runtime `NavigationPath`

## Zombie Perception Architecture
Server-authoritative perception supports:
- Vision: range, FOV, obstruction check
- Hearing: abstract sound events with server-validated event types/strength
- Memory: last known position, seen/heard ticks, confidence, reason

Perception outputs drive AI state changes in authoritative tick processing.

## Zombie Target Selection
Deterministic score-based target selection uses data-driven weights for:
- visibility
- distance
- sound
- memory
- current target persistence bonus

Controls against thrashing:
- retarget threshold
- retarget cooldown
- target persistence lock window

## Player-Zombie Recruitment
Player-zombie proximity alone does not recruit NPC zombies.

Recruitment catalyst behavior now requires meaningful hostile encounter events (for example zombie attack on a human) plus server-authoritative checks:
- encounter event type
- distance/chunk relevance
- deterministic recruitment probability
- cooldown

## Dynamic Horde Behavior
Horde logic is relationship-based, not a single shared AI brain.

Each NPC zombie keeps independent:
- perception
- memory
- state
- target
- path status

Dynamic horde grouping/splitting is derived from per-zombie target decisions and represented through per-target horde IDs.

## Target Splitting, Switching, and Abandonment
Implemented behaviors:
- one primary target per NPC zombie
- per-zombie target switching when score thresholds are met
- pursuit abandonment on timeout or navigation failure
- post-abandonment fallback states (`search`/`wander`)

## Human NPC Encounter Foundation
Implemented human NPC foundation states:
- threat detection
- flee/combat response
- investigate (sound-driven)
- wander fallback

Human NPCs are valid zombie AI targets.

## Chunk-Aware AI
AI candidate evaluation is limited by configurable chunk radius.

This prevents full-world scans and aligns with streamed world requirements.

## Persistence
Persisted (required) AI state:
- `NpcAiState`
- sensory memory records
- horde NPC membership relation

Not persisted (transient):
- per-tick perception event stream
- temporary score calculations

## Server Authority
Clients submit intents only.

Clients cannot authoritatively set:
- perception outcomes
- zombie targets
- horde recruitment/membership outcomes
- target switching
- pursuit abandonment
- NPC AI state transitions

All such outcomes are decided on the server tick.

## Data-Driven Configuration
Phase 3 tuning now loads from:
- `data/phase3_ai_definitions.json`

Configurable parameters include:
- vision/hearing/memory
- targeting weights and thresholds
- pursuit timeout/persistence
- recruitment controls
- human NPC behavior settings
- chunk awareness radius
- allowed player sound event strengths

## Known Limitations
- Deterministic navigation provider is a functional abstraction baseline, not final production navmesh pathfinding
- Obstruction/visibility is an abstraction-level approximation
- Horde relation IDs are runtime-derived and optimized for deterministic behavior tests
- No direct Recast runtime adapter is included yet (boundary is prepared)

## Future Extension Points
- Unity/Recast adapter implementation behind `NavigationProvider`
- richer sensory propagation and occlusion modeling
- expanded NPC behavior trees/state tooling on top of deterministic core scoring rules
- advanced horde strategy layers while preserving per-entity authority
