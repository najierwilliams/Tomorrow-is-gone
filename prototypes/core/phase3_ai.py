from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from math import atan2, cos, degrees, radians, sin
from typing import Protocol

from .phase15_contracts import WorldCoordinate, WorldGridConfig


class NavigationPathStatus(str, Enum):
    REACHABLE = "reachable"
    PARTIAL = "partial"
    UNREACHABLE = "unreachable"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class NavigationQuery:
    agent_id: str
    start: WorldCoordinate
    destination: WorldCoordinate
    required_chunk_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class NavigationPath:
    status: NavigationPathStatus
    waypoints: tuple[WorldCoordinate, ...] = ()
    traversed_chunk_keys: tuple[str, ...] = ()
    reason: str = ""


class NavigationProvider(Protocol):
    def query_path(self, query: NavigationQuery) -> NavigationPath:
        ...

    def are_tiles_available(self, chunk_keys: tuple[str, ...]) -> bool:
        ...


@dataclass
class DeterministicChunkNavigationProvider:
    grid_config: WorldGridConfig
    unavailable_chunk_keys: set[str] = field(default_factory=set)
    blocked_chunk_keys: set[str] = field(default_factory=set)

    @staticmethod
    def _chunk_key(grid_config: WorldGridConfig, coordinate: WorldCoordinate) -> str:
        chunk = grid_config.to_chunk_address(coordinate)
        return f"{chunk.chunk_x}:{chunk.chunk_y}:{chunk.chunk_z}"

    def _traversed_chunks(self, start: WorldCoordinate, destination: WorldCoordinate) -> tuple[str, ...]:
        keys: list[str] = []
        steps = max(1, int(distance(start, destination) // max(self.grid_config.chunk_size_meters / 2, 1)))
        for index in range(steps + 1):
            alpha = index / steps
            point = WorldCoordinate(
                x=start.x + (destination.x - start.x) * alpha,
                y=start.y + (destination.y - start.y) * alpha,
                z=start.z + (destination.z - start.z) * alpha,
            )
            key = self._chunk_key(self.grid_config, point)
            if key not in keys:
                keys.append(key)
        return tuple(keys)

    def are_tiles_available(self, chunk_keys: tuple[str, ...]) -> bool:
        return all(chunk_key not in self.unavailable_chunk_keys for chunk_key in chunk_keys)

    def query_path(self, query: NavigationQuery) -> NavigationPath:
        traversed = self._traversed_chunks(query.start, query.destination)
        required = tuple(dict.fromkeys((*query.required_chunk_keys, *traversed)))
        if not self.are_tiles_available(required):
            return NavigationPath(
                status=NavigationPathStatus.UNAVAILABLE,
                waypoints=(query.start,),
                traversed_chunk_keys=required,
                reason="navigation_tile_unavailable",
            )

        blocked = [chunk for chunk in required if chunk in self.blocked_chunk_keys]
        if blocked:
            return NavigationPath(
                status=NavigationPathStatus.UNREACHABLE,
                waypoints=(query.start,),
                traversed_chunk_keys=required,
                reason="blocked_path",
            )

        if query.start == query.destination:
            return NavigationPath(
                status=NavigationPathStatus.PARTIAL,
                waypoints=(query.start,),
                traversed_chunk_keys=required,
                reason="already_at_destination",
            )

        return NavigationPath(
            status=NavigationPathStatus.REACHABLE,
            waypoints=(query.start, query.destination),
            traversed_chunk_keys=required,
            reason="",
        )


@dataclass(frozen=True)
class SoundEvent:
    event_id: str
    source_entity_id: str
    source_entity_type: str
    event_type: str
    position: WorldCoordinate
    strength: float
    tick_index: int


@dataclass
class PerceptionMemory:
    target_id: str
    target_type: str
    last_known_position: WorldCoordinate
    last_seen_tick: int | None = None
    last_heard_tick: int | None = None
    confidence: float = 0.0
    reason: str = ""


@dataclass
class NpcAiState:
    behavior_state: str = "wander"
    primary_target_id: str | None = None
    primary_target_type: str | None = None
    target_locked_until_tick: int = 0
    last_target_switch_tick: int = -9999
    last_visible_tick: int = -9999
    target_lost_tick: int = -9999
    current_chunk_key: str = ""
    last_navigation_status: str = NavigationPathStatus.PARTIAL.value
    last_path_chunk_keys: list[str] = field(default_factory=list)
    horde_id: str | None = None
    last_recruitment_tick: int = -9999
    last_abandon_tick: int = -9999


@dataclass(frozen=True)
class AiPerceptionConfig:
    vision_range: float
    vision_angle_degrees: float
    hearing_range: float
    hearing_min_strength: float
    memory_ticks: int


@dataclass(frozen=True)
class ZombieTargetingConfig:
    visibility_weight: float
    distance_weight: float
    sound_weight: float
    memory_weight: float
    current_target_bonus: float
    retarget_threshold: float
    retarget_cooldown_ticks: int
    target_persistence_ticks: int
    pursuit_timeout_ticks: int
    minimum_target_score: float


@dataclass(frozen=True)
class RecruitmentConfig:
    enabled_event_types: tuple[str, ...]
    distance: float
    probability: float
    cooldown_ticks: int


@dataclass(frozen=True)
class HumanNpcBehaviorConfig:
    threat_range: float
    flee_distance: float
    combat_preference: float


@dataclass(frozen=True)
class Phase3AiConfig:
    perception: AiPerceptionConfig
    zombie_targeting: ZombieTargetingConfig
    recruitment: RecruitmentConfig
    human_npc: HumanNpcBehaviorConfig
    chunk_awareness_radius: int


def deterministic_roll(seed: str) -> float:
    digest = sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:12], 16) / float(0xFFFFFFFFFFFF)


