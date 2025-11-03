import unittest
import json
import os
from unittest.mock import patch, mock_open
from core.configmanager import ConfigManager

class TestConfigManager(unittest.TestCase):

    def setUp(self):
        # Reset singleton instance before each test
        ConfigManager._instance = None
        self.config_data = {
            "villages": {
                "123": {"units": "noble_rush_phase1_units"}
            }
        }
        # Create a mock config file
        with open("config.json", "w") as f:
            json.dump(self.config_data, f)

    def tearDown(self):
        # Remove the mock config file
        os.remove("config.json")

    def test_load_config(self):
        cm = ConfigManager()
        self.assertEqual(cm.get_config(), self.config_data)

    def test_save_config(self):
        with open('test_config.json', 'w') as f:
            json.dump({}, f)
        cm = ConfigManager(config_path='test_config.json')
        cm.config = {"key": "new_value"}
        cm.save_config()
        with open('test_config.json', 'r') as f:
            data = json.load(f)
        self.assertEqual(data, {"key": "new_value"})
        os.remove('test_config.json')

    def test_update_village_config(self):
        with open('test_config.json', 'w') as f:
            json.dump(self.config_data, f)
        cm = ConfigManager(config_path='test_config.json')
        cm.update_village_config("123", "units", "noble_rush_final_units")
        with open('test_config.json', 'r') as f:
            data = json.load(f)
        self.assertEqual(data["villages"]["123"]["units"], "noble_rush_final_units")
        os.remove('test_config.json')

if __name__ == '__main__':
    unittest.main()
