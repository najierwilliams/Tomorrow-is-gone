import json
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
from prototypes.core.phase5_contracts import (
    RealWorldProviderRegistry,
    VehicleType,
    load_phase5_definitions,
)
from prototypes.core.phase5_validation import validate_definition_files
from unity.phase16_unity_adapter import Phase16UnityAdapter


def build_runtime(root: Path):
    transport = InProcessTransport()
    repository = FileBackedJsonRepository(root)
    loot_generator = TieredLootGenerator(
        loot_pools={
            "pool_tier_1": [{"item_id": "water_bottle", "min_qty": 1, "max_qty": 2}],
            "pool_tier_2": [{"item_id": "pistol_9mm", "min_qty": 1, "max_qty": 1}],
            "pool_tier_3": [{"item_id": "cosmetic_mask", "min_qty": 1, "max_qty": 1}],
        }
    )
    runtime = AuthoritativeServerRuntime(repository=repository, transport=transport, loot_generator=loot_generator)
    runtime.start()
    return runtime, transport


class Phase5FinalCoreSystemsAndUnityPreparationTests(unittest.TestCase):
    def test_phase5_definitions_load(self) -> None:
        definitions = load_phase5_definitions(Path(__file__).resolve().parents[1] / "data" / "phase5_definitions.json")
        self.assertTrue(definitions.server_rules.custom_missions_allowed)
        self.assertIn("vehicle_plane_player_built", definitions.vehicles)
        self.assertEqual(definitions.vehicles["vehicle_car_scout"].vehicle_type, VehicleType.CAR)

    def test_real_world_provider_registry_is_replaceable(self) -> None:
        registry = RealWorldProviderRegistry()
        self.assertTrue(registry.is_replaceable())

    def test_player_snapshot_contains_phase5_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.process_tick()
            snapshot = transport.pop_snapshots("human")[-1]["state"]
            self.assertEqual(snapshot["role"], "survivor")
            self.assertIn("chunk_key", snapshot)
            self.assertIn("equipment", snapshot)
            self.assertIn("inventory", snapshot)

    def test_human_death_and_respawn_is_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            player = runtime.players["human"]
            player.human_state.dead = True
            player.human_state.stats.health = 0.0
            player.inventory.add_item(runtime._item_definition_for("wood_log"), 1)
            transport.submit_command_intent(
                ClientCommandIntent("respawn", "human", "player.respawn", {"x": 3.0, "y": 0.0, "z": 3.0})
            )
            runtime.process_tick()
            self.assertTrue(runtime.command_results[0]["accepted"])
            self.assertFalse(player.human_state.dead)
            self.assertEqual(player.human_state.stats.health, 100.0)
            self.assertEqual(player.inventory.total_items(), 0)

    def test_vehicle_enter_exit_and_owner_control(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("driver", PlayerForm.HUMAN, WorldCoordinate(9.0, 0.0, 7.0))
            runtime.join_player("other", PlayerForm.HUMAN, WorldCoordinate(9.5, 0.0, 7.0))
            transport.submit_command_intent(
                ClientCommandIntent("enter", "driver", "vehicle.enter", {"vehicle_id": "vehicle_runtime_car_a"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("move_bad", "other", "vehicle.intent_move", {"vehicle_id": "vehicle_runtime_car_a", "dx": 1.0})
            )
            transport.submit_command_intent(
                ClientCommandIntent("move_ok", "driver", "vehicle.intent_move", {"vehicle_id": "vehicle_runtime_car_a", "dx": 2.0})
            )
            transport.submit_command_intent(
                ClientCommandIntent("exit", "driver", "vehicle.exit", {"vehicle_id": "vehicle_runtime_car_a"})
            )
            runtime.process_tick()
            self.assertTrue(runtime.command_results[0]["accepted"])
            self.assertFalse(runtime.command_results[1]["accepted"])
            self.assertTrue(runtime.command_results[2]["accepted"])
            self.assertTrue(runtime.command_results[3]["accepted"])

    def test_vehicle_persistence_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, transport = build_runtime(root)
            runtime.join_player("driver", PlayerForm.HUMAN, WorldCoordinate(9.0, 0.0, 7.0))
            transport.submit_command_intent(
                ClientCommandIntent("enter", "driver", "vehicle.enter", {"vehicle_id": "vehicle_runtime_car_a"})
            )
            transport.submit_command_intent(
                ClientCommandIntent("move", "driver", "vehicle.intent_move", {"vehicle_id": "vehicle_runtime_car_a", "dx": 4.0})
            )
            runtime.process_tick()
            runtime.shutdown()

            restored, _ = build_runtime(root)
            self.assertIn("vehicle_runtime_car_a", restored.world.vehicles)
            self.assertGreater(restored.world.vehicles["vehicle_runtime_car_a"].coordinate.x, 9.0)

    def test_world_time_and_day_night_progress(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            start_state = runtime.world_time.day_night_state
            for _ in range(2000):
                runtime.process_tick()
            self.assertNotEqual(runtime.world_time.elapsed_ticks, 0)
            self.assertIn(runtime.world_time.day_night_state, {"day", "night"})
            self.assertIn(start_state, {"day", "night"})

    def test_mission_completion_and_world_mutations_reject_client_forgery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            intents = [
                ClientCommandIntent("mission", "human", "mission.complete", {"mission_id": "mission_human_survive_cycle"}),
                ClientCommandIntent("time", "human", "world.time_set", {"tick": 0}),
                ClientCommandIntent("environment", "human", "world.environment_set", {"season": "winter"}),
                ClientCommandIntent("event", "human", "event.inject", {"event_type": "structure_destroyed"}),
            ]
            for intent in intents:
                transport.submit_command_intent(intent)
            runtime.process_tick()
            self.assertTrue(all(not result["accepted"] for result in runtime.command_results))

    def test_authoritative_events_emitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("owner", PlayerForm.HUMAN, WorldCoordinate(8.0, 0.0, 8.0))
            player = runtime.players["owner"]
            player.inventory.add_item(runtime._item_definition_for("wood_log"), 2)
            player.inventory.add_item(runtime._item_definition_for("metal_plate"), 1)
            transport.submit_command_intent(
                ClientCommandIntent(
                    "build",
                    "owner",
                    "structure.build",
                    {"structure_id": "s_phase5", "blueprint_id": "bp_wood_wall", "x": 8.0, "y": 0.0, "z": 8.0},
                )
            )
            runtime.process_tick()
            self.assertTrue(any(event["event_type"] == "structure_created" for event in runtime.authoritative_events))

    def test_replication_includes_phase5_projection_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(9.0, 0.0, 7.0))
            runtime.process_tick()
            payload = transport.pop_snapshots("human")[-1]
            self.assertIn("vehicles", payload)
            self.assertIn("world_time", payload)
            self.assertIn("authoritative_events", payload)
            self.assertIn("unity_allowed_intents", payload)
            self.assertIn("real_world_provider_contracts", payload)

    def test_unity_adapter_projects_phase5_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(9.0, 0.0, 7.0))
            runtime.process_tick()
            payload = transport.pop_snapshots("human")[-1]
            adapter = Phase16UnityAdapter()
            adapter.push_state_snapshot("server.snapshot", payload)
            self.assertIn("vehicle_runtime_car_a", adapter.view.vehicle_representation)
            self.assertIn("day_night_state", adapter.view.world_time_representation)
            self.assertTrue(adapter.view.allowed_intents)

    def test_definition_validation_passes(self) -> None:
        result = validate_definition_files(Path(__file__).resolve().parents[1] / "data")
        self.assertTrue(all(result.values()))

    def test_definition_validation_fails_for_invalid_phase5(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_root = Path(__file__).resolve().parents[1] / "data"
            for file_name in [
                "items.json",
                "loot_tables.json",
                "phase2_definitions.json",
                "phase3_ai_definitions.json",
                "phase4_world_definitions.json",
                "phase5_definitions.json",
            ]:
                (root / file_name).write_text((source_root / file_name).read_text())
            broken = json.loads((root / "phase5_definitions.json").read_text())
            broken.pop("server_rules", None)
            (root / "phase5_definitions.json").write_text(json.dumps(broken))
            with self.assertRaises(ValueError):
                validate_definition_files(root)

    def test_vehicle_ownership_forgery_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("owner", PlayerForm.HUMAN, WorldCoordinate(9.0, 0.0, 7.0))
            runtime.join_player("attacker", PlayerForm.HUMAN, WorldCoordinate(9.0, 0.0, 7.0))
            transport.submit_command_intent(
                ClientCommandIntent("enter", "owner", "vehicle.enter", {"vehicle_id": "vehicle_runtime_car_a"})
            )
            runtime.process_tick()
            transport.submit_command_intent(
                ClientCommandIntent(
                    "forged_move",
                    "attacker",
                    "vehicle.intent_move",
                    {"vehicle_id": "vehicle_runtime_car_a", "dx": 5.0, "owner_player_id": "attacker"},
                )
            )
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])

    def test_zombie_respawn_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 1.0))
            player = runtime.players["z"]
            self.assertIsNotNone(player.zombie_state)
            player.zombie_state.dead = True
            player.zombie_state.health = 0.0
            transport.submit_command_intent(
                ClientCommandIntent("respawn_z", "z", "player.respawn", {"x": 2.0, "y": 0.0, "z": 2.0})
            )
            runtime.process_tick()
            self.assertTrue(runtime.command_results[0]["accepted"])
            self.assertFalse(player.zombie_state.dead)
            self.assertEqual(player.zombie_state.health, 100.0)


if __name__ == "__main__":
    unittest.main()