def distance(a: WorldCoordinate, b: WorldCoordinate) -> float:
    dx = a.x - b.x
    dy = a.y - b.y
    dz = a.z - b.z
    return (dx * dx + dy * dy + dz * dz) ** 0.5


def facing_towards(observer: WorldCoordinate, target: WorldCoordinate, fov_degrees: float, facing_yaw: float = 0.0) -> bool:
    direction_x = target.x - observer.x
    direction_z = target.z - observer.z
    if direction_x == 0.0 and direction_z == 0.0:
        return True
    angle = degrees(atan2(direction_z, direction_x))
    delta = (angle - facing_yaw + 180.0) % 360.0 - 180.0
    return abs(delta) <= fov_degrees / 2.0


def move_away(from_point: WorldCoordinate, threat: WorldCoordinate, distance_units: float) -> WorldCoordinate:
    dx = from_point.x - threat.x
    dz = from_point.z - threat.z
    magnitude = (dx * dx + dz * dz) ** 0.5
    if magnitude <= 0.0:
        return WorldCoordinate(from_point.x + distance_units, from_point.y, from_point.z)
    norm_x = dx / magnitude
    norm_z = dz / magnitude
    return WorldCoordinate(
        x=from_point.x + norm_x * distance_units,
        y=from_point.y,
        z=from_point.z + norm_z * distance_units,
    )


def interpolate_sound_strength(base_strength: float, source: WorldCoordinate, listener: WorldCoordinate) -> float:
    d = distance(source, listener)
    if d <= 0.0:
        return base_strength
    attenuation = max(0.0, 1.0 - (d / max(d, 1.0)))
    # simplified deterministic attenuation that still scales by distance
    return max(0.0, base_strength / (1.0 + d * 0.05) + attenuation * 0.01)


def heading_from_to(start: WorldCoordinate, end: WorldCoordinate) -> tuple[float, float]:
    angle = atan2(end.z - start.z, end.x - start.x)
    return cos(radians(degrees(angle))), sin(radians(degrees(angle)))
