# Repository Development Guide

This repository is prepared for Unity development while preserving the engine-independent Phase 1–5 core.

## Repository Structure

- `/prototypes` — engine-independent gameplay/runtime contracts and implementations
- `/data` — source-controlled gameplay/world definition data
- `/tests` — automated validation for core contracts and runtime behavior
- `/docs` — architecture and development documentation
- `/unity` — Unity integration boundary and future Unity project root
  - `/unity/Assets`
  - `/unity/Packages`
  - `/unity/ProjectSettings`
- `/server` — future server-side runtime/infrastructure code
- `/tools` — pipelines and utility tooling
- `/assets` and `/design` — source references and production asset/design inputs

## What Belongs in Git

Store in Git:
- Source code (Python/C#/tooling)
- Game/server configuration and definitions (items, loot, crafting, missions, AI, world rules)
- Tests
- Documentation
- Import/generation tooling and metadata

Do not store in Git:
- Unity cache/generated directories
- Build outputs (PS5/PC/server binaries and packaging outputs)
- Generated world datasets by default
- Live server/player persistence data
- Secrets/credentials

## Git LFS Policy

Use Git LFS for large binary source assets (configured in `.gitattributes`), including:
- `*.psd`, `*.psb`
- `*.fbx`, `*.blend`
- `*.wav`
- `*.mp4`, `*.mov`
- `*.tga`, `*.tif`, `*.tiff`, `*.exr`, `*.hdr`

Do not use LFS for normal source files (`.py`, `.cs`, `.json`, `.yml`, `.md`, etc.) or generated/live datasets.

## Generated Data and Live Data Policy

1. **Source-controlled definitions (Git):**
   - Rules, schemas, configuration, contracts, source code, tests, docs
2. **Generated/static world data (external storage by default):**
   - Generated terrain, imported city datasets, processed geometry, derived navigation data
3. **Persistent/live server data (never in Git):**
   - Player saves, inventories, world deltas, destruction state, vehicles, loot/NPC state, server databases

GitHub is source control, not the live game database and not the long-term storage layer for unlimited generated world data.

## Unity Conventions

- Keep gameplay authority in engine-independent server/core logic.
- Use Unity for presentation/integration boundaries without rewriting core contracts.
- Commit Unity reproducible project sources (`Assets`, `Packages`, `ProjectSettings`) and exclude generated cache/build folders.

## Branch Workflow

Recommended:
- `main` — stable, integrated releases
- `development` — active integration branch
- `feature/*` — isolated feature work

Unity examples:
- `feature/unity-phase-1`
- `feature/player-integration`
- `feature/world-integration`
- `feature/zombie-ai-integration`

## Secrets and Safe Configuration

- Never commit API keys, passwords, cert private keys, platform credentials, or production secrets.
- Use local `.env`/secret files (ignored by `.gitignore`) and commit only safe examples (for example `.env.example`).

## Large-World and Real-World City Scale Note

Tomorrow Is Gone is intended to support extremely large persistent worlds and eventually potentially 1:1 real-world city pipelines. Keep world rules/tools/metadata in Git, but store large processed world datasets and persistent world state outside Git. Open City Model integration is deferred to a separate implementation and licensing/compatibility review.
