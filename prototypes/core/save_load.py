import json
from dataclasses import asdict, dataclass

from .inventory import Inventory
from .items import ItemStack
from .player import PlayerStats


@dataclass
class GameSnapshot:
    player: PlayerStats
    inventory: Inventory

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "GameSnapshot":
        data = json.loads(payload)
        player = PlayerStats(**data["player"])
        inventory = Inventory(
            capacity_slots=data["inventory"]["capacity_slots"],
            stacks=[ItemStack(**stack) for stack in data["inventory"]["stacks"]],
        )
        return cls(player=player, inventory=inventory)
