import unittest
from unittest.mock import MagicMock, patch
from game.troopmanager import TroopManager

class TestTroopManager(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = 123
        self.troop_manager = TroopManager(self.wrapper, self.village_id)
        self.troop_manager.logger = MagicMock()

    def test_recruit_unresearched_unit_with_insufficient_resources(self):
        # The bot should not attempt to recruit a unit if it is not researched and there are insufficient resources to research it.
        self.troop_manager.recruit_data = {}
        self.troop_manager._research_failed_resources = True
        self.wrapper.get_action.return_value = ""
        self.wrapper.reporter.report = MagicMock()
        result = self.troop_manager.recruit('axe', 10)
        self.assertFalse(result)
        self.troop_manager.logger.debug.assert_called_with("Skipping recruitment, waiting for research resources")

if __name__ == '__main__':
    unittest.main()
