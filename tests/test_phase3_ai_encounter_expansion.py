import tempfile
import unittest
from pathlib import Path

from prototypes.core.phase15_contracts import ClientCommandIntent, PlayerForm, WorldCoordinate
from prototypes.core.phase16_authoritative_runtime import (
    AuthoritativeServerRuntime,
    DeterministicChunkNavigationProvider,
    FileBackedJsonRepository,
    HordeRuntime,
    NpcRuntime,
    StructureRuntime,
    TieredLootGenerator,
)
from prototypes.core.phase3_ai import NavigationPathStatus, NavigationProvider, NavigationQuery


class AlwaysUnavailableNavigationProvider(NavigationProvider):
    def query_path(self, query: NavigationQuery):
        from prototypes.core.phase3_ai import NavigationPath

        return NavigationPath(
            status=NavigationPathStatus.UNAVAILABLE,
            waypoints=(query.start,),
            traversed_chunk_keys=query.required_chunk_keys,
            reason="forced_unavailable",
        )

    def are_tiles_available(self, chunk_keys: tuple[str, ...]) -> bool:
        return False


def build_runtime(root: Path, navigation_provider: NavigationProvider | None = None):
    transport = InProcessTransport()
    repository = FileBackedJsonRepository(root)
    loot_generator = TieredLootGenerator(
        loot_pools={
            "pool_tier_1": [{"item_id": "water_bottle", "min_qty": 1, "max_qty": 2}],
            "pool_tier_2": [{"item_id": "pistol_9mm", "min_qty": 1, "max_qty": 1}],
            "pool_tier_3": [{"item_id": "weapon_blueprint_t1", "min_qty": 1, "max_qty": 1}],
        }
    )
    runtime = AuthoritativeServerRuntime(
        repository=repository,
        transport=transport,
        loot_generator=loot_generator,
        navigation_provider=navigation_provider,
    )
    runtime.start()
    return runtime, transport


from prototypes.core.phase16_authoritative_runtime import InProcessTransport


