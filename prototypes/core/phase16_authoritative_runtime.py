from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .inventory import Inventory
from .items import ItemDefinition, ItemStack
from .phase15_contracts import (
    AnimalAbilityDefinition,
    AnimalAbilityDomain,
    AnimalHabitat,
    AnimalStateModel,
    ClientCommandIntent,
    InfectionState,
    LootContainerDefinition,
    LootGenerationPort,
    LootTierDefinition,
    MissionAudience,
    MissionDefinition,
    PersistentStateRepository,
    PlayerForm,
    PlayerStateModel,
    RecipeDefinition,
    ServerConfiguration,
    ServerRuleSet,
    TameState,
    WorkbenchDefinition,
    WorldCoordinate,
    WorldGridConfig,
    ZombieSanityBandDefinition,
    ZombieSanityState,
    ZombieTierDefinition,
    is_valid_form_transition,
    resolve_zombie_sanity_band,
)
from .player import PlayerStats


@dataclass(frozen=True)
class FoodDefinition:
    item_id: str
    hunger_restore: float
    health_restore: float = 0.0
    durability_loss_on_use: float = 0.0


@dataclass(frozen=True)
class MedicineDefinition:
    item_id: str
    health_restore: float
    zombie_sanity_delta: float = 0.0
    cure_progress_delta: float = 0.0


@dataclass(frozen=True)
class WeaponRuntimeDefinition:
    weapon_id: str
    damage: float
    stamina_cost: float
    durability_loss: float
    ammo_per_attack: int = 0


@dataclass(frozen=True)
class ArmorDefinition:
    armor_id: str
    mitigation: float
    durability_loss_factor: float


@dataclass(frozen=True)
class StructureDefinition:
    blueprint_id: str
    required_materials: dict[str, int]
    max_health: float
    build_tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResourceNodeDefinition:
    node_type: str
    yields_item_id: str
    yield_per_gather: int
    respawn_ticks: int


@dataclass(frozen=True)
class CropDefinition:
    crop_id: str
    seed_item_id: str
    harvest_item_id: str
    growth_ticks_required: int
    water_per_tick: float


@dataclass(frozen=True)
class AnimalDefinition:
    species_id: str
    habitat: AnimalHabitat
    max_health: float
    tame_difficulty: float
    base_ability_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PowerSourceDefinition:
    source_id: str
    generation: float


@dataclass(frozen=True)
class PoweredDeviceDefinition:
    device_id: str
    consumption: float


@dataclass(frozen=True)
class ProgressionDefinition:
    levels: list[dict[str, int]]
    zombie_tier_thresholds: dict[str, float]


@dataclass(frozen=True)
class EconomyDefinition:
    currency_id: str
    starting_balance: int


@dataclass(frozen=True)
class SurvivalConfig:
    hunger_depletion_per_tick: float
    thirst_depletion_per_tick: float
    stamina_recovery_per_tick: float
    starvation_threshold: float
    dehydration_threshold: float
    starvation_damage_per_tick: float
    dehydration_damage_per_tick: float
    zombie_hunger_depletion_per_tick: float
    zombie_starvation_threshold: float
    zombie_starvation_damage_per_tick: float
    zombie_sleep_heal_per_tick: float
    food_degrade_per_tick: float


@dataclass
class EquipmentInstance:
    instance_id: str
    item_id: str
    durability: float
    max_durability: float
    equipped: bool = False

    @property
    def usable(self) -> bool:
        return self.durability > 0.0


@dataclass
class HumanRuntimeState:
    stats: PlayerStats = field(default_factory=PlayerStats)
    position: WorldCoordinate = field(default_factory=lambda: WorldCoordinate(x=0.0, y=0.0, z=0.0))
    movement_state: str = "idle"
    dead: bool = False


@dataclass
class ZombieRuntimeState:
    feeding_state: str = "idle"
    hunger: float = 0.0
    sleeping: bool = False
    sanity: ZombieSanityState = field(default_factory=lambda: ZombieSanityState(value=50.0))
    sanity_band_id: str = "volatile"
    behavior_tags: list[str] = field(default_factory=lambda: ["aggressive"])
    tier_id: str = "z_tier_1"
    mission_eligible: bool = True
    health: float = 100.0
    dead: bool = False


@dataclass
class MissionRuntimeState:
    accepted: bool = False
    completed: bool = False
    completed_objective_ids: set[str] = field(default_factory=set)


@dataclass
class PlayerEquipmentState:
    equipped_weapon_instance_id: str | None = None
    equipped_armor_instance_id: str | None = None


@dataclass
class AuthoritativePlayer:
    state: PlayerStateModel
    human_state: HumanRuntimeState
    zombie_state: ZombieRuntimeState | None = None
    inventory: Inventory = field(default_factory=lambda: Inventory(capacity_slots=30))
    equipment_instances: dict[str, EquipmentInstance] = field(default_factory=dict)
    equipment: PlayerEquipmentState = field(default_factory=PlayerEquipmentState)
    currency_balance: int = 0


@dataclass
class LootContainerRuntime:
    container_id: str
    definition: LootContainerDefinition
    coordinate: WorldCoordinate
    generated_items: list[ItemStack] = field(default_factory=list)
    looted: bool = False


@dataclass
class ResourceNodeRuntime:
    node_id: str
    node_type: str
    coordinate: WorldCoordinate
    quantity: int
    max_quantity: int
    respawn_ticks: int
    depleted_ticks: int = 0


@dataclass
class GardenPlotRuntime:
    plot_id: str
    coordinate: WorldCoordinate
    planted_crop_id: str | None = None
    owner_player_id: str | None = None
    growth_ticks: int = 0
    water: float = 0.0
    plant_health: float = 100.0


@dataclass
class StructureRuntime:
    structure_id: str
    blueprint_id: str
    coordinate: WorldCoordinate
    orientation_yaw: float
    owner_player_id: str
    health: float
    max_health: float
    state: str = "completed"


@dataclass
class DestructionRuntimeRecord:
    target_id: str
    source_actor_id: str
    damage: float


@dataclass
class WorkbenchRuntime:
    workbench_id: str
    definition_id: str
    coordinate: WorldCoordinate
    power_group_id: str | None = None


@dataclass
class PowerSourceRuntime:
    source_instance_id: str
    definition_id: str
    power_group_id: str
    enabled: bool = True


@dataclass
class PoweredDeviceRuntime:
    device_instance_id: str
    definition_id: str
    power_group_id: str
    enabled: bool = True
    powered: bool = False


@dataclass
class AnimalRuntime:
    state: AnimalStateModel
    coordinate: WorldCoordinate
    health: float
    owner_player_id: str | None = None


@dataclass
class HordeRuntime:
    horde_id: str
    leader_player_id: str | None = None
    member_player_ids: set[str] = field(default_factory=set)


@dataclass
class NpcRuntime:
    npc_id: str
    npc_type: str
    coordinate: WorldCoordinate
    settlement_id: str | None = None
    shop_id: str | None = None


@dataclass
class WorldChunkRuntime:
    chunk_key: str
    building_ids: list[str] = field(default_factory=list)
    container_ids: list[str] = field(default_factory=list)
    active: bool = False


@dataclass
class WorldRuntimeState:
    chunks: dict[str, WorldChunkRuntime] = field(default_factory=dict)
    containers: dict[str, LootContainerRuntime] = field(default_factory=dict)
    resource_nodes: dict[str, ResourceNodeRuntime] = field(default_factory=dict)
    structures: dict[str, StructureRuntime] = field(default_factory=dict)
    destruction_records: list[DestructionRuntimeRecord] = field(default_factory=list)
    gardens: dict[str, GardenPlotRuntime] = field(default_factory=dict)
    workbenches: dict[str, WorkbenchRuntime] = field(default_factory=dict)
    power_sources: dict[str, PowerSourceRuntime] = field(default_factory=dict)
    powered_devices: dict[str, PoweredDeviceRuntime] = field(default_factory=dict)
    animals: dict[str, AnimalRuntime] = field(default_factory=dict)
    hordes: dict[str, HordeRuntime] = field(default_factory=dict)
    npcs: dict[str, NpcRuntime] = field(default_factory=dict)


class InProcessTransport:
    def __init__(self) -> None:
        self._commands: list[ClientCommandIntent] = []
        self._snapshots: dict[str, list[dict]] = {}

    def submit_command_intent(self, intent: ClientCommandIntent) -> None:
        self._commands.append(intent)

    def drain_command_intents(self) -> list[ClientCommandIntent]:
        commands = list(self._commands)
        self._commands.clear()
        return commands

    def push_snapshot(self, player_id: str, payload: dict) -> None:
        self._snapshots.setdefault(player_id, []).append(payload)

    def pop_snapshots(self, player_id: str) -> list[dict]:
        payloads = list(self._snapshots.get(player_id, []))
        self._snapshots[player_id] = []
        return payloads


class FileBackedJsonRepository(PersistentStateRepository):
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def load_by_key(self, key: str) -> dict:
        path = self.root / f"{key}.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    def save_by_key(self, key: str, payload: dict) -> None:
        path = self.root / f"{key}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True))


