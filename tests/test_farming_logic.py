import unittest
from unittest.mock import MagicMock, patch
from game.attack import AttackManager
from game.reports import ReportManager

class TestFarmingLogic(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "21739"

        # Mock TroopManager
        self.troop_manager = MagicMock()
        self.troop_manager.troops = {'light': '100', 'spy': '10'}

        # Mock ReportManager
        self.report_manager = ReportManager(self.wrapper, self.village_id)
        self.report_manager.logger = MagicMock()

        # Setup AttackManager
        self.attack_manager = AttackManager(self.wrapper, self.village_id, self.troop_manager)
        self.attack_manager.repman = self.report_manager
        self.attack_manager.logger = MagicMock()
        self.attack_manager.attacked = MagicMock()
        self.attack_manager.can_attack = MagicMock(return_value=True)
        self.attack_manager.template = [
            {"name": "A_Farm", "condition": "not_full_haul", "units": {"light": 1}},
            {"name": "B_Farm", "condition": "full_haul_small_res", "units": {"light": 4, "spy": 1}},
            {"name": "C_Farm", "condition": "large_res", "units": {"light": 0}, "calculate": "total_res / 80"}
        ]

    def test_a_farm_selection(self):
        # Scenario: Last haul was not full
        target_id = "123"
        self.report_manager.get_last_haul_status = MagicMock(return_value="not_full")
        self.attack_manager.attack = MagicMock(return_value=True)
        self.attack_manager.can_attack = MagicMock(return_value=True)

        self.attack_manager.send_farm((_mock_target(target_id), 0))

        self.attack_manager.attack.assert_called_with(target_id, troops={'light': 1})

    def test_b_farm_selection(self):
        # Scenario: Last haul was full, but scouted resources are low
        target_id = "124"
        self.report_manager.get_last_haul_status = MagicMock(return_value="full_small")
        self.attack_manager.attack = MagicMock(return_value=True)
        self.attack_manager.can_attack = MagicMock(return_value=True)

        self.attack_manager.send_farm((_mock_target(target_id), 0))

        self.attack_manager.attack.assert_called_with(target_id, troops={'light': 4, 'spy': 1})

    def test_c_farm_selection_and_calculation(self):
        # Scenario: Large amount of scouted resources
        target_id = "125"
        self.report_manager.get_last_haul_status = MagicMock(return_value="large")
        self.report_manager.get_scouted_resources = MagicMock(return_value=1200) # Should result in 15 LC
        self.attack_manager.attack = MagicMock(return_value=True)
        self.attack_manager.can_attack = MagicMock(return_value=True)

        self.attack_manager.send_farm((_mock_target(target_id), 0))

        self.attack_manager.attack.assert_called_with(target_id, troops={'light': 15})

def _mock_target(vid):
    return {"id": vid}

if __name__ == '__main__':
    unittest.main()