class Phase3AiEncounterExpansionTests(unittest.TestCase):
    def test_navigation_query_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            provider = runtime.navigation_provider
            path = provider.query_path(
                NavigationQuery(
                    agent_id="npc",
                    start=WorldCoordinate(0.0, 0.0, 0.0),
                    destination=WorldCoordinate(16.0, 0.0, 16.0),
                )
            )
            self.assertEqual(path.status, NavigationPathStatus.REACHABLE)
            self.assertEqual(path.waypoints[-1], WorldCoordinate(16.0, 0.0, 16.0))

    def test_navigation_unreachable_destination_is_handled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            provider = runtime.navigation_provider
            assert isinstance(provider, DeterministicChunkNavigationProvider)
            provider.blocked_chunk_keys.add("0:0:0")
            path = provider.query_path(
                NavigationQuery(
                    agent_id="npc",
                    start=WorldCoordinate(0.0, 0.0, 0.0),
                    destination=WorldCoordinate(8.0, 0.0, 8.0),
                )
            )
            self.assertEqual(path.status, NavigationPathStatus.UNREACHABLE)

    def test_navigation_remains_chunk_aware(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            provider = runtime.navigation_provider
            path = provider.query_path(
                NavigationQuery(
                    agent_id="npc",
                    start=WorldCoordinate(0.0, 0.0, 0.0),
                    destination=WorldCoordinate(130.0, 0.0, 0.0),
                )
            )
            self.assertGreaterEqual(len(path.traversed_chunk_keys), 2)

    def test_navigation_provider_is_replaceable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory), navigation_provider=AlwaysUnavailableNavigationProvider())
            runtime.world.npcs["npc_survivor_a"].coordinate = WorldCoordinate(300.0, 0.0, 300.0)
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(26.0, 0.0, 18.0))
            runtime.process_tick()
            npc = runtime.world.npcs["npc_zombie_a"]
            self.assertEqual(npc.ai_state.last_navigation_status, NavigationPathStatus.UNAVAILABLE.value)

    def test_zombie_detects_visible_human_within_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 18.0))
            runtime.process_tick()
            self.assertEqual(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id, "human")

    def test_zombie_does_not_detect_target_outside_range(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(800.0, 0.0, 800.0))
            runtime.process_tick()
            self.assertIsNone(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_field_of_view_restrictions_work(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_survivor_a"].coordinate = WorldCoordinate(300.0, 0.0, 300.0)
            runtime.world.npcs["npc_zombie_a"].coordinate = WorldCoordinate(0.0, 0.0, 0.0)
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(-18.0, 0.0, 0.0))
            runtime.process_tick()
            self.assertIsNone(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_obstruction_logic_works(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_survivor_a"].coordinate = WorldCoordinate(300.0, 0.0, 300.0)
            runtime.world.npcs["npc_zombie_a"].coordinate = WorldCoordinate(0.0, 0.0, 0.0)
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(10.0, 0.0, 0.0))
            runtime.world.structures["wall"] = StructureRuntime(
                structure_id="wall",
                blueprint_id="bp_wood_wall",
                coordinate=WorldCoordinate(5.0, 0.0, 0.0),
                orientation_yaw=0.0,
                owner_player_id="human",
                health=100.0,
                max_health=100.0,
            )
            runtime.process_tick()
            self.assertIsNone(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_sound_event_can_trigger_investigation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(2.0, 0.0, 2.0))
            transport.submit_command_intent(ClientCommandIntent("snd", "human", "player.emit_sound", {"event_type": "shout"}))
            runtime.process_tick()
            self.assertIn(runtime.world.npcs["npc_survivor_a"].ai_state.behavior_state, {"investigate", "flee", "combat"})

    def test_sound_event_outside_configured_conditions_does_not_trigger_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(2.0, 0.0, 2.0))
            transport.submit_command_intent(ClientCommandIntent("snd", "human", "player.emit_sound", {"event_type": "forged"}))
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])

    def test_sensory_memory_stores_last_known_location(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 18.0))
            runtime.process_tick()
            memory = runtime.world.npcs["npc_zombie_a"].sensory_memory.get("human")
            self.assertIsNotNone(memory)
            self.assertEqual(memory.last_known_position, WorldCoordinate(20.0, 0.0, 18.0))

    def test_zombie_selects_valid_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 20.0))
            runtime.process_tick()
            self.assertEqual(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_type, "player_human")

    def test_target_selection_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_a, _ = build_runtime(root / "a")
            runtime_b, _ = build_runtime(root / "b")
            for runtime in (runtime_a, runtime_b):
                runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
                runtime.join_player("human_b", PlayerForm.HUMAN, WorldCoordinate(21.0, 0.0, 21.0))
                runtime.process_tick()
            self.assertEqual(
                runtime_a.world.npcs["npc_zombie_a"].ai_state.primary_target_id,
                runtime_b.world.npcs["npc_zombie_a"].ai_state.primary_target_id,
            )

    def test_target_persistence_prevents_unnecessary_thrashing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 20.0))
            runtime.join_player("human_b", PlayerForm.HUMAN, WorldCoordinate(20.5, 0.0, 20.5))
            runtime.process_tick()
            first = runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id
            runtime.process_tick()
            self.assertEqual(first, runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_zombie_can_retarget_when_threshold_is_met(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.world.npcs["npc_survivor_a"].coordinate = WorldCoordinate(300.0, 0.0, 300.0)
            runtime.join_player("human_far", PlayerForm.HUMAN, WorldCoordinate(30.0, 0.0, 18.0))
            runtime.process_tick()
            runtime.join_player("human_close", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 18.0))
            transport.submit_command_intent(
                ClientCommandIntent("sound_close", "human_close", "player.emit_sound", {"event_type": "shout"})
            )
            runtime.world.npcs["npc_zombie_a"].ai_state.target_locked_until_tick = runtime._tick_index
            runtime.world.npcs["npc_zombie_a"].ai_state.last_target_switch_tick = -9999
            runtime.process_tick()
            self.assertEqual(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id, "human_close")

    def test_player_zombie_walking_does_not_recruit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(17.0, 0.0, 17.0))
            transport.submit_command_intent(
                ClientCommandIntent("walk", "z", "player.move", {"target_x": 19.0, "target_y": 0.0, "target_z": 19.0})
            )
            runtime.process_tick()
            self.assertIsNone(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_player_zombie_attacking_human_can_create_recruitment_opportunity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(18.0, 0.0, 18.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 18.0))
            transport.submit_command_intent(
                ClientCommandIntent("atk", "z", "player.interact", {"action": "attack_player", "target_player_id": "human_a"})
            )
            runtime.process_tick()
            self.assertEqual(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id, "human_a")

    def test_recruitment_is_conditional_not_guaranteed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.world.npcs["npc_zombie_b"] = NpcRuntime("npc_zombie_b", "npc_zombie", WorldCoordinate(19.0, 0.0, 18.0))
            runtime.world.npcs["npc_zombie_c"] = NpcRuntime("npc_zombie_c", "npc_zombie", WorldCoordinate(19.5, 0.0, 18.0))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(18.0, 0.0, 18.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 18.0))
            transport.submit_command_intent(
                ClientCommandIntent("atk", "z", "player.interact", {"action": "attack_player", "target_player_id": "human_a"})
            )
            runtime.process_tick()
            recruited = [
                npc_id
                for npc_id in ("npc_zombie_b", "npc_zombie_c")
                if runtime.world.npcs[npc_id].ai_state.primary_target_id == "human_a"
            ]
            self.assertTrue(recruited)
            self.assertNotEqual(len(recruited), 2)

    def test_client_cannot_force_npc_recruitment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "horde.force_npc_recruit", {"npc_id": "npc_zombie_a"}))
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")

    def test_recruited_npc_joins_pursuit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(18.0, 0.0, 18.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 18.0))
            transport.submit_command_intent(
                ClientCommandIntent("atk", "z", "player.interact", {"action": "attack_player", "target_player_id": "human_a"})
            )
            runtime.process_tick()
            horde_id = runtime.world.npcs["npc_zombie_a"].ai_state.horde_id
            self.assertIn("npc_zombie_a", runtime.world.hordes[horde_id].member_npc_ids)

    def test_horde_members_retain_individual_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_zombie_b"] = NpcRuntime("npc_zombie_b", "npc_zombie", WorldCoordinate(19.0, 0.0, 19.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.5, 0.0, 19.5))
            runtime.process_tick()
            runtime.world.npcs["npc_zombie_b"].ai_state.behavior_state = "search"
            self.assertNotEqual(
                runtime.world.npcs["npc_zombie_a"].ai_state.behavior_state,
                runtime.world.npcs["npc_zombie_b"].ai_state.behavior_state,
            )

    def test_one_zombie_has_one_primary_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.join_player("human_b", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 20.0))
            runtime.process_tick()
            self.assertIsInstance(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id, str)

    def test_additional_humans_can_cause_target_splitting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_zombie_b"] = NpcRuntime("npc_zombie_b", "npc_zombie", WorldCoordinate(19.0, 0.0, 20.0))
            runtime.world.npcs["npc_zombie_c"] = NpcRuntime("npc_zombie_c", "npc_zombie", WorldCoordinate(21.0, 0.0, 20.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.join_player("human_b", PlayerForm.HUMAN, WorldCoordinate(22.0, 0.0, 22.0))
            runtime.process_tick()
            targets = {runtime.world.npcs[n].ai_state.primary_target_id for n in ["npc_zombie_a", "npc_zombie_b", "npc_zombie_c"]}
            self.assertGreaterEqual(len(targets), 2)

    def test_horde_can_split_dynamically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_zombie_b"] = NpcRuntime("npc_zombie_b", "npc_zombie", WorldCoordinate(19.0, 0.0, 20.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.join_player("human_b", PlayerForm.HUMAN, WorldCoordinate(23.0, 0.0, 23.0))
            runtime.process_tick()
            horde_ids = {runtime.world.npcs[n].ai_state.horde_id for n in ["npc_zombie_a", "npc_zombie_b"]}
            self.assertGreaterEqual(len(horde_ids), 1)

    def test_original_target_can_retain_some_pursuing_zombies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_zombie_b"] = NpcRuntime("npc_zombie_b", "npc_zombie", WorldCoordinate(19.0, 0.0, 20.0))
            runtime.join_player("human_a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.join_player("human_b", PlayerForm.HUMAN, WorldCoordinate(26.0, 0.0, 26.0))
            runtime.process_tick()
            pursuers_a = [n for n in ["npc_zombie_a", "npc_zombie_b"] if runtime.world.npcs[n].ai_state.primary_target_id == "human_a"]
            self.assertTrue(pursuers_a)

    def test_target_switching_is_server_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.process_tick()
            before = runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "npc.switch_target", {"npc_id": "npc_zombie_a"}))
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])
            self.assertEqual(before, runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_target_switching_does_not_thrash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("a", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.join_player("b", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 20.0))
            runtime.process_tick()
            t1 = runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id
            runtime.process_tick()
            t2 = runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id
            self.assertEqual(t1, t2)

    def test_zombies_can_abandon_impossible_pursuit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.process_tick()
            provider = runtime.navigation_provider
            assert isinstance(provider, DeterministicChunkNavigationProvider)
            for key in runtime.world.npcs["npc_zombie_a"].ai_state.last_path_chunk_keys:
                provider.blocked_chunk_keys.add(key)
            runtime.process_tick()
            self.assertIsNone(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id)

    def test_abandoned_zombies_return_to_search_wander_or_regroup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.process_tick()
            provider = runtime.navigation_provider
            assert isinstance(provider, DeterministicChunkNavigationProvider)
            for key in runtime.world.npcs["npc_zombie_a"].ai_state.last_path_chunk_keys:
                provider.blocked_chunk_keys.add(key)
            runtime.process_tick()
            self.assertIn(runtime.world.npcs["npc_zombie_a"].ai_state.behavior_state, {"search", "wander"})

    def test_zombies_can_form_new_pursuit_groups_dynamically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.hordes["custom"] = HordeRuntime(horde_id="custom")
            runtime.world.npcs["npc_zombie_b"] = NpcRuntime("npc_zombie_b", "npc_zombie", WorldCoordinate(19.0, 0.0, 20.0))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(19.0, 0.0, 19.0))
            runtime.process_tick()
            dynamic_hordes = [hid for hid in runtime.world.hordes if hid.startswith("horde_target_")]
            self.assertTrue(dynamic_hordes)

    def test_human_npc_detects_threat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(3.0, 0.0, 2.0))
            runtime.process_tick()
            self.assertIn(runtime.world.npcs["npc_survivor_a"].ai_state.behavior_state, {"flee", "combat"})

    def test_human_npc_can_flee_or_respond(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            start = runtime.world.npcs["npc_survivor_a"].coordinate
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(3.0, 0.0, 2.0))
            runtime.process_tick()
            behavior = runtime.world.npcs["npc_survivor_a"].ai_state.behavior_state
            if behavior == "flee":
                self.assertNotEqual(runtime.world.npcs["npc_survivor_a"].coordinate, start)
            else:
                self.assertEqual(behavior, "combat")

    def test_human_npc_can_become_zombie_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, _ = build_runtime(Path(directory))
            runtime.world.npcs["npc_survivor_a"].coordinate = WorldCoordinate(19.0, 0.0, 19.0)
            runtime.process_tick()
            self.assertEqual(runtime.world.npcs["npc_zombie_a"].ai_state.primary_target_id, "npc_survivor_a")

    def test_client_cannot_set_perception_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "npc.perception.set", {"npc_id": "npc_zombie_a"}))
            runtime.process_tick()
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")

    def test_client_cannot_set_zombie_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "npc.target.set", {"target": "human"}))
            runtime.process_tick()
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")

    def test_client_cannot_force_horde_membership(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(
                ClientCommandIntent("hack", "human", "horde.membership", {"horde_id": "horde_alpha", "action": "join"})
            )
            runtime.process_tick()
            self.assertEqual(runtime.command_results[0]["reason"], "horde_requires_zombie")

    def test_client_cannot_force_target_switching(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "npc.target.switch", {"npc_id": "npc_zombie_a"}))
            runtime.process_tick()
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")

    def test_client_cannot_force_pursuit_abandonment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "npc.pursuit.abandon", {"npc_id": "npc_zombie_a"}))
            runtime.process_tick()
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")

    def test_client_cannot_directly_control_npc_ai_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(ClientCommandIntent("hack", "human", "npc.state.set", {"state": "chase"}))
            runtime.process_tick()
            self.assertEqual(runtime.command_results[0]["reason"], "unknown_topic")

    def test_required_persistent_ai_state_survives_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, _ = build_runtime(root)
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 18.0))
            runtime.process_tick()
            runtime.shutdown()

            restored, _ = build_runtime(root)
            restored.start()
            self.assertIn("npc_zombie_a", restored.world.npcs)
            self.assertTrue(restored.world.npcs["npc_zombie_a"].sensory_memory)

    def test_transient_ai_calculations_are_not_unnecessarily_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, _ = build_runtime(root)
            runtime.join_player("human", PlayerForm.HUMAN, WorldCoordinate(20.0, 0.0, 18.0))
            runtime.process_tick()
            runtime.shutdown()
            world_payload = (root / "world.json").read_text()
            self.assertNotIn("perception_events", world_payload)


if __name__ == "__main__":
    unittest.main()
