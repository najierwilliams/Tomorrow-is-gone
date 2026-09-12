import tempfile
import unittest
from pathlib import Path

from prototypes.core.phase15_contracts import ClientCommandIntent, PlayerForm, WorldCoordinate
from prototypes.core.phase16_authoritative_runtime import (
    AuthoritativeServerRuntime,
    FileBackedJsonRepository,
    InProcessTransport,
    TieredLootGenerator,
)


def build_runtime(root: Path):
    transport = InProcessTransport()
    repository = FileBackedJsonRepository(root)
    loot_generator = TieredLootGenerator(
        loot_pools={
            "pool_tier_1": [
                {"item_id": "water_bottle", "min_qty": 1, "max_qty": 2},
                {"item_id": "canned_food", "min_qty": 1, "max_qty": 2},
                {"item_id": "scrap_metal", "min_qty": 1, "max_qty": 4},
            ],
            "pool_tier_2": [
                {"item_id": "pistol_9mm", "min_qty": 1, "max_qty": 1},
                {"item_id": "jacket_armor", "min_qty": 1, "max_qty": 1},
                {"item_id": "med_kit", "min_qty": 1, "max_qty": 1},
            ],
            "pool_tier_3": [
                {"item_id": "weapon_blueprint_t1", "min_qty": 1, "max_qty": 1},
                {"item_id": "cosmetic_mask", "min_qty": 1, "max_qty": 1},
            ],
        }
    )
    runtime = AuthoritativeServerRuntime(repository=repository, transport=transport, loot_generator=loot_generator)
    runtime.start()
    return runtime, transport


