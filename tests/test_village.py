import unittest
import json
import os
from unittest.mock import patch, MagicMock
from datetime import datetime

from game.village import Village
from game.attack import AttackManager
from game.buildingmanager import BuildingManager
from game.troopmanager import TroopManager


class TestVillage(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village = Village(village_id='123', wrapper=self.wrapper)
        self.village.logger = MagicMock()
        self.village.config = {
            "farms": {
                "forced_peace_times": [
                    {
                        "start": "01.01.25 10:00:00",
                        "end": "01.01.25 12:00:00"
                    }
                ]
            },
            "bot": {},
            "world": {},
            "villages": {
                "123": {}
            }
        }
        # Mock dependencies
        self.village.builder = MagicMock(spec=BuildingManager)
        self.village.units = MagicMock(spec=TroopManager)
        self.village.attack = MagicMock(spec=AttackManager)


    @patch('game.village.datetime')
    def test_check_forced_peace_today(self, mock_datetime):
        # Arrange
        # Set the mocked "now" to a date that is inside the peace time window's day
        mock_datetime.now.return_value = datetime(2025, 1, 1, 9, 0, 0)
        mock_datetime.strptime.side_effect = lambda *args, **kw: datetime.strptime(*args, **kw)
        mock_datetime.today.return_value = mock_datetime.now.return_value

        # Act
        self.village.check_forced_peace()

        # Assert
        # This should be True but is False because of the bug
        self.assertTrue(self.village.forced_peace_today, "forced_peace_today should be True but is False")
        self.assertIsNotNone(self.village.forced_peace_today_start, "forced_peace_today_start should be set")

    @patch('game.village.datetime')
    def test_check_forced_peace_active(self, mock_datetime):
        # Arrange
        # Set the mocked "now" to a time that is inside the peace time window
        mock_datetime.now.return_value = datetime(2025, 1, 1, 11, 0, 0)
        mock_datetime.strptime.side_effect = lambda *args, **kw: datetime.strptime(*args, **kw)
        mock_datetime.today.return_value = mock_datetime.now.return_value

        # Act
        self.village.check_forced_peace()

        # Assert
        self.assertTrue(self.village.forced_peace, "forced_peace should be True")

    def test_set_farm_options_gathers_all_templates_ignoring_locked_entries(self):
        """
        Tests that set_farm_options correctly gathers all available farm templates
        from a troop template, even if some entries are 'locked' by unmet building
        level requirements. The loop should not break on the first locked entry.
        """
        # Arrange
        mock_farm_template = [
            {"name": "A_Farm", "condition": "not_full_haul", "units": {"light": 1}}
        ]
        mock_troop_template = [
            {
                "building": "barracks",
                "level": 5,
                "build": {"barracks": {"spear": 100}}
            },
            {
                "building": "stable",
                "level": 3,
                "build": {"stable": {"spy": 10}},
                "farm": mock_farm_template
            }
        ]

        # Simulate that barracks is level 1 (locked) and stable is level 3 (unlocked)
        self.village.builder.levels = {'barracks': 1, 'stable': 3}
        self.village.units.template = mock_troop_template

        # Act
        self.village.set_farm_options()

        # Assert
        self.assertIsNotNone(self.village.attack.template, "Attack template should not be None.")
        self.assertEqual(len(self.village.attack.template), 1, "Should have found one farm template.")
        self.assertEqual(self.village.attack.template, mock_farm_template, "The correct farm template was not loaded.")

    def test_automatic_template_switching(self):
        """
        Tests that the bot automatically switches to the next template when the
        condition in the 'next_template' section is met.
        """
        # Arrange
        mock_config_manager = MagicMock()
        self.village.config_manager = mock_config_manager
        self.village.unit_template_full = {
            "next_template": {
                "template_name": "noble_rush_final_units",
                "condition": {"building": "stable", "level": 3}
            },
            "template_data": []
        }
        self.village.builder.get_level.return_value = 3 # Stable is level 3

        # Act
        self.village._check_and_handle_template_switch()

        # Assert
        mock_config_manager.update_village_config.assert_called_once_with(
            '123', 'units', 'noble_rush_final_units'
        )

    def test_set_unit_wanted_levels_handles_missing_build_key(self):
        """
        Tests that set_unit_wanted_levels does not crash when a troop template
        entry is missing the 'build' key.
        """
        # Arrange
        # This template entry is intentionally missing the 'build' key
        self.village.units.get_template_action.return_value = {
            "building": "stable",
            "level": 1
        }
        self.village.builder.levels = {'stable': 1}
        self.village.units.wanted = {}

        # Act & Assert
        try:
            self.village.set_unit_wanted_levels()
            # If we get here, the test has passed because no KeyError was raised.
        except KeyError:
            self.fail("set_unit_wanted_levels raised a KeyError unexpectedly.")

    def test_automatic_building_template_switching(self):
        """
        Tests that the bot automatically switches to the next building template
        when the current linear queue is empty.
        """
        # Arrange
        mock_config_manager = MagicMock()
        self.village.config_manager = mock_config_manager
        self.village.build_template_full = {
            "next_template": {
                "template_name": "noble_rush_stage_2",
                "condition": {} # No condition, just completion
            },
            "template_data": [],
            "mode": "linear"
        }
        self.village.builder.mode = "linear"
        self.village.builder.queue = [] # Queue is empty

        # Act
        self.village._check_and_handle_template_switch()

        # Assert
        mock_config_manager.update_village_config.assert_called_once_with(
            '123', 'building', 'noble_rush_stage_2'
        )


if __name__ == '__main__':
    unittest.main()
