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
            {"name": "A - Default", "units": {"light": 1}, "condition": "default"},
            {"name": "B - Medium", "units": {"light": 4, "spy": 1}, "condition": "last_haul_full_scouted_lt_1000"},
            {"name": "C - Heavy", "units": {"light": 50}, "condition": "scouted_gt_1000", "calculate": "total_res_div_80"}
        ]

        target_village_id = "54321"

        # --- Scenario A: Last haul was NOT full -> Should select Template A (Default) ---
        self.report_manager.get_last_haul_status.return_value = "not_full"
        self.report_manager.get_scouted_resources.return_value = 500
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertEqual(selected_template["name"], "A - Default")

        # --- Scenario B: Last haul WAS full AND scouted resources < 1000 -> Should select Template B ---
        self.report_manager.get_last_haul_status.return_value = "full"
        self.report_manager.get_scouted_resources.return_value = 800
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertEqual(selected_template["name"], "B - Medium")

        # --- Scenario C: Scouted resources > 1000 -> Should select Template C ---
        self.report_manager.get_last_haul_status.return_value = "full"
        self.report_manager.get_scouted_resources.return_value = 2500
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertEqual(selected_template["name"], "C - Heavy")

        # --- Scenario: No report available (new farm) -> Should default to Template A ---
        self.report_manager.get_last_haul_status.return_value = None
        self.report_manager.get_scouted_resources.return_value = 0
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertEqual(selected_template["name"], "A - Default")

        # --- Scenario: Last haul was full, but scouted > 1000 -> C should take precedence over B ---
        self.report_manager.get_last_haul_status.return_value = "full"
        self.report_manager.get_scouted_resources.return_value = 1500
        selected_template = self.manager.get_template_for_target(target_village_id)
        self.assertEqual(selected_template["name"], "C - Heavy")

if __name__ == '__main__':
    unittest.main()
