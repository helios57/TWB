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

    @patch('core.extractors.Extractor.smith_data')
    def test_attempt_upgrade_skips_completed_research(self, mock_smith_data):
        """
        Tests that attempt_upgrade does not try to research a unit
        that is already at the desired level.
        """
        # Arrange
        self.troop_manager.wanted_levels = {"axe": 1}
        mock_smith_data.return_value = {
            "available": {
                "axe": {"level": "1", "can_research": False}
            }
        }
        self.wrapper.get_action.return_value = "mocked_html"

        # Act
        result = self.troop_manager.attempt_upgrade()

        # Assert
        self.assertFalse(result) # No upgrade should have been started
        self.troop_manager.logger.debug.assert_any_call("Unit axe is already at or above the desired level (1/1).")

    @patch('core.extractors.Extractor.smith_data')
    def test_attempt_upgrade_respects_research_failed_flag(self, mock_smith_data):
        """
        Tests that attempt_upgrade sets the _research_failed_resources flag
        when research fails due to lack of resources.
        """
        # Arrange
        self.troop_manager.wanted_levels = {"light": 1}
        self.troop_manager.game_data = {'village': {'wood': 10, 'stone': 10, 'iron': 10}}
        mock_smith_data.return_value = {
            "available": {
                "light": {
                    "level": "0",
                    "can_research": True,
                    "research_error": "Not enough resources",
                    "wood": 100, "stone": 100, "iron": 100
                }
            }
        }
        self.wrapper.get_action.return_value = "mocked_html"

        # Act
        self.troop_manager.attempt_upgrade()

        # Assert
        self.assertTrue(self.troop_manager._research_failed_resources)
        self.troop_manager.logger.debug.assert_any_call("Skipping research of %s because of research error (not enough resources)", "light")

    @patch('game.troopmanager.TroopManager.attempt_research')
    @patch('core.extractors.Extractor.recruit_data')
    def test_recruit_respects_research_failed_flag(self, mock_recruit_data, mock_attempt_research):
        """
        Tests that recruit does not attempt to research a unit if the
        _research_failed_resources flag is set.
        """
        # Arrange
        self.troop_manager._research_failed_resources = True
        mock_recruit_data.return_value = {} # Simulate unit not being in recruit_data
        self.wrapper.get_action.return_value.text = "mocked_html"


        # Act
        self.troop_manager.recruit(unit_type="axe", amount=10)

        # Assert
        mock_attempt_research.assert_not_called()
        self.troop_manager.logger.warning.assert_any_call("Recruitment of 10 axe failed because it is not researched")

    def test_get_template_action_merges_unlocked_stages(self):
        """
        Tests that get_template_action correctly merges the 'build' and 'upgrades'
        from all unlocked stages of a troop template.
        """
        # Arrange
        self.troop_manager.template = [
            {
                "building": "barracks", "level": 1,
                "build": {"barracks": {"spear": 50}},
                "upgrades": {"axe": 1}
            },
            {
                "building": "stable", "level": 1,
                "build": {"barracks": {"spear": 100}, "stable": {"spy": 10}},
                "upgrades": {"axe": 1, "light": 1}
            },
            {
                "building": "stable", "level": 3,
                "build": {"stable": {"spy": 20, "light": 50}}
            }
        ]
        building_levels = {"barracks": 5, "stable": 2}

        # Act
        result = self.troop_manager.get_template_action(building_levels)

        # Assert
        expected_build = {
            "barracks": {"spear": 100},
            "stable": {"spy": 10}
        }
        expected_upgrades = {"axe": 1, "light": 1}

        self.assertIsNotNone(result)
        self.assertEqual(result['build'], expected_build)
        self.assertEqual(self.troop_manager.wanted_levels, expected_upgrades)


class TestAutomatedHoarding(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = 123
        # Mock the village object that the TroopManager will interact with
        self.mock_village = MagicMock()
        self.mock_village._priority_research_unaffordable = False
        self.troop_manager = TroopManager(self.wrapper, self.village_id, village=self.mock_village)
        self.troop_manager.logger = MagicMock()
        self.troop_manager.resman = MagicMock()

    @patch('core.extractors.Extractor.smith_data')
    def test_hoard_mode_triggered_for_unaffordable_critical_unit(self, mock_smith_data):
        """
        Verify that when research for a critical unit (light cavalry) is unaffordable,
        the TroopManager signals the village to enter hoard mode.
        """
        # Arrange
        self.troop_manager.wanted_levels = {"light": 1}
        self.troop_manager.game_data = {'village': {'wood': 10, 'stone': 10, 'iron': 10}}
        mock_smith_data.return_value = {
            "available": {
                "light": {
                    "level": "0", "can_research": True, "research_error": "Not enough resources",
                    "wood": 100, "stone": 100, "iron": 100
                }
            }
        }
        self.wrapper.get_action.return_value.text = "mocked_html"

        # Act
        self.troop_manager.attempt_research("light", smith_data=mock_smith_data.return_value)

        # Assert
        self.assertTrue(self.mock_village._priority_research_unaffordable)
        self.troop_manager.logger.info.assert_any_call("Critical unit 'light' is unaffordable. Signaling village to hoard resources.")

    @patch('core.extractors.Extractor.smith_data')
    def test_hoard_mode_not_triggered_for_unaffordable_non_critical_unit(self, mock_smith_data):
        """
        Verify that when research for a non-critical unit (spy) is unaffordable,
        hoard mode is NOT triggered.
        """
        # Arrange
        self.troop_manager.wanted_levels = {"spy": 1}
        self.troop_manager.game_data = {'village': {'wood': 10, 'stone': 10, 'iron': 10}}
        mock_smith_data.return_value = {
            "available": {
                "spy": {
                    "level": "0", "can_research": True, "research_error": "Not enough resources",
                    "wood": 100, "stone": 100, "iron": 100
                }
            }
        }
        self.wrapper.get_action.return_value.text = "mocked_html"

        # Act
        self.troop_manager.attempt_research("spy", smith_data=mock_smith_data.return_value)

        # Assert
        self.assertFalse(self.mock_village._priority_research_unaffordable)
        self.troop_manager.logger.info.assert_not_called()

    @patch('core.extractors.Extractor.smith_data')
    def test_hoard_mode_not_triggered_for_affordable_critical_unit(self, mock_smith_data):
        """
        Verify that if a critical unit is affordable, hoard mode is NOT triggered.
        """
        # Arrange
        self.troop_manager.wanted_levels = {"axe": 1}
        # Provide enough resources
        self.troop_manager.game_data = {'village': {'wood': 200, 'stone': 200, 'iron': 200}}
        mock_smith_data.return_value = {
            "available": {
                "axe": {
                    "level": "0", "can_research": True, "research_error": None,
                    "wood": 100, "stone": 100, "iron": 100
                }
            }
        }
        self.wrapper.get_action.return_value.text = "mocked_html"
        self.wrapper.get_api_action.return_value = {"success": True} # Simulate successful API call

        # Act
        self.troop_manager.attempt_research("axe", smith_data=mock_smith_data.return_value)

        # Assert
        self.assertFalse(self.mock_village._priority_research_unaffordable)


if __name__ == '__main__':
    unittest.main()
