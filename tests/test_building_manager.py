import unittest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.buildingmanager import BuildingManager

class TestBuildingManager(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "12345"
        self.manager = BuildingManager(self.wrapper, self.village_id)
        self.manager.logger = MagicMock()
        self.manager.resman = MagicMock()
        self.manager.game_state = {
            "village": {
                "wood": 50000, "stone": 50000, "iron": 50000,
                "pop": 1000, "pop_max": 24000
            }
        }
        self.manager.resman.storage = 80000
        self.manager.resman.actual = {"wood": 50000, "stone": 50000, "iron": 50000}

    def test_get_planned_dynamic_actions_priority_1_troop_queues(self):
        self.manager.mode = "dynamic"
        self.manager.target_levels = {"stable": 20, "barracks": 20}
        self.manager.levels = {"stable": 10, "barracks": 15}
        self.manager.troop_queue_status = {"stable_queue_time": 3000, "barracks_queue_time": 4000}

        actions = self.manager.get_planned_actions()
        self.assertIn("Build Stable to level 11 (Reason: Stable queue running low)", actions[0])

        self.manager.troop_queue_status = {"stable_queue_time": 4000, "barracks_queue_time": 3000}
        actions = self.manager.get_planned_actions()
        self.assertIn("Build Barracks to level 16 (Reason: Barracks queue running low)", actions[0])

    def test_get_planned_dynamic_actions_priority_2_academy_prereqs(self):
        self.manager.mode = "dynamic"
        self.manager.target_levels = {"main": 20, "smith": 20, "market": 10, "snob": 1}
        self.manager.levels = {"main": 15, "smith": 20, "market": 10}
        self.manager.troop_queue_status = {"stable_queue_time": 9999, "barracks_queue_time": 9999}

        actions = self.manager.get_planned_actions()
        self.assertIn("Build Main to level 16 (Reason: Academy prerequisite)", actions[0])

    def test_get_planned_dynamic_actions_priority_3_jit_provisioning(self):
        self.manager.mode = "dynamic"
        self.manager.target_levels = {"storage": 30, "farm": 30, "snob": 1}
        self.manager.levels = {"main": 20, "smith": 20, "market": 10, "snob": 1, "storage": 15, "farm": 20}
        self.manager.troop_queue_status = {"stable_queue_time": 9999, "barracks_queue_time": 9999}
        self.manager.resman.storage = 80000

        actions = self.manager.get_planned_actions()
        self.assertIn("Build Storage to level 16 (Reason: Warehouse too small for Nobleman)", actions[0])

    def test_get_planned_dynamic_actions_priority_4_resource_sink(self):
        self.manager.mode = "dynamic"
        self.manager.target_levels = {"wood": 30, "stone": 30, "iron": 30, "snob": 1}
        self.manager.levels = {"main": 20, "smith": 20, "market": 10, "snob": 1, "storage": 30, "farm": 30, "wood": 10, "stone": 12, "iron": 11}
        self.manager.troop_queue_status = {"stable_queue_time": 9999, "barracks_queue_time": 9999}
        self.manager.resman.storage = 100000
        self.manager.resman.actual = {"wood": 98000, "stone": 50000, "iron": 50000}

        actions = self.manager.get_planned_actions()
        self.assertIn("Build Wood to level 11 (Reason: Resource storage full)", actions[0])

    def test_get_next_linear_action_fallback_logic(self):
        """
        Tests that the fallback logic in _get_next_linear_action correctly
        identifies and builds the lowest-level resource pit when the queue is empty.
        """
        # Arrange
        self.manager.mode = "linear"
        self.manager.queue = [] # Empty queue
        self.manager.levels = {"wood": 10, "stone": 8, "iron": 12}
        self.manager.costs = {
            "stone": {"can_build": True, "build_time": 100, "wood": 10, "stone": 10, "iron": 10, "pop": 1, "name": "stone"}
        }

        # Mock the _build method to prevent actual building and just check if it's called correctly
        with patch.object(self.manager, '_build') as mock_build:
            # Act
            result = self.manager._get_next_linear_action()

            # Assert
            self.assertTrue(result)
            mock_build.assert_called_once_with("stone")

if __name__ == '__main__':
    unittest.main()