class Phase2CoreGameplayRuntimeTests(unittest.TestCase):
    def test_human_hunger_thirst_depletion_starvation_dehydration_and_death(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            player = runtime.players["human"]
            player.human_state.stats.hunger = 99.0
            player.human_state.stats.thirst = 99.0
            player.human_state.stats.health = 6.0

            runtime.process_tick()

            self.assertEqual(player.human_state.stats.health, 0.0)
            self.assertTrue(player.human_state.dead)

    def test_invalid_client_side_state_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            before_health = runtime.players["human"].human_state.stats.health

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="client_hack",
                    player_id="human",
                    topic="player.set_health",
                    payload={"health": 9999.0},
                )
            )
            runtime.process_tick()

            self.assertFalse(runtime.command_results[0]["accepted"])
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")
            self.assertEqual(runtime.players["human"].human_state.stats.health, before_health)

    def test_zombie_survival_feeding_no_water_requirement_and_sleep_healing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 0.0))
            player = runtime.players["z"]
            player.zombie_state.health = 50.0
            player.zombie_state.hunger = 80.0

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="sleep",
                    player_id="z",
                    topic="zombie.sleep",
                    payload={"sleeping": True},
                )
            )
            runtime.process_tick()
            self.assertGreater(player.zombie_state.health, 50.0)

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="feed",
                    player_id="z",
                    topic="zombie.feed",
                    payload={"sanity_gain": 15.0, "hunger_recovery": 30.0},
                )
            )
            runtime.process_tick()

            self.assertLess(player.zombie_state.hunger, 60.0)
            self.assertEqual(player.human_state.stats.thirst, 0.0)

    def test_food_and_medicine_usage_are_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            player = runtime.players["human"]
            player.inventory.add_item(runtime._item_definition_for("canned_food"), 1)
            player.inventory.add_item(runtime._item_definition_for("med_kit"), 1)
            player.human_state.stats.hunger = 60.0
            player.human_state.stats.health = 50.0

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="eat",
                    player_id="human",
                    topic="player.use_item",
                    payload={"item_id": "canned_food"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="medicate",
                    player_id="human",
                    topic="player.use_item",
                    payload={"item_id": "med_kit"},
                )
            )
            runtime.process_tick()

            self.assertLess(player.human_state.stats.hunger, 60.0)
            self.assertGreater(player.human_state.stats.health, 50.0)

    def test_weapon_and_armor_equipment_damage_mitigation_and_durability(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.join_player("b", PlayerForm.HUMAN, WorldCoordinate(1.0, 0.0, 0.0))

            attacker = runtime.players["a"]
            defender = runtime.players["b"]
            attacker.inventory.add_item(runtime._item_definition_for("ammo_9mm"), 10)

            transport.submit_command_intent(
                ClientCommandIntent("equip_w", "a", "player.equip", {"item_id": "pistol_9mm"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("equip_a", "b", "player.equip", {"item_id": "jacket_armor"})
            )
            runtime.process_tick()

            pre_health = defender.human_state.stats.health
            transport.submit_command_intent(
                ClientCommandIntent(
                    "attack",
                    "a",
                    "player.interact",
                    {"action": "attack_player", "target_player_id": "b"},
                )
            )
            runtime.process_tick()

            self.assertLess(defender.human_state.stats.health, pre_health)
            weapon_instance = attacker.equipment_instances[attacker.equipment.equipped_weapon_instance_id]
            armor_instance = defender.equipment_instances[defender.equipment.equipped_armor_instance_id]
            self.assertLess(weapon_instance.durability, weapon_instance.max_durability)
            self.assertLess(armor_instance.durability, armor_instance.max_durability)

    def test_crafting_and_workbench_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(4.0, 0.0, 4.0))
            player = runtime.players["human"]
            player.inventory.add_item(runtime._item_definition_for("scrap_metal"), 2)

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="craft",
                    player_id="human",
                    topic="crafting.start",
                    payload={"recipe_id": "recipe_metal_plate", "workbench_id": "bench_general_a"},
                )
            )
            runtime.process_tick()

            self.assertTrue(any(r["accepted"] for r in runtime.command_results))
            self.assertTrue(any(stack.item_id == "metal_plate" for stack in player.inventory.stacks))

    def test_resource_gathering_and_respawn(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(12.0, 0.0, 12.0))
            node = runtime.world.resource_nodes["node_scrap_1"]

            while node.quantity > 0:
                transport.submit_command_intent(
                    ClientCommandIntent("gather", "human", "gather.resource", {"node_id": "node_scrap_1"})
                )
                runtime.process_tick()

            self.assertEqual(node.quantity, 0)
            for _ in range(node.respawn_ticks):
                runtime.process_tick()
            self.assertEqual(node.quantity, node.max_quantity)

    def test_gardening_plant_water_harvest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(6.0, 0.0, 6.0))
            player = runtime.players["human"]
            player.inventory.add_item(runtime._item_definition_for("seed_potato"), 1)

            transport.submit_command_intent(
                ClientCommandIntent(
                    "plant",
                    "human",
                    "garden.action",
                    {"action": "plant", "plot_id": "garden_plot_a", "crop_id": "potato"},
                )
            )
            runtime.process_tick()

            transport.submit_command_intent(
                ClientCommandIntent(
                    "water",
                    "human",
                    "garden.action",
                    {"action": "water", "plot_id": "garden_plot_a", "amount": 50.0},
                )
            )
            runtime.process_tick()
            runtime.process_tick()

            transport.submit_command_intent(
                ClientCommandIntent(
                    "harvest",
                    "human",
                    "garden.action",
                    {"action": "harvest", "plot_id": "garden_plot_a"},
                )
            )
            runtime.process_tick()

            self.assertTrue(any(stack.item_id == "harvest_potato" for stack in player.inventory.stacks))

    def test_human_can_build_and_both_forms_can_destroy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(8.0, 0.0, 8.0))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(8.5, 0.0, 8.0))
            builder = runtime.players["human"]
            builder.inventory.add_item(runtime._item_definition_for("wood_log"), 2)
            builder.inventory.add_item(runtime._item_definition_for("metal_plate"), 1)

            transport.submit_command_intent(
                ClientCommandIntent(
                    "build",
                    "human",
                    "structure.build",
                    {"structure_id": "s1", "blueprint_id": "bp_wood_wall", "x": 8.0, "y": 0.0, "z": 8.5},
                )
            )
            runtime.process_tick()
            self.assertIn("s1", runtime.world.structures)

            transport.submit_command_intent(
                ClientCommandIntent(
                    "bad_build",
                    "z",
                    "structure.build",
                    {"structure_id": "s2", "blueprint_id": "bp_wood_wall", "x": 8.0, "y": 0.0, "z": 8.5},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    "destroy",
                    "z",
                    "structure.damage",
                    {"structure_id": "s1", "damage": 500.0},
                )
            )
            runtime.process_tick()

            self.assertFalse(runtime.command_results[0]["accepted"])
            self.assertEqual(runtime.world.structures["s1"].state, "destroyed")

    def test_power_foundation_updates_device_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.process_tick()
            self.assertTrue(runtime.world.powered_devices["device_fabricator_a"].powered)

            transport.submit_command_intent(
                ClientCommandIntent(
                    "off",
                    "human",
                    "power.source_toggle",
                    {"source_instance_id": "source_generator_a", "enabled": False},
                )
            )
            runtime.process_tick()
            self.assertFalse(runtime.world.powered_devices["device_fabricator_a"].powered)

    def test_animal_taming_infection_ability_and_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, transport = build_runtime(root)
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(14.0, 0.0, 14.0))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(16.0, 0.0, 15.0))

            transport.submit_command_intent(
                ClientCommandIntent("tame", "human", "animal.tame", {"animal_id": "animal_wolf_1", "tame_bonus": 1.0})
            )
            runtime.process_tick()
            self.assertEqual(runtime.world.animals["animal_wolf_1"].owner_player_id, "human")

            transport.submit_command_intent(
                ClientCommandIntent(
                    "infect",
                    "z",
                    "player.interact",
                    {"action": "infect_animal", "animal_id": "animal_wolf_1"},
                )
            )
            runtime.process_tick()
            self.assertEqual(runtime.world.animals["animal_wolf_1"].state.infection_state.value, "infected")

            transport.submit_command_intent(
                ClientCommandIntent(
                    "ability",
                    "human",
                    "animal.use_ability",
                    {"animal_id": "animal_wolf_1", "ability_id": "wolf_scavenge"},
                )
            )
            runtime.process_tick()
            self.assertTrue(runtime.command_results[0]["accepted"])

            runtime.shutdown()
            restored, _ = build_runtime(root)
            restored.start()
            self.assertIn("animal_wolf_1", restored.world.animals)
            self.assertEqual(restored.world.animals["animal_wolf_1"].owner_player_id, "human")

    def test_horde_membership_requires_zombie_and_persists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent("h1", "human", "horde.membership", {"horde_id": "horde_alpha", "action": "join"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("h2", "z", "horde.membership", {"horde_id": "horde_alpha", "action": "join"})
            )
            runtime.process_tick()

            self.assertFalse(runtime.command_results[0]["accepted"])
            self.assertTrue(runtime.command_results[1]["accepted"])
            self.assertIn("z", runtime.world.hordes["horde_alpha"].member_player_ids)

    def test_progression_missions_loot_currency_and_replication(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(10.0, 0.0, 10.0))
            player = runtime.players["human"]

            transport.submit_command_intent(
                ClientCommandIntent("macc", "human", "mission.accept", {"mission_id": "mission_human_gather_resources"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("loot", "human", "player.interact", {"action": "loot_container", "container_id": "container_a"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("gather", "human", "gather.resource", {"node_id": "node_scrap_1"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("earn", "human", "economy.mutate", {"action": "earn", "amount": 25})
            )
            runtime.process_tick()

            mission = runtime.mission_states["human"]["mission_human_gather_resources"]
            self.assertTrue(mission.completed)
            self.assertGreater(player.human_state.stats.experience, 0)
            self.assertGreater(player.currency_balance, 50)

            snapshots = transport.pop_snapshots("human")
            self.assertTrue(snapshots)
            latest = snapshots[-1]
            self.assertIn("inventory", latest)
            self.assertIn("animals", latest)
            self.assertIn("structures", latest)
            self.assertIn("economy", latest)

    def test_multiplayer_authoritative_human_zombie_interaction_and_infection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent(
                    "atk",
                    "z",
                    "player.interact",
                    {
                        "action": "attack_player",
                        "target_player_id": "human",
                        "damage": 15.0,
                        "attempt_infect": True,
                    },
                )
            )
            runtime.process_tick()

            self.assertLess(runtime.players["human"].human_state.stats.health, 100.0)
            self.assertEqual(runtime.players["human"].state.form, PlayerForm.INFECTED_HUMAN)


if __name__ == "__main__":
    unittest.main()
