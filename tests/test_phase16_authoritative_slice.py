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
from unity.phase16_unity_adapter import Phase16UnityAdapter


def build_runtime(root: Path):
    transport = InProcessTransport()
    repository = FileBackedJsonRepository(root)
    loot_generator = TieredLootGenerator(
        loot_pools={
            "pool_tier_1": [
                {"item_id": "water_bottle", "min_qty": 1, "max_qty": 2},
                {"item_id": "canned_food", "min_qty": 1, "max_qty": 2},
                {"item_id": "scrap_metal", "min_qty": 1, "max_qty": 3},
            ],
            "pool_tier_2": [
                {"item_id": "pistol_9mm", "min_qty": 1, "max_qty": 1},
                {"item_id": "armor_patch", "min_qty": 1, "max_qty": 1},
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


class Phase16AuthoritativeSliceTests(unittest.TestCase):
    def test_server_creates_authoritative_player(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.process_tick()

            self.assertIn("player_a", runtime.players)
            self.assertEqual(runtime.players["player_a"].state.form, PlayerForm.HUMAN)

    def test_client_command_accepted_and_invalid_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="cmd_move",
                    player_id="player_a",
                    topic="player.move",
                    payload={"target_x": 20.0, "target_y": 0.0, "target_z": 12.0},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="cmd_invalid",
                    player_id="player_a",
                    topic="player.move",
                    payload={"target_x": 20.0, "target_y": 5000.0, "target_z": 12.0},
                )
            )
            runtime.process_tick()

            self.assertTrue(runtime.command_results[0]["accepted"])
            self.assertFalse(runtime.command_results[1]["accepted"])
            self.assertEqual(runtime.command_results[1]["reason"], "position_out_of_world_bounds")

    def test_human_infected_zombie_and_cure_gated_transition(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="infect",
                    player_id="player_a",
                    topic="player.infect",
                    payload={"target_form": "infected_human"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="zombify",
                    player_id="player_a",
                    topic="player.infect",
                    payload={"target_form": "zombie"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="invalid_cure",
                    player_id="player_a",
                    topic="player.infect",
                    payload={"target_form": "human"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="valid_cure",
                    player_id="player_a",
                    topic="player.infect",
                    payload={"target_form": "human", "cure_available": True},
                )
            )
            runtime.process_tick()

            self.assertEqual(runtime.command_results[0]["accepted"], True)
            self.assertEqual(runtime.command_results[1]["accepted"], True)
            self.assertEqual(runtime.command_results[2]["accepted"], False)
            self.assertEqual(runtime.command_results[3]["accepted"], True)
            self.assertEqual(runtime.players["player_a"].state.form, PlayerForm.HUMAN)

    def test_chunk_interest_activates_and_deactivates_relevant_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.process_tick()

            active_before = {key for key, chunk in runtime.world.chunks.items() if chunk.active}
            self.assertTrue(active_before)

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="move_far",
                    player_id="player_a",
                    topic="player.move",
                    payload={"target_x": 256.0, "target_y": 0.0, "target_z": 256.0},
                )
            )
            runtime.process_tick()
            active_after = {key for key, chunk in runtime.world.chunks.items() if chunk.active}

            self.assertTrue(active_after)
            self.assertNotEqual(active_before, active_after)

    def test_loot_generation_respects_container_tier(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))

            expected_item_sets = {
                "container_a": {"water_bottle", "canned_food", "scrap_metal"},
                "container_b": {"pistol_9mm", "armor_patch"},
                "container_c": {"weapon_blueprint_t1", "cosmetic_mask"},
            }

            for index, container_id in enumerate(["container_a", "container_b", "container_c"]):
                transport.submit_command_intent(
                    ClientCommandIntent(
                        command_id=f"loot_{index}",
                        player_id="player_a",
                        topic="player.interact",
                        payload={"action": "loot_container", "container_id": container_id},
                    )
                )
                runtime.process_tick()
                generated_ids = {item.item_id for item in runtime.world.containers[container_id].generated_items}
                self.assertTrue(generated_ids.issubset(expected_item_sets[container_id]))

    def test_loot_persistence_and_player_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, transport = build_runtime(root)
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="move",
                    player_id="player_a",
                    topic="player.move",
                    payload={"target_x": 20.0, "target_y": 0.0, "target_z": 10.0},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="loot",
                    player_id="player_a",
                    topic="player.interact",
                    payload={"action": "loot_container", "container_id": "container_a"},
                )
            )
            runtime.process_tick()
            runtime.shutdown()

            restored_runtime, _ = build_runtime(root)
            restored_runtime.start()

            self.assertIn("player_a", restored_runtime.players)
            self.assertEqual(
                restored_runtime.players["player_a"].human_state.position.x,
                20.0,
            )
            self.assertTrue(restored_runtime.world.containers["container_a"].looted)
            self.assertTrue(restored_runtime.world.containers["container_a"].generated_items)

    def test_human_and_zombie_missions_progress_authoritatively(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_h", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.join_player("player_z", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="human_accept",
                    player_id="player_h",
                    topic="mission.accept",
                    payload={"mission_id": "mission_human_retrieve_item"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="human_progress_1",
                    player_id="player_h",
                    topic="mission.progress",
                    payload={"mission_id": "mission_human_retrieve_item", "objective_id": "reach_building_a"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="human_progress_2",
                    player_id="player_h",
                    topic="mission.progress",
                    payload={"mission_id": "mission_human_retrieve_item", "objective_id": "retrieve_water_bottle"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="zombie_accept",
                    player_id="player_z",
                    topic="mission.accept",
                    payload={"mission_id": "mission_zombie_feed_target"},
                )
            )
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="zombie_feed",
                    player_id="player_z",
                    topic="zombie.feed",
                    payload={"sanity_gain": 12.0},
                )
            )
            runtime.process_tick()

            human_mission = runtime.mission_states["player_h"]["mission_human_retrieve_item"]
            zombie_mission = runtime.mission_states["player_z"]["mission_zombie_feed_target"]
            self.assertTrue(human_mission.completed)
            self.assertTrue(zombie_mission.completed)

    def test_server_authoritative_combat_replication_and_unity_adapter_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.join_player("player_b", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 0.0))

            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="attack",
                    player_id="player_b",
                    topic="player.interact",
                    payload={"action": "attack_player", "target_player_id": "player_a", "damage": 25.0},
                )
            )
            runtime.process_tick()

            snapshots_for_a = transport.pop_snapshots("player_a")
            self.assertTrue(snapshots_for_a)
            latest_snapshot = snapshots_for_a[-1]
            self.assertEqual(latest_snapshot["state"]["health"], 75.0)

            adapter = Phase16UnityAdapter()
            adapter.push_state_snapshot("authoritative.snapshot", latest_snapshot)
            self.assertEqual(adapter.view.player_representations["player_a"]["health"], 75.0)
            self.assertIn("active_chunks", adapter.view.world_representation)


if __name__ == "__main__":
    unittest.main()
