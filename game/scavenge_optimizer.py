"""
This module contains the ScavengeOptimizer class, which is responsible for
generating an optimal scavenging plan by allocating troops to the most
profitable scavenging options.
"""
import logging
import math

class ScavengeOptimizer:
    """
    Optimizes scavenging operations to maximize resource income per hour.
    """
    def __init__(self, troop_manager):
        self.logger = logging.getLogger("ScavengeOptimizer")
        self.troop_manager = troop_manager
        self.unit_capacity = self._get_unit_carry_capacity()

    def create_optimal_plan(self, available_troops, scavenge_options):
        """
        Generates an optimal scavenging plan.

        Args:
            available_troops (dict): A dictionary of available troops.
            scavenge_options (dict): A dictionary of available scavenging options.

        Returns:
            list: A list of scavenging commands representing the optimal plan.
        """
        if not available_troops or not scavenge_options:
            return []

        # 1. Score and sort all potential options
        scored_options = self._score_options(scavenge_options)

        # 2. Allocate troops using a greedy approach
        plan = self._allocate_troops(available_troops, scored_options)

        return plan

    def _score_options(self, options):
        """
        Scores scavenging options based on their loot and duration.
        """
        scored = []
        for option_id, data in options.items():
            # Defensively check if data is a dictionary before proceeding
            if not isinstance(data, dict):
                continue
            if data.get('is_locked') or data.get('scavenging_squad') is not None:
                continue

            # Total potential loot is the sum of resources, use .get() for safety
            total_loot = sum(data.get('loot', {}).values())
            if total_loot == 0:
                continue
            duration_hours = data.get('duration_in_seconds', 0) / 3600

            # Score is loot per hour
            score = total_loot / duration_hours if duration_hours > 0 else 0

            data['id'] = option_id
            scored.append({'option_data': data, 'score': score, 'total_loot': total_loot})

        # Sort options by score in descending order
        return sorted(scored, key=lambda x: x['score'], reverse=True)

    def _allocate_troops(self, available_troops, scored_options):
        """
        Allocates troops to the highest-scored scavenging options greedily, using
        the most efficient units first.
        """
        plan = []
        remaining_troops = {unit: count for unit, count in available_troops.items() if self.unit_capacity.get(unit, 0) > 0}

        # Sort available units by carry capacity (most efficient first)
        sorted_units = sorted(remaining_troops.keys(), key=lambda u: self.unit_capacity[u], reverse=True)

        for option in scored_options:
            if not any(remaining_troops.values()):
                break

            loot_to_carry = option['total_loot']
            troops_to_send = {}

            for unit in sorted_units:
                if loot_to_carry <= 0 or remaining_troops.get(unit, 0) == 0:
                    continue

                capacity = self.unit_capacity[unit]
                units_needed = math.ceil(loot_to_carry / capacity)
                units_available = remaining_troops[unit]

                num_to_send = min(units_needed, units_available)

                if num_to_send > 0:
                    troops_to_send[unit] = num_to_send
                    remaining_troops[unit] -= num_to_send
                    loot_to_carry -= num_to_send * capacity

            if troops_to_send:
                plan.append({
                    'option_id': option['option_data']['id'],
                    'troops': troops_to_send,
                    'estimated_loot': option['total_loot']
                })

        return plan

    def _get_unit_carry_capacity(self):
        return {
            'spear': 25, 'sword': 15, 'axe': 10, 'archer': 10,
            'spy': 0, 'light': 80, 'marcher': 50, 'heavy': 50,
            'ram': 0, 'catapult': 0, 'knight': 100, 'snob': 0
        }

    def calculate_marginal_income(self, available_troops, scavenge_options):
        """
        Calculates the marginal income gain from adding one of each scavenging unit.
        """
        marginal_incomes = {}
        scavenging_units = [unit for unit, capacity in self.unit_capacity.items() if capacity > 0]

        if not scavenge_options:
            return {unit: 0 for unit in scavenging_units}

        # Calculate baseline income
        base_plan = self.create_optimal_plan(available_troops, scavenge_options)
        base_income = self._calculate_plan_loot(base_plan)

        for unit in scavenging_units:
            hypothetical_troops = available_troops.copy()
            hypothetical_troops[unit] = hypothetical_troops.get(unit, 0) + 1

            new_plan = self.create_optimal_plan(hypothetical_troops, scavenge_options)
            new_income = self._calculate_plan_loot(new_plan)

            marginal_incomes[unit] = new_income - base_income

        return marginal_incomes

    def _calculate_plan_loot(self, plan):
        """
        Calculates the total estimated loot from a scavenging plan, capped by carry capacity.
        """
        total_loot = 0
        for squad in plan:
            sent_capacity = sum(count * self.unit_capacity[unit] for unit, count in squad['troops'].items())
            actual_loot = min(squad['estimated_loot'], sent_capacity)
            total_loot += actual_loot
        return total_loot
