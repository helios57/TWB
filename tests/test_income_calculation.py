import unittest
from unittest.mock import MagicMock

from game.resources import ResourceManager


class TestIncomeCalculation(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "12345"
        self.resource_manager = ResourceManager(self.wrapper, self.village_id)

    def test_income_calculation_with_valid_data(self):
        """Verify income calculation with a complete game_state."""
        game_state = {
            'village': {
                'wood_prod': 100,
                'stone_prod': 150,
                'iron_prod': 200,
            }
        }
        self.resource_manager.calculate_income(game_state)
        self.assertEqual(self.resource_manager.income['wood'], 100)
        self.assertEqual(self.resource_manager.income['stone'], 150)
        self.assertEqual(self.resource_manager.income['iron'], 200)

    def test_income_calculation_with_missing_data(self):
        """Verify income calculation with a partial game_state."""
        game_state = {
            'village': {
                'wood_prod': 100,
            }
        }
        self.resource_manager.calculate_income(game_state)
        self.assertEqual(self.resource_manager.income['wood'], 100)
        self.assertEqual(self.resource_manager.income.get('stone', 0), 0)
        self.assertEqual(self.resource_manager.income.get('iron', 0), 0)

    def test_income_calculation_with_no_data(self):
        """Verify income calculation with an empty game_state."""
        game_state = {
            'village': {}
        }
        self.resource_manager.calculate_income(game_state)
        self.assertEqual(self.resource_manager.income.get('wood', 0), 0)
        self.assertEqual(self.resource_manager.income.get('stone', 0), 0)
        self.assertEqual(self.resource_manager.income.get('iron', 0), 0)


if __name__ == '__main__':
    unittest.main()
