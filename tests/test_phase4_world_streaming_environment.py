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
from prototypes.core.phase4_world import (
    ChunkCoordinate,
    ChunkIdentity,
    ChunkInterestManager,
    ChunkLifecycleState,
    ChunkPersistentDelta,
    ChunkRecord,
    DeterministicWorldGenerator,
    EntityPersistenceClass,
    InterestRadii,
    RegionCoordinate,
    ResourceAuthorityService,
    ResourceHarvestRule,
    ResourceNodeState,
    SpawnAuthorityService,
    SpawnRuleDefinition,
    WorldBounds,
    WorldCoordinateMapper,
    WorldGridDefinition,
    WorldPosition,
    load_phase4_world_definitions,
)


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


class Phase4WorldStreamingEnvironmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mapper = WorldCoordinateMapper(
            WorldGridDefinition(
                chunk_size_xz=64,
                chunk_height=32,
                chunks_per_region_xz=8,
                chunks_per_region_y=8,
                world_bounds=WorldBounds(
                    minimum_x=-4096,
                    maximum_x=4096,
                    minimum_y=-256,
                    maximum_y=256,
                    minimum_z=-4096,
                    maximum_z=4096,
                ),
            )
        )

    def test_coordinate_conversion_positive(self) -> None:
        address = self.mapper.to_world_address(WorldPosition(x=130, y=33, z=64))
        self.assertEqual((address.chunk.x, address.chunk.y, address.chunk.z), (2, 1, 1))

    def test_coordinate_conversion_negative(self) -> None:
        address = self.mapper.to_world_address(WorldPosition(x=-1, y=-1, z=-65))
        self.assertEqual((address.chunk.x, address.chunk.y, address.chunk.z), (-1, -1, -2))
        self.assertEqual((address.local.x, address.local.y, address.local.z), (63, 31, 63))

    def test_chunk_boundary_conversion(self) -> None:
        a = self.mapper.to_world_address(WorldPosition(x=63, y=0, z=63))
        b = self.mapper.to_world_address(WorldPosition(x=64, y=0, z=64))
        self.assertEqual((a.chunk.x, a.chunk.z), (0, 0))
        self.assertEqual((b.chunk.x, b.chunk.z), (1, 1))

    def test_region_boundary_conversion(self) -> None:
        address = self.mapper.to_world_address(WorldPosition(x=512, y=0, z=512))
        self.assertEqual((address.region.x, address.region.z), (1, 1))

    def test_vertical_boundary_conversion(self) -> None:
        low = self.mapper.to_world_address(WorldPosition(x=0, y=-256, z=0))
        high = self.mapper.to_world_address(WorldPosition(x=0, y=256, z=0))
        self.assertLessEqual(low.chunk.y, high.chunk.y)

    def test_extreme_valid_coordinates(self) -> None:
        address = self.mapper.to_world_address(WorldPosition(x=4096, y=256, z=-4096))
        self.assertIsNotNone(address)

    def test_invalid_coordinates_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.mapper.to_world_address(WorldPosition(x=5000, y=0, z=0))

    def test_world_reverse_conversion(self) -> None:
        chunk = ChunkCoordinate(x=-2, y=1, z=3)
        world = self.mapper.from_chunk_local(chunk, local=self.mapper.to_local_coordinate(WorldPosition(x=-100, y=40, z=200), chunk))
        self.assertEqual(world, WorldPosition(x=-100, y=40, z=200))

    def test_chunk_lifecycle_transitions(self) -> None:
        identity = ChunkIdentity(coordinate=ChunkCoordinate(1, 0, 1), region=self.mapper.to_region_coordinate(ChunkCoordinate(1, 0, 1)), generation_version=1)
        chunk = ChunkRecord(identity=identity)
        chunk.request_load()
        chunk.mark_active()
        chunk.request_unload()
        chunk.mark_unloaded()
        self.assertEqual(chunk.state, ChunkLifecycleState.UNLOADED)

    def test_chunk_failed_loading_state(self) -> None:
        identity = ChunkIdentity(coordinate=ChunkCoordinate(1, 0, 1), region=self.mapper.to_region_coordinate(ChunkCoordinate(1, 0, 1)), generation_version=1)
        chunk = ChunkRecord(identity=identity)
        chunk.mark_failed("io_error")
        self.assertEqual(chunk.state, ChunkLifecycleState.FAILED)

    def test_chunk_identity_is_deterministic(self) -> None:
        identity_a = ChunkIdentity(coordinate=ChunkCoordinate(3, 2, 1), region=RegionCoordinate(x=0, y=0, z=0), generation_version=1)
        identity_b = ChunkIdentity(coordinate=ChunkCoordinate(3, 2, 1), region=RegionCoordinate(x=0, y=0, z=0), generation_version=1)
        self.assertEqual(identity_a.key, identity_b.key)

    def test_interest_selects_nearby_chunks(self) -> None:
        manager = ChunkInterestManager(InterestRadii(2, 2, 3, 2, 1))
        relevant = manager.relevant_chunks(ChunkCoordinate(10, 0, 10))
        self.assertIn(ChunkCoordinate(11, 1, 11), relevant)

    def test_interest_excludes_distant_chunks(self) -> None:
        manager = ChunkInterestManager(InterestRadii(1, 1, 2, 1, 0))
        self.assertFalse(manager.chunk_is_relevant(ChunkCoordinate(0, 0, 0), ChunkCoordinate(3, 0, 0)))

    def test_interest_vertical_relevance(self) -> None:
        manager = ChunkInterestManager(InterestRadii(1, 1, 2, 1, 1))
        self.assertTrue(manager.chunk_is_relevant(ChunkCoordinate(0, 0, 0), ChunkCoordinate(0, 1, 0)))
        self.assertFalse(manager.chunk_is_relevant(ChunkCoordinate(0, 0, 0), ChunkCoordinate(0, 2, 0)))

    def test_generation_same_seed_and_chunk_same_baseline(self) -> None:
        generator = DeterministicWorldGenerator(seed=42, generation_version=3)
        chunk = ChunkCoordinate(4, 0, -1)
        a = generator.generate_chunk(chunk)
        b = generator.generate_chunk(chunk)
        self.assertEqual(a, b)

    def test_generation_different_coordinates_different_baseline(self) -> None:
        generator = DeterministicWorldGenerator(seed=42, generation_version=3)
        a = generator.generate_chunk(ChunkCoordinate(1, 0, 1))
        b = generator.generate_chunk(ChunkCoordinate(2, 0, 1))
        self.assertNotEqual(a.chunk_coordinate, b.chunk_coordinate)
        self.assertNotEqual(a.terrain.base_height, b.terrain.base_height)

    def test_persistent_delta_does_not_overwrite_baseline(self) -> None:
        delta = ChunkPersistentDelta(destroyed_structure_ids={"house_a"})
        self.assertIn("house_a", delta.destroyed_structure_ids)

    def test_resource_node_is_chunk_owned(self) -> None:
        node = ResourceNodeState(
            node_id="node",
            node_type="wood",
            position=WorldPosition(0, 0, 0),
            chunk_coordinate=ChunkCoordinate(0, 0, 0),
            quantity=3,
            max_quantity=3,
            respawn_ticks=2,
        )
        self.assertEqual(node.chunk_coordinate, ChunkCoordinate(0, 0, 0))

    def test_resource_gather_is_server_authoritative(self) -> None:
        authority = ResourceAuthorityService({"wood": ResourceHarvestRule(gather_distance=3, required_tool_tags=("axe",))})
        node = ResourceNodeState("node", "wood", WorldPosition(0, 0, 0), ChunkCoordinate(0, 0, 0), 2, 2, 2)
        ok, reason, _ = authority.harvest(node, WorldPosition(0, 0, 0), {"hand"}, 1)
        self.assertFalse(ok)
        self.assertEqual(reason, "missing_required_tool")

    def test_resource_depletion_persists_and_respawns(self) -> None:
        authority = ResourceAuthorityService({"wood": ResourceHarvestRule(gather_distance=4)})
        node = ResourceNodeState("node", "wood", WorldPosition(0, 0, 0), ChunkCoordinate(0, 0, 0), 1, 1, 2)
        ok, _, qty = authority.harvest(node, WorldPosition(0, 0, 0), set(), 1)
        self.assertTrue(ok)
        self.assertEqual(qty, 1)
        self.assertEqual(node.quantity, 0)
        authority.tick_respawn(node)
        authority.tick_respawn(node)
        self.assertEqual(node.quantity, 1)

    def test_spawn_rules_are_authoritative(self) -> None:
        rules = {
            "npc_zombie": SpawnRuleDefinition(
                spawn_type="npc_zombie",
                allowed_biomes=("urban",),
                max_active=2,
                min_distance_from_players=10,
            )
        }
        service = SpawnAuthorityService(rules)
        self.assertFalse(service.can_spawn("npc_zombie", "forest", 0, 20))
        self.assertFalse(service.can_spawn("npc_zombie", "urban", 2, 20))
        self.assertTrue(service.can_spawn("npc_zombie", "urban", 1, 20))

    def test_spawn_despawn_distinguishes_persistence_classes(self) -> None:
        self.assertFalse(SpawnAuthorityService.can_despawn(EntityPersistenceClass.PERSISTENT, inside_interest=False))
        self.assertTrue(SpawnAuthorityService.can_despawn(EntityPersistenceClass.TRANSIENT, inside_interest=False))

    def test_phase4_definitions_load(self) -> None:
        definitions = load_phase4_world_definitions(
            Path(__file__).resolve().parents[1] / "data" / "phase4_world_definitions.json"
        )
        self.assertIn("urban", definitions.biomes)
        self.assertIn("spring", definitions.seasons)
        self.assertIn("poi_house", definitions.pois)

    def test_runtime_interest_is_server_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="force_chunk",
                    player_id="player_a",
                    topic="world.force_chunk_load",
                    payload={"chunk_key": "100:0:100"},
                )
            )
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])

    def test_runtime_rejects_out_of_world_bounds_move(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="move_oob",
                    player_id="player_a",
                    topic="player.move",
                    payload={"target_x": 99999999.0, "target_y": 0.0, "target_z": 0.0},
                )
            )
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])
            self.assertEqual(runtime.command_results[0]["reason"], "position_out_of_world_bounds")

    def test_runtime_chunk_lifecycle_metadata_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.process_tick()
            active = [chunk for chunk in runtime.world.chunks.values() if chunk.active]
            self.assertTrue(active)
            self.assertTrue(all(chunk.lifecycle_state == ChunkLifecycleState.ACTIVE.value for chunk in active))
            runtime.players["player_a"].human_state.position = WorldCoordinate(1024.0, 0.0, 1024.0)
            runtime.process_tick()
            self.assertTrue(any(chunk.lifecycle_state in {ChunkLifecycleState.UNLOADING.value, ChunkLifecycleState.UNLOADED.value} for chunk in runtime.world.chunks.values()))

    def test_runtime_persists_destroyed_structure_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime, transport = build_runtime(root)
            runtime.join_player("owner", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.players["owner"].inventory.add_item(runtime._item_definition_for("wood_log"), 4)
            runtime.players["owner"].inventory.add_item(runtime._item_definition_for("metal_plate"), 2)
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="build",
                    player_id="owner",
                    topic="structure.build",
                    payload={"structure_id": "s1", "blueprint_id": "bp_wood_wall", "x": 1.0, "y": 0.0, "z": 1.0},
                )
            )
            runtime.process_tick()
            runtime.join_player("z", PlayerForm.ZOMBIE, WorldCoordinate(1.0, 0.0, 1.0))
            for _ in range(20):
                transport.submit_command_intent(
                    ClientCommandIntent(
                        command_id=f"damage_{_}",
                        player_id="z",
                        topic="structure.damage",
                        payload={"structure_id": "s1"},
                    )
                )
                runtime.process_tick()
                if runtime.world.structures["s1"].state == "destroyed":
                    break
            runtime.shutdown()

            restored, _ = build_runtime(root)
            self.assertEqual(restored.world.structures["s1"].state, "destroyed")

    def test_runtime_replication_does_not_send_unrelated_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            runtime.process_tick()
            payload = transport.pop_snapshots("player_a")[-1]
            self.assertNotIn("999:0:999", payload.get("active_chunks", []))

    def test_runtime_rejects_unknown_world_mutation_topics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime, transport = build_runtime(Path(directory))
            runtime.join_player("player_a", PlayerForm.HUMAN, WorldCoordinate(0.0, 0.0, 0.0))
            transport.submit_command_intent(
                ClientCommandIntent(
                    command_id="inject_spawn",
                    player_id="player_a",
                    topic="world.spawn_entity",
                    payload={"npc_type": "npc_zombie", "count": 1000},
                )
            )
            runtime.process_tick()
            self.assertFalse(runtime.command_results[0]["accepted"])


if __name__ == "__main__":
    unittest.main()
