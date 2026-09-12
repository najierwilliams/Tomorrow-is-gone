from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Protocol


class ChunkLifecycleState(str, Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    UNLOADING = "unloading"
    FAILED = "failed"


@dataclass(frozen=True)
class WorldPosition:
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class RegionCoordinate:
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class ChunkCoordinate:
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class LocalChunkCoordinate:
    x: int
    y: int
    z: int


@dataclass(frozen=True)
class WorldBounds:
    minimum_x: int
    maximum_x: int
    minimum_y: int
    maximum_y: int
    minimum_z: int
    maximum_z: int

    def contains(self, position: WorldPosition) -> bool:
        return (
            self.minimum_x <= position.x <= self.maximum_x
            and self.minimum_y <= position.y <= self.maximum_y
            and self.minimum_z <= position.z <= self.maximum_z
        )


@dataclass(frozen=True)
class WorldGridDefinition:
    chunk_size_xz: int
    chunk_height: int
    chunks_per_region_xz: int
    chunks_per_region_y: int
    world_bounds: WorldBounds


@dataclass(frozen=True)
class WorldAddress:
    world: WorldPosition
    region: RegionCoordinate
    chunk: ChunkCoordinate
    local: LocalChunkCoordinate


class WorldCoordinateMapper:
    def __init__(self, definition: WorldGridDefinition) -> None:
        self.definition = definition

    def validate_world_position(self, position: WorldPosition) -> None:
        if not self.definition.world_bounds.contains(position):
            raise ValueError("position_out_of_world_bounds")

    def to_chunk_coordinate(self, position: WorldPosition) -> ChunkCoordinate:
        self.validate_world_position(position)
        return ChunkCoordinate(
            x=position.x // self.definition.chunk_size_xz,
            y=position.y // self.definition.chunk_height,
            z=position.z // self.definition.chunk_size_xz,
        )

    def to_region_coordinate(self, chunk: ChunkCoordinate) -> RegionCoordinate:
        return RegionCoordinate(
            x=chunk.x // self.definition.chunks_per_region_xz,
            y=chunk.y // self.definition.chunks_per_region_y,
            z=chunk.z // self.definition.chunks_per_region_xz,
        )

    def to_local_coordinate(self, position: WorldPosition, chunk: ChunkCoordinate | None = None) -> LocalChunkCoordinate:
        self.validate_world_position(position)
        chunk_coordinate = chunk or self.to_chunk_coordinate(position)
        return LocalChunkCoordinate(
            x=position.x - (chunk_coordinate.x * self.definition.chunk_size_xz),
            y=position.y - (chunk_coordinate.y * self.definition.chunk_height),
            z=position.z - (chunk_coordinate.z * self.definition.chunk_size_xz),
        )

    def from_chunk_local(self, chunk: ChunkCoordinate, local: LocalChunkCoordinate) -> WorldPosition:
        position = WorldPosition(
            x=(chunk.x * self.definition.chunk_size_xz) + local.x,
            y=(chunk.y * self.definition.chunk_height) + local.y,
            z=(chunk.z * self.definition.chunk_size_xz) + local.z,
        )
        self.validate_world_position(position)
        return position

    def to_world_address(self, position: WorldPosition) -> WorldAddress:
        chunk = self.to_chunk_coordinate(position)
        return WorldAddress(
            world=position,
            chunk=chunk,
            region=self.to_region_coordinate(chunk),
            local=self.to_local_coordinate(position, chunk),
        )


@dataclass(frozen=True)
class ChunkIdentity:
    coordinate: ChunkCoordinate
    region: RegionCoordinate
    generation_version: int

    @property
    def key(self) -> str:
        return (
            f"region:{self.region.x}:{self.region.y}:{self.region.z}|"
            f"chunk:{self.coordinate.x}:{self.coordinate.y}:{self.coordinate.z}|"
            f"gen:{self.generation_version}"
        )


@dataclass
class ChunkRecord:
    identity: ChunkIdentity
    state: ChunkLifecycleState = ChunkLifecycleState.UNLOADED
    static_metadata: dict[str, object] = field(default_factory=dict)
    dynamic_metadata: dict[str, object] = field(default_factory=dict)
    last_error: str = ""

    def request_load(self) -> None:
        if self.state in {ChunkLifecycleState.UNLOADED, ChunkLifecycleState.FAILED}:
            self.state = ChunkLifecycleState.LOADING
            self.last_error = ""

    def mark_active(self) -> None:
        if self.state in {ChunkLifecycleState.LOADING, ChunkLifecycleState.UNLOADING, ChunkLifecycleState.UNLOADED}:
            self.state = ChunkLifecycleState.ACTIVE

    def request_unload(self) -> None:
        if self.state == ChunkLifecycleState.ACTIVE:
            self.state = ChunkLifecycleState.UNLOADING

    def mark_unloaded(self) -> None:
        if self.state == ChunkLifecycleState.UNLOADING:
            self.state = ChunkLifecycleState.UNLOADED

    def mark_failed(self, reason: str) -> None:
        self.state = ChunkLifecycleState.FAILED
        self.last_error = reason


@dataclass(frozen=True)
class InterestRadii:
    simulation_radius: int
    replication_radius: int
    persistence_activation_radius: int
    ai_interest_radius: int
    vertical_radius: int


class ChunkInterestManager:
    def __init__(self, radii: InterestRadii) -> None:
        self.radii = radii

    def relevant_chunks(self, center: ChunkCoordinate, radius: int | None = None) -> set[ChunkCoordinate]:
        use_radius = self.radii.replication_radius if radius is None else max(0, radius)
        relevant: set[ChunkCoordinate] = set()
        for offset_x in range(-use_radius, use_radius + 1):
            for offset_y in range(-self.radii.vertical_radius, self.radii.vertical_radius + 1):
                for offset_z in range(-use_radius, use_radius + 1):
                    relevant.add(
                        ChunkCoordinate(
                            x=center.x + offset_x,
                            y=center.y + offset_y,
                            z=center.z + offset_z,
                        )
                    )
        return relevant

    def chunk_is_relevant(self, center: ChunkCoordinate, target: ChunkCoordinate, radius: int | None = None) -> bool:
        use_radius = self.radii.replication_radius if radius is None else max(0, radius)
        return (
            abs(center.x - target.x) <= use_radius
            and abs(center.z - target.z) <= use_radius
            and abs(center.y - target.y) <= self.radii.vertical_radius
        )


class WorldObjectType(str, Enum):
    TREE = "tree"
    ROCK = "rock"
    RESOURCE_NODE = "resource_node"
    BUILDING = "building"
    STRUCTURE = "structure"
    CONTAINER = "container"
    ENVIRONMENTAL_OBJECT = "environmental_object"
    NPC_SPAWN_LOCATION = "npc_spawn_location"
    POINT_OF_INTEREST = "point_of_interest"
    VEHICLE = "vehicle"
    WILDLIFE = "wildlife"


class PersistenceClassification(str, Enum):
    PERSISTENT = "persistent"
    SEMI_PERSISTENT = "semi_persistent"
    TRANSIENT = "transient"


@dataclass
class WorldObjectRecord:
    object_id: str
    object_type: WorldObjectType
    position: WorldPosition
    chunk_coordinate: ChunkCoordinate
    persistence: PersistenceClassification
    state: dict[str, object] = field(default_factory=dict)


@dataclass
class ChunkPersistentDelta:
    destroyed_structure_ids: set[str] = field(default_factory=set)
    harvested_resource_ids: set[str] = field(default_factory=set)
    modified_containers: dict[str, dict[str, object]] = field(default_factory=dict)
    player_built_structures: dict[str, dict[str, object]] = field(default_factory=dict)
    persistent_entity_state: dict[str, dict[str, object]] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedTerrainData:
    biome_id: str
    base_height: int
    water_depth: int


@dataclass(frozen=True)
class GeneratedResourceNode:
    node_id: str
    node_type: str
    position: WorldPosition


@dataclass(frozen=True)
class GeneratedPoi:
    poi_id: str
    poi_type: str
    position: WorldPosition


@dataclass(frozen=True)
class GeneratedSpawnPoint:
    spawn_id: str
    spawn_type: str
    position: WorldPosition


@dataclass(frozen=True)
class BaselineChunkData:
    chunk_coordinate: ChunkCoordinate
    terrain: GeneratedTerrainData
    resources: tuple[GeneratedResourceNode, ...]
    pois: tuple[GeneratedPoi, ...]
    spawns: tuple[GeneratedSpawnPoint, ...]


class TerrainGenerator(Protocol):
    def generate(self, *, seed: int, chunk: ChunkCoordinate, generation_version: int) -> GeneratedTerrainData:
        ...


class ResourceGenerator(Protocol):
    def generate(self, *, seed: int, chunk: ChunkCoordinate, generation_version: int) -> tuple[GeneratedResourceNode, ...]:
        ...


class PoiGenerator(Protocol):
    def generate(self, *, seed: int, chunk: ChunkCoordinate, generation_version: int) -> tuple[GeneratedPoi, ...]:
        ...


class SpawnGenerator(Protocol):
    def generate(self, *, seed: int, chunk: ChunkCoordinate, generation_version: int) -> tuple[GeneratedSpawnPoint, ...]:
        ...


class WorldGenerator(Protocol):
    def generate_chunk(self, chunk: ChunkCoordinate) -> BaselineChunkData:
        ...


class DeterministicWorldGenerator(WorldGenerator):
    def __init__(self, seed: int, generation_version: int) -> None:
        self.seed = seed
        self.generation_version = generation_version

    def _roll(self, chunk: ChunkCoordinate, key: str, modulo: int) -> int:
        digest = sha256(
            f"{self.seed}:{self.generation_version}:{chunk.x}:{chunk.y}:{chunk.z}:{key}".encode("utf-8")
        ).hexdigest()
        return int(digest[:12], 16) % modulo

    def generate_chunk(self, chunk: ChunkCoordinate) -> BaselineChunkData:
        terrain_roll = self._roll(chunk, "terrain", 100)
        biome_id = "urban" if terrain_roll % 3 == 0 else "forest" if terrain_roll % 3 == 1 else "coastal"
        water_depth = self._roll(chunk, "water", 12) if biome_id in {"coastal", "ocean", "underwater"} else 0
        terrain = GeneratedTerrainData(
            biome_id=biome_id,
            base_height=self._roll(chunk, "height", 96),
            water_depth=water_depth,
        )

        resources = (
            GeneratedResourceNode(
                node_id=f"res:{chunk.x}:{chunk.y}:{chunk.z}:0",
                node_type="wood" if biome_id == "forest" else "stone",
                position=WorldPosition(x=chunk.x * 64 + 8, y=chunk.y * 32 + 1, z=chunk.z * 64 + 8),
            ),
        )
        pois = (
            GeneratedPoi(
                poi_id=f"poi:{chunk.x}:{chunk.y}:{chunk.z}:0",
                poi_type="house" if biome_id in {"urban", "suburban"} else "camp",
                position=WorldPosition(x=chunk.x * 64 + 20, y=chunk.y * 32 + 1, z=chunk.z * 64 + 20),
            ),
        )
        spawns = (
            GeneratedSpawnPoint(
                spawn_id=f"spawn:{chunk.x}:{chunk.y}:{chunk.z}:0",
                spawn_type="zombie",
                position=WorldPosition(x=chunk.x * 64 + 12, y=chunk.y * 32 + 1, z=chunk.z * 64 + 12),
            ),
        )
        return BaselineChunkData(chunk_coordinate=chunk, terrain=terrain, resources=resources, pois=pois, spawns=spawns)


@dataclass(frozen=True)
class ResourceHarvestRule:
    gather_distance: int
    required_tool_tags: tuple[str, ...] = ()


@dataclass
class ResourceNodeState:
    node_id: str
    node_type: str
    position: WorldPosition
    chunk_coordinate: ChunkCoordinate
    quantity: int
    max_quantity: int
    respawn_ticks: int
    depleted_ticks: int = 0

    @property
    def available(self) -> bool:
        return self.quantity > 0


class ResourceAuthorityService:
    def __init__(self, harvest_rules: dict[str, ResourceHarvestRule]) -> None:
        self.harvest_rules = harvest_rules

    @staticmethod
    def _distance(a: WorldPosition, b: WorldPosition) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def validate_harvest(
        self,
        node: ResourceNodeState | None,
        player_position: WorldPosition,
        tool_tags: set[str],
    ) -> tuple[bool, str]:
        if node is None:
            return False, "resource_not_found"
        if not node.available:
            return False, "resource_depleted"
        rule = self.harvest_rules.get(node.node_type, ResourceHarvestRule(gather_distance=3))
        if self._distance(node.position, player_position) > rule.gather_distance:
            return False, "resource_out_of_range"
        if rule.required_tool_tags and not set(rule.required_tool_tags).issubset(tool_tags):
            return False, "missing_required_tool"
        return True, ""

    def harvest(
        self,
        node: ResourceNodeState,
        player_position: WorldPosition,
        tool_tags: set[str],
        quantity: int,
    ) -> tuple[bool, str, int]:
        valid, reason = self.validate_harvest(node, player_position, tool_tags)
        if not valid:
            return False, reason, 0
        harvested = min(max(1, quantity), node.quantity)
        node.quantity -= harvested
        if node.quantity == 0:
            node.depleted_ticks = node.respawn_ticks
        return True, "", harvested

    def tick_respawn(self, node: ResourceNodeState) -> None:
        if node.quantity > 0 or node.depleted_ticks <= 0:
            return
        node.depleted_ticks -= 1
        if node.depleted_ticks == 0:
            node.quantity = node.max_quantity


class EntityPersistenceClass(str, Enum):
    PERSISTENT = "persistent"
    SEMI_PERSISTENT = "semi_persistent"
    TRANSIENT = "transient"


@dataclass(frozen=True)
class SpawnRuleDefinition:
    spawn_type: str
    allowed_biomes: tuple[str, ...]
    max_active: int
    min_distance_from_players: int


class SpawnAuthorityService:
    def __init__(self, spawn_rules: dict[str, SpawnRuleDefinition]) -> None:
        self.spawn_rules = spawn_rules

    def can_spawn(self, spawn_type: str, biome_id: str, current_active: int, nearest_player_distance: int) -> bool:
        rule = self.spawn_rules.get(spawn_type)
        if rule is None:
            return False
        if biome_id not in rule.allowed_biomes:
            return False
        if current_active >= rule.max_active:
            return False
        if nearest_player_distance < rule.min_distance_from_players:
            return False
        return True

    @staticmethod
    def can_despawn(persistence: EntityPersistenceClass, inside_interest: bool) -> bool:
        if inside_interest:
            return False
        return persistence in {EntityPersistenceClass.SEMI_PERSISTENT, EntityPersistenceClass.TRANSIENT}


@dataclass(frozen=True)
class BiomeDefinition:
    biome_id: str
    terrain_characteristics: dict[str, object]
    resource_pool_ids: tuple[str, ...]
    vegetation_pool_ids: tuple[str, ...]
    animal_pool_ids: tuple[str, ...]
    zombie_spawn_tendencies: dict[str, float]
    npc_spawn_tendencies: dict[str, float]
    temperature_range: tuple[int, int]
    environment_modifiers: dict[str, float]


@dataclass(frozen=True)
class PoiDefinition:
    poi_id: str
    poi_type: str
    placement_tags: tuple[str, ...]
    allowed_biomes: tuple[str, ...]
    spawn_weight: float


@dataclass(frozen=True)
class SeasonDefinition:
    season_id: str
    temperature_modifier: float
    precipitation_modifier: float
    weather_weights: dict[str, float]


@dataclass(frozen=True)
class RegionalEnvironmentState:
    region: RegionCoordinate
    season_id: str
    temperature_celsius: float
    precipitation_intensity: float
    is_underwater: bool
    water_depth_meters: int = 0


@dataclass(frozen=True)
class WaterRegionDefinition:
    water_region_id: str
    depth_meters: int
    supports_underwater_poi: bool
    supports_underwater_resources: bool


@dataclass(frozen=True)
class WorldEventRecord:
    event_id: str
    event_type: str
    location: WorldPosition
    chunk_coordinate: ChunkCoordinate
    tick_index: int
    persistence: PersistenceClassification
    affected_world_state: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class Phase4WorldDefinitions:
    grid: WorldGridDefinition
    interest_radii: InterestRadii
    world_seed: int
    generation_version: int
    biomes: dict[str, BiomeDefinition]
    resources: dict[str, dict[str, object]]
    pois: dict[str, PoiDefinition]
    spawn_rules: dict[str, SpawnRuleDefinition]
    seasons: dict[str, SeasonDefinition]
    environment_states: dict[str, dict[str, object]]



def load_phase4_world_definitions(path: Path) -> Phase4WorldDefinitions:
    payload = json.loads(path.read_text())
    chunk_def = payload["chunk_dimensions"]
    region_def = payload["region_dimensions"]
    bounds = payload["world_bounds"]
    interest = payload["streaming_distances"]

    grid = WorldGridDefinition(
        chunk_size_xz=int(chunk_def["chunk_size_xz"]),
        chunk_height=int(chunk_def["chunk_height"]),
        chunks_per_region_xz=int(region_def["chunks_per_region_xz"]),
        chunks_per_region_y=int(region_def["chunks_per_region_y"]),
        world_bounds=WorldBounds(
            minimum_x=int(bounds["minimum_x"]),
            maximum_x=int(bounds["maximum_x"]),
            minimum_y=int(bounds["minimum_y"]),
            maximum_y=int(bounds["maximum_y"]),
            minimum_z=int(bounds["minimum_z"]),
            maximum_z=int(bounds["maximum_z"]),
        ),
    )

    interest_radii = InterestRadii(
        simulation_radius=int(interest["simulation_radius"]),
        replication_radius=int(interest["replication_radius"]),
        persistence_activation_radius=int(interest["persistence_activation_radius"]),
        ai_interest_radius=int(interest["ai_interest_radius"]),
        vertical_radius=int(interest["vertical_radius"]),
    )

    biome_map = {
        entry["biome_id"]: BiomeDefinition(
            biome_id=entry["biome_id"],
            terrain_characteristics=dict(entry.get("terrain_characteristics", {})),
            resource_pool_ids=tuple(entry.get("resource_pool_ids", [])),
            vegetation_pool_ids=tuple(entry.get("vegetation_pool_ids", [])),
            animal_pool_ids=tuple(entry.get("animal_pool_ids", [])),
            zombie_spawn_tendencies=dict(entry.get("zombie_spawn_tendencies", {})),
            npc_spawn_tendencies=dict(entry.get("npc_spawn_tendencies", {})),
            temperature_range=(
                int(entry.get("temperature_range", {}).get("minimum", -10)),
                int(entry.get("temperature_range", {}).get("maximum", 40)),
            ),
            environment_modifiers=dict(entry.get("environment_modifiers", {})),
        )
        for entry in payload.get("biomes", [])
    }

    poi_map = {
        entry["poi_id"]: PoiDefinition(
            poi_id=entry["poi_id"],
            poi_type=entry["poi_type"],
            placement_tags=tuple(entry.get("placement_tags", [])),
            allowed_biomes=tuple(entry.get("allowed_biomes", [])),
            spawn_weight=float(entry.get("spawn_weight", 1.0)),
        )
        for entry in payload.get("pois", [])
    }

    spawn_rules = {
        entry["spawn_type"]: SpawnRuleDefinition(
            spawn_type=entry["spawn_type"],
            allowed_biomes=tuple(entry.get("allowed_biomes", [])),
            max_active=int(entry.get("max_active", 0)),
            min_distance_from_players=int(entry.get("min_distance_from_players", 0)),
        )
        for entry in payload.get("spawn_rules", [])
    }

    seasons = {
        entry["season_id"]: SeasonDefinition(
            season_id=entry["season_id"],
            temperature_modifier=float(entry.get("temperature_modifier", 0.0)),
            precipitation_modifier=float(entry.get("precipitation_modifier", 0.0)),
            weather_weights=dict(entry.get("weather_weights", {})),
        )
        for entry in payload.get("season_definitions", [])
    }

    resources = {entry["resource_id"]: dict(entry) for entry in payload.get("resources", [])}

    return Phase4WorldDefinitions(
        grid=grid,
        interest_radii=interest_radii,
        world_seed=int(payload.get("world_generation", {}).get("seed", 1)),
        generation_version=int(payload.get("world_generation", {}).get("generation_version", 1)),
        biomes=biome_map,
        resources=resources,
        pois=poi_map,
        spawn_rules=spawn_rules,
        seasons=seasons,
        environment_states={entry["state_id"]: dict(entry) for entry in payload.get("environment_states", [])},
    )
