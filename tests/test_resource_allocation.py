import unittest
from unittest.mock import MagicMock
from game.resource_allocation import ResourceAllocationSolver

class TestResourceAllocationSolver(unittest.TestCase):

    def setUp(self):
        self.farm_optimizer = MagicMock()
        self.scavenge_optimizer = MagicMock()
        self.solver = ResourceAllocationSolver(self.farm_optimizer, self.scavenge_optimizer)

        self.available_troops = {'light': 100}
        self.farm_targets = [({'id': 'farm1'}, 1.0)]
        self.scavenge_options = {'1': {'is_locked': False, 'scavenging_squad': None}}

    def test_determine_best_strategy_selects_farming(self):
        # Arrange: Make farming more profitable
        self.farm_optimizer.create_optimal_plan.return_value = [{'estimated_loot': 2000}]
        self.farm_optimizer._calculate_plan_loot.return_value = 2000
        self.scavenge_optimizer.create_optimal_plan.return_value = [{'estimated_loot': 1000}]
        self.scavenge_optimizer._calculate_plan_loot.return_value = 1000

        # Act
        strategy, plan = self.solver.determine_best_strategy(self.available_troops, self.farm_targets, self.scavenge_options)

        # Assert
        self.assertEqual(strategy, 'farming')
        self.assertEqual(self.farm_optimizer._calculate_plan_loot(plan), 2000)

    def test_determine_best_strategy_selects_scavenging(self):
        # Arrange: Make scavenging more profitable
        self.farm_optimizer.create_optimal_plan.return_value = [{'estimated_loot': 1000}]
        self.farm_optimizer._calculate_plan_loot.return_value = 1000
        self.scavenge_optimizer.create_optimal_plan.return_value = [{'estimated_loot': 2000}]
        self.scavenge_optimizer._calculate_plan_loot.return_value = 2000

        # Act
        strategy, plan = self.solver.determine_best_strategy(self.available_troops, self.farm_targets, self.scavenge_options)

        # Assert
        self.assertEqual(strategy, 'scavenging')
        self.assertEqual(self.scavenge_optimizer._calculate_plan_loot(plan), 2000)

    def test_calculate_unified_marginal_income(self):
        # Arrange: Give different marginal incomes for different units
        self.farm_optimizer.calculate_marginal_income.return_value = {'light': 80, 'spear': 10}
        self.scavenge_optimizer.calculate_marginal_income.return_value = {'light': 50, 'spear': 25}

        # Act
        unified_incomes = self.solver.calculate_unified_marginal_income(self.available_troops, self.farm_targets, self.scavenge_options)

        # Assert: The solver should pick the max for each unit
        self.assertEqual(unified_incomes['light'], 80) # 80 from farm > 50 from scavenge
        self.assertEqual(unified_incomes['spear'], 25) # 25 from scavenge > 10 from farm

if __name__ == '__main__':
    unittest.main()
