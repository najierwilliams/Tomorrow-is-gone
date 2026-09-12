import unittest

from prototypes.core.phase15_contracts import (
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
        self.assertEqual(address.chunk_z, -1)
        self.assertEqual(address.region_x, 0)
        self.assertEqual(address.region_z, -1)

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


if __name__ == "__main__":
    unittest.main()
