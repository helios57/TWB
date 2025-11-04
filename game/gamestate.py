"""
This module defines the GameState class, which serves as a centralized data
model for all information related to a single village. It is designed to be
populated by various manager classes and then used by an optimizing agent to
make decisions.
"""

class GameState:
    """
    Represents the complete state of a village at a specific point in time.
    """
    def __init__(self, village_id: str):
        self.village_id = village_id
        self.timestamp = 0

        # --- Resources ---
        self.resources = {
            'wood': 0,
            'stone': 0,
            'iron': 0,
            'pop': 0
        }
        self.storage_capacity = 0
        self.resource_income = {
            'wood': 0,
            'stone': 0,
            'iron': 0
        }

        # --- Buildings ---
        self.building_levels = {}
        self.building_queue = []

        # --- Troops ---
        self.troop_counts = {}
        self.units_in_village = {}
        self.units_outside_village = {}
        self.research_levels = {}
        self.troop_queue = {
            'barracks_queue_time': 0,
            'stable_queue_time': 0,
            'garage_queue_time': 0
        }

        # --- Village Status ---
        self.is_under_attack = False
        self.flags = {}

        # --- AI Planner State ---
        self.last_action = None # The action that led to this state

    def __repr__(self):
        return f"<GameState for Village {self.village_id} at {self.timestamp}>"
