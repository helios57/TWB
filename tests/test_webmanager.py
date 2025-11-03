import unittest
import sys
import os
import json
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from webmanager.server import app

class TestWebManager(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        # Mock the sync function to provide controlled data
        self.sync_patcher = patch('webmanager.server.sync')
        self.mock_sync = self.sync_patcher.start()
        self.mock_sync.return_value = self.get_mock_sync_data()

    def tearDown(self):
        self.sync_patcher.stop()

    def get_mock_sync_data(self):
        return {
            "bot": {
                "12345": {
                    "public": {"id": "12345", "name": "Test Village", "location": "500|500"},
                    "planned_actions": [
                        "Build Main to level 20 (Reason: Academy prerequisite)",
                        "Recruit 100 Light Cavalry (Target: 2500)"
                    ]
                }
            },
            "config": {"villages": {"12345": {"building": "noble_rush_final", "units": "noble_rush_strategy"}}}
        }

    def test_village_detail_page_loads_and_shows_planned_actions(self):
        # Act
        response = self.client.get('/village?id=12345')

        # Assert
        self.assertEqual(response.status_code, 200)

        # Check that the planned actions are rendered in the HTML
        response_text = response.get_data(as_text=True)
        self.assertIn("<h4>Planned Actions</h4>", response_text)
        self.assertIn("Build Main to level 20 (Reason: Academy prerequisite)", response_text)
        self.assertIn("Recruit 100 Light Cavalry (Target: 2500)", response_text)
        self.assertIn("Test Village", response_text)

if __name__ == '__main__':
    unittest.main()
