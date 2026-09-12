import random
from dataclasses import dataclass


@dataclass(frozen=True)
class LootEntry:
    item_id: str
    chance: float
    min_qty: int = 1
    max_qty: int = 1


@dataclass
class LootTable:
    table_id: str
    entries: list[LootEntry]

    def roll(self, rng: random.Random) -> dict[str, int]:
        drops: dict[str, int] = {}
        for entry in self.entries:
            if rng.random() <= entry.chance:
                quantity = rng.randint(entry.min_qty, entry.max_qty)
                drops[entry.item_id] = drops.get(entry.item_id, 0) + quantity
        return drops
