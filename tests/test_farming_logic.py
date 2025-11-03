import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.attack import AttackManager

class TestFarmingLogic(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "12345"
        self.troop_manager = MagicMock()
        self.map_instance = MagicMock()
        self.report_manager = MagicMock()

        self.manager = AttackManager(self.wrapper, self.village_id, self.troop_manager, self.map_instance)
        self.manager.repman = self.report_manager
        self.manager.logger = MagicMock()

    def test_abc_farming_template_selection(self):
        # Setup the multi-template config from the strategy doc
        self.manager.template = [
            {"name": "A - Light Farm", "active": True, "units": {"light": 5}, "condition": "not_full"},
            {"name": "B - Medium Farm", "active": True, "units": {"light": 20}, "condition": "full_but_small"},
            {"name": "C - Heavy Farm", "active": True, "units": {"light": 100, "spy": 1}, "condition": "large_scouted"}
        ]

        target_village_id = "54321"

        # --- Scenario 1: Last haul was "not_full" -> Should select Template A ---
        self.report_manager.get_last_haul_status.return_value = "not_full"
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertIsNotNone(selected_template)
        self.assertEqual(selected_template["name"], "A - Light Farm")

        # --- Scenario 2: Last haul was "full_but_small" -> Should select Template B ---
        self.report_manager.get_last_haul_status.return_value = "full_but_small"
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertIsNotNone(selected_template)
        self.assertEqual(selected_template["name"], "B - Medium Farm")

        # --- Scenario 3: Last haul was "large_scouted" -> Should select Template C ---
        self.report_manager.get_last_haul_status.return_value = "large_scouted"
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertIsNotNone(selected_template)
        self.assertEqual(selected_template["name"], "C - Heavy Farm")

        # --- Scenario 4: No report available (new farm) -> Should default to Template A ---
        self.report_manager.get_last_haul_status.return_value = None
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertIsNotNone(selected_template)
        self.assertEqual(selected_template["name"], "A - Light Farm")

if __name__ == '__main__':
    unittest.main()
