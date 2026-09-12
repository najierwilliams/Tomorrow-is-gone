from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .inventory import Inventory
from .items import ItemStack
from .phase15_contracts import (
    ClientCommandIntent,
    LootContainerDefinition,
    LootGenerationPort,
    LootTierDefinition,
    MissionAudience,
    MissionDefinition,
    PersistentStateRepository,
    PlayerForm,
    PlayerStateModel,
    ServerConfiguration,
    ServerRuleSet,
    WorldCoordinate,
    WorldGridConfig,
    ZombieSanityState,
    is_valid_form_transition,
)
from .player import PlayerStats


@dataclass
class HumanRuntimeState:
    stats: PlayerStats = field(default_factory=PlayerStats)
    position: WorldCoordinate = field(default_factory=lambda: WorldCoordinate(x=0.0, y=0.0, z=0.0))
    movement_state: str = "idle"


@dataclass
class ZombieRuntimeState:
    feeding_state: str = "idle"
    sanity: ZombieSanityState = field(default_factory=lambda: ZombieSanityState(value=50.0))
    tier_id: str = "z_tier_1"
    mission_eligible: bool = True
    health: float = 100.0


@dataclass
class MissionRuntimeState:
    accepted: bool = False
    completed: bool = False
    completed_objective_ids: set[str] = field(default_factory=set)


@dataclass
class AuthoritativePlayer:
    state: PlayerStateModel
    human_state: HumanRuntimeState
    zombie_state: ZombieRuntimeState | None = None
    inventory: Inventory = field(default_factory=lambda: Inventory(capacity_slots=20))


