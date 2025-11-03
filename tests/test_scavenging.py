import unittest
from unittest.mock import MagicMock, patch
from game.troopmanager import TroopManager

class TestScavenging(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = 123
        self.troop_manager = TroopManager(self.wrapper, self.village_id)
        self.troop_manager.logger = MagicMock()

    def test_unlock_gather_options_respects_warehouse_capacity(self):
        """
        Tests that the final gather option is not unlocked if warehouse capacity is less than 12000.
        """
        # Arrange
        village_data = {
            'options': {
                4: {
                    'is_locked': True,
                    'unlock_costs': {'wood': 100, 'stone': 100, 'iron': 100}
                }
            }
        }
        self.troop_manager.game_data = {
            'village': {
                'storage_max': 11000,
                'wood': 200, 'stone': 200, 'iron': 200
            }
        }
        self.troop_manager.wrapper.get_api_action.return_value = None

        # Act
        unlocked = self.troop_manager._unlock_gather_options(village_data)

        # Assert
        self.assertFalse(unlocked)
        self.troop_manager.logger.info.assert_called_with("Skipping unlock of final gather option: warehouse capacity is less than 12000.")

    def test_unlock_gather_options_unlocks_when_capacity_sufficient(self):
        """
        Tests that the final gather option is unlocked if warehouse capacity is sufficient.
        """
        # Arrange
        village_data = {
            'options': {
                4: {
                    'is_locked': True,
                    'unlock_costs': {'wood': 100, 'stone': 100, 'iron': 100}
                }
            }
        }
        self.troop_manager.game_data = {
            'village': {
                'storage_max': 13000,
                'wood': 200, 'stone': 200, 'iron': 200
            }
        }
        # Simulate a successful API call
        self.troop_manager.wrapper.get_api_action.return_value = {"success": True}

        # Act
        unlocked = self.troop_manager._unlock_gather_options(village_data)

        # Assert
        self.assertTrue(unlocked)
        self.troop_manager.logger.info.assert_any_call("Attempting to unlock gather option 4...")

if __name__ == '__main__':
    unittest.main()
