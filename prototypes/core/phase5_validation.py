from __future__ import annotations

import json
from pathlib import Path

from .data_loader import load_item_definitions, load_loot_tables
from .phase4_world import load_phase4_world_definitions
from .phase5_contracts import load_phase5_definitions


def _require_dict(payload: object, name: str) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise ValueError(f"invalid_{name}")
    return payload


def validate_definition_files(data_root: Path) -> dict[str, bool]:
    items_path = data_root / "items.json"
    loot_path = data_root / "loot_tables.json"
    phase2_path = data_root / "phase2_definitions.json"
    phase3_path = data_root / "phase3_ai_definitions.json"
    phase4_path = data_root / "phase4_world_definitions.json"
    phase5_path = data_root / "phase5_definitions.json"

    load_item_definitions(items_path)
    load_loot_tables(loot_path)
    phase2_payload = _require_dict(json.loads(phase2_path.read_text()), "phase2_payload")
    phase3_payload = _require_dict(json.loads(phase3_path.read_text()), "phase3_payload")
    load_phase4_world_definitions(phase4_path)
    load_phase5_definitions(phase5_path)

    required_phase2_sections = {
        "items",
        "weapons",
        "recipes",
        "structures",
        "animals",
        "missions",
        "economy",
        "power_sources",
        "powered_devices",
    }
    missing_phase2 = required_phase2_sections.difference(phase2_payload.keys())
    if missing_phase2:
        raise ValueError(f"missing_phase2_sections:{','.join(sorted(missing_phase2))}")

    ai_payload = _require_dict(phase3_payload.get("ai"), "phase3_ai")
    if "perception" not in ai_payload or "zombie_targeting" not in ai_payload:
        raise ValueError("missing_phase3_ai_sections")

    return {
        "items": True,
        "loot_tables": True,
        "phase2": True,
        "phase3": True,
        "phase4": True,
        "phase5": True,
    }

