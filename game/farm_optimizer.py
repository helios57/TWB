"""
This module contains the FarmOptimizer class, which is responsible for
generating an optimal farming plan based on available troops, target data,
and historical report information.
"""
import logging
import math

class FarmOptimizer:
    """
    Optimizes farming operations to maximize resource income per hour.
    """
    def __init__(self, troop_manager, report_manager, map_data):
        self.logger = logging.getLogger("FarmOptimizer")
        self.troop_manager = troop_manager
        self.report_manager = report_manager
        self.map_data = map_data
        self.unit_speeds = self._get_unit_speeds()
        self.unit_capacity = self._get_unit_carry_capacity()

    def create_optimal_plan(self, available_troops, targets):
        """
        Generates an optimal farming plan.

        Args:
            available_troops (dict): A dictionary of available troops for farming.
            targets (list): A list of potential farm targets from the Map module.

        Returns:
            list: A list of attack commands representing the optimal plan.
        """
        if not available_troops or not targets:
            return []

        # 1. Score and sort all potential targets
        scored_targets = self._score_targets(targets)

        # 2. Allocate troops using a greedy approach
        plan = self._allocate_troops(available_troops, scored_targets)

        return plan

    def _score_targets(self, targets):
        """
        Scores targets based on predicted loot and travel time.
        """
        scored = []
        for target_info, distance in targets:
            predicted_loot = self._predict_loot(target_info['id'])
            # We need a representative speed to estimate travel time.
            # Light Cavalry is a good default for farming.
            travel_time_hours = (distance * self.unit_speeds.get('light', 20)) / 60

            # Score is loot per hour of travel time
            score = predicted_loot / (travel_time_hours + 1) # Add 1 to avoid division by zero
            scored.append({'target_info': target_info, 'distance': distance, 'score': score, 'predicted_loot': predicted_loot})

        # Sort targets by score in descending order
        return sorted(scored, key=lambda x: x['score'], reverse=True)

    def _predict_loot(self, village_id):
        """
        Predicts the amount of loot a village will have.
        Placeholder: This will be a more sophisticated model later.
        """
        # For now, use the last scouted resources or a default value
        scouted = self.report_manager.get_scouted_resources(village_id)
        if scouted > 0:
            return scouted

        # Fallback to a default assumption if not scouted
        return 200 # Average loot for an unscouted farm

    def _allocate_troops(self, available_troops, scored_targets):
        """
        Allocates troops to the highest-scored targets greedily using the most
        efficient units first.
        """
        plan = []
        remaining_troops = {unit: count for unit, count in available_troops.items() if self.unit_capacity.get(unit, 0) > 0}

        # Sort available units by carry capacity (most efficient first)
        sorted_units = sorted(remaining_troops.keys(), key=lambda u: self.unit_capacity[u], reverse=True)

        for target in scored_targets:
            if not any(remaining_troops.values()):
                break

            loot_to_carry = target['predicted_loot']
            troops_to_send = {}

            for unit in sorted_units:
                if loot_to_carry <= 0 or remaining_troops.get(unit, 0) == 0:
                    continue

                capacity = self.unit_capacity[unit]
                units_needed = math.ceil(loot_to_carry / capacity)
                units_available = remaining_troops[unit]

                num_to_send = min(units_needed, units_available)

                troops_to_send[unit] = num_to_send
                remaining_troops[unit] -= num_to_send
                loot_to_carry -= num_to_send * capacity

            if troops_to_send:
                plan.append({
                    'target_id': target['target_info']['id'],
                    'troops': troops_to_send,
                    'estimated_loot': target['predicted_loot']
                })

        return plan


    def _get_unit_speeds(self):
        # These are approximations in minutes per field
        return {
            'spear': 18, 'sword': 22, 'axe': 18, 'archer': 18,
            'spy': 9, 'light': 10, 'marcher': 10, 'heavy': 11,
            'ram': 30, 'catapult': 30, 'knight': 10, 'snob': 35
        }

    def _get_unit_carry_capacity(self):
        return {
            'spear': 25, 'sword': 15, 'axe': 10, 'archer': 10,
            'spy': 0, 'light': 80, 'marcher': 50, 'heavy': 50,
            'ram': 0, 'catapult': 0, 'knight': 100, 'snob': 0
        }

    def calculate_marginal_income(self, available_troops, targets):
        """
        Calculates the marginal income gain from adding one of each farm unit.
        """
        marginal_incomes = {}
        farming_units = [unit for unit, capacity in self.unit_capacity.items() if capacity > 0]

        if not targets:
            return {unit: 0 for unit in farming_units}

        # Calculate baseline income with current troops
        base_plan = self.create_optimal_plan(available_troops, targets)
        base_income = self._calculate_plan_loot(base_plan)

        # Iterate through each unit type to calculate its marginal value
        for unit in farming_units:
            # Create a hypothetical troop set with one extra unit
            hypothetical_troops = available_troops.copy()
            hypothetical_troops[unit] = hypothetical_troops.get(unit, 0) + 1

            # Calculate the new optimal income with the extra unit
            new_plan = self.create_optimal_plan(hypothetical_troops, targets)
            new_income = self._calculate_plan_loot(new_plan)

            # The marginal income is the difference
            marginal_incomes[unit] = new_income - base_income
            self.logger.debug(f"Marginal income for an extra '{unit}': {marginal_incomes[unit]:.2f} resources")

        return marginal_incomes

    def _calculate_plan_loot(self, plan):
        """
        Calculates the total estimated loot from a farming plan, capped by carry capacity.
        """
        total_loot = 0
        for attack in plan:
            # The actual loot is the minimum of what's available and what we can carry
            sent_capacity = sum(count * self.unit_capacity[unit] for unit, count in attack['troops'].items())
            actual_loot = min(attack['estimated_loot'], sent_capacity)
            total_loot += actual_loot
        return total_loot
