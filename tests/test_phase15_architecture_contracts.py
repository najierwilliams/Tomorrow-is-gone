import unittest

from prototypes.core.phase15_contracts import (
    AuthorityRole,
    ClientCommandIntent,
    LootContainerDefinition,
    LootTierDefinition,
    ReplicationRule,
    ZombieSanityBandDefinition,
    resolve_zombie_sanity_band,
    PlayerForm,
    PlayerStateModel,
    ServerConfiguration,
    ServerRuleSet,
    WorldCoordinate,
    WorldGridConfig,
    is_valid_form_transition,
    PersistenceLayout,
    AnimalAbilityDefinition,
    AnimalAbilityDomain,
)


class Phase15ArchitectureContractTests(unittest.TestCase):
    def test_unified_player_forms_support_infection_and_cure(self) -> None:
        state = PlayerStateModel(player_id="p-1", form=PlayerForm.HUMAN)
        self.assertEqual(state.form, PlayerForm.HUMAN)

        self.assertTrue(is_valid_form_transition(PlayerForm.HUMAN, PlayerForm.INFECTED_HUMAN))
        self.assertTrue(is_valid_form_transition(PlayerForm.INFECTED_HUMAN, PlayerForm.ZOMBIE))
        self.assertFalse(is_valid_form_transition(PlayerForm.INFECTED_HUMAN, PlayerForm.HUMAN))
        self.assertTrue(
            is_valid_form_transition(
                PlayerForm.INFECTED_HUMAN,
                PlayerForm.HUMAN,
                cure_available=True,
            )
        )
        self.assertFalse(is_valid_form_transition(PlayerForm.ZOMBIE, PlayerForm.HUMAN))
        self.assertTrue(
            is_valid_form_transition(
                PlayerForm.ZOMBIE,
                PlayerForm.HUMAN,
                cure_available=True,
            )
        )

    def test_world_grid_contract_supports_large_map_streaming_addresses(self) -> None:
        grid = WorldGridConfig(chunk_size_meters=64, chunks_per_region=64)

        address = grid.to_chunk_address(WorldCoordinate(x=130.0, y=0.0, z=-1.0))

        self.assertEqual(address.chunk_x, 2)
        self.assertEqual(address.chunk_y, 0)
        self.assertEqual(address.chunk_z, -1)
        self.assertEqual(address.region_x, 0)
        self.assertEqual(address.region_y, 0)
        self.assertEqual(address.region_z, -1)

    def test_world_grid_contract_supports_configurable_finite_vertical_range(self) -> None:
        grid = WorldGridConfig(
            chunk_size_meters=64,
            chunks_per_region=64,
            chunk_height_meters=32,
            chunks_per_vertical_region=32,
            minimum_world_y_meters=-128,
            maximum_world_y_meters=256,
        )

        address = grid.to_chunk_address(WorldCoordinate(x=0.0, y=-33.0, z=0.0))
        self.assertEqual(address.chunk_y, -2)
        self.assertEqual(address.region_y, -1)
        self.assertTrue(grid.supports_vertical_coordinate(255.0))
        self.assertFalse(grid.supports_vertical_coordinate(300.0))

        with self.assertRaises(ValueError):
            grid.to_chunk_address(WorldCoordinate(x=0.0, y=300.0, z=0.0))

    def test_server_configuration_is_data_driven(self) -> None:
        config = ServerConfiguration(
            server_id="srv-public-east",
            map_id="us_ny_manhattan",
            region_id="us-east",
            is_public=True,
            creative_mode_enabled=False,
            max_players=120,
            rule_set=ServerRuleSet(
                custom_rules={"friendly_fire": False, "drop_loot_on_death": True},
                custom_difficulty={"zombie_density": 1.25, "loot_abundance": 0.85},
                custom_mission_ids=["mission_human_scavenge_tier2", "mission_zombie_feed_night"],
            ),
        )

        self.assertIn("friendly_fire", config.rule_set.custom_rules)
        self.assertEqual(config.rule_set.custom_difficulty["zombie_density"], 1.25)
        self.assertEqual(len(config.rule_set.custom_mission_ids), 2)

    def test_persistence_layout_explicitly_separates_state_domains(self) -> None:
        layout = PersistenceLayout(
            player_state_store="players",
            world_state_store="world",
            inventory_state_store="inventories",
            structure_state_store="structures",
            destruction_state_store="destruction",
            vehicle_state_store="vehicles",
            npc_state_store="npcs",
            loot_state_store="loot",
            server_configuration_store="server_config",
        )

        self.assertEqual(
            layout.categories(),
            (
                "player",
                "world",
                "inventory",
                "structure",
                "destruction",
                "vehicle",
                "npc",
                "loot",
                "server_configuration",
            ),
        )

    def test_animal_abilities_are_data_driven_by_domain(self) -> None:
        ability = AnimalAbilityDefinition(
            ability_id="infected_hound_salvage",
            domain=AnimalAbilityDomain.RESOURCE_GATHERING,
            modifiers={"scrap_find_bonus": 0.2},
        )

        self.assertEqual(ability.domain, AnimalAbilityDomain.RESOURCE_GATHERING)
        self.assertGreater(ability.modifiers["scrap_find_bonus"], 0)

    def test_zombie_sanity_bands_are_data_driven(self) -> None:
        bands = [
            ZombieSanityBandDefinition(
                band_id="feral",
                minimum=0.0,
                maximum=30.0,
                human_coexistence_allowed=False,
                hostility_level=1.0,
                cure_eligible=False,
                mission_availability_tags=["predation"],
                behavior_tags=["attack_on_sight"],
            ),
            ZombieSanityBandDefinition(
                band_id="coexistence",
                minimum=30.0,
                maximum=100.0,
                human_coexistence_allowed=True,
                hostility_level=0.2,
                cure_eligible=True,
                mission_availability_tags=["trade", "alliance"],
                behavior_tags=["restraint"],
            ),
        ]

        low_sanity = resolve_zombie_sanity_band(10.0, bands)
        high_sanity = resolve_zombie_sanity_band(90.0, bands)

        self.assertIsNotNone(low_sanity)
        self.assertEqual(low_sanity.band_id, "feral")
        self.assertFalse(low_sanity.human_coexistence_allowed)
        self.assertIsNotNone(high_sanity)
        self.assertEqual(high_sanity.band_id, "coexistence")
        self.assertTrue(high_sanity.cure_eligible)

    def test_loot_container_to_tier_contract_distinguishes_pool_eligibility(self) -> None:
        tier = LootTierDefinition(
            tier_id="urban_residential_mid",
            weight=1.0,
            eligible_loot_pool_ids=["pool_food_basic", "pool_medical_basic"],
            eligible_categories=["food", "medical"],
            eligible_quality_levels=["common", "uncommon"],
        )
        container = LootContainerDefinition(
            container_type="house_fridge",
            container_tier_id="residential",
            tier_weights={tier.tier_id: tier.weight},
            respawn_seconds=1800,
        )

        self.assertEqual(container.container_tier_id, "residential")
        self.assertIn("food", tier.eligible_categories)
        self.assertIn("common", tier.eligible_quality_levels)
        self.assertIn("pool_food_basic", tier.eligible_loot_pool_ids)

    def test_replication_rule_remains_server_authoritative_and_client_intent_driven(self) -> None:
        rule = ReplicationRule(
            channel_id="player_state",
            authority=AuthorityRole.SERVER,
            state_topics=["player.form", "player.health", "player.position"],
            client_command_topics=["player.move", "player.interact"],
        )
        command = ClientCommandIntent(
            command_id="cmd-1",
            player_id="p-1",
            topic="player.move",
            payload={"target_x": 20.0, "target_z": 12.0},
        )

        self.assertEqual(rule.authority, AuthorityRole.SERVER)
        self.assertTrue(rule.server_authoritative)
        self.assertIn("player.move", rule.client_command_topics)
        self.assertEqual(command.topic, "player.move")


if __name__ == "__main__":
    unittest.main()
