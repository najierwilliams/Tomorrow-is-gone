from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import floor
from typing import Protocol


class PlayerForm(str, Enum):
    HUMAN = "human"
    INFECTED_HUMAN = "infected_human"
    ZOMBIE = "zombie"


def is_valid_form_transition(
    current: PlayerForm,
    target: PlayerForm,
    *,
    cure_available: bool = False,
) -> bool:
    if current == target:
        return True
    if current == PlayerForm.HUMAN:
        return target == PlayerForm.INFECTED_HUMAN
    if current == PlayerForm.INFECTED_HUMAN:
        if target == PlayerForm.ZOMBIE:
            return True
        if target == PlayerForm.HUMAN:
            return cure_available
        return False
    if current == PlayerForm.ZOMBIE and target == PlayerForm.HUMAN:
        return cure_available
    return False


@dataclass(frozen=True)
class PlayerStateModel:
    player_id: str
    form: PlayerForm
    infection_progress: float = 0.0
    zombie_sanity: float | None = None


@dataclass(frozen=True)
class ZombieTierDefinition:
    tier_id: str
    display_name: str
    sanity_drain_rate: float
    feeding_efficiency: float


@dataclass(frozen=True)
class ZombieSanityBandDefinition:
    band_id: str
    minimum: float
    maximum: float
    human_coexistence_allowed: bool
    hostility_level: float
    cure_eligible: bool
    mission_availability_tags: list[str] = field(default_factory=list)
    behavior_tags: list[str] = field(default_factory=list)


@dataclass
class ZombieSanityState:
    value: float
    minimum: float = 0.0
    maximum: float = 100.0

    def apply_delta(self, delta: float) -> None:
        self.value = max(self.minimum, min(self.maximum, self.value + delta))


def resolve_zombie_sanity_band(
    sanity_value: float,
    bands: list[ZombieSanityBandDefinition],
) -> ZombieSanityBandDefinition | None:
    for band in bands:
        if band.minimum <= sanity_value < band.maximum:
            return band
    if not bands:
        return None
    highest_maximum = max(band.maximum for band in bands)
    if sanity_value == highest_maximum:
        for band in bands:
            if band.maximum == highest_maximum:
                return band
    return None


@dataclass(frozen=True)
class ServerRuleSet:
    custom_rules: dict[str, bool] = field(default_factory=dict)
    custom_difficulty: dict[str, float] = field(default_factory=dict)
    custom_mission_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ServerConfiguration:
    server_id: str
    map_id: str
    region_id: str
    is_public: bool
    creative_mode_enabled: bool
    max_players: int
    rule_set: ServerRuleSet


class InfectionState(str, Enum):
    NORMAL = "normal"
    INFECTED = "infected"


class TameState(str, Enum):
    WILD = "wild"
    TAMED = "tamed"
    PET = "pet"


class AnimalHabitat(str, Enum):
    LAND = "land"
    WATER = "water"
    AMPHIBIOUS = "amphibious"


class AnimalAbilityDomain(str, Enum):
    COMBAT = "combat"
    CRAFTING = "crafting"
    GARDENING = "gardening"
    BUILDING = "building"
    RESOURCE_GATHERING = "resource_gathering"


@dataclass(frozen=True)
class AnimalAbilityDefinition:
    ability_id: str
    domain: AnimalAbilityDomain
    modifiers: dict[str, float]


@dataclass(frozen=True)
class AnimalStateModel:
    animal_id: str
    species_id: str
    habitat: AnimalHabitat
    infection_state: InfectionState
    tame_state: TameState
    ability_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class WorldCoordinate:
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class ChunkAddress:
    region_x: int
    region_y: int
    region_z: int
    chunk_x: int
    chunk_y: int
    chunk_z: int


@dataclass(frozen=True)
class WorldGridConfig:
    chunk_size_meters: int
    chunks_per_region: int
    chunk_height_meters: int = 64
    chunks_per_vertical_region: int = 64
    minimum_world_y_meters: int = -2048
    maximum_world_y_meters: int = 2048

    def supports_vertical_coordinate(self, y: float) -> bool:
        return self.minimum_world_y_meters <= y <= self.maximum_world_y_meters

    def to_chunk_address(self, coordinate: WorldCoordinate) -> ChunkAddress:
        if not self.supports_vertical_coordinate(coordinate.y):
            raise ValueError("coordinate y is outside configured vertical world bounds")
        chunk_x = floor(coordinate.x / self.chunk_size_meters)
        chunk_y = floor(coordinate.y / self.chunk_height_meters)
        chunk_z = floor(coordinate.z / self.chunk_size_meters)
        return ChunkAddress(
            region_x=floor(chunk_x / self.chunks_per_region),
            region_y=floor(chunk_y / self.chunks_per_vertical_region),
            region_z=floor(chunk_z / self.chunks_per_region),
            chunk_x=chunk_x,
            chunk_y=chunk_y,
            chunk_z=chunk_z,
        )


