import unittest
from unittest.mock import MagicMock
from game.action_generator import ActionGenerator
from game.gamestate import GameState

class TestActionGenerator(unittest.TestCase):

    def setUp(self):
        self.action_generator = ActionGenerator()
        self.game_state = GameState(village_id=1)
        self.game_state.building_levels = {'main': 1, 'farm': 1}
        self.game_state.resources = {'wood': 1000, 'stone': 1000, 'iron': 1000}
        self.action_generator.building_costs = {
            'main': {'wood': 100, 'stone': 100, 'iron': 100},
            'farm': {'wood': 100, 'stone': 100, 'iron': 100}
        }
        self.game_state.resources = {'wood': 1000, 'stone': 1000, 'iron': 1000}

    def test_generate_build_actions_handles_invalid_template_lines(self):
        """
        Tests that the `_generate_build_actions` method can handle templates
        with comments and invalid lines without crashing.
        """
        building_templates = {
            "template_data": [
                "main:5",
                "# this is a comment",
                "farm:2",
                "",
                "invalid_line",
                "main:",
                "market:non_numeric"
            ],
            "mode": "linear"
        }
        self.action_generator.update_data(building_templates, {}, self.action_generator.building_costs, {}, {})

        # The test passes if this doesn't raise a ValueError
        actions = self.action_generator.generate(self.game_state)
        self.assertEqual(len(actions), 2)
        self.assertEqual(actions[0].building, 'main')
        self.assertEqual(actions[1].building, 'farm')

if __name__ == '__main__':
    unittest.main()
