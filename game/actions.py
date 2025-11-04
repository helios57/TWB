"""
This module defines the action space for the TWB bot. Each action is
represented by a class that encapsulates the action's name, any relevant
parameters, and a method to calculate its cost.
"""

class Action:
    """Base class for all actions."""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"<Action: {self.name}>"

    def cost(self):
        """Returns the resource cost of the action."""
        return {'wood': 0, 'stone': 0, 'iron': 0, 'pop': 0}


class BuildAction(Action):
    """Represents a building construction or upgrade action."""
    def __init__(self, building, level, cost_data):
        super().__init__(f"Build {building} to level {level}")
        self.building = building
        self.level = level
        self._cost = cost_data

    def cost(self):
        return self._cost


class RecruitAction(Action):
    """Represents a troop recruitment action."""
    def __init__(self, unit, amount, cost_data):
        super().__init__(f"Recruit {amount} of {unit}")
        self.unit = unit
        self.amount = amount
        self._cost = {
            'wood': cost_data.get('wood', 0) * amount,
            'stone': cost_data.get('stone', 0) * amount,
            'iron': cost_data.get('iron', 0) * amount,
            'pop': cost_data.get('pop', 0) * amount
        }

    def cost(self):
        return self._cost


class ResearchAction(Action):
    """Represents a research action."""
    def __init__(self, unit, level, cost_data):
        super().__init__(f"Research {unit} to level {level}")
        self.unit = unit
        self.level = level
        self._cost = cost_data

    def cost(self):
        return self._cost