@dataclass(frozen=True)
class StructureRecord:
    structure_id: str
    owner_player_id: str
    blueprint_id: str
    anchor: WorldCoordinate
    integrity: float


@dataclass(frozen=True)
class DestructionRecord:
    target_id: str
    source_actor_id: str
    damage: float
    occurred_at_unix: int


@dataclass(frozen=True)
class LootTierDefinition:
    tier_id: str
    weight: float
    eligible_loot_pool_ids: list[str]
    eligible_categories: list[str] = field(default_factory=list)
    eligible_quality_levels: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LootContainerDefinition:
    container_type: str
    container_tier_id: str
    tier_weights: dict[str, float]
    respawn_seconds: int


@dataclass(frozen=True)
class RecipeDefinition:
    recipe_id: str
    recipe_tags: list[str]
    input_item_quantities: dict[str, int]
    output_item_quantities: dict[str, int]
    required_workbench_id: str | None = None


@dataclass(frozen=True)
class WorkbenchDefinition:
    workbench_id: str
    supported_recipe_tags: list[str]
    power_required: bool


@dataclass
class DurabilityState:
    current: float
    maximum: float

    def apply_wear(self, value: float) -> None:
        self.current = max(0.0, min(self.maximum, self.current - max(0.0, value)))


class VehicleType(str, Enum):
    CAR = "car"
    BOAT = "boat"
    PLANE = "plane"


@dataclass(frozen=True)
class VehicleDefinition:
    vehicle_id: str
    vehicle_type: VehicleType
    seat_count: int
    cargo_slots: int


@dataclass(frozen=True)
class VehicleStateModel:
    instance_id: str
    definition_id: str
    position: WorldCoordinate
    fuel: float
    durability: float


class NpcFaction(str, Enum):
    HUMAN_SETTLEMENT = "human_settlement"
    ZOMBIE_HORDE = "zombie_horde"


@dataclass(frozen=True)
class NpcDefinition:
    npc_id: str
    faction: NpcFaction
    behavior_profile_id: str
    mission_ids: list[str] = field(default_factory=list)
    shop_id: str | None = None


class MissionAudience(str, Enum):
    HUMAN = "human"
    ZOMBIE = "zombie"
    SERVER_CUSTOM = "server_custom"


@dataclass(frozen=True)
class MissionDefinition:
    mission_id: str
    audience: MissionAudience
    objective_ids: list[str]
    reward_id: str
    prerequisite_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EconomyConfig:
    currency_id: str
    starting_balance: int
    price_multipliers: dict[str, float]


@dataclass(frozen=True)
class WeatherPreset:
    weather_id: str
    temperature_celsius: float
    precipitation_intensity: float
    wind_speed_mps: float
    hazard_tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RegionalClimateProfile:
    region_id: str
    season_ids: list[str]
    weather_weights: dict[str, float]


@dataclass(frozen=True)
class PersistenceLayout:
    player_state_store: str
    world_state_store: str
    inventory_state_store: str
    structure_state_store: str
    destruction_state_store: str
    vehicle_state_store: str
    npc_state_store: str
    loot_state_store: str
    server_configuration_store: str

    def categories(self) -> tuple[str, ...]:
        return (
            "player",
            "world",
            "inventory",
            "structure",
            "destruction",
            "vehicle",
            "npc",
            "loot",
            "server_configuration",
        )


class AuthorityRole(str, Enum):
    SERVER = "server"
    CLIENT = "client"


@dataclass(frozen=True)
class ReplicationRule:
    channel_id: str
    authority: AuthorityRole
    state_topics: list[str]
    server_authoritative: bool = True
    client_command_topics: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ClientCommandIntent:
    command_id: str
    player_id: str
    topic: str
    payload: dict[str, object]


class ServerConfigurationProvider(Protocol):
    def get_server_configuration(self, server_id: str) -> ServerConfiguration:
        ...


class PersistentStateRepository(Protocol):
    def load_by_key(self, key: str) -> dict:
        ...

    def save_by_key(self, key: str, payload: dict) -> None:
        ...


class WorldChunkStream(Protocol):
    def required_chunks_for_player(self, player_id: str) -> list[ChunkAddress]:
        ...


class LootGenerationPort(Protocol):
    def generate_loot_for_container(
        self,
        container: LootContainerDefinition,
        tier_definitions: dict[str, LootTierDefinition],
        *,
        seed: int | None = None,
    ) -> list[dict]:
        ...


class UnityIntegrationPort(Protocol):
    def push_state_snapshot(self, topic: str, payload: dict) -> None:
        ...

    def pull_input_commands(self) -> list[ClientCommandIntent]:
        ...
