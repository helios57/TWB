"""
This module contains the ActionGenerator class, which is responsible for
generating all possible actions from a given GameState.
"""

from game.gamestate import GameState
from game.actions import BuildAction, RecruitAction, ResearchAction

class ActionGenerator:
    """
    Generates possible actions based on the current game state and templates.
    """
    def __init__(self):
        self.building_templates = {}
        self.troop_templates = {}
        self.building_costs = {}
        self.recruit_costs = {}
        self.research_costs = {}

    def update_data(self, building_templates, troop_templates, building_costs, recruit_costs, research_costs):
        """
        Updates the generator with the latest templates and costs.
        """
        self.building_templates = building_templates
        self.troop_templates = troop_templates
        self.building_costs = building_costs
        self.recruit_costs = recruit_costs
        self.research_costs = research_costs

    def generate(self, state: GameState):
        """
        Generates a list of all possible actions.
        """
        actions = []
        actions.extend(self._generate_build_actions(state))
        actions.extend(self._generate_recruit_actions(state))
        actions.extend(self._generate_research_actions(state))
        return actions

    def _can_afford(self, state: GameState, cost):
        return (state.resources['wood'] >= cost.get('wood', 0) and
                state.resources['stone'] >= cost.get('stone', 0) and
                state.resources['iron'] >= cost.get('iron', 0))

    def _generate_build_actions(self, state: GameState):
        build_actions = []
        if not self.building_templates or 'template_data' not in self.building_templates:
            return build_actions

        template_data = self.building_templates['template_data']
        for item in template_data:
            if ":" not in item or item.startswith("#"):
                continue
            parts = item.split(":")
            if len(parts) != 2:
                continue
            building, target_level_str = parts
            building = building.strip()
            if not target_level_str.isdigit():
                continue
            target_level = int(target_level_str)
            current_level = state.building_levels.get(building, 0)
            if current_level < target_level:
                if building in self.building_costs:
                    cost = self.building_costs[building]
                    if self._can_afford(state, cost):
                        build_actions.append(BuildAction(building, current_level + 1, cost))
        return build_actions

    def _generate_recruit_actions(self, state: GameState):
        recruit_actions = []
        if not self.troop_templates or 'template_data' not in self.troop_templates:
            return recruit_actions

        template_data = self.troop_templates['template_data']
        for entry in template_data:
            if 'build' in entry:
                for building, units in entry['build'].items():
                    if state.building_levels.get(building, 0) > 0:
                        for unit, amount in units.items():
                            if unit in self.recruit_costs:
                                cost = self.recruit_costs[unit]
                                if self._can_afford(state, cost):
                                    recruit_actions.append(RecruitAction(unit, 10, cost)) # Recruit in batches of 10
        return recruit_actions

    def _generate_research_actions(self, state: GameState):
        research_actions = []
        if not self.troop_templates or 'template_data' not in self.troop_templates:
            return research_actions

        if state.building_levels.get('smith', 0) > 0:
            template_data = self.troop_templates['template_data']
            for entry in template_data:
                if 'upgrades' in entry:
                    for unit, target_level in entry['upgrades'].items():
                        current_level = state.research_levels.get(unit, 0)
                        if target_level > current_level:
                            if self.research_costs and unit in self.research_costs.get('available', {}):
                                cost = self.research_costs['available'][unit]
                                if self._can_afford(state, cost):
                                    research_actions.append(ResearchAction(unit, target_level, cost))
        return research_actions
