from dataclasses import dataclass

from .enums import ItemCategory


@dataclass(frozen=True)
class ItemDefinition:
    item_id: str
    name: str
    category: ItemCategory
    max_stack: int = 1
    weight: float = 0.0


@dataclass
class ItemStack:
    item_id: str
    quantity: int


@dataclass(frozen=True)
class WeaponDefinition:
    weapon_id: str
    name: str
    damage: float
    stamina_cost: float
    durability_loss: float


@dataclass
class WeaponInstance:
    definition: WeaponDefinition
    durability: float = 100.0

    def can_use(self) -> bool:
        return self.durability > 0

    def attack_damage(self) -> float:
        if not self.can_use():
            return 0.0
        self.durability = max(0.0, self.durability - self.definition.durability_loss)
        return self.definition.damage
