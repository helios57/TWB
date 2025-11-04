import unittest
from unittest.mock import MagicMock
from game.scavenge_optimizer import ScavengeOptimizer

class TestScavengeOptimizer(unittest.TestCase):

    def setUp(self):
        self.troop_manager = MagicMock()
        self.optimizer = ScavengeOptimizer(self.troop_manager)

        self.available_troops = {'spear': 100, 'light': 50}
        self.scavenge_options = {
            '1': {'is_locked': False, 'scavenging_squad': None, 'loot': {'wood': 1000, 'stone': 1000, 'iron': 1000}, 'duration_in_seconds': 3600},
            '2': {'is_locked': False, 'scavenging_squad': None, 'loot': {'wood': 2000, 'stone': 2000, 'iron': 2000}, 'duration_in_seconds': 14400},
            '3': {'is_locked': True, 'scavenging_squad': None, 'loot': {}, 'duration_in_seconds': 0},
        }

    def test_score_options(self):
        scored = self.optimizer._score_options(self.scavenge_options)
        self.assertEqual(len(scored), 2)
        # Option 1: 3000 loot / 1 hour = 3000 score
        # Option 2: 6000 loot / 4 hours = 1500 score
        self.assertEqual(scored[0]['option_data']['id'], '1')
        self.assertEqual(scored[1]['option_data']['id'], '2')

    def test_allocate_troops(self):
        scored_options = self.optimizer._score_options(self.scavenge_options)
        plan = self.optimizer._allocate_troops(self.available_troops, scored_options)

        self.assertEqual(len(plan), 2)

        # Best option is #1, needs 3000 loot.
        # 50 LC * 80 carry = 4000 capacity. More than enough.
        # Troops needed: ceil(3000 / 80) = 38 LC
        self.assertEqual(plan[0]['option_id'], '1')
        self.assertEqual(plan[0]['troops']['light'], 38)

        # Second best is #2, needs 6000 loot.
        # Remaining troops: 12 LC (960 capacity) and 100 spears (2500 capacity). Total = 3460
        self.assertEqual(plan[1]['option_id'], '2')
        self.assertEqual(plan[1]['troops']['light'], 12)
        self.assertEqual(plan[1]['troops']['spear'], 100)

    def test_marginal_income(self):
        # With 37 LC, we can't quite get all 3000 loot from option 1 (37*80=2960)
        troops = {'light': 37}
        base_plan = self.optimizer.create_optimal_plan(troops, self.scavenge_options)
        base_loot = self.optimizer._calculate_plan_loot(base_plan)
        self.assertAlmostEqual(base_loot, 2960)

        # With one more LC, we can get all 3000. Marginal gain should be 40.
        incomes = self.optimizer.calculate_marginal_income(troops, self.scavenge_options)
        self.assertAlmostEqual(incomes['light'], 40)

    def test_score_options_handles_invalid_data(self):
        """
        Tests that the `_score_options` method can handle invalid data structures gracefully.
        """
        invalid_options = {
            '1': {'is_locked': False, 'scavenging_squad': None, 'loot': {'wood': 1000, 'stone': 1000, 'iron': 1000}, 'duration_in_seconds': 3600},
            'invalid_int': 123,
            '2': {'is_locked': False, 'scavenging_squad': None, 'loot': {'wood': 2000, 'stone': 2000, 'iron': 2000}, 'duration_in_seconds': 14400},
            'missing_loot': {'is_locked': False, 'scavenging_squad': None, 'duration_in_seconds': 3600},
            'missing_duration': {'is_locked': False, 'scavenging_squad': None, 'loot': {'wood': 500}},
        }

        scored = self.optimizer._score_options(invalid_options)
        self.assertEqual(len(scored), 3)
        self.assertEqual(scored[0]['option_data']['id'], '1')
        self.assertEqual(scored[1]['option_data']['id'], '2')
        self.assertEqual(scored[2]['option_data']['id'], 'missing_duration')


if __name__ == '__main__':
    unittest.main()
