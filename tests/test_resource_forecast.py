import unittest
from unittest.mock import MagicMock, PropertyMock

from game.village import Village
from game.buildingmanager import BuildingManager
from game.troopmanager import TroopManager


class TestResourceForecast(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village = Village(village_id="12345", wrapper=self.wrapper)
        self.village.builder = BuildingManager(wrapper=self.wrapper, village_id="12345")
        self.village.units = TroopManager(wrapper=self.wrapper, village_id="12345")

    def test_forecast_calculation(self):
        """Verify that the resource forecast is calculated correctly."""
        # Mock building data
        self.village.builder.costs = {
            'main': {'wood': 100, 'stone': 150, 'iron': 50},
            'barracks': {'wood': 200, 'stone': 100, 'iron': 150}
        }
        self.village.builder.get_planned_actions = MagicMock(return_value=["Build main to level 2", "Build barracks to level 3"])

        # Mock troop data
        self.village.units.recruit_data = {
            'spear': {'wood': 50, 'stone': 30, 'iron': 10},
            'sword': {'wood': 30, 'stone': 50, 'iron': 20}
        }
        self.village.units.get_planned_actions = MagicMock(return_value=["Recruit 10 spear", "Recruit 5 sword"])

        # Disable units is not needed for this test
        self.village.disabled_units = []

        forecast = self.village.calculate_resource_forecast()

        # Expected calculation:
        # Buildings: wood=300, clay=250, iron=200
        # Troops: wood=(10*50 + 5*30)=650, clay=(10*30 + 5*50)=550, iron=(10*10 + 5*20)=200
        # Total: wood=950, clay=800, iron=400
        self.assertEqual(forecast['wood'], 950)
        self.assertEqual(forecast['clay'], 800)
        self.assertEqual(forecast['iron'], 400)


if __name__ == '__main__':
    unittest.main()
