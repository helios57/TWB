import unittest
from unittest.mock import MagicMock, patch
from game.gamestate import GameState
from game.village import Village
from game.resources import ResourceManager
from game.buildingmanager import BuildingManager
from game.troopmanager import TroopManager

class TestGameStatePopulation(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village = Village(village_id='123', wrapper=self.wrapper)
        self.village.logger = MagicMock()
        self.game_state_model = self.village.game_state_model

        # Mock game data
        self.raw_game_state = {
            "village": {
                "wood": 100, "stone": 150, "iron": 200, "pop": 50, "pop_max": 1000,
                "storage_max": 2000, "wood_prod": 10, "stone_prod": 12, "iron_prod": 15,
                "buildings": {"main": 5, "barracks": 3, "stable": 1}
            }
        }
        self.village.game_data = self.raw_game_state

    def test_resource_manager_populates_game_state(self):
        # Arrange
        resman = ResourceManager(wrapper=self.wrapper, village_id='123')
        resman.income = {'total': {'wood': 10, 'clay': 12, 'iron': 15}}

        # Act
        resman.update_game_state(self.game_state_model, self.raw_game_state)

        # Assert
        self.assertEqual(self.game_state_model.resources['wood'], 100)
        self.assertEqual(self.game_state_model.storage_capacity, 2000)
        self.assertEqual(self.game_state_model.resource_income['stone'], 12)
        self.assertNotEqual(self.game_state_model.timestamp, 0)

    def test_building_manager_populates_game_state(self):
        # Arrange
        buildman = BuildingManager(wrapper=self.wrapper, village_id='123')
        buildman.levels = {"main": 5, "barracks": 3, "stable": 1}
        buildman.waits_building = ["main"]

        # Act
        buildman.update_game_state(self.game_state_model)

        # Assert
        self.assertEqual(self.game_state_model.building_levels['barracks'], 3)
        self.assertEqual(self.game_state_model.building_queue, ["main"])

    def test_troop_manager_populates_game_state(self):
        # Arrange
        troopman = TroopManager(wrapper=self.wrapper, village_id='123')
        troopman.total_troops = {'spear': 50, 'sword': 10}
        troopman.troops = {'spear': 50, 'sword': 10}
        troopman.wait_for = {'123': {'barracks': 12345, 'stable': 0, 'garage': 0}}

        # Act
        with patch('time.time', return_value=12340):
            troopman.update_game_state(self.game_state_model)

        # Assert
        self.assertEqual(self.game_state_model.troop_counts['spear'], 50)
        self.assertEqual(self.game_state_model.units_in_village['sword'], 10)
        self.assertEqual(self.game_state_model.troop_queue['barracks_queue_time'], 5)

if __name__ == '__main__':
    unittest.main()
