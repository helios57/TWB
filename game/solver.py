"""
This module contains the core logic for the optimizing agent, including the
heuristic evaluation function and the search algorithm.
"""

from game.gamestate import GameState
from game.actions import RecruitAction

def evaluate_state(game_state: GameState, marginal_incomes: dict) -> float:
    """
    Calculates a heuristic score for a given GameState.
    A higher score indicates a more desirable state.
    """
    score = 0.0

    # Prioritize resource income (existing + future from new troops)
    score += game_state.resource_income.get('wood', 0) * 1.5
    score += game_state.resource_income.get('stone', 0) * 1.5
    score += game_state.resource_income.get('iron', 0) * 1.5

    # Factor in marginal income from newly recruited units
    if game_state.last_action and isinstance(game_state.last_action, RecruitAction):
        unit = game_state.last_action.unit
        amount = game_state.last_action.amount
        future_income = marginal_incomes.get(unit, 0) * amount
        score += future_income

    # Factor in building levels
    import math
    for building, level in game_state.building_levels.items():
        weight = 20 if building == 'main' else 10
        score += math.log(level + 1) * weight

    # Factor in total troop count
    troop_weights = {
        'spear': 1, 'sword': 1, 'axe': 2, 'light': 5, 'heavy': 8, 'ram': 10
    }
    for unit, count in game_state.troop_counts.items():
        score += count * troop_weights.get(unit, 1)

    # Penalize having a full warehouse
    total_resources = sum(game_state.resources.values())
    if game_state.storage_capacity > 0:
        fill_ratio = total_resources / game_state.storage_capacity
        if fill_ratio > 0.95:
            score *= 0.8

    return score


class MultiActionPlanner:
    """
    A planner that generates a sequence of actions to take in a single bot cycle.
    """
    def __init__(self, action_generator):
        self.action_generator = action_generator

    def plan_actions(self, initial_state: GameState, marginal_incomes: dict, max_actions=5):
        """
        Generates a sequence of the best actions to take.
        """
        import copy
        plan = []
        current_state = copy.deepcopy(initial_state)

        for _ in range(max_actions):
            best_action = self._find_best_immediate_action(current_state, marginal_incomes)

            if best_action:
                plan.append(best_action)
                current_state = self._simulate_action(current_state, best_action)
            else:
                break

        return plan

    def _find_best_immediate_action(self, state: GameState, marginal_incomes: dict):
        """
        Finds the single best affordable action from the current state.
        """
        best_action = None
        best_score = -float('inf')

        possible_actions = self.action_generator.generate(state)

        for action in possible_actions:
            cost = action.cost()
            if all(state.resources.get(res, 0) >= cost.get(res, 0) for res in cost):
                next_state = self._simulate_action(state, action)
                score = evaluate_state(next_state, marginal_incomes)

                if score > best_score:
                    best_score = score
                    best_action = action

        return best_action


    def _simulate_action(self, state: GameState, action) -> GameState:
        """
        Simulates the effect of an action on a game state.
        """
        import copy
        new_state = copy.deepcopy(state)
        new_state.last_action = action # Set the action that led to this state

        cost = action.cost()
        new_state.resources['wood'] -= cost.get('wood', 0)
        new_state.resources['stone'] -= cost.get('stone', 0)
        new_state.resources['iron'] -= cost.get('iron', 0)

        if "Build" in action.name:
            new_state.building_levels[action.building] = action.level
        elif "Recruit" in action.name:
            current_amount = new_state.troop_counts.get(action.unit, 0)
            new_state.troop_counts[action.unit] = current_amount + action.amount

        return new_state
