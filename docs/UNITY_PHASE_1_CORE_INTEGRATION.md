# Unity Phase 1 — Core Unity Integration

## Unity Version

- Selected Unity editor version: `2022.3.62f1` (LTS track).
- Declared in `unity/ProjectSettings/ProjectVersion.txt`.

## Project Structure

Unity project root remains under `unity/` and now contains reproducible source folders:

- `unity/Assets/Scenes`
- `unity/Assets/Scripts/CoreIntegration`
- `unity/Assets/Scripts/Gameplay`
- `unity/Assets/Scripts/Player`
- `unity/Assets/Scripts/AI`
- `unity/Assets/Scripts/UI`
- `unity/Assets/Scripts/World`
- `unity/Assets/World`
- `unity/Packages/manifest.json`
- `unity/ProjectSettings/ProjectVersion.txt`

## Core ↔ Unity Boundary

- Existing authoritative Python contracts and runtime remain unchanged.
- Unity integration is isolated behind `IAuthoritativeRuntimeClient` and intent/snapshot contracts in `Assets/Scripts/CoreIntegration/AuthoritativeContracts.cs`.
- Unity emits **client intent only** (`ClientCommandIntent`) and consumes authoritative snapshots (`AuthoritativeSnapshot`).
- No Unity-side duplicate implementation was added for authoritative gameplay systems (combat authority, inventory authority, zombie brain authority, mission/economy authority, persistence authority).
- `MockAuthoritativeRuntimeClient` is an explicit local integration stub for editor-phase projection tests and does not replace server authority.

## Scenes Created

- `unity/Assets/Scenes/BootstrapCoreIntegration.unity`
- `unity/Assets/Scenes/PlayableTestScene.unity`

Runtime behavior:

- Bootstrap scene loads the playable scene.
- Playable scene auto-installs `PlayableSceneController` and projects runtime snapshots into world/player/zombie/UI placeholders.

## Adapters and Projected Systems

Projected into Unity presentation layer (minimal Phase 1 scope):

- Player spawn/presentation and input-to-intent flow
- Player state projection (health/stamina/hunger/thirst/role/form)
- Basic first-person-style test camera follow
- Zombie visual projection with state-to-color mapping (idle/wander/investigate/chase/dead)
- Authoritative event projection to HUD summary (combat hit/death and other events)
- Basic combat request flow (`player.interact` intent -> authoritative response projection)
- Basic inventory/equipped/durability projection to HUD
- Chunk/world projection with active chunk placeholder geometry
- Input abstraction layer with keyboard/mouse + gamepad adapters via `IIntentInputSource`

## Deferred / Intentionally Out of Scope

- Production networking stack and replication transport
- Production movement model and physics reconciliation
- Final combat, AI animation trees, and effects
- Production inventory/crafting UI
- Final world streaming/terrain generation/navmesh pipeline
- Matchmaking/public servers
- Voice chat and microphone/noise detection
- PS5 SDK packaging and platform-specific runtime validation

## External Dependencies

- Added no third-party gameplay frameworks.
- Unity package manifest uses built-in Unity modules only.

## Testing Performed

- Core test suite command:
  - `python -m unittest discover -s tests -p "test_*.py"`
- Unity runtime/editor checks in this environment:
  - Static project structure validation only (Unity editor/CLI not available in this environment).

## Known Limitations

- Unity editor is not available in the current execution environment, so opening the project, scene-play validation, and C# compile confirmation could not be executed here.
- `MockAuthoritativeRuntimeClient` is a temporary local integration aid pending direct transport wiring to the authoritative runtime boundary.

## Next Recommended Unity Phase 1 Tasks

1. Replace `MockAuthoritativeRuntimeClient` with real transport binding to authoritative runtime snapshots/intents.
2. Validate scene compilation and play mode in Unity Editor (`2022.3 LTS`).
3. Add deterministic integration checks around snapshot translation and intent serialization.
4. Expand zombie state visualization to full Phase 3 state taxonomy from authoritative payloads.
5. Add minimal prefab-based scene organization while preserving authoritative core boundaries.