class TieredLootGenerator(LootGenerationPort):
    def __init__(self, loot_pools: dict[str, list[dict[str, int | str]]]) -> None:
        self.loot_pools = loot_pools

    def generate_loot_for_container(
        self,
        container: LootContainerDefinition,
        tier_definitions: dict[str, LootTierDefinition],
        *,
        seed: int | None = None,
    ) -> list[dict]:
        rng = random.Random(seed)

        weighted_tiers = [
            (tier_id, weight)
            for tier_id, weight in container.tier_weights.items()
            if tier_id in tier_definitions and weight > 0
        ]
        if not weighted_tiers:
            return []

        tier_ids = [tier_id for tier_id, _ in weighted_tiers]
        weights = [weight for _, weight in weighted_tiers]
        selected_tier_id = rng.choices(tier_ids, weights=weights, k=1)[0]
        selected_tier = tier_definitions[selected_tier_id]

        pools = [pool_id for pool_id in selected_tier.eligible_loot_pool_ids if pool_id in self.loot_pools]
        if not pools:
            return []

        pool_id = rng.choice(pools)
        entries = self.loot_pools[pool_id]
        if not entries:
            return []

        roll_count = min(max(1, len(entries) // 2), len(entries))
        rolled_entries = rng.sample(entries, roll_count)
        generated: list[dict] = []
        for entry in rolled_entries:
            minimum = int(entry.get("min_qty", 1))
            maximum = int(entry.get("max_qty", 1))
            generated.append(
                {
                    "item_id": str(entry["item_id"]),
                    "quantity": rng.randint(minimum, maximum),
                    "tier_id": selected_tier_id,
                    "pool_id": pool_id,
                }
            )
        return generated


class AuthoritativeServerRuntime:
    def __init__(
        self,
        repository: PersistentStateRepository,
        transport: InProcessTransport,
        loot_generator: LootGenerationPort,
        *,
        data_root: Path | None = None,
        grid_config: WorldGridConfig | None = None,
        interest_radius_chunks: int = 1,
    ) -> None:
        self.repository = repository
        self.transport = transport
        self.loot_generator = loot_generator
        self.data_root = data_root or Path(__file__).resolve().parents[2] / "data"
        self.grid_config = grid_config or WorldGridConfig(
            chunk_size_meters=64,
            chunks_per_region=8,
            chunk_height_meters=32,
            chunks_per_vertical_region=8,
            minimum_world_y_meters=-64,
            maximum_world_y_meters=128,
        )
        self.interest_radius_chunks = interest_radius_chunks
        self._tick_index = 0

        self.server_configuration = ServerConfiguration(
            server_id="phase16-local",
            map_id="phase16_test_world",
            region_id="phase16_region",
            is_public=False,
            creative_mode_enabled=False,
            max_players=16,
            rule_set=ServerRuleSet(custom_rules={"friendly_fire": False}),
        )

        self.players: dict[str, AuthoritativePlayer] = {}
        self.world = WorldRuntimeState()
        self.mission_states: dict[str, dict[str, MissionRuntimeState]] = {}
        self.command_results: list[dict] = []

        self._instance_counter = 0

        self.item_definitions: dict[str, ItemDefinition] = {}
        self.food_definitions: dict[str, FoodDefinition] = {}
        self.medicine_definitions: dict[str, MedicineDefinition] = {}
        self.weapon_definitions: dict[str, WeaponRuntimeDefinition] = {}
        self.armor_definitions: dict[str, ArmorDefinition] = {}
        self.recipes: dict[str, RecipeDefinition] = {}
        self.workbench_definitions: dict[str, WorkbenchDefinition] = {}
        self.resource_node_definitions: dict[str, ResourceNodeDefinition] = {}
        self.crop_definitions: dict[str, CropDefinition] = {}
        self.structure_definitions: dict[str, StructureDefinition] = {}
        self.animal_definitions: dict[str, AnimalDefinition] = {}
        self.animal_ability_definitions: dict[str, AnimalAbilityDefinition] = {}
        self.power_source_definitions: dict[str, PowerSourceDefinition] = {}
        self.power_device_definitions: dict[str, PoweredDeviceDefinition] = {}
        self.progression_definition = ProgressionDefinition(levels=[{"level": 1, "xp_required": 0}], zombie_tier_thresholds={})
        self.economy_definition = EconomyDefinition(currency_id="credits", starting_balance=0)
        self.zombie_tiers: dict[str, ZombieTierDefinition] = {}
        self.zombie_sanity_bands: list[ZombieSanityBandDefinition] = []
        self.mission_definitions: dict[str, MissionDefinition] = {}
        self.tier_definitions: dict[str, LootTierDefinition] = {}
        self.survival_config = SurvivalConfig(
            hunger_depletion_per_tick=1.0,
            thirst_depletion_per_tick=1.2,
            stamina_recovery_per_tick=5.0,
            starvation_threshold=95.0,
            dehydration_threshold=95.0,
            starvation_damage_per_tick=5.0,
            dehydration_damage_per_tick=7.0,
            zombie_hunger_depletion_per_tick=1.1,
            zombie_starvation_threshold=95.0,
            zombie_starvation_damage_per_tick=6.0,
            zombie_sleep_heal_per_tick=4.0,
            food_degrade_per_tick=1.0,
        )

        self._load_phase2_definitions()
        self._build_test_world()

    def _load_phase2_definitions(self) -> None:
        path = self.data_root / "phase2_definitions.json"
        if not path.exists():
            return
        payload = json.loads(path.read_text())

        for item in payload.get("items", []):
            self.item_definitions[item["item_id"]] = ItemDefinition(
                item_id=item["item_id"],
                name=item["name"],
                category=item["category"],
                max_stack=int(item.get("max_stack", 1)),
                weight=float(item.get("weight", 0.0)),
            )

        for food in payload.get("food", []):
            self.food_definitions[food["item_id"]] = FoodDefinition(
                item_id=food["item_id"],
                hunger_restore=float(food.get("hunger_restore", 0.0)),
                health_restore=float(food.get("health_restore", 0.0)),
                durability_loss_on_use=float(food.get("durability_loss_on_use", 0.0)),
            )

        for med in payload.get("medicine", []):
            self.medicine_definitions[med["item_id"]] = MedicineDefinition(
                item_id=med["item_id"],
                health_restore=float(med.get("health_restore", 0.0)),
                zombie_sanity_delta=float(med.get("zombie_sanity_delta", 0.0)),
                cure_progress_delta=float(med.get("cure_progress_delta", 0.0)),
            )

        for weapon in payload.get("weapons", []):
            self.weapon_definitions[weapon["weapon_id"]] = WeaponRuntimeDefinition(
                weapon_id=weapon["weapon_id"],
                damage=float(weapon["damage"]),
                stamina_cost=float(weapon["stamina_cost"]),
                durability_loss=float(weapon["durability_loss"]),
                ammo_per_attack=int(weapon.get("ammo_per_attack", 0)),
            )

        for armor in payload.get("armor", []):
            self.armor_definitions[armor["armor_id"]] = ArmorDefinition(
                armor_id=armor["armor_id"],
                mitigation=float(armor["mitigation"]),
                durability_loss_factor=float(armor["durability_loss_factor"]),
            )

        for tier in payload.get("loot_tiers", []):
            self.tier_definitions[tier["tier_id"]] = LootTierDefinition(
                tier_id=tier["tier_id"],
                weight=float(tier["weight"]),
                eligible_loot_pool_ids=list(tier.get("eligible_loot_pool_ids", [])),
                eligible_categories=list(tier.get("eligible_categories", [])),
                eligible_quality_levels=list(tier.get("eligible_quality_levels", [])),
            )

        for recipe in payload.get("recipes", []):
            self.recipes[recipe["recipe_id"]] = RecipeDefinition(
                recipe_id=recipe["recipe_id"],
                recipe_tags=list(recipe.get("recipe_tags", [])),
                input_item_quantities=dict(recipe.get("input_item_quantities", {})),
                output_item_quantities=dict(recipe.get("output_item_quantities", {})),
                required_workbench_id=recipe.get("required_workbench_id"),
            )

        for workbench in payload.get("workbenches", []):
            self.workbench_definitions[workbench["workbench_id"]] = WorkbenchDefinition(
                workbench_id=workbench["workbench_id"],
                supported_recipe_tags=list(workbench.get("supported_recipe_tags", [])),
                power_required=bool(workbench.get("power_required", False)),
            )

        for node in payload.get("resource_nodes", []):
            self.resource_node_definitions[node["node_type"]] = ResourceNodeDefinition(
                node_type=node["node_type"],
                yields_item_id=node["yields_item_id"],
                yield_per_gather=int(node["yield_per_gather"]),
                respawn_ticks=int(node["respawn_ticks"]),
            )

        for crop in payload.get("crops", []):
            self.crop_definitions[crop["crop_id"]] = CropDefinition(
                crop_id=crop["crop_id"],
                seed_item_id=crop["seed_item_id"],
                harvest_item_id=crop["harvest_item_id"],
                growth_ticks_required=int(crop["growth_ticks_required"]),
                water_per_tick=float(crop["water_per_tick"]),
            )

        for structure in payload.get("structures", []):
            self.structure_definitions[structure["blueprint_id"]] = StructureDefinition(
                blueprint_id=structure["blueprint_id"],
                required_materials=dict(structure.get("required_materials", {})),
                max_health=float(structure["max_health"]),
                build_tags=list(structure.get("build_tags", [])),
            )

        for animal in payload.get("animals", []):
            self.animal_definitions[animal["species_id"]] = AnimalDefinition(
                species_id=animal["species_id"],
                habitat=AnimalHabitat(animal["habitat"]),
                max_health=float(animal["max_health"]),
                tame_difficulty=float(animal["tame_difficulty"]),
                base_ability_ids=list(animal.get("base_ability_ids", [])),
            )

        for ability in payload.get("animal_abilities", []):
            self.animal_ability_definitions[ability["ability_id"]] = AnimalAbilityDefinition(
                ability_id=ability["ability_id"],
                domain=AnimalAbilityDomain(ability["domain"]),
                modifiers=dict(ability.get("modifiers", {})),
            )

        for source in payload.get("power_sources", []):
            self.power_source_definitions[source["source_id"]] = PowerSourceDefinition(
                source_id=source["source_id"],
                generation=float(source["generation"]),
            )

        for device in payload.get("powered_devices", []):
            self.power_device_definitions[device["device_id"]] = PoweredDeviceDefinition(
                device_id=device["device_id"],
                consumption=float(device["consumption"]),
            )

        progression = payload.get("progression", {})
        self.progression_definition = ProgressionDefinition(
            levels=list(progression.get("levels", [])),
            zombie_tier_thresholds=dict(progression.get("zombie_tier_thresholds", {})),
        )

        economy = payload.get("economy", {"currency_id": "credits", "starting_balance": 0})
        self.economy_definition = EconomyDefinition(
            currency_id=economy["currency_id"],
            starting_balance=int(economy["starting_balance"]),
        )

        for tier in payload.get("zombie_tiers", []):
            self.zombie_tiers[tier["tier_id"]] = ZombieTierDefinition(
                tier_id=tier["tier_id"],
                display_name=tier["display_name"],
                sanity_drain_rate=float(tier["sanity_drain_rate"]),
                feeding_efficiency=float(tier["feeding_efficiency"]),
            )

        self.zombie_sanity_bands = [
            ZombieSanityBandDefinition(
                band_id=band["band_id"],
                minimum=float(band["minimum"]),
                maximum=float(band["maximum"]),
                human_coexistence_allowed=bool(band["human_coexistence_allowed"]),
                hostility_level=float(band["hostility_level"]),
                cure_eligible=bool(band["cure_eligible"]),
                mission_availability_tags=list(band.get("mission_availability_tags", [])),
                behavior_tags=list(band.get("behavior_tags", [])),
            )
            for band in payload.get("zombie_sanity_bands", [])
        ]

        self.mission_definitions = {
            mission["mission_id"]: MissionDefinition(
                mission_id=mission["mission_id"],
                audience=MissionAudience(mission["audience"]),
                objective_ids=list(mission.get("objective_ids", [])),
                reward_id=mission.get("reward_id", "reward_none"),
                prerequisite_ids=list(mission.get("prerequisite_ids", [])),
            )
            for mission in payload.get("missions", [])
        }

        survival = payload.get("survival_config", {})
        if survival:
            self.survival_config = SurvivalConfig(
                hunger_depletion_per_tick=float(survival["hunger_depletion_per_tick"]),
                thirst_depletion_per_tick=float(survival["thirst_depletion_per_tick"]),
                stamina_recovery_per_tick=float(survival["stamina_recovery_per_tick"]),
                starvation_threshold=float(survival["starvation_threshold"]),
                dehydration_threshold=float(survival["dehydration_threshold"]),
                starvation_damage_per_tick=float(survival["starvation_damage_per_tick"]),
                dehydration_damage_per_tick=float(survival["dehydration_damage_per_tick"]),
                zombie_hunger_depletion_per_tick=float(survival["zombie_hunger_depletion_per_tick"]),
                zombie_starvation_threshold=float(survival["zombie_starvation_threshold"]),
                zombie_starvation_damage_per_tick=float(survival["zombie_starvation_damage_per_tick"]),
                zombie_sleep_heal_per_tick=float(survival["zombie_sleep_heal_per_tick"]),
                food_degrade_per_tick=float(survival["food_degrade_per_tick"]),
            )

    def _build_test_world(self) -> None:
        container_defs = [
            LootContainerRuntime(
                container_id="container_a",
                definition=LootContainerDefinition(
                    container_type="locker",
                    container_tier_id="tier_1",
                    tier_weights={"tier_1": 1.0},
                    respawn_seconds=300,
                ),
                coordinate=WorldCoordinate(x=10.0, y=0.0, z=10.0),
            ),
            LootContainerRuntime(
                container_id="container_b",
                definition=LootContainerDefinition(
                    container_type="safe",
                    container_tier_id="tier_2",
                    tier_weights={"tier_2": 1.0},
                    respawn_seconds=600,
                ),
                coordinate=WorldCoordinate(x=80.0, y=0.0, z=5.0),
            ),
            LootContainerRuntime(
                container_id="container_c",
                definition=LootContainerDefinition(
                    container_type="vault",
                    container_tier_id="tier_3",
                    tier_weights={"tier_3": 1.0},
                    respawn_seconds=900,
                ),
                coordinate=WorldCoordinate(x=5.0, y=0.0, z=78.0),
            ),
        ]

        for container in container_defs:
            self.world.containers[container.container_id] = container

        chunk_containers: dict[str, list[str]] = {}
        for container in container_defs:
            address = self.grid_config.to_chunk_address(container.coordinate)
            chunk_key = self.chunk_key(address)
            chunk_containers.setdefault(chunk_key, []).append(container.container_id)

        for chunk_key, container_ids in chunk_containers.items():
            self.world.chunks[chunk_key] = WorldChunkRuntime(
                chunk_key=chunk_key,
                building_ids=[f"building_{chunk_key}"],
                container_ids=container_ids,
            )

        self.world.resource_nodes["node_scrap_1"] = ResourceNodeRuntime(
            node_id="node_scrap_1",
            node_type="scrap_pile",
            coordinate=WorldCoordinate(x=12.0, y=0.0, z=12.0),
            quantity=4,
            max_quantity=4,
            respawn_ticks=self.resource_node_definitions.get("scrap_pile", ResourceNodeDefinition("scrap_pile", "scrap_metal", 1, 3)).respawn_ticks,
        )
        self.world.resource_nodes["node_wood_1"] = ResourceNodeRuntime(
            node_id="node_wood_1",
            node_type="wood_stump",
            coordinate=WorldCoordinate(x=20.0, y=0.0, z=8.0),
            quantity=5,
            max_quantity=5,
            respawn_ticks=self.resource_node_definitions.get("wood_stump", ResourceNodeDefinition("wood_stump", "wood_log", 2, 2)).respawn_ticks,
        )

        self.world.gardens["garden_plot_a"] = GardenPlotRuntime(
            plot_id="garden_plot_a",
            coordinate=WorldCoordinate(x=6.0, y=0.0, z=6.0),
        )

        self.world.workbenches["bench_general_a"] = WorkbenchRuntime(
            workbench_id="bench_general_a",
            definition_id="wb_general",
            coordinate=WorldCoordinate(x=4.0, y=0.0, z=4.0),
            power_group_id="grid_a",
        )

        self.world.power_sources["source_generator_a"] = PowerSourceRuntime(
            source_instance_id="source_generator_a",
            definition_id="generator_small",
            power_group_id="grid_a",
            enabled=True,
        )
        self.world.powered_devices["device_fabricator_a"] = PoweredDeviceRuntime(
            device_instance_id="device_fabricator_a",
            definition_id="fabricator",
            power_group_id="grid_a",
            enabled=True,
        )

        wolf = self.animal_definitions.get("wolf")
        dolphin = self.animal_definitions.get("dolphin")
        infected_hound = self.animal_definitions.get("infected_hound")
        if wolf:
            self.world.animals["animal_wolf_1"] = AnimalRuntime(
                state=AnimalStateModel(
                    animal_id="animal_wolf_1",
                    species_id="wolf",
                    habitat=wolf.habitat,
                    infection_state=InfectionState.NORMAL,
                    tame_state=TameState.WILD,
                    ability_ids=list(wolf.base_ability_ids),
                ),
                coordinate=WorldCoordinate(x=14.0, y=0.0, z=14.0),
                health=wolf.max_health,
            )
        if dolphin:
            self.world.animals["animal_dolphin_1"] = AnimalRuntime(
                state=AnimalStateModel(
                    animal_id="animal_dolphin_1",
                    species_id="dolphin",
                    habitat=dolphin.habitat,
                    infection_state=InfectionState.NORMAL,
                    tame_state=TameState.WILD,
                    ability_ids=list(dolphin.base_ability_ids),
                ),
                coordinate=WorldCoordinate(x=70.0, y=-2.0, z=70.0),
                health=dolphin.max_health,
            )
        if infected_hound:
            self.world.animals["animal_hound_1"] = AnimalRuntime(
                state=AnimalStateModel(
                    animal_id="animal_hound_1",
                    species_id="infected_hound",
                    habitat=infected_hound.habitat,
                    infection_state=InfectionState.INFECTED,
                    tame_state=TameState.WILD,
                    ability_ids=list(infected_hound.base_ability_ids),
                ),
                coordinate=WorldCoordinate(x=16.0, y=0.0, z=15.0),
                health=infected_hound.max_health,
            )

        self.world.hordes["horde_alpha"] = HordeRuntime(horde_id="horde_alpha", leader_player_id=None)

        self.world.npcs["npc_survivor_a"] = NpcRuntime(
            npc_id="npc_survivor_a",
            npc_type="npc_human",
            coordinate=WorldCoordinate(x=2.0, y=0.0, z=2.0),
            settlement_id="settlement_alpha",
            shop_id="shop_alpha",
        )
        self.world.npcs["npc_zombie_a"] = NpcRuntime(
            npc_id="npc_zombie_a",
            npc_type="npc_zombie",
            coordinate=WorldCoordinate(x=18.0, y=0.0, z=18.0),
            settlement_id=None,
            shop_id=None,
        )

    @staticmethod
    def chunk_key(address) -> str:
        return f"{address.chunk_x}:{address.chunk_y}:{address.chunk_z}"

    def start(self) -> None:
        self._load_persisted_state()

    def shutdown(self) -> None:
        self.save_state()

    def join_player(self, player_id: str, form: PlayerForm, position: WorldCoordinate) -> None:
        if player_id in self.players:
            return

        state = PlayerStateModel(player_id=player_id, form=form)
        human_state = HumanRuntimeState(position=position)
        zombie_state = ZombieRuntimeState() if form == PlayerForm.ZOMBIE else None
        if zombie_state is not None:
            self._refresh_zombie_sanity_state(zombie_state)

        self.players[player_id] = AuthoritativePlayer(
            state=state,
            human_state=human_state,
            zombie_state=zombie_state,
            currency_balance=self.economy_definition.starting_balance,
        )
        self.mission_states.setdefault(player_id, {})

    def process_tick(self) -> None:
        self.command_results.clear()
        for intent in self.transport.drain_command_intents():
            self._apply_intent(intent)

        self._apply_survival_tick()
        self._update_world_systems()
        self._refresh_chunk_interest()
        self._replicate_state()
        self._tick_index += 1

    def save_state(self) -> None:
        player_payload: dict[str, dict] = {}
        inventory_payload: dict[str, dict] = {}
        equipment_payload: dict[str, dict] = {}
        progression_payload: dict[str, dict] = {}
        economy_payload: dict[str, dict] = {}
        missions_payload: dict[str, dict] = {}

        for player_id, player in self.players.items():
            player_payload[player_id] = {
                "state": {
                    "player_id": player.state.player_id,
                    "form": player.state.form.value,
                    "infection_progress": player.state.infection_progress,
                    "zombie_sanity": player.state.zombie_sanity,
                },
                "human_state": {
                    "stats": asdict(player.human_state.stats),
                    "position": asdict(player.human_state.position),
                    "movement_state": player.human_state.movement_state,
                    "dead": player.human_state.dead,
                },
                "zombie_state": self._serialize_zombie_state(player.zombie_state),
            }
            inventory_payload[player_id] = {
                "capacity_slots": player.inventory.capacity_slots,
                "stacks": [asdict(stack) for stack in player.inventory.stacks],
            }
            equipment_payload[player_id] = {
                "instances": {
                    key: {
                        "instance_id": instance.instance_id,
                        "item_id": instance.item_id,
                        "durability": instance.durability,
                        "max_durability": instance.max_durability,
                        "equipped": instance.equipped,
                    }
                    for key, instance in player.equipment_instances.items()
                },
                "equipped_weapon_instance_id": player.equipment.equipped_weapon_instance_id,
                "equipped_armor_instance_id": player.equipment.equipped_armor_instance_id,
            }
            progression_payload[player_id] = {
                "experience": player.human_state.stats.experience,
                "level": player.human_state.stats.level,
            }
            economy_payload[player_id] = {"currency_balance": player.currency_balance}
            missions_payload[player_id] = self._serialize_player_missions(player_id)

        world_payload = {
            "chunks": {
                key: {
                    "chunk_key": chunk.chunk_key,
                    "building_ids": chunk.building_ids,
                    "container_ids": chunk.container_ids,
                    "active": chunk.active,
                }
                for key, chunk in self.world.chunks.items()
            },
            "resource_nodes": {
                node_id: {
                    "node_id": node.node_id,
                    "node_type": node.node_type,
                    "coordinate": asdict(node.coordinate),
                    "quantity": node.quantity,
                    "max_quantity": node.max_quantity,
                    "respawn_ticks": node.respawn_ticks,
                    "depleted_ticks": node.depleted_ticks,
                }
                for node_id, node in self.world.resource_nodes.items()
            },
            "gardens": {
                plot_id: {
                    "plot_id": plot.plot_id,
                    "coordinate": asdict(plot.coordinate),
                    "planted_crop_id": plot.planted_crop_id,
                    "owner_player_id": plot.owner_player_id,
                    "growth_ticks": plot.growth_ticks,
                    "water": plot.water,
                    "plant_health": plot.plant_health,
                }
                for plot_id, plot in self.world.gardens.items()
            },
            "structures": {
                structure_id: {
                    "structure_id": structure.structure_id,
                    "blueprint_id": structure.blueprint_id,
                    "coordinate": asdict(structure.coordinate),
                    "orientation_yaw": structure.orientation_yaw,
                    "owner_player_id": structure.owner_player_id,
                    "health": structure.health,
                    "max_health": structure.max_health,
                    "state": structure.state,
                }
                for structure_id, structure in self.world.structures.items()
            },
            "destruction_records": [asdict(record) for record in self.world.destruction_records],
            "animals": {
                animal_id: {
                    "state": {
                        "animal_id": animal.state.animal_id,
                        "species_id": animal.state.species_id,
                        "habitat": animal.state.habitat.value,
                        "infection_state": animal.state.infection_state.value,
                        "tame_state": animal.state.tame_state.value,
                        "ability_ids": animal.state.ability_ids,
                    },
                    "coordinate": asdict(animal.coordinate),
                    "health": animal.health,
                    "owner_player_id": animal.owner_player_id,
                }
                for animal_id, animal in self.world.animals.items()
            },
            "hordes": {
                horde_id: {
                    "horde_id": horde.horde_id,
                    "leader_player_id": horde.leader_player_id,
                    "member_player_ids": sorted(horde.member_player_ids),
                }
                for horde_id, horde in self.world.hordes.items()
            },
            "power_sources": {
                source_id: {
                    "source_instance_id": source.source_instance_id,
                    "definition_id": source.definition_id,
                    "power_group_id": source.power_group_id,
                    "enabled": source.enabled,
                }
                for source_id, source in self.world.power_sources.items()
            },
            "powered_devices": {
                device_id: {
                    "device_instance_id": device.device_instance_id,
                    "definition_id": device.definition_id,
                    "power_group_id": device.power_group_id,
                    "enabled": device.enabled,
                    "powered": device.powered,
                }
                for device_id, device in self.world.powered_devices.items()
            },
            "npcs": {
                npc_id: {
                    "npc_id": npc.npc_id,
                    "npc_type": npc.npc_type,
                    "coordinate": asdict(npc.coordinate),
                    "settlement_id": npc.settlement_id,
                    "shop_id": npc.shop_id,
                }
                for npc_id, npc in self.world.npcs.items()
            },
            "workbenches": {
                workbench_id: {
                    "workbench_id": wb.workbench_id,
                    "definition_id": wb.definition_id,
                    "coordinate": asdict(wb.coordinate),
                    "power_group_id": wb.power_group_id,
                }
                for workbench_id, wb in self.world.workbenches.items()
            },
        }

        loot_payload = {
            container_id: {
                "container_type": container.definition.container_type,
                "container_tier_id": container.definition.container_tier_id,
                "tier_weights": container.definition.tier_weights,
                "respawn_seconds": container.definition.respawn_seconds,
                "coordinate": asdict(container.coordinate),
                "generated_items": [asdict(item) for item in container.generated_items],
                "looted": container.looted,
            }
            for container_id, container in self.world.containers.items()
        }

        self.repository.save_by_key("players", player_payload)
        self.repository.save_by_key("inventories", inventory_payload)
        self.repository.save_by_key("equipment", equipment_payload)
        self.repository.save_by_key("progression", progression_payload)
        self.repository.save_by_key("economy", economy_payload)
        self.repository.save_by_key("missions", missions_payload)
        self.repository.save_by_key("world", world_payload)
        self.repository.save_by_key("loot", loot_payload)

    def _load_persisted_state(self) -> None:
        player_payload = self.repository.load_by_key("players")
        inventory_payload = self.repository.load_by_key("inventories")
        equipment_payload = self.repository.load_by_key("equipment")
        progression_payload = self.repository.load_by_key("progression")
        economy_payload = self.repository.load_by_key("economy")
        missions_payload = self.repository.load_by_key("missions")
        world_payload = self.repository.load_by_key("world")
        loot_payload = self.repository.load_by_key("loot")

        for player_id, payload in player_payload.items():
            state_payload = payload["state"]
            human_payload = payload["human_state"]
            state = PlayerStateModel(
                player_id=state_payload["player_id"],
                form=PlayerForm(state_payload["form"]),
                infection_progress=float(state_payload.get("infection_progress", 0.0)),
                zombie_sanity=state_payload.get("zombie_sanity"),
            )
            human_state = HumanRuntimeState(
                stats=PlayerStats(**human_payload["stats"]),
                position=WorldCoordinate(**human_payload["position"]),
                movement_state=human_payload.get("movement_state", "idle"),
                dead=bool(human_payload.get("dead", False)),
            )
            inventory_source = inventory_payload.get(player_id, {"capacity_slots": 30, "stacks": []})
            inventory = Inventory(
                capacity_slots=inventory_source["capacity_slots"],
                stacks=[ItemStack(**stack) for stack in inventory_source.get("stacks", [])],
            )
            zombie_state = self._deserialize_zombie_state(payload.get("zombie_state"))

            player = AuthoritativePlayer(
                state=state,
                human_state=human_state,
                zombie_state=zombie_state,
                inventory=inventory,
                currency_balance=int(economy_payload.get(player_id, {}).get("currency_balance", self.economy_definition.starting_balance)),
            )

            equipment = equipment_payload.get(player_id, {})
            for instance_id, source in equipment.get("instances", {}).items():
                player.equipment_instances[instance_id] = EquipmentInstance(
                    instance_id=source["instance_id"],
                    item_id=source["item_id"],
                    durability=float(source["durability"]),
                    max_durability=float(source["max_durability"]),
                    equipped=bool(source.get("equipped", False)),
                )
            player.equipment = PlayerEquipmentState(
                equipped_weapon_instance_id=equipment.get("equipped_weapon_instance_id"),
                equipped_armor_instance_id=equipment.get("equipped_armor_instance_id"),
            )

            progression = progression_payload.get(player_id, {})
            player.human_state.stats.experience = int(progression.get("experience", player.human_state.stats.experience))
            player.human_state.stats.level = int(progression.get("level", player.human_state.stats.level))

            self.players[player_id] = player

            self.mission_states[player_id] = {}
            for mission_id, mission_payload in missions_payload.get(player_id, {}).items():
                self.mission_states[player_id][mission_id] = MissionRuntimeState(
                    accepted=bool(mission_payload.get("accepted", False)),
                    completed=bool(mission_payload.get("completed", False)),
                    completed_objective_ids=set(mission_payload.get("completed_objective_ids", [])),
                )

        for key, payload in world_payload.get("chunks", {}).items():
            if key in self.world.chunks:
                self.world.chunks[key].active = bool(payload.get("active", False))

        for container_id, payload in loot_payload.items():
            if container_id not in self.world.containers:
                continue
            container = self.world.containers[container_id]
            container.generated_items = [ItemStack(**item) for item in payload.get("generated_items", [])]
            container.looted = bool(payload.get("looted", False))

        for node_id, payload in world_payload.get("resource_nodes", {}).items():
            if node_id in self.world.resource_nodes:
                node = self.world.resource_nodes[node_id]
                node.quantity = int(payload.get("quantity", node.quantity))
                node.depleted_ticks = int(payload.get("depleted_ticks", node.depleted_ticks))

        for plot_id, payload in world_payload.get("gardens", {}).items():
            if plot_id in self.world.gardens:
                plot = self.world.gardens[plot_id]
                plot.planted_crop_id = payload.get("planted_crop_id")
                plot.owner_player_id = payload.get("owner_player_id")
                plot.growth_ticks = int(payload.get("growth_ticks", plot.growth_ticks))
                plot.water = float(payload.get("water", plot.water))
                plot.plant_health = float(payload.get("plant_health", plot.plant_health))

        for structure_id, payload in world_payload.get("structures", {}).items():
            self.world.structures[structure_id] = StructureRuntime(
                structure_id=payload["structure_id"],
                blueprint_id=payload["blueprint_id"],
                coordinate=WorldCoordinate(**payload["coordinate"]),
                orientation_yaw=float(payload.get("orientation_yaw", 0.0)),
                owner_player_id=payload["owner_player_id"],
                health=float(payload["health"]),
                max_health=float(payload["max_health"]),
                state=payload.get("state", "completed"),
            )

        self.world.destruction_records = [
            DestructionRuntimeRecord(
                target_id=record["target_id"],
                source_actor_id=record["source_actor_id"],
                damage=float(record["damage"]),
            )
            for record in world_payload.get("destruction_records", [])
        ]

        for animal_id, payload in world_payload.get("animals", {}).items():
            source_state = payload["state"]
            self.world.animals[animal_id] = AnimalRuntime(
                state=AnimalStateModel(
                    animal_id=source_state["animal_id"],
                    species_id=source_state["species_id"],
                    habitat=AnimalHabitat(source_state["habitat"]),
                    infection_state=InfectionState(source_state["infection_state"]),
                    tame_state=TameState(source_state["tame_state"]),
                    ability_ids=list(source_state.get("ability_ids", [])),
                ),
                coordinate=WorldCoordinate(**payload["coordinate"]),
                health=float(payload["health"]),
                owner_player_id=payload.get("owner_player_id"),
            )

        for horde_id, payload in world_payload.get("hordes", {}).items():
            self.world.hordes[horde_id] = HordeRuntime(
                horde_id=payload["horde_id"],
                leader_player_id=payload.get("leader_player_id"),
                member_player_ids=set(payload.get("member_player_ids", [])),
            )

        for source_id, payload in world_payload.get("power_sources", {}).items():
            if source_id in self.world.power_sources:
                self.world.power_sources[source_id].enabled = bool(payload.get("enabled", True))

        for device_id, payload in world_payload.get("powered_devices", {}).items():
            if device_id in self.world.powered_devices:
                self.world.powered_devices[device_id].enabled = bool(payload.get("enabled", True))
                self.world.powered_devices[device_id].powered = bool(payload.get("powered", False))

    def _serialize_zombie_state(self, zombie_state: ZombieRuntimeState | None) -> dict | None:
        if zombie_state is None:
            return None
        return {
            "feeding_state": zombie_state.feeding_state,
            "hunger": zombie_state.hunger,
            "sleeping": zombie_state.sleeping,
            "sanity": {
                "value": zombie_state.sanity.value,
                "minimum": zombie_state.sanity.minimum,
                "maximum": zombie_state.sanity.maximum,
            },
            "sanity_band_id": zombie_state.sanity_band_id,
            "behavior_tags": zombie_state.behavior_tags,
            "tier_id": zombie_state.tier_id,
            "mission_eligible": zombie_state.mission_eligible,
            "health": zombie_state.health,
            "dead": zombie_state.dead,
        }

    def _deserialize_zombie_state(self, payload: dict | None) -> ZombieRuntimeState | None:
        if payload is None:
            return None
        return ZombieRuntimeState(
            feeding_state=payload.get("feeding_state", "idle"),
            hunger=float(payload.get("hunger", 0.0)),
            sleeping=bool(payload.get("sleeping", False)),
            sanity=ZombieSanityState(**payload.get("sanity", {"value": 50.0})),
            sanity_band_id=payload.get("sanity_band_id", "volatile"),
            behavior_tags=list(payload.get("behavior_tags", ["aggressive"])),
            tier_id=payload.get("tier_id", "z_tier_1"),
            mission_eligible=bool(payload.get("mission_eligible", True)),
            health=float(payload.get("health", 100.0)),
            dead=bool(payload.get("dead", False)),
        )

    def _serialize_player_missions(self, player_id: str) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for mission_id, mission in self.mission_states.get(player_id, {}).items():
            result[mission_id] = {
                "accepted": mission.accepted,
                "completed": mission.completed,
                "completed_objective_ids": sorted(mission.completed_objective_ids),
            }
        return result

    def _apply_intent(self, intent: ClientCommandIntent) -> None:
        result = {
            "command_id": intent.command_id,
            "player_id": intent.player_id,
            "topic": intent.topic,
            "accepted": False,
            "reason": "",
        }
        player = self.players.get(intent.player_id)
        if player is None:
            result["reason"] = "player_not_found"
            self.command_results.append(result)
            return

        handlers = {
            "player.move": self._handle_move,
            "player.interact": self._handle_interact,
            "player.infect": self._handle_infect,
            "zombie.feed": self._handle_zombie_feed,
            "zombie.sleep": self._handle_zombie_sleep,
            "player.inventory_action": self._handle_inventory_action,
            "player.use_item": self._handle_use_item,
            "player.equip": self._handle_equip,
            "mission.accept": self._handle_mission_accept,
            "mission.progress": self._handle_mission_progress,
            "crafting.start": self._handle_crafting,
            "gather.resource": self._handle_gather,
            "garden.action": self._handle_garden_action,
            "structure.build": self._handle_structure_build,
            "structure.damage": self._handle_structure_damage,
            "animal.tame": self._handle_animal_tame,
            "horde.membership": self._handle_horde_membership,
            "economy.mutate": self._handle_economy_mutation,
            "power.source_toggle": self._handle_power_toggle,
            "animal.use_ability": self._handle_animal_ability,
        }

        handler = handlers.get(intent.topic)
        if handler is None:
            result["reason"] = "unknown_topic"
            self.command_results.append(result)
            return

        accepted, reason = handler(player, intent.payload)
        result["accepted"] = accepted
        result["reason"] = reason
        self.command_results.append(result)

    def _handle_move(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        try:
            position = WorldCoordinate(
                x=float(payload.get("target_x", player.human_state.position.x)),
                y=float(payload.get("target_y", player.human_state.position.y)),
                z=float(payload.get("target_z", player.human_state.position.z)),
            )
        except (TypeError, ValueError):
            return False, "invalid_position_payload"

        if not self.grid_config.supports_vertical_coordinate(position.y):
            return False, "position_out_of_world_bounds"

        player.human_state.position = position
        player.human_state.movement_state = str(payload.get("movement_state", "moving"))

        stamina_cost = float(payload.get("stamina_cost", 1.0))
        player.human_state.stats.spend_stamina(max(0.0, stamina_cost))
        return True, "ok"

    def _handle_infect(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        target_value = payload.get("target_form")
        if not isinstance(target_value, str):
            return False, "missing_target_form"

        try:
            target_form = PlayerForm(target_value)
        except ValueError:
            return False, "invalid_target_form"

        cure_available = bool(payload.get("cure_available", False))

        if player.state.form == PlayerForm.ZOMBIE and target_form == PlayerForm.HUMAN and not cure_available:
            return False, "cure_required"

        if not is_valid_form_transition(player.state.form, target_form, cure_available=cure_available):
            return False, "invalid_form_transition"

        infection_progress = player.state.infection_progress
        zombie_sanity = player.state.zombie_sanity
        if target_form == PlayerForm.INFECTED_HUMAN:
            infection_progress = max(0.1, infection_progress)
            zombie_sanity = None
        elif target_form == PlayerForm.ZOMBIE:
            infection_progress = 1.0
            zombie_sanity = player.zombie_state.sanity.value if player.zombie_state else 50.0
            if player.zombie_state is None:
                player.zombie_state = ZombieRuntimeState()
            self._refresh_zombie_sanity_state(player.zombie_state)
        elif target_form == PlayerForm.HUMAN:
            infection_progress = 0.0
            zombie_sanity = None
            if player.zombie_state is not None:
                player.zombie_state.sleeping = False

        player.state = PlayerStateModel(
            player_id=player.state.player_id,
            form=target_form,
            infection_progress=infection_progress,
            zombie_sanity=zombie_sanity,
        )
        return True, "ok"

    def _handle_zombie_feed(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        if player.state.form != PlayerForm.ZOMBIE:
            return False, "player_not_zombie"
        if player.zombie_state is None:
            player.zombie_state = ZombieRuntimeState()

        sanity_gain = float(payload.get("sanity_gain", 12.0))
        health_gain = float(payload.get("health_gain", 6.0))
        hunger_recovery = float(payload.get("hunger_recovery", 30.0))

        player.zombie_state.feeding_state = "feeding"
        player.zombie_state.hunger = max(0.0, player.zombie_state.hunger - max(0.0, hunger_recovery))
        player.zombie_state.sanity.apply_delta(sanity_gain)
        player.zombie_state.health = min(100.0, player.zombie_state.health + max(0.0, health_gain))
        player.zombie_state.sleeping = False
        self._refresh_zombie_sanity_state(player.zombie_state)

        self._progress_mission_objective(player.state.player_id, "mission_zombie_feed_target", "feed_once")
        self._record_progression(player, xp_gain=10)
        return True, "ok"

    def _handle_zombie_sleep(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        if player.state.form != PlayerForm.ZOMBIE:
            return False, "player_not_zombie"
        if player.zombie_state is None:
            player.zombie_state = ZombieRuntimeState()
        sleeping = bool(payload.get("sleeping", True))
        player.zombie_state.sleeping = sleeping
        return True, "ok"

    def _handle_inventory_action(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        action = payload.get("action")
        item_id = payload.get("item_id")
        quantity = int(payload.get("quantity", 0))
        if not isinstance(item_id, str) or quantity <= 0:
            return False, "invalid_inventory_payload"

        if action == "remove":
            removed = player.inventory.remove_item(item_id=item_id, quantity=quantity)
            if not removed:
                return False, "insufficient_items"
            return True, "ok"

        if action == "add":
            definition = self._item_definition_for(item_id)
            overflow = player.inventory.add_item(definition=definition, quantity=quantity)
            if overflow > 0:
                return False, "inventory_full"
            return True, "ok"

        return False, "unsupported_inventory_action"

    def _handle_use_item(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        item_id = payload.get("item_id")
        if not isinstance(item_id, str):
            return False, "missing_item_id"

        if item_id in self.food_definitions:
            if not player.inventory.remove_item(item_id, 1):
                return False, "insufficient_items"
            if self._is_food_spoiled(item_id):
                return False, "food_spoiled"
            food = self.food_definitions[item_id]
            player.human_state.stats.hunger = max(0.0, player.human_state.stats.hunger - food.hunger_restore)
            player.human_state.stats.heal(food.health_restore)
            self._record_progression(player, xp_gain=3)
            self._progress_mission_objective(player.state.player_id, "mission_human_survive_cycle", "consume_food")
            return True, "ok"

        if item_id in self.medicine_definitions:
            if not player.inventory.remove_item(item_id, 1):
                return False, "insufficient_items"
            med = self.medicine_definitions[item_id]
            if player.state.form == PlayerForm.ZOMBIE and player.zombie_state is not None:
                player.zombie_state.sanity.apply_delta(med.zombie_sanity_delta)
                self._refresh_zombie_sanity_state(player.zombie_state)
            player.human_state.stats.heal(med.health_restore)
            if med.cure_progress_delta < 0 and player.state.form == PlayerForm.ZOMBIE and player.zombie_state:
                pass
            if med.cure_progress_delta > 0 and player.state.form in {PlayerForm.INFECTED_HUMAN, PlayerForm.ZOMBIE}:
                new_progress = max(0.0, player.state.infection_progress - med.cure_progress_delta)
                player.state = PlayerStateModel(
                    player_id=player.state.player_id,
                    form=player.state.form,
                    infection_progress=new_progress,
                    zombie_sanity=player.state.zombie_sanity,
                )
            self._record_progression(player, xp_gain=5)
            return True, "ok"

        return False, "item_not_usable"

    def _handle_equip(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        action = payload.get("action", "equip")
        item_id = payload.get("item_id")
        if action == "unequip":
            slot = payload.get("slot")
            if slot == "weapon":
                player.equipment.equipped_weapon_instance_id = None
                return True, "ok"
            if slot == "armor":
                player.equipment.equipped_armor_instance_id = None
                return True, "ok"
            return False, "invalid_slot"

        if not isinstance(item_id, str):
            return False, "missing_item_id"

        if item_id in self.weapon_definitions:
            instance = self._ensure_equipment_instance(player, item_id)
            if not instance.usable:
                return False, "item_unusable"
            player.equipment.equipped_weapon_instance_id = instance.instance_id
            instance.equipped = True
            return True, "ok"

        if item_id in self.armor_definitions:
            instance = self._ensure_equipment_instance(player, item_id)
            if not instance.usable:
                return False, "item_unusable"
            player.equipment.equipped_armor_instance_id = instance.instance_id
            instance.equipped = True
            return True, "ok"

        return False, "item_not_equippable"

    def _handle_interact(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        action = payload.get("action")
        if action == "loot_container":
            container_id = payload.get("container_id")
            if not isinstance(container_id, str):
                return False, "missing_container_id"
            return self._loot_container(player, container_id)

        if action == "attack_player":
            target_player_id = payload.get("target_player_id")
            if not isinstance(target_player_id, str):
                return False, "missing_target"
            target = self.players.get(target_player_id)
            if target is None:
                return False, "target_not_found"
            if not self._within_range(player.human_state.position, target.human_state.position, max_distance=4.0):
                return False, "target_out_of_range"
            if player.state.form != PlayerForm.ZOMBIE and player.equipment.equipped_weapon_instance_id is None:
                return False, "no_attack_capability"
            damage = self._resolve_attack_damage(player, payload)
            mitigated = self._apply_armor_and_damage(target, damage)
            if player.state.form == PlayerForm.ZOMBIE:
                infect = bool(payload.get("attempt_infect", False))
                if infect and target.state.form == PlayerForm.HUMAN and mitigated > 0:
                    target.state = PlayerStateModel(
                        player_id=target.state.player_id,
                        form=PlayerForm.INFECTED_HUMAN,
                        infection_progress=max(0.15, target.state.infection_progress),
                        zombie_sanity=None,
                    )
            self._record_progression(player, xp_gain=8)
            return True, "ok"

        if action == "attack_structure":
            structure_id = payload.get("structure_id")
            if not isinstance(structure_id, str):
                return False, "missing_structure_id"
            return self._damage_structure(player, structure_id, float(payload.get("damage", 10.0)))

        if action == "infect_animal":
            animal_id = payload.get("animal_id")
            if not isinstance(animal_id, str):
                return False, "missing_animal_id"
            if player.state.form != PlayerForm.ZOMBIE:
                return False, "player_not_zombie"
            animal = self.world.animals.get(animal_id)
            if animal is None:
                return False, "animal_not_found"
            animal.state = AnimalStateModel(
                animal_id=animal.state.animal_id,
                species_id=animal.state.species_id,
                habitat=animal.state.habitat,
                infection_state=InfectionState.INFECTED,
                tame_state=animal.state.tame_state,
                ability_ids=animal.state.ability_ids,
            )
            self._record_progression(player, xp_gain=6)
            return True, "ok"

        return False, "unsupported_interaction"

    def _handle_mission_accept(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        mission_id = payload.get("mission_id")
        if not isinstance(mission_id, str):
            return False, "missing_mission_id"

        mission = self.mission_definitions.get(mission_id)
        if mission is None:
            return False, "mission_not_found"

        if mission.audience == MissionAudience.HUMAN and player.state.form == PlayerForm.ZOMBIE:
            return False, "mission_audience_mismatch"
        if mission.audience == MissionAudience.ZOMBIE and player.state.form != PlayerForm.ZOMBIE:
            return False, "mission_audience_mismatch"

        state = self.mission_states.setdefault(player.state.player_id, {}).setdefault(mission_id, MissionRuntimeState())
        state.accepted = True
        return True, "ok"

    def _handle_mission_progress(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        mission_id = payload.get("mission_id")
        objective_id = payload.get("objective_id")
        if not isinstance(mission_id, str) or not isinstance(objective_id, str):
            return False, "invalid_mission_progress_payload"

        definition = self.mission_definitions.get(mission_id)
        if definition is None:
            return False, "mission_not_found"

        state = self.mission_states.setdefault(player.state.player_id, {}).setdefault(mission_id, MissionRuntimeState())
        if not state.accepted:
            return False, "mission_not_accepted"
        if objective_id not in definition.objective_ids:
            return False, "objective_not_in_mission"

        state.completed_objective_ids.add(objective_id)
        was_completed = state.completed
        state.completed = set(definition.objective_ids).issubset(state.completed_objective_ids)
        if state.completed and not was_completed:
            self._record_progression(player, xp_gain=30)
            player.currency_balance += 15
        return True, "ok"

    def _handle_crafting(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        recipe_id = payload.get("recipe_id")
        workbench_id = payload.get("workbench_id")
        if not isinstance(recipe_id, str):
            return False, "missing_recipe_id"
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            return False, "recipe_not_found"

        if recipe.required_workbench_id is not None:
            if not isinstance(workbench_id, str):
                return False, "workbench_required"
            wb = self.world.workbenches.get(workbench_id)
            if wb is None:
                return False, "workbench_not_found"
            if wb.definition_id != recipe.required_workbench_id:
                return False, "workbench_incompatible"
            if not self._within_range(player.human_state.position, wb.coordinate, max_distance=5.0):
                return False, "workbench_out_of_range"
            if self.workbench_definitions.get(wb.definition_id, WorkbenchDefinition(wb.definition_id, [], False)).power_required:
                if not self._is_power_group_sufficient(wb.power_group_id or ""):
                    return False, "insufficient_power"

        for item_id, quantity in recipe.input_item_quantities.items():
            if not self._has_item(player.inventory, item_id, quantity):
                return False, "insufficient_resources"

        for item_id, quantity in recipe.input_item_quantities.items():
            player.inventory.remove_item(item_id, quantity)

        for item_id, quantity in recipe.output_item_quantities.items():
            if item_id in self.weapon_definitions or item_id in self.armor_definitions:
                for _ in range(quantity):
                    self._create_equipment_instance(player, item_id)
            else:
                overflow = player.inventory.add_item(self._item_definition_for(item_id), quantity)
                if overflow > 0:
                    return False, "output_inventory_full"

        self._progress_mission_objective(player.state.player_id, "mission_human_craft_weapon", "craft_item")
        self._record_progression(player, xp_gain=20)
        return True, "ok"

    def _handle_gather(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        node_id = payload.get("node_id")
        if not isinstance(node_id, str):
            return False, "missing_node_id"
        node = self.world.resource_nodes.get(node_id)
        if node is None:
            return False, "node_not_found"
        if node.quantity <= 0:
            return False, "node_depleted"
        if not self._within_range(player.human_state.position, node.coordinate, max_distance=4.0):
            return False, "node_out_of_range"

        definition = self.resource_node_definitions.get(node.node_type)
        if definition is None:
            return False, "node_definition_not_found"

        bonus = self._animal_ability_modifier(player.state.player_id, AnimalAbilityDomain.RESOURCE_GATHERING, "yield_bonus")
        gather_amount = max(1, int(round(definition.yield_per_gather * (1.0 + bonus))))
        gathered = min(node.quantity, gather_amount)
        node.quantity -= gathered
        if node.quantity == 0:
            node.depleted_ticks = node.respawn_ticks

        overflow = player.inventory.add_item(self._item_definition_for(definition.yields_item_id), gathered)
        if overflow > 0:
            return False, "inventory_full"

        self._record_progression(player, xp_gain=7)
        self._progress_mission_objective(player.state.player_id, "mission_human_gather_resources", "gather_once")
        return True, "ok"

    def _handle_garden_action(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        action = payload.get("action")
        plot_id = payload.get("plot_id")
        if not isinstance(plot_id, str):
            return False, "missing_plot_id"

        plot = self.world.gardens.get(plot_id)
        if plot is None:
            return False, "plot_not_found"
        if not self._within_range(player.human_state.position, plot.coordinate, max_distance=4.0):
            return False, "plot_out_of_range"

        if action == "plant":
            crop_id = payload.get("crop_id")
            if not isinstance(crop_id, str):
                return False, "missing_crop_id"
            if plot.planted_crop_id is not None:
                return False, "plot_already_planted"
            crop = self.crop_definitions.get(crop_id)
            if crop is None:
                return False, "crop_not_found"
            if not player.inventory.remove_item(crop.seed_item_id, 1):
                return False, "missing_seed"
            plot.planted_crop_id = crop_id
            plot.owner_player_id = player.state.player_id
            plot.growth_ticks = 0
            plot.water = 20.0
            plot.plant_health = 100.0
            return True, "ok"

        if action == "water":
            amount = float(payload.get("amount", 10.0))
            plot.water = min(100.0, plot.water + max(0.0, amount))
            return True, "ok"

        if action == "harvest":
            if plot.planted_crop_id is None:
                return False, "nothing_planted"
            crop = self.crop_definitions.get(plot.planted_crop_id)
            if crop is None:
                return False, "crop_not_found"
            if plot.growth_ticks < crop.growth_ticks_required:
                return False, "crop_not_ready"
            if plot.plant_health <= 0:
                return False, "crop_dead"
            yield_bonus = self._animal_ability_modifier(player.state.player_id, AnimalAbilityDomain.GARDENING, "harvest_bonus")
            quantity = max(1, int(round(2 * (1.0 + yield_bonus))))
            overflow = player.inventory.add_item(self._item_definition_for(crop.harvest_item_id), quantity)
            if overflow > 0:
                return False, "inventory_full"
            plot.planted_crop_id = None
            plot.owner_player_id = None
            plot.growth_ticks = 0
            plot.water = 0.0
            plot.plant_health = 100.0
            self._record_progression(player, xp_gain=10)
            return True, "ok"

        return False, "unsupported_garden_action"

    def _handle_structure_build(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        if player.state.form == PlayerForm.ZOMBIE:
            return False, "zombie_cannot_build"

        blueprint_id = payload.get("blueprint_id")
        structure_id = payload.get("structure_id")
        if not isinstance(blueprint_id, str) or not isinstance(structure_id, str):
            return False, "invalid_build_payload"
        if structure_id in self.world.structures:
            return False, "structure_exists"

        definition = self.structure_definitions.get(blueprint_id)
        if definition is None:
            return False, "unknown_blueprint"

        for item_id, required in definition.required_materials.items():
            if not self._has_item(player.inventory, item_id, required):
                return False, "insufficient_materials"

        try:
            coordinate = WorldCoordinate(
                x=float(payload["x"]),
                y=float(payload["y"]),
                z=float(payload["z"]),
            )
        except (KeyError, TypeError, ValueError):
            return False, "invalid_coordinate"

        for item_id, required in definition.required_materials.items():
            player.inventory.remove_item(item_id, required)

        self.world.structures[structure_id] = StructureRuntime(
            structure_id=structure_id,
            blueprint_id=blueprint_id,
            coordinate=coordinate,
            orientation_yaw=float(payload.get("orientation_yaw", 0.0)),
            owner_player_id=player.state.player_id,
            health=definition.max_health,
            max_health=definition.max_health,
            state="completed",
        )
        self._record_progression(player, xp_gain=25)
        self._progress_mission_objective(player.state.player_id, "mission_human_survive_cycle", "build_structure")
        return True, "ok"

    def _handle_structure_damage(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        structure_id = payload.get("structure_id")
        if not isinstance(structure_id, str):
            return False, "missing_structure_id"
        damage = float(payload.get("damage", 10.0))
        return self._damage_structure(player, structure_id, damage)

    def _damage_structure(self, player: AuthoritativePlayer, structure_id: str, damage: float) -> tuple[bool, str]:
        structure = self.world.structures.get(structure_id)
        if structure is None:
            return False, "structure_not_found"
        if not self._within_range(player.human_state.position, structure.coordinate, max_distance=5.0):
            return False, "structure_out_of_range"

        structure.health = max(0.0, structure.health - max(0.0, damage))
        self.world.destruction_records.append(
            DestructionRuntimeRecord(target_id=structure_id, source_actor_id=player.state.player_id, damage=max(0.0, damage))
        )
        if structure.health == 0.0:
            structure.state = "destroyed"
            self._progress_mission_objective(player.state.player_id, "mission_zombie_destroy_structure", "destroy_once")
        return True, "ok"

    def _handle_animal_tame(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        animal_id = payload.get("animal_id")
        if not isinstance(animal_id, str):
            return False, "missing_animal_id"
        animal = self.world.animals.get(animal_id)
        if animal is None:
            return False, "animal_not_found"
        if not self._within_range(player.human_state.position, animal.coordinate, max_distance=4.0):
            return False, "animal_out_of_range"

        chance_bonus = float(payload.get("tame_bonus", 0.0))
        definition = self.animal_definitions.get(animal.state.species_id)
        if definition is None:
            return False, "animal_definition_not_found"

        effective = max(0.0, min(1.0, chance_bonus + (0.55 if animal.state.infection_state == InfectionState.NORMAL else 0.45)))
        if effective < definition.tame_difficulty:
            return False, "tame_failed"

        animal.state = AnimalStateModel(
            animal_id=animal.state.animal_id,
            species_id=animal.state.species_id,
            habitat=animal.state.habitat,
            infection_state=animal.state.infection_state,
            tame_state=TameState.TAMED,
            ability_ids=animal.state.ability_ids,
        )
        animal.owner_player_id = player.state.player_id
        self._record_progression(player, xp_gain=12)
        return True, "ok"

    def _handle_horde_membership(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        if player.state.form != PlayerForm.ZOMBIE:
            return False, "horde_requires_zombie"

        horde_id = payload.get("horde_id")
        action = payload.get("action")
        if not isinstance(horde_id, str):
            return False, "missing_horde_id"
        horde = self.world.hordes.get(horde_id)
        if horde is None:
            return False, "horde_not_found"

        if action == "join":
            horde.member_player_ids.add(player.state.player_id)
            if horde.leader_player_id is None:
                horde.leader_player_id = player.state.player_id
            return True, "ok"

        if action == "leave":
            horde.member_player_ids.discard(player.state.player_id)
            if horde.leader_player_id == player.state.player_id:
                horde.leader_player_id = next(iter(horde.member_player_ids), None)
            return True, "ok"

        return False, "unsupported_horde_action"

    def _handle_economy_mutation(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        action = payload.get("action")
        amount = int(payload.get("amount", 0))
        if amount <= 0:
            return False, "invalid_amount"

        if action == "earn":
            player.currency_balance += amount
            return True, "ok"

        if action == "spend":
            if player.currency_balance < amount:
                return False, "insufficient_currency"
            player.currency_balance -= amount
            return True, "ok"

        return False, "unsupported_economy_action"

    def _handle_power_toggle(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        source_instance_id = payload.get("source_instance_id")
        if not isinstance(source_instance_id, str):
            return False, "missing_source_id"
        source = self.world.power_sources.get(source_instance_id)
        if source is None:
            return False, "power_source_not_found"
        source.enabled = bool(payload.get("enabled", not source.enabled))
        return True, "ok"

    def _handle_animal_ability(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        animal_id = payload.get("animal_id")
        ability_id = payload.get("ability_id")
        if not isinstance(animal_id, str) or not isinstance(ability_id, str):
            return False, "invalid_ability_payload"
        animal = self.world.animals.get(animal_id)
        if animal is None:
            return False, "animal_not_found"
        if animal.owner_player_id != player.state.player_id:
            return False, "not_animal_owner"
        if ability_id not in animal.state.ability_ids:
            return False, "ability_not_available"
        ability = self.animal_ability_definitions.get(ability_id)
        if ability is None:
            return False, "ability_definition_not_found"

        if ability.domain == AnimalAbilityDomain.COMBAT:
            player.human_state.stats.recover_stamina(10.0)
        elif ability.domain == AnimalAbilityDomain.CRAFTING:
            player.currency_balance += int(ability.modifiers.get("craft_credit_bonus", 0.0))
        elif ability.domain == AnimalAbilityDomain.BUILDING:
            player.currency_balance += int(ability.modifiers.get("build_credit_bonus", 0.0))
        elif ability.domain == AnimalAbilityDomain.GARDENING:
            for plot in self.world.gardens.values():
                if plot.owner_player_id == player.state.player_id:
                    plot.plant_health = min(100.0, plot.plant_health + ability.modifiers.get("plant_health_bonus", 0.0))
        elif ability.domain == AnimalAbilityDomain.RESOURCE_GATHERING:
            pass
        return True, "ok"

    def _loot_container(self, player: AuthoritativePlayer, container_id: str) -> tuple[bool, str]:
        container = self.world.containers.get(container_id)
        if container is None:
            return False, "container_not_found"

        if not self._within_range(player.human_state.position, container.coordinate, max_distance=16.0):
            return False, "container_out_of_range"

        if not container.generated_items:
            seed = int(abs(player.human_state.position.x) + abs(player.human_state.position.z)) + len(container_id)
            generated = self.loot_generator.generate_loot_for_container(
                container.definition,
                self.tier_definitions,
                seed=seed,
            )
            container.generated_items = [
                ItemStack(item_id=str(item["item_id"]), quantity=int(item["quantity"])) for item in generated
            ]

        if container.looted:
            return False, "container_already_looted"

        for stack in container.generated_items:
            if stack.item_id in self.weapon_definitions or stack.item_id in self.armor_definitions:
                for _ in range(stack.quantity):
                    self._create_equipment_instance(player, stack.item_id)
            else:
                overflow = player.inventory.add_item(
                    definition=self._item_definition_for(stack.item_id),
                    quantity=stack.quantity,
                )
                if overflow > 0:
                    return False, "inventory_full"

        container.looted = True
        self._record_progression(player, xp_gain=8)
        return True, "ok"

    def _item_definition_for(self, item_id: str) -> ItemDefinition:
        from .enums import ItemCategory

        if item_id in self.item_definitions:
            item = self.item_definitions[item_id]
            category = item.category if isinstance(item.category, ItemCategory) else ItemCategory(item.category)
            return ItemDefinition(
                item_id=item.item_id,
                name=item.name,
                category=category,
                max_stack=item.max_stack,
                weight=item.weight,
            )

        category_map = {
            "pistol_9mm": ItemCategory.WEAPON,
            "weapon_blueprint_t1": ItemCategory.QUEST,
            "scrap_metal": ItemCategory.CRAFTING,
            "wood_log": ItemCategory.CRAFTING,
            "metal_plate": ItemCategory.CRAFTING,
            "canned_food": ItemCategory.FOOD,
            "cooked_meat": ItemCategory.FOOD,
            "armor_patch": ItemCategory.CLOTHING,
            "cosmetic_mask": ItemCategory.CLOTHING,
            "water_bottle": ItemCategory.WATER,
            "med_kit": ItemCategory.MEDICAL,
            "antiviral_serum": ItemCategory.MEDICAL,
        }
        return ItemDefinition(
            item_id=item_id,
            name=item_id.replace("_", " ").title(),
            category=category_map.get(item_id, ItemCategory.MISC),
            max_stack=10,
            weight=0.5,
        )

    def _ensure_equipment_instance(self, player: AuthoritativePlayer, item_id: str) -> EquipmentInstance:
        for instance in player.equipment_instances.values():
            if instance.item_id == item_id:
                return instance
        return self._create_equipment_instance(player, item_id)

    def _create_equipment_instance(self, player: AuthoritativePlayer, item_id: str) -> EquipmentInstance:
        self._instance_counter += 1
        instance_id = f"{item_id}_inst_{self._instance_counter}"
        instance = EquipmentInstance(
            instance_id=instance_id,
            item_id=item_id,
            durability=100.0,
            max_durability=100.0,
            equipped=False,
        )
        player.equipment_instances[instance_id] = instance
        return instance

    def _apply_survival_tick(self) -> None:
        for player in self.players.values():
            if player.state.form != PlayerForm.ZOMBIE:
                player.human_state.stats.consume_resources(
                    self.survival_config.hunger_depletion_per_tick,
                    self.survival_config.thirst_depletion_per_tick,
                )
                player.human_state.stats.recover_stamina(self.survival_config.stamina_recovery_per_tick)

                if player.human_state.stats.hunger >= self.survival_config.starvation_threshold:
                    player.human_state.stats.apply_damage(self.survival_config.starvation_damage_per_tick)
                if player.human_state.stats.thirst >= self.survival_config.dehydration_threshold:
                    player.human_state.stats.apply_damage(self.survival_config.dehydration_damage_per_tick)

                if player.human_state.stats.health <= 0:
                    player.human_state.dead = True
            else:
                if player.zombie_state is None:
                    player.zombie_state = ZombieRuntimeState()
                zombie = player.zombie_state
                zombie.hunger = min(100.0, zombie.hunger + self.survival_config.zombie_hunger_depletion_per_tick)
                if zombie.hunger >= self.survival_config.zombie_starvation_threshold:
                    zombie.health = max(0.0, zombie.health - self.survival_config.zombie_starvation_damage_per_tick)
                if zombie.sleeping:
                    zombie.health = min(100.0, zombie.health + self.survival_config.zombie_sleep_heal_per_tick)
                if zombie.health <= 0:
                    zombie.dead = True

                tier = self.zombie_tiers.get(zombie.tier_id)
                if tier is not None:
                    zombie.sanity.apply_delta(-tier.sanity_drain_rate)
                self._refresh_zombie_sanity_state(zombie)
                player.state = PlayerStateModel(
                    player_id=player.state.player_id,
                    form=player.state.form,
                    infection_progress=player.state.infection_progress,
                    zombie_sanity=zombie.sanity.value,
                )

            if player.state.form == PlayerForm.INFECTED_HUMAN:
                next_progress = min(1.0, player.state.infection_progress + 0.05)
                next_form = PlayerForm.ZOMBIE if next_progress >= 1.0 else PlayerForm.INFECTED_HUMAN
                player.state = PlayerStateModel(
                    player_id=player.state.player_id,
                    form=next_form,
                    infection_progress=next_progress,
                    zombie_sanity=player.state.zombie_sanity,
                )
                if next_form == PlayerForm.ZOMBIE and player.zombie_state is None:
                    player.zombie_state = ZombieRuntimeState()
                    self._refresh_zombie_sanity_state(player.zombie_state)

    def _refresh_zombie_sanity_state(self, zombie: ZombieRuntimeState) -> None:
        band = resolve_zombie_sanity_band(zombie.sanity.value, self.zombie_sanity_bands)
        if band is None:
            zombie.sanity_band_id = "volatile"
            zombie.behavior_tags = ["aggressive"]
            zombie.mission_eligible = zombie.sanity.value >= 20.0
            return
        zombie.sanity_band_id = band.band_id
        zombie.behavior_tags = list(band.behavior_tags)
        zombie.mission_eligible = bool(band.mission_availability_tags)

    def _update_world_systems(self) -> None:
        for node in self.world.resource_nodes.values():
            if node.quantity <= 0 and node.depleted_ticks > 0:
                node.depleted_ticks -= 1
                if node.depleted_ticks == 0:
                    node.quantity = node.max_quantity

        for plot in self.world.gardens.values():
            if plot.planted_crop_id is None:
                continue
            crop = self.crop_definitions.get(plot.planted_crop_id)
            if crop is None:
                continue
            plot.water = max(0.0, plot.water - crop.water_per_tick)
            if plot.water <= 0.0:
                plot.plant_health = max(0.0, plot.plant_health - 5.0)
            else:
                plot.growth_ticks += 1

        self._update_power_state()

    def _update_power_state(self) -> None:
        generation_by_group: dict[str, float] = {}
        for source in self.world.power_sources.values():
            if not source.enabled:
                continue
            definition = self.power_source_definitions.get(source.definition_id)
            if definition is None:
                continue
            generation_by_group[source.power_group_id] = generation_by_group.get(source.power_group_id, 0.0) + definition.generation

        consumption_by_group: dict[str, float] = {}
        for device in self.world.powered_devices.values():
            if not device.enabled:
                continue
            definition = self.power_device_definitions.get(device.definition_id)
            if definition is None:
                continue
            consumption_by_group[device.power_group_id] = consumption_by_group.get(device.power_group_id, 0.0) + definition.consumption

        for device in self.world.powered_devices.values():
            if not device.enabled:
                device.powered = False
                continue
            available = generation_by_group.get(device.power_group_id, 0.0)
            required = consumption_by_group.get(device.power_group_id, 0.0)
            device.powered = available >= required and required > 0.0

    def _resolve_attack_damage(self, attacker: AuthoritativePlayer, payload: dict) -> float:
        if attacker.state.form == PlayerForm.ZOMBIE:
            return float(payload.get("damage", 12.0))

        instance_id = attacker.equipment.equipped_weapon_instance_id
        if instance_id is None:
            return float(payload.get("damage", 2.0))
        instance = attacker.equipment_instances.get(instance_id)
        if instance is None or not instance.usable:
            return 0.0
        definition = self.weapon_definitions.get(instance.item_id)
        if definition is None:
            return float(payload.get("damage", 2.0))

        if not attacker.human_state.stats.spend_stamina(definition.stamina_cost):
            return 0.0

        if definition.ammo_per_attack > 0 and not attacker.inventory.remove_item("ammo_9mm", definition.ammo_per_attack):
            return 0.0

        instance.durability = max(0.0, instance.durability - definition.durability_loss)
        return definition.damage

    def _apply_armor_and_damage(self, target: AuthoritativePlayer, incoming_damage: float) -> float:
        damage = max(0.0, incoming_damage)
        armor_instance_id = target.equipment.equipped_armor_instance_id
        if armor_instance_id is not None:
            instance = target.equipment_instances.get(armor_instance_id)
            if instance is not None and instance.usable:
                definition = self.armor_definitions.get(instance.item_id)
                if definition is not None:
                    mitigated = damage * definition.mitigation
                    damage = max(0.0, damage - mitigated)
                    instance.durability = max(0.0, instance.durability - incoming_damage * definition.durability_loss_factor)

        target.human_state.stats.apply_damage(damage)
        if target.human_state.stats.health <= 0:
            target.human_state.dead = True
        return damage

    def _progress_mission_objective(self, player_id: str, mission_id: str, objective_id: str) -> None:
        definition = self.mission_definitions.get(mission_id)
        if definition is None or objective_id not in definition.objective_ids:
            return
        state = self.mission_states.setdefault(player_id, {}).setdefault(mission_id, MissionRuntimeState())
        if not state.accepted:
            return
        state.completed_objective_ids.add(objective_id)
        state.completed = set(definition.objective_ids).issubset(state.completed_objective_ids)

    def _record_progression(self, player: AuthoritativePlayer, xp_gain: int) -> None:
        player.human_state.stats.add_experience(xp_gain)
        if player.state.form == PlayerForm.ZOMBIE and player.zombie_state is not None:
            for tier_id, threshold in sorted(self.progression_definition.zombie_tier_thresholds.items(), key=lambda x: x[1]):
                if player.human_state.stats.level >= threshold:
                    player.zombie_state.tier_id = tier_id

    def _has_item(self, inventory: Inventory, item_id: str, quantity: int) -> bool:
        available = sum(stack.quantity for stack in inventory.stacks if stack.item_id == item_id)
        return available >= quantity

    def _is_food_spoiled(self, item_id: str) -> bool:
        # deterministic spoilage approximation based on runtime ticks and configured degradation
        if self.survival_config.food_degrade_per_tick <= 0:
            return False
        spoil_ticks = int(100 / self.survival_config.food_degrade_per_tick)
        return self._tick_index > spoil_ticks and item_id in self.food_definitions

    @staticmethod
    def _distance(a: WorldCoordinate, b: WorldCoordinate) -> float:
        dx = a.x - b.x
        dy = a.y - b.y
        dz = a.z - b.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5

    def _within_range(self, a: WorldCoordinate, b: WorldCoordinate, max_distance: float) -> bool:
        return self._distance(a, b) <= max_distance

    def _player_required_chunks(self, player: AuthoritativePlayer) -> list[str]:
        center = self.grid_config.to_chunk_address(player.human_state.position)
        required: list[str] = []
        for offset_x in range(-self.interest_radius_chunks, self.interest_radius_chunks + 1):
            for offset_z in range(-self.interest_radius_chunks, self.interest_radius_chunks + 1):
                required.append(f"{center.chunk_x + offset_x}:{center.chunk_y}:{center.chunk_z + offset_z}")
        return required

    def _refresh_chunk_interest(self) -> None:
        required_for_all: set[str] = set()
        for player in self.players.values():
            required_for_all.update(self._player_required_chunks(player))

        for chunk_key in required_for_all:
            chunk = self.world.chunks.setdefault(chunk_key, WorldChunkRuntime(chunk_key=chunk_key))
            chunk.active = True

        for key, chunk in self.world.chunks.items():
            if key not in required_for_all:
                chunk.active = False

    def _is_power_group_sufficient(self, power_group_id: str) -> bool:
        available = 0.0
        required = 0.0
        for source in self.world.power_sources.values():
            if source.power_group_id == power_group_id and source.enabled:
                definition = self.power_source_definitions.get(source.definition_id)
                if definition:
                    available += definition.generation
        for device in self.world.powered_devices.values():
            if device.power_group_id == power_group_id and device.enabled:
                definition = self.power_device_definitions.get(device.definition_id)
                if definition:
                    required += definition.consumption
        return available >= required and required > 0

    def _animal_ability_modifier(self, owner_player_id: str, domain: AnimalAbilityDomain, key: str) -> float:
        modifier = 0.0
        for animal in self.world.animals.values():
            if animal.owner_player_id != owner_player_id:
                continue
            for ability_id in animal.state.ability_ids:
                ability = self.animal_ability_definitions.get(ability_id)
                if ability is None or ability.domain != domain:
                    continue
                modifier += float(ability.modifiers.get(key, 0.0))
        return modifier

    def _replicate_state(self) -> None:
        for player_id, player in self.players.items():
            visible_chunk_keys = set(self._player_required_chunks(player))
            visible_players = [
                self._player_snapshot_payload(other)
                for other in self.players.values()
                if self.chunk_key(self.grid_config.to_chunk_address(other.human_state.position)) in visible_chunk_keys
            ]

            visible_animals = {
                animal_id: self._animal_snapshot(animal)
                for animal_id, animal in self.world.animals.items()
                if self.chunk_key(self.grid_config.to_chunk_address(animal.coordinate)) in visible_chunk_keys
            }

            visible_structures = {
                structure_id: {
                    "blueprint_id": structure.blueprint_id,
                    "state": structure.state,
                    "health": structure.health,
                    "position": asdict(structure.coordinate),
                }
                for structure_id, structure in self.world.structures.items()
                if self.chunk_key(self.grid_config.to_chunk_address(structure.coordinate)) in visible_chunk_keys
            }

            visible_resources = {
                node_id: {
                    "node_type": node.node_type,
                    "quantity": node.quantity,
                    "position": asdict(node.coordinate),
                }
                for node_id, node in self.world.resource_nodes.items()
                if self.chunk_key(self.grid_config.to_chunk_address(node.coordinate)) in visible_chunk_keys
            }

            payload = {
                "player_id": player_id,
                "state": self._player_snapshot_payload(player),
                "visible_players": visible_players,
                "active_chunks": sorted(
                    key
                    for key in visible_chunk_keys
                    if self.world.chunks.get(key, WorldChunkRuntime(key)).active
                ),
                "containers": {
                    container_id: {
                        "looted": container.looted,
                        "generated_items": [asdict(stack) for stack in container.generated_items],
                    }
                    for container_id, container in self.world.containers.items()
                    if self.chunk_key(self.grid_config.to_chunk_address(container.coordinate)) in visible_chunk_keys
                },
                "inventory": {
                    "stacks": [asdict(stack) for stack in player.inventory.stacks],
                    "equipment": {
                        "weapon": player.equipment.equipped_weapon_instance_id,
                        "armor": player.equipment.equipped_armor_instance_id,
                    },
                },
                "missions": self._serialize_player_missions(player_id),
                "animals": visible_animals,
                "structures": visible_structures,
                "resource_nodes": visible_resources,
                "gardens": {
                    plot_id: {
                        "planted_crop_id": plot.planted_crop_id,
                        "growth_ticks": plot.growth_ticks,
                        "water": plot.water,
                        "plant_health": plot.plant_health,
                    }
                    for plot_id, plot in self.world.gardens.items()
                    if self.chunk_key(self.grid_config.to_chunk_address(plot.coordinate)) in visible_chunk_keys
                },
                "power": {
                    "sources": {
                        source_id: {"enabled": source.enabled, "group": source.power_group_id}
                        for source_id, source in self.world.power_sources.items()
                    },
                    "devices": {
                        device_id: {"enabled": device.enabled, "powered": device.powered, "group": device.power_group_id}
                        for device_id, device in self.world.powered_devices.items()
                    },
                },
                "hordes": {
                    horde_id: {
                        "leader_player_id": horde.leader_player_id,
                        "member_player_ids": sorted(horde.member_player_ids),
                    }
                    for horde_id, horde in self.world.hordes.items()
                },
                "economy": {
                    "currency_id": self.economy_definition.currency_id,
                    "balance": player.currency_balance,
                },
                "npcs": {
                    npc_id: {
                        "npc_type": npc.npc_type,
                        "position": asdict(npc.coordinate),
                        "settlement_id": npc.settlement_id,
                        "shop_id": npc.shop_id,
                    }
                    for npc_id, npc in self.world.npcs.items()
                },
            }
            self.transport.push_snapshot(player_id, payload)

    def _animal_snapshot(self, animal: AnimalRuntime) -> dict:
        return {
            "animal_id": animal.state.animal_id,
            "species_id": animal.state.species_id,
            "tame_state": animal.state.tame_state.value,
            "infection_state": animal.state.infection_state.value,
            "owner_player_id": animal.owner_player_id,
            "health": animal.health,
            "habitat": animal.state.habitat.value,
            "abilities": animal.state.ability_ids,
            "position": asdict(animal.coordinate),
        }

    def _player_snapshot_payload(self, player: AuthoritativePlayer) -> dict:
        mission_state = {
            mission_id: {
                "accepted": state.accepted,
                "completed": state.completed,
                "completed_objective_ids": sorted(state.completed_objective_ids),
            }
            for mission_id, state in self.mission_states.get(player.state.player_id, {}).items()
        }

        return {
            "player_id": player.state.player_id,
            "form": player.state.form.value,
            "infection_progress": player.state.infection_progress,
            "zombie_sanity": player.state.zombie_sanity,
            "health": player.human_state.stats.health,
            "stamina": player.human_state.stats.stamina,
            "hunger": player.human_state.stats.hunger,
            "thirst": player.human_state.stats.thirst,
            "dead": player.human_state.dead,
            "position": asdict(player.human_state.position),
            "inventory_total_items": player.inventory.total_items(),
            "zombie_state": self._serialize_zombie_state(player.zombie_state),
            "missions": mission_state,
            "progression": {
                "experience": player.human_state.stats.experience,
                "level": player.human_state.stats.level,
            },
            "economy": {
                "currency_id": self.economy_definition.currency_id,
                "balance": player.currency_balance,
            },
        }