@dataclass
class LootContainerRuntime:
    container_id: str
    definition: LootContainerDefinition
    coordinate: WorldCoordinate
    generated_items: list[ItemStack] = field(default_factory=list)
    looted: bool = False


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
        grid_config: WorldGridConfig | None = None,
        interest_radius_chunks: int = 1,
    ) -> None:
        self.repository = repository
        self.transport = transport
        self.loot_generator = loot_generator
        self.grid_config = grid_config or WorldGridConfig(
            chunk_size_meters=64,
            chunks_per_region=8,
            chunk_height_meters=32,
            chunks_per_vertical_region=8,
            minimum_world_y_meters=-64,
            maximum_world_y_meters=128,
        )
        self.interest_radius_chunks = interest_radius_chunks

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

        self.tier_definitions: dict[str, LootTierDefinition] = {
            "tier_1": LootTierDefinition(
                tier_id="tier_1",
                weight=1.0,
                eligible_loot_pool_ids=["pool_tier_1"],
                eligible_categories=["food", "crafting"],
                eligible_quality_levels=["common"],
            ),
            "tier_2": LootTierDefinition(
                tier_id="tier_2",
                weight=1.0,
                eligible_loot_pool_ids=["pool_tier_2"],
                eligible_categories=["weapon", "armor"],
                eligible_quality_levels=["common", "uncommon"],
            ),
            "tier_3": LootTierDefinition(
                tier_id="tier_3",
                weight=1.0,
                eligible_loot_pool_ids=["pool_tier_3"],
                eligible_categories=["weapon_blueprint", "cosmetic"],
                eligible_quality_levels=["rare"],
            ),
        }

        self.mission_definitions: dict[str, MissionDefinition] = {
            "mission_human_retrieve_item": MissionDefinition(
                mission_id="mission_human_retrieve_item",
                audience=MissionAudience.HUMAN,
                objective_ids=["reach_building_a", "retrieve_water_bottle"],
                reward_id="reward_human_t1",
            ),
            "mission_zombie_feed_target": MissionDefinition(
                mission_id="mission_zombie_feed_target",
                audience=MissionAudience.ZOMBIE,
                objective_ids=["feed_once"],
                reward_id="reward_zombie_t1",
            ),
        }

        self._build_test_world()

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
        self.players[player_id] = AuthoritativePlayer(
            state=state,
            human_state=human_state,
            zombie_state=zombie_state,
        )
        self.mission_states.setdefault(player_id, {})

    def process_tick(self) -> None:
        for intent in self.transport.drain_command_intents():
            self._apply_intent(intent)
        self._refresh_chunk_interest()
        self._replicate_state()

    def save_state(self) -> None:
        player_payload: dict[str, dict] = {}
        inventory_payload: dict[str, dict] = {}

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
                },
                "zombie_state": self._serialize_zombie_state(player.zombie_state),
                "missions": self._serialize_player_missions(player_id),
            }
            inventory_payload[player_id] = {
                "capacity_slots": player.inventory.capacity_slots,
                "stacks": [asdict(stack) for stack in player.inventory.stacks],
            }

        world_payload = {
            "chunks": {
                key: {
                    "chunk_key": chunk.chunk_key,
                    "building_ids": chunk.building_ids,
                    "container_ids": chunk.container_ids,
                    "active": chunk.active,
                }
                for key, chunk in self.world.chunks.items()
            }
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
        server_payload = {
            "server_id": self.server_configuration.server_id,
            "map_id": self.server_configuration.map_id,
            "region_id": self.server_configuration.region_id,
            "is_public": self.server_configuration.is_public,
            "creative_mode_enabled": self.server_configuration.creative_mode_enabled,
            "max_players": self.server_configuration.max_players,
            "rule_set": {
                "custom_rules": self.server_configuration.rule_set.custom_rules,
                "custom_difficulty": self.server_configuration.rule_set.custom_difficulty,
                "custom_mission_ids": self.server_configuration.rule_set.custom_mission_ids,
            },
        }

        self.repository.save_by_key("players", player_payload)
        self.repository.save_by_key("inventories", inventory_payload)
        self.repository.save_by_key("world", world_payload)
        self.repository.save_by_key("loot", loot_payload)
        self.repository.save_by_key("server_config", server_payload)

    def _load_persisted_state(self) -> None:
        player_payload = self.repository.load_by_key("players")
        inventory_payload = self.repository.load_by_key("inventories")
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
            )
            inventory_source = inventory_payload.get(player_id, {"capacity_slots": 20, "stacks": []})
            inventory = Inventory(
                capacity_slots=inventory_source["capacity_slots"],
                stacks=[ItemStack(**stack) for stack in inventory_source.get("stacks", [])],
            )
            zombie_state = self._deserialize_zombie_state(payload.get("zombie_state"))

            self.players[player_id] = AuthoritativePlayer(
                state=state,
                human_state=human_state,
                zombie_state=zombie_state,
                inventory=inventory,
            )

            self.mission_states[player_id] = {}
            for mission_id, mission_payload in payload.get("missions", {}).items():
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

    def _serialize_zombie_state(self, zombie_state: ZombieRuntimeState | None) -> dict | None:
        if zombie_state is None:
            return None
        return {
            "feeding_state": zombie_state.feeding_state,
            "sanity": {
                "value": zombie_state.sanity.value,
                "minimum": zombie_state.sanity.minimum,
                "maximum": zombie_state.sanity.maximum,
            },
            "tier_id": zombie_state.tier_id,
            "mission_eligible": zombie_state.mission_eligible,
            "health": zombie_state.health,
        }

    def _deserialize_zombie_state(self, payload: dict | None) -> ZombieRuntimeState | None:
        if payload is None:
            return None
        return ZombieRuntimeState(
            feeding_state=payload.get("feeding_state", "idle"),
            sanity=ZombieSanityState(**payload.get("sanity", {"value": 50.0})),
            tier_id=payload.get("tier_id", "z_tier_1"),
            mission_eligible=bool(payload.get("mission_eligible", True)),
            health=float(payload.get("health", 100.0)),
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
            "player.inventory_action": self._handle_inventory_action,
            "mission.accept": self._handle_mission_accept,
            "mission.progress": self._handle_mission_progress,
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
        elif target_form == PlayerForm.HUMAN:
            infection_progress = 0.0
            zombie_sanity = None

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

        sanity_gain = float(payload.get("sanity_gain", 10.0))
        health_gain = float(payload.get("health_gain", 5.0))

        player.zombie_state.feeding_state = "feeding"
        player.zombie_state.sanity.apply_delta(sanity_gain)
        player.zombie_state.health = min(100.0, player.zombie_state.health + max(0.0, health_gain))
        player.zombie_state.mission_eligible = player.zombie_state.sanity.value >= 20.0

        mission = self.mission_states.setdefault(player.state.player_id, {}).setdefault(
            "mission_zombie_feed_target",
            MissionRuntimeState(),
        )
        if mission.accepted:
            mission.completed_objective_ids.add("feed_once")
            mission.completed = True

        return True, "ok"

    def _handle_inventory_action(self, player: AuthoritativePlayer, payload: dict) -> tuple[bool, str]:
        item_id = payload.get("item_id")
        quantity = int(payload.get("quantity", 0))
        if not isinstance(item_id, str) or quantity <= 0:
            return False, "invalid_inventory_payload"

        action = payload.get("action", "remove")
        if action != "remove":
            return False, "unsupported_inventory_action"

        removed = player.inventory.remove_item(item_id=item_id, quantity=quantity)
        if not removed:
            return False, "insufficient_items"
        return True, "ok"

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
            if player.state.form != PlayerForm.ZOMBIE:
                return False, "attacker_not_zombie"
            target = self.players.get(target_player_id)
            if target is None:
                return False, "target_not_found"
            damage = float(payload.get("damage", 10.0))
            target.human_state.stats.apply_damage(damage)
            return True, "ok"

        return False, "unsupported_interaction"

    def _loot_container(self, player: AuthoritativePlayer, container_id: str) -> tuple[bool, str]:
        container = self.world.containers.get(container_id)
        if container is None:
            return False, "container_not_found"

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
            overflow = player.inventory.add_item(
                definition=self._item_definition_for(stack.item_id),
                quantity=stack.quantity,
            )
            if overflow > 0:
                return False, "inventory_full"

        container.looted = True
        return True, "ok"

    def _item_definition_for(self, item_id: str):
        from .enums import ItemCategory
        from .items import ItemDefinition

        category_map = {
            "pistol_9mm": ItemCategory.WEAPON,
            "weapon_blueprint_t1": ItemCategory.QUEST,
            "scrap_metal": ItemCategory.CRAFTING,
            "canned_food": ItemCategory.FOOD,
            "armor_patch": ItemCategory.CLOTHING,
            "cosmetic_mask": ItemCategory.CLOTHING,
            "water_bottle": ItemCategory.WATER,
        }
        return ItemDefinition(
            item_id=item_id,
            name=item_id.replace("_", " ").title(),
            category=category_map.get(item_id, ItemCategory.MISC),
            max_stack=10,
            weight=0.5,
        )

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
        state.completed = set(definition.objective_ids).issubset(state.completed_objective_ids)
        return True, "ok"

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

    def _replicate_state(self) -> None:
        for player_id, player in self.players.items():
            visible_chunk_keys = set(self._player_required_chunks(player))
            visible_players = [
                self._player_snapshot_payload(other)
                for other in self.players.values()
                if self.chunk_key(self.grid_config.to_chunk_address(other.human_state.position)) in visible_chunk_keys
            ]
            payload = {
                "player_id": player_id,
                "state": self._player_snapshot_payload(player),
                "visible_players": visible_players,
                "active_chunks": sorted(key for key in visible_chunk_keys if self.world.chunks.get(key, WorldChunkRuntime(key)).active),
                "containers": {
                    container_id: {
                        "looted": container.looted,
                        "generated_items": [asdict(stack) for stack in container.generated_items],
                    }
                    for container_id, container in self.world.containers.items()
                    if self.chunk_key(self.grid_config.to_chunk_address(container.coordinate)) in visible_chunk_keys
                },
            }
            self.transport.push_snapshot(player_id, payload)

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
            "position": asdict(player.human_state.position),
            "inventory_total_items": player.inventory.total_items(),
            "zombie_state": self._serialize_zombie_state(player.zombie_state),
            "missions": mission_state,
        }
