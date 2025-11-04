import unittest
from unittest.mock import MagicMock
from game.gamestate import GameState
from game.solver import MultiActionPlanner
from game.actions import BuildAction

class TestSolver(unittest.TestCase):

    def setUp(self):
        self.game_state = GameState(village_id='123')
        self.game_state.resources = {'wood': 100, 'stone': 100, 'iron': 100}
        self.game_state.building_levels = {'main': 1, 'barracks': 0}
        # Add other necessary gamestate attributes for evaluate_state to work
        self.game_state.troop_counts = {}
        self.game_state.storage_capacity = 1000
        self.game_state.resource_income = {'wood': 10, 'stone': 10, 'iron': 10}


    def test_multi_action_planner_creates_action_sequence(self):
        # Arrange
        action_generator = MagicMock()

        # Define actions with different costs to test sequential planning
        # action_best is clearly better according to the heuristic (higher level building)
        # and leaves enough resources for the next action.
        action_best = BuildAction('main', 2, {'wood': 20, 'stone': 20, 'iron': 20})
        action_next = BuildAction('barracks', 1, {'wood': 70, 'stone': 70, 'iron': 70})
        action_alternative = BuildAction('main', 2, {'wood': 90, 'stone': 90, 'iron': 90})


        # Configure the mock to return different sets of actions based on the
        # simulated state during planning.
        def generate_side_effect(state):
            if state.resources['wood'] == 100:
                # Initially, both actions are possible. The solver should pick the
                # one that results in a higher score. Since both action_best and
                # action_alternative result in the same building level, and the
                # heuristic doesn't heavily penalize resource spending, the
                # solver will pick the first one it sees.
                return [action_best, action_next, action_alternative]
            elif state.resources['wood'] == 80:
                # After 'action_best' is chosen, only 'action_next' is affordable
                return [action_next]
            else:
                # No more actions should be generated
                return []

        action_generator.generate.side_effect = generate_side_effect
        planner = MultiActionPlanner(action_generator)

        # Act
        plan = planner.plan_actions(self.game_state, marginal_incomes={}, max_actions=5)

        # Assert
        self.assertEqual(len(plan), 2)
        self.assertEqual(plan[0], action_best) # First action should be the one leading to the best score
        self.assertEqual(plan[1], action_next) # Second action is the only one possible after the first

if __name__ == '__main__':
    unittest.main()
