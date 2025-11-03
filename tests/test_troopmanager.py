import unittest
from unittest.mock import MagicMock, patch
from game.troopmanager import TroopManager

class TestTroopManager(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = 123
        self.troop_manager = TroopManager(self.wrapper, self.village_id)
        self.troop_manager.logger = MagicMock()

    @patch('core.extractors.Extractor.smith_data')
    def test_get_planned_actions_hides_completed_research(self, mock_smith_data):
        """
        Tests that get_planned_actions does not include research tasks
        for units that are already at or above the target level.
        """
        # Arrange
        self.troop_manager.wanted_levels = {"axe": 1, "light": 1}
        mock_smith_data.return_value = {
            "available": {
                "axe": {"level": "1"},
                "light": {"level": "0"}
            }
        }
        self.wrapper.get_action.return_value = "mocked_html"

        # Act
        actions = self.troop_manager.get_planned_actions()

        # Assert
        self.assertIn("Research Light to level 1", actions)
        self.assertNotIn("Research Axe to level 1", actions)
        self.wrapper.get_action.assert_called_once_with(village_id=123, action="smith")

if __name__ == '__main__':
    unittest.main()
