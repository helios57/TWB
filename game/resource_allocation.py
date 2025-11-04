"""
This module contains the ResourceAllocationSolver, a high-level planner that
decides the best overall resource gathering strategy by comparing the profitability
of farming and scavenging.
"""
import logging

class ResourceAllocationSolver:
    """
    Determines the optimal resource gathering strategy by comparing farming
    and scavenging plans.
    """
    def __init__(self, farm_optimizer, scavenge_optimizer):
        self.logger = logging.getLogger("ResourceAllocationSolver")
        self.farm_optimizer = farm_optimizer
        self.scavenge_optimizer = scavenge_optimizer

    def determine_best_strategy(self, available_troops, farm_targets, scavenge_options):
        """
        Compares the optimal farming and scavenging plans and returns the best one.

        Returns:
            A tuple containing the name of the best strategy ('farming' or 'scavenging')
            and the plan itself.
        """
        self.logger.info("Determining optimal resource gathering strategy...")

        # 1. Generate optimal plan for each strategy
        farming_plan = self.farm_optimizer.create_optimal_plan(available_troops, farm_targets)
        scavenging_plan = self.scavenge_optimizer.create_optimal_plan(available_troops, scavenge_options)

        # 2. Calculate the total estimated loot for each plan
        farm_loot = self.farm_optimizer._calculate_plan_loot(farming_plan)
        scavenge_loot = self._calculate_scavenge_plan_loot(scavenging_plan) # Need to implement this

        self.logger.info(f"Farming plan estimated loot: {farm_loot}")
        self.logger.info(f"Scavenging plan estimated loot: {scavenge_loot}")

        # 3. Compare and decide
        if farm_loot > scavenge_loot:
            self.logger.info("Decision: Farming is the optimal strategy for this cycle.")
            return 'farming', farming_plan
        else:
            self.logger.info("Decision: Scavenging is the optimal strategy for this cycle.")
            return 'scavenging', scavenging_plan

    def calculate_unified_marginal_income(self, available_troops, farm_targets, scavenge_options):
        """
        Calculates the marginal income for each unit by taking the maximum potential
        income from either farming or scavenging.
        """
        farm_incomes = self.farm_optimizer.calculate_marginal_income(available_troops, farm_targets)
        scavenge_incomes = self.scavenge_optimizer.calculate_marginal_income(available_troops, scavenge_options)

        unified_incomes = {}
        all_units = set(farm_incomes.keys()) | set(scavenge_incomes.keys())

        for unit in all_units:
            farm_income = farm_incomes.get(unit, 0)
            scavenge_income = scavenge_incomes.get(unit, 0)
            unified_incomes[unit] = max(farm_income, scavenge_income)
            self.logger.debug(f"Unified marginal income for '{unit}': {unified_incomes[unit]:.2f} (from max(farm:{farm_income:.2f}, scavenge:{scavenge_income:.2f}))")

        return unified_incomes

    def _calculate_scavenge_plan_loot(self, plan):
        """
        Calculates the total estimated loot from a scavenging plan.
        """
        return self.scavenge_optimizer._calculate_plan_loot(plan)
