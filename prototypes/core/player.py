from dataclasses import dataclass


@dataclass
class PlayerStats:
    max_health: float = 100.0
    max_stamina: float = 100.0
    health: float = 100.0
    stamina: float = 100.0
    hunger: float = 0.0
    thirst: float = 0.0
    experience: int = 0
    level: int = 1

    def apply_damage(self, amount: float) -> None:
        self.health = max(0.0, self.health - max(0.0, amount))

    def heal(self, amount: float) -> None:
        self.health = min(self.max_health, self.health + max(0.0, amount))

    def spend_stamina(self, amount: float) -> bool:
        amount = max(0.0, amount)
        if self.stamina < amount:
            return False
        self.stamina -= amount
        return True

    def recover_stamina(self, amount: float) -> None:
        self.stamina = min(self.max_stamina, self.stamina + max(0.0, amount))

    def consume_resources(self, hunger_delta: float, thirst_delta: float) -> None:
        self.hunger = min(100.0, max(0.0, self.hunger + hunger_delta))
        self.thirst = min(100.0, max(0.0, self.thirst + thirst_delta))

    def add_experience(self, amount: int) -> None:
        if amount <= 0:
            return
        self.experience += amount
        while self.experience >= self._experience_required(self.level):
            self.experience -= self._experience_required(self.level)
            self.level += 1

    @staticmethod
    def _experience_required(level: int) -> int:
        return 100 + (level - 1) * 50
