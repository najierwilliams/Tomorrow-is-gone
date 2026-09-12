import random
import unittest
from pathlib import Path

from prototypes.core.data_loader import load_item_definitions, load_loot_tables
from prototypes.core.enums import ZombieState
from prototypes.core.inventory import Inventory
from prototypes.core.items import WeaponDefinition, WeaponInstance
from prototypes.core.player import PlayerStats
from prototypes.core.save_load import GameSnapshot
from prototypes.core.zombies import ZombieEntity


class Phase1PrototypeTests(unittest.TestCase):
    def test_player_damage_and_survival_stats(self) -> None:
        player = PlayerStats()
        player.apply_damage(35)
        player.consume_resources(15, 20)

        self.assertEqual(player.health, 65.0)
        self.assertEqual(player.hunger, 15.0)
        self.assertEqual(player.thirst, 20.0)

    def test_stamina_spend_and_recover(self) -> None:
        player = PlayerStats(stamina=30, max_stamina=100)

        self.assertTrue(player.spend_stamina(20))
        self.assertFalse(player.spend_stamina(20))

        player.recover_stamina(50)
        self.assertEqual(player.stamina, 60)

    def test_inventory_item_handling(self) -> None:
        item_defs = load_item_definitions(Path("data/items.json"))
        inventory = Inventory(capacity_slots=2)

        overflow = inventory.add_item(item_defs["water_bottle"], 6)

        self.assertEqual(overflow, 0)
        self.assertEqual(len(inventory.stacks), 2)
        self.assertTrue(inventory.remove_item("water_bottle", 4))
        self.assertEqual(inventory.total_items(), 2)

    def test_weapon_behavior(self) -> None:
        knife = WeaponDefinition(
            weapon_id="knife",
            name="Combat Knife",
            damage=20,
            stamina_cost=10,
            durability_loss=25,
        )
        instance = WeaponInstance(definition=knife)

        damages = [instance.attack_damage() for _ in range(5)]

        self.assertEqual(damages[:4], [20, 20, 20, 20])
        self.assertEqual(damages[4], 0.0)

    def test_zombie_state_transitions(self) -> None:
        zombie = ZombieEntity(zombie_id="z-001")

        zombie.tick(
            can_see_player=False,
            in_attack_range=False,
            heard_noise=False,
            has_last_known_position=False,
        )
        zombie.tick(
            can_see_player=False,
            in_attack_range=False,
            heard_noise=True,
            has_last_known_position=False,
        )
        zombie.tick(
            can_see_player=True,
            in_attack_range=False,
            heard_noise=False,
            has_last_known_position=True,
        )
        zombie.tick(
            can_see_player=True,
            in_attack_range=True,
            heard_noise=False,
            has_last_known_position=True,
        )
        zombie.tick(
            can_see_player=False,
            in_attack_range=False,
            heard_noise=False,
            has_last_known_position=False,
        )

        for expected in [
            ZombieState.WANDER,
            ZombieState.INVESTIGATE,
            ZombieState.DETECT_PLAYER,
            ZombieState.CHASE,
            ZombieState.ATTACK,
            ZombieState.LOSE_TARGET,
            ZombieState.RETURN_TO_WANDER,
        ]:
            self.assertIn(expected, zombie.state_history)

    def test_loot_generation(self) -> None:
        tables = load_loot_tables(Path("data/loot_tables.json"))
        rng = random.Random(42)

        drops = tables["residential_common"].roll(rng)

        self.assertTrue(set(drops.keys()).issubset({"water_bottle", "canned_food", "scrap_metal"}))

    def test_save_load_serialization(self) -> None:
        item_defs = load_item_definitions(Path("data/items.json"))
        player = PlayerStats(health=77, stamina=55, hunger=10, thirst=12, experience=25, level=2)
        inventory = Inventory(capacity_slots=5)
        inventory.add_item(item_defs["canned_food"], 3)

        snapshot = GameSnapshot(player=player, inventory=inventory)
        loaded = GameSnapshot.from_json(snapshot.to_json())

        self.assertEqual(loaded.player.health, 77)
        self.assertEqual(loaded.inventory.stacks[0].item_id, "canned_food")
        self.assertEqual(loaded.inventory.stacks[0].quantity, 3)


if __name__ == "__main__":
    unittest.main()
