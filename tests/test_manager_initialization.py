import unittest
from unittest.mock import MagicMock

from game.buildingmanager import BuildingManager
from game.troopmanager import TroopManager
from game.resources import ResourceManager
from game.defence_manager import DefenceManager
from game.attack import AttackManager


class TestManagerInitialization(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "12345"

    def test_building_manager_initialization(self):
        """Verify BuildingManager initializes all attributes accessed by Village."""
        manager = BuildingManager(self.wrapper, self.village_id)
        # This attribute caused the crash
        self.assertTrue(hasattr(manager, "last_status"), "BuildingManager must have 'last_status' attribute on initialization.")
        # Other attributes accessed by Village
        self.assertTrue(hasattr(manager, "levels"), "BuildingManager must have 'levels' attribute on initialization.")
        self.assertTrue(hasattr(manager, "queue"), "BuildingManager must have 'queue' attribute on initialization.")

    def test_troop_manager_initialization(self):
        """Verify TroopManager initializes all attributes accessed by Village."""
        manager = TroopManager(self.wrapper, self.village_id)
        self.assertTrue(hasattr(manager, "troops"), "TroopManager must have 'troops' attribute on initialization.")
        self.assertTrue(hasattr(manager, "total_troops"), "TroopManager must have 'total_troops' attribute on initialization.")
        self.assertTrue(hasattr(manager, "can_attack"), "TroopManager must have 'can_attack' attribute on initialization.")

    def test_resource_manager_initialization(self):
        """Verify ResourceManager initializes all attributes accessed by Village."""
        manager = ResourceManager(self.wrapper, self.village_id)
        self.assertTrue(hasattr(manager, "actual"), "ResourceManager must have 'actual' attribute on initialization.")
        self.assertTrue(hasattr(manager, "requested"), "ResourceManager must have 'requested' attribute on initialization.")
        self.assertTrue(hasattr(manager, "storage"), "ResourceManager must have 'storage' attribute on initialization.")

    def test_defence_manager_initialization(self):
        """Verify DefenceManager initializes all attributes accessed by Village."""
        manager = DefenceManager(self.wrapper, self.village_id)
        self.assertTrue(hasattr(manager, "under_attack"), "DefenceManager must have 'under_attack' attribute on initialization.")

    def test_attack_manager_initialization(self):
        """Verify AttackManager initializes all attributes accessed by Village."""
        # AttackManager has a more complex __init__, so we need to mock its dependencies
        troop_manager_mock = MagicMock()
        map_mock = MagicMock()
        manager = AttackManager(self.wrapper, self.village_id, troopmanager=troop_manager_mock, map=map_mock)
        self.assertTrue(hasattr(manager, "last_farm_bag_state"), "AttackManager must have 'last_farm_bag_state' attribute on initialization.")


if __name__ == '__main__':
    unittest.main()
