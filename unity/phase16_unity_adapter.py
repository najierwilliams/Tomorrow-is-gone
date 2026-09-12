from __future__ import annotations

from dataclasses import dataclass, field

from prototypes.core.phase15_contracts import ClientCommandIntent, UnityIntegrationPort


@dataclass
class UnityAuthoritativeView:
    latest_topic: str = ""
    latest_payload: dict = field(default_factory=dict)
    player_representations: dict[str, dict] = field(default_factory=dict)
    world_representation: dict = field(default_factory=dict)
    inventory_representation: dict = field(default_factory=dict)
    mission_representation: dict = field(default_factory=dict)
    animal_representation: dict = field(default_factory=dict)
    structure_representation: dict = field(default_factory=dict)
    vehicle_representation: dict = field(default_factory=dict)
    npc_ai_representation: dict = field(default_factory=dict)
    perception_representation: list[dict] = field(default_factory=list)
    world_time_representation: dict = field(default_factory=dict)
    event_representation: list[dict] = field(default_factory=list)
    allowed_intents: list[str] = field(default_factory=list)


class Phase16UnityAdapter(UnityIntegrationPort):
    def __init__(self) -> None:
        self._pending_commands: list[ClientCommandIntent] = []
        self.view = UnityAuthoritativeView()

    def push_state_snapshot(self, topic: str, payload: dict) -> None:
        self.view.latest_topic = topic
        self.view.latest_payload = payload

        state = payload.get("state", {})
        visible_players = payload.get("visible_players", [])
        self.view.player_representations = {
            player["player_id"]: {
                "form": player.get("form"),
                "health": player.get("health"),
                "stamina": player.get("stamina"),
                "hunger": player.get("hunger"),
                "thirst": player.get("thirst"),
                "position": player.get("position"),
                "zombie_state": player.get("zombie_state"),
                "economy": player.get("economy", {}),
                "dead": player.get("dead"),
            }
            for player in visible_players + [state]
            if "player_id" in player
        }

        self.view.world_representation = {
            "active_chunks": payload.get("active_chunks", []),
            "chunk_metadata": payload.get("chunk_metadata", {}),
            "containers": payload.get("containers", {}),
            "resource_nodes": payload.get("resource_nodes", {}),
            "environment_state_by_region": payload.get("environment_state_by_region", {}),
            "gardens": payload.get("gardens", {}),
            "power": payload.get("power", {}),
            "hordes": payload.get("hordes", {}),
            "npcs": payload.get("npcs", {}),
            "vehicles": payload.get("vehicles", {}),
            "perception_events": payload.get("perception_events", []),
            "world_time": payload.get("world_time", {}),
        }

        self.view.inventory_representation = payload.get("inventory", {})
        self.view.mission_representation = payload.get("missions", {})
        self.view.animal_representation = payload.get("animals", {})
        self.view.structure_representation = payload.get("structures", {})
        self.view.vehicle_representation = payload.get("vehicles", {})
        self.view.npc_ai_representation = {
            npc_id: npc_payload.get("ai_state", {})
            for npc_id, npc_payload in payload.get("npcs", {}).items()
        }
        self.view.perception_representation = list(payload.get("perception_events", []))
        self.view.world_time_representation = payload.get("world_time", {})
        self.view.event_representation = list(payload.get("authoritative_events", []))
        self.view.allowed_intents = list(payload.get("unity_allowed_intents", []))

    def pull_input_commands(self) -> list[ClientCommandIntent]:
        intents = list(self._pending_commands)
        self._pending_commands.clear()
        return intents

    def queue_input_command(self, intent: ClientCommandIntent) -> None:
        self._pending_commands.append(intent)
