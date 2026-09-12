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
            }
            for player in visible_players + [state]
            if "player_id" in player
        }

        self.view.world_representation = {
            "active_chunks": payload.get("active_chunks", []),
            "containers": payload.get("containers", {}),
            "resource_nodes": payload.get("resource_nodes", {}),
            "gardens": payload.get("gardens", {}),
            "power": payload.get("power", {}),
            "hordes": payload.get("hordes", {}),
            "npcs": payload.get("npcs", {}),
        }

        self.view.inventory_representation = payload.get("inventory", {})
        self.view.mission_representation = payload.get("missions", {})
        self.view.animal_representation = payload.get("animals", {})
        self.view.structure_representation = payload.get("structures", {})

    def pull_input_commands(self) -> list[ClientCommandIntent]:
        intents = list(self._pending_commands)
        self._pending_commands.clear()
        return intents

    def queue_input_command(self, intent: ClientCommandIntent) -> None:
        self._pending_commands.append(intent)
