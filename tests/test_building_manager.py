import unittest
from unittest.mock import MagicMock, patch
from game.buildingmanager import BuildingManager
from tests.helpers import get_mock_data

class TestBuildingManager(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "21739"
        self.builder = BuildingManager(self.wrapper, self.village_id)
        self.builder.resman = MagicMock()
        self.builder.logger = MagicMock()

        self.builder.game_state = {
            "village": {
                "wood": 10000, "stone": 10000, "iron": 10000,
                "pop": 100, "pop_max": 2000,
                "buildings": {"main": 10, "barracks": 5, "stable": 3, "smith": 5, "market": 1, "snob": 0, "garage": 0, "farm": 10, "storage": 10, "wall": 0, "wood": 10, "stone": 10, "iron": 10}
            },
            "link_base_pure": "/game.php?village=21739&screen=",
            "csrf": "test_csrf"
        }
        self.builder.resman.storage = 30000
        self.builder.resman.actual = {"wood": 10000, "stone": 10000, "iron": 10000}
        self.builder.levels = self.builder.game_state["village"]["buildings"].copy()

        self.builder.costs = {
            "main": {"can_build": True, "wood": 100, "stone": 100, "iron": 100, "pop": 10, "build_time": 60, "id": "main", "build_link": "main_link"},
            "barracks": {"can_build": True, "wood": 150, "stone": 150, "iron": 150, "pop": 20, "build_time": 120, "id": "barracks", "build_link": "barracks_link"},
            "stable": {"can_build": True, "wood": 200, "stone": 200, "iron": 200, "pop": 30, "build_time": 180, "id": "stable", "build_link": "stable_link"},
            "smith": {"can_build": True, "wood": 250, "stone": 250, "iron": 250, "pop": 40, "build_time": 240, "id": "smith", "build_link": "smith_link"},
            "market": {"can_build": True, "wood": 300, "stone": 300, "iron": 300, "pop": 50, "build_time": 300, "id": "market", "build_link": "market_link"},
            "farm": {"can_build": True, "wood": 50, "stone": 50, "iron": 50, "pop": 0, "build_time": 30, "id": "farm", "build_link": "farm_link"},
            "storage": {"can_build": True, "wood": 80, "stone": 80, "iron": 80, "pop": 0, "build_time": 45, "id": "storage", "build_link": "storage_link"},
            "wood": {"can_build": True, "wood": 120, "stone": 120, "iron": 120, "pop": 5, "build_time": 90, "id": "wood", "build_link": "wood_link"}
        }
        self.wrapper.get_url.return_value.text = get_mock_data('main.html')

    def _mock_build(self, building_name):
        self.builder.levels[building_name] += 1
        return True

    @patch('game.buildingmanager.Extractor')
    def test_linear_build_mode(self, mock_extractor):
        self.builder.mode = 'linear'
        self.builder.queue = ["main:11"]
        self.builder._build = MagicMock(side_effect=self._mock_build)
        mock_extractor.game_state.return_value = self.builder.game_state
        mock_extractor.building_data.return_value = self.builder.costs
        result = self.builder._get_next_linear_action()
        self.assertTrue(result)
        self.builder._build.assert_called_with("main")
        self.assertEqual(self.builder.get_level('main'), 11)

    @patch('game.buildingmanager.Extractor')
    def test_dynamic_priority_order(self, mock_extractor):
        self.builder.mode = 'dynamic'
        self.builder.target_levels = {"stable": 20, "main": 20, "storage": 30, "wood": 30}
        self.builder._build = MagicMock(side_effect=self._mock_build)
        mock_extractor.game_state.return_value = self.builder.game_state
        mock_extractor.building_data.return_value = self.builder.costs

        # 1. Test Priority 1 (Troop Queues)
        self.builder.troop_queue_status = {'stable_queue_time': 600}
        self.builder._get_next_dynamic_action()
        self.builder._build.assert_called_with("stable")

        # 2. Test Priority 2 (Strategic Goals)
        self.builder.troop_queue_status = {'stable_queue_time': 4000}
        self.builder._get_next_dynamic_action()
        self.builder._build.assert_called_with("main")

        # 3. Test Priority 3 (JIT Provisioning)
        self.builder.levels['main'] = 20 # Mark strategic goal as met
        self.builder.resman.storage = 100000
        self.builder._get_next_dynamic_action()
        self.builder._build.assert_called_with("storage")

        # 4. Test Priority 4 (Resource Sink)
        self.builder.levels['storage'] = 30 # Mark JIT goal as met
        self.builder.resman.storage = 200000
        self.builder.resman.actual['wood'] = 195000 # Near capacity
        self.builder._get_next_dynamic_action()
        self.builder._build.assert_called_with("wood")

if __name__ == '__main__':
    unittest.main()
