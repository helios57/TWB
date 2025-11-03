import unittest
from unittest.mock import MagicMock, patch
import time

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
        with patch('game.resources.ReportCache.cache_grab', return_value={}):
            self.resource_manager.calculate_income(game_state)

        self.assertEqual(self.resource_manager.income['mines']['wood'], 100)
        self.assertEqual(self.resource_manager.income['mines']['clay'], 150)
        self.assertEqual(self.resource_manager.income['mines']['iron'], 200)
        self.assertEqual(self.resource_manager.income['farming']['wood'], 0)
        self.assertEqual(self.resource_manager.income['farming']['clay'], 0)
        self.assertEqual(self.resource_manager.income['farming']['iron'], 0)
        self.assertEqual(self.resource_manager.income['total']['wood'], 100)
        self.assertEqual(self.resource_manager.income['total']['clay'], 150)
        self.assertEqual(self.resource_manager.income['total']['iron'], 200)

    def test_income_calculation_with_missing_data(self):
        """Verify income calculation with a partial game_state."""
        game_state = {
            'village': {
                'wood_prod': 100,
            }
        }
        with patch('game.resources.ReportCache.cache_grab', return_value={}):
            self.resource_manager.calculate_income(game_state)

        self.assertEqual(self.resource_manager.income['mines']['wood'], 100)
        self.assertEqual(self.resource_manager.income['mines'].get('clay', 0), 0)
        self.assertEqual(self.resource_manager.income['mines'].get('iron', 0), 0)
        self.assertEqual(self.resource_manager.income['total']['wood'], 100)
        self.assertEqual(self.resource_manager.income['total'].get('clay', 0), 0)
        self.assertEqual(self.resource_manager.income['total'].get('iron', 0), 0)

    def test_income_calculation_with_no_data(self):
        """Verify income calculation with an empty game_state."""
        game_state = {
            'village': {}
        }
        with patch('game.resources.ReportCache.cache_grab', return_value={}):
            self.resource_manager.calculate_income(game_state)

        self.assertEqual(self.resource_manager.income['mines'].get('wood', 0), 0)
        self.assertEqual(self.resource_manager.income['mines'].get('clay', 0), 0)
        self.assertEqual(self.resource_manager.income['mines'].get('iron', 0), 0)
        self.assertEqual(self.resource_manager.income['total'].get('wood', 0), 0)
        self.assertEqual(self.resource_manager.income['total'].get('clay', 0), 0)
        self.assertEqual(self.resource_manager.income['total'].get('iron', 0), 0)

    @patch('time.time')
    @patch('game.resources.ReportCache.cache_grab')
    def test_farming_income_calculation(self, mock_cache_grab, mock_time):
        """Verify farming income calculation with mock report data."""
        now = 1678886400  # A fixed timestamp for "now"
        mock_time.return_value = now

        mock_reports = {
            'report1': {'type': 'attack', 'origin': '12345', 'extra': {'when': now - 7200, 'loot': {'wood': 100, 'stone': 150, 'iron': 50}}},
            'report2': {'type': 'attack', 'origin': '12345', 'extra': {'when': now - 3600, 'loot': {'wood': 200, 'stone': 150, 'iron': 250}}},
            'report3': {'type': 'attack', 'origin': '12345', 'extra': {'when': now - 90000, 'loot': {'wood': 1000, 'stone': 1000, 'iron': 1000}}}, # Too old
            'report4': {'type': 'attack', 'origin': '99999', 'extra': {'when': now - 3600, 'loot': {'wood': 500, 'stone': 500, 'iron': 500}}}, # Wrong origin
            'report5': {'type': 'support', 'origin': '12345', 'extra': {'when': now - 3600}}, # Wrong type
        }
        mock_cache_grab.return_value = mock_reports

        game_state = {
            'village': {
                'wood_prod': 100,
                'stone_prod': 150,
                'iron_prod': 200,
            }
        }

        self.resource_manager.calculate_income(game_state)

        # Expected calculation:
        # Total loot: wood=300, clay=300, iron=300
        # Duration: 2 hours (from the first report at now - 7200)
        # Income per hour: wood=150, clay=150, iron=150
        self.assertEqual(self.resource_manager.income['farming']['wood'], 150)
        self.assertEqual(self.resource_manager.income['farming']['clay'], 150)
        self.assertEqual(self.resource_manager.income['farming']['iron'], 150)

        # Verify total income
        self.assertEqual(self.resource_manager.income['total']['wood'], 100 + 150)
        self.assertEqual(self.resource_manager.income['total']['clay'], 150 + 150)
        self.assertEqual(self.resource_manager.income['total']['iron'], 200 + 150)


if __name__ == '__main__':
    unittest.main()
