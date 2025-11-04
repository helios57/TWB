import unittest
from unittest.mock import MagicMock
from game.farm_optimizer import FarmOptimizer

class TestFarmOptimizer(unittest.TestCase):

    def setUp(self):
        # Mock dependencies
        self.troop_manager = MagicMock()
        self.report_manager = MagicMock()
        self.map_data = MagicMock()

        # Mock troop and target data
        self.available_troops = {'light': 100, 'spear': 50}
        self.targets = [
            ({'id': 'target1', 'location': [500, 501]}, 1.0), # Close, high loot
            ({'id': 'target2', 'location': [510, 510]}, 10.0), # Far, low loot
            ({'id': 'target3', 'location': [502, 502]}, 2.0)  # Close, medium loot
        ]

        # Configure mock methods
        def get_scouted_resources_side_effect(village_id):
            if village_id == 'target1':
                return 1000
            if village_id == 'target3':
                return 400
            return 100 # Default for target2
        self.report_manager.get_scouted_resources.side_effect = get_scouted_resources_side_effect

        # Initialize the optimizer
        self.optimizer = FarmOptimizer(self.troop_manager, self.report_manager, self.map_data)

    def test_create_optimal_plan_prioritizes_best_targets(self):
        # Act
        plan = self.optimizer.create_optimal_plan(self.available_troops, self.targets)

        # Assert
        # The optimizer should create a plan for all profitable targets since enough troops are available.
        # Targets are prioritized by score: target1 > target3 > target2.
        self.assertEqual(len(plan), 3)

        # 1. First attack should be to the highest-scored target
        self.assertEqual(plan[0]['target_id'], 'target1')
        # Troops needed: ceil(1000 loot / 80 carry_per_lc) = 13 LC
        self.assertDictEqual(plan[0]['troops'], {'light': 13})

        # 2. Second attack should go to the second-best target
        self.assertEqual(plan[1]['target_id'], 'target3')
        # Troops needed: ceil(400 loot / 80 carry_per_lc) = 5 LC
        self.assertDictEqual(plan[1]['troops'], {'light': 5})

        # 3. Third attack should go to the third-best target
        self.assertEqual(plan[2]['target_id'], 'target2')
        # Troops needed: ceil(100 loot / 80 carry_per_lc) = 2 LC
        self.assertDictEqual(plan[2]['troops'], {'light': 2})


    def test_marginal_income_calculation(self):
        # Arrange
        # With 10 LC, we can raid target3 (400 loot / 80 = 5 LC) and have 5 LC left
        # Total loot = 400.
        troops = {'light': 10}
        targets = [self.targets[2]] # Only the medium target

        # Act
        marginal_incomes = self.optimizer.calculate_marginal_income(troops, targets)

        # Assert
        # Base income with 10 LC is 400.
        # With 11 LC, we can still only carry 400 from this one target.
        # So, the marginal income of one extra LC should be 0 in this scenario.
        self.assertIn('light', marginal_incomes)
        self.assertEqual(marginal_incomes['light'], 0)

        # Now, let's test a scenario where one more unit *does* make a difference
        # Here we have just enough for target3, but not target1
        troops_saturate_one_target = {'light': 5}
        targets_two = [self.targets[0], self.targets[2]] # High and medium targets

        # Base income: 400 (from target3, because target1 is prioritized but we only have 5 LC, so we get min(1000, 5*80)=400)
        # With one more LC (6 total), we can get min(1000, 6*80)=480 from target1.
        # The marginal income should be the capacity of one LC.
        marginal_incomes_2 = self.optimizer.calculate_marginal_income(troops_saturate_one_target, targets_two)

        self.assertAlmostEqual(marginal_incomes_2['light'], self.optimizer.unit_capacity['light'])


if __name__ == '__main__':
    unittest.main()
