from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .phase15_contracts import VehicleType


@dataclass(frozen=True)
class ServerRuleCategories:
    pvp_enabled: bool
    pve_enabled: bool
    zombie_difficulty_multiplier: float
    hunger_thirst_multiplier: float
    loot_multiplier: float
    resource_rate_multiplier: float
    infection_multiplier: float
    death_penalty_multiplier: float
    mission_multiplier: float
    build_permissions: str
    creative_mode_private_only: bool
    custom_missions_allowed: bool


@dataclass(frozen=True)
class UtilityDefinition:
    utility_id: str
    category: str
    power_required: float
    power_capacity: float
    connection_type: str


@dataclass(frozen=True)
class VehicleDefinition:
    definition_id: str
    vehicle_type: VehicleType
    seat_count: int
    max_durability: float
    fuel_capacity: float
    persistence_class: str


@dataclass(frozen=True)
class WorldTimeDefinition:
    ticks_per_day: int
    dawn_tick: int
    dusk_tick: int


@dataclass(frozen=True)
class EnvironmentHooksDefinition:
    affects_zombie_behavior: bool
    affects_npc_behavior: bool
    affects_farming: bool
    affects_weather: bool
    affects_lighting: bool


@dataclass(frozen=True)
class CustomContentDefinition:
    mission_ids: list[str] = field(default_factory=list)
    objective_types: list[str] = field(default_factory=list)
    reward_types: list[str] = field(default_factory=list)
    rule_ids: list[str] = field(default_factory=list)
    spawn_types: list[str] = field(default_factory=list)
    location_types: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Phase5Definitions:
    server_rules: ServerRuleCategories
    utilities: dict[str, UtilityDefinition]
    vehicles: dict[str, VehicleDefinition]
    world_time: WorldTimeDefinition
    environment_hooks: EnvironmentHooksDefinition
    custom_content: CustomContentDefinition


class RealWorldCityDataProvider(Protocol):
    def get_city_metadata(self, city_id: str) -> dict[str, object]:
        ...


class RealWorldBuildingProvider(Protocol):
    def get_buildings(self, city_id: str, chunk_key: str) -> list[dict[str, object]]:
        ...


class RealWorldRoadProvider(Protocol):
    def get_roads(self, city_id: str, chunk_key: str) -> list[dict[str, object]]:
        ...


class RealWorldPOIProvider(Protocol):
    def get_pois(self, city_id: str, chunk_key: str) -> list[dict[str, object]]:
        ...


@dataclass
class RealWorldProviderRegistry:
    city_provider: RealWorldCityDataProvider | None = None
    building_provider: RealWorldBuildingProvider | None = None
    road_provider: RealWorldRoadProvider | None = None
    poi_provider: RealWorldPOIProvider | None = None

    def is_replaceable(self) -> bool:
        return True


def _require_section(payload: dict[str, object], key: str) -> dict[str, object]:
    section = payload.get(key)
    if not isinstance(section, dict):
        raise ValueError(f"invalid_or_missing_section:{key}")
    return section


def load_phase5_definitions(path: Path) -> Phase5Definitions:
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("invalid_phase5_payload")

    rule_payload = _require_section(payload, "server_rules")
    server_rules = ServerRuleCategories(
        pvp_enabled=bool(rule_payload["pvp_enabled"]),
        pve_enabled=bool(rule_payload["pve_enabled"]),
        zombie_difficulty_multiplier=float(rule_payload["zombie_difficulty_multiplier"]),
        hunger_thirst_multiplier=float(rule_payload["hunger_thirst_multiplier"]),
        loot_multiplier=float(rule_payload["loot_multiplier"]),
        resource_rate_multiplier=float(rule_payload["resource_rate_multiplier"]),
        infection_multiplier=float(rule_payload["infection_multiplier"]),
        death_penalty_multiplier=float(rule_payload["death_penalty_multiplier"]),
        mission_multiplier=float(rule_payload["mission_multiplier"]),
        build_permissions=str(rule_payload["build_permissions"]),
        creative_mode_private_only=bool(rule_payload["creative_mode_private_only"]),
        custom_missions_allowed=bool(rule_payload["custom_missions_allowed"]),
    )

    utility_payload = payload.get("utilities", [])
    if not isinstance(utility_payload, list):
        raise ValueError("invalid_utilities")
    utilities: dict[str, UtilityDefinition] = {}
    for raw in utility_payload:
        if not isinstance(raw, dict):
            raise ValueError("invalid_utility_entry")
        utility = UtilityDefinition(
            utility_id=str(raw["utility_id"]),
            category=str(raw["category"]),
            power_required=float(raw.get("power_required", 0.0)),
            power_capacity=float(raw.get("power_capacity", 0.0)),
            connection_type=str(raw.get("connection_type", "direct")),
        )
        utilities[utility.utility_id] = utility

    vehicle_payload = payload.get("vehicles", [])
    if not isinstance(vehicle_payload, list):
        raise ValueError("invalid_vehicles")
    vehicles: dict[str, VehicleDefinition] = {}
    for raw in vehicle_payload:
        if not isinstance(raw, dict):
            raise ValueError("invalid_vehicle_entry")
        definition = VehicleDefinition(
            definition_id=str(raw["definition_id"]),
            vehicle_type=VehicleType(str(raw["vehicle_type"])),
            seat_count=int(raw["seat_count"]),
            max_durability=float(raw["max_durability"]),
            fuel_capacity=float(raw.get("fuel_capacity", 0.0)),
            persistence_class=str(raw.get("persistence_class", "persistent")),
        )
        vehicles[definition.definition_id] = definition

    time_payload = _require_section(payload, "world_time")
    world_time = WorldTimeDefinition(
        ticks_per_day=int(time_payload["ticks_per_day"]),
        dawn_tick=int(time_payload["dawn_tick"]),
        dusk_tick=int(time_payload["dusk_tick"]),
    )

    environment_payload = _require_section(payload, "environment_hooks")
    environment_hooks = EnvironmentHooksDefinition(
        affects_zombie_behavior=bool(environment_payload["affects_zombie_behavior"]),
        affects_npc_behavior=bool(environment_payload["affects_npc_behavior"]),
        affects_farming=bool(environment_payload["affects_farming"]),
        affects_weather=bool(environment_payload["affects_weather"]),
        affects_lighting=bool(environment_payload["affects_lighting"]),
    )

    custom_payload = _require_section(payload, "custom_content")
    custom_content = CustomContentDefinition(
        mission_ids=[str(value) for value in custom_payload.get("mission_ids", [])],
        objective_types=[str(value) for value in custom_payload.get("objective_types", [])],
        reward_types=[str(value) for value in custom_payload.get("reward_types", [])],
        rule_ids=[str(value) for value in custom_payload.get("rule_ids", [])],
        spawn_types=[str(value) for value in custom_payload.get("spawn_types", [])],
        location_types=[str(value) for value in custom_payload.get("location_types", [])],
    )

    return Phase5Definitions(
        server_rules=server_rules,
        utilities=utilities,
        vehicles=vehicles,
        world_time=world_time,
        environment_hooks=environment_hooks,
        custom_content=custom_content,
    )

