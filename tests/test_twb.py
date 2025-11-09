import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Ensure the root directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from twb import TWB

class TestTWB(unittest.TestCase):

    def setUp(self):
        """Set up a TWB instance for testing."""
        self.twb = TWB()
        # Mock the wrapper to avoid actual web requests, though it won't be used if we patch OverviewPage
        self.twb.wrapper = MagicMock()

    @patch('twb.OverviewPage')
    @patch('twb.Extractor')
    @patch('twb.TWB.add_village')
    def test_get_overview_handles_first_run_with_no_villages(self, mock_add_village, mock_extractor_class, mock_overview_page_class):
        """
        Test that TWB.get_overview correctly handles the first run when config['villages'] is empty.
        It should detect the new village and call add_village without crashing.
        """
        # Arrange: Simulate a first run with an empty villages dict
        mock_config = {
            "bot": {"add_new_villages": True},
            "villages": {},
            "village_template": {"building": "default", "units": "default"}
        }

        # Configure the mock for OverviewPage to avoid real web requests and parsing
        mock_overview_instance = MagicMock()
        mock_overview_instance.result_get.text = "mock html content"
        mock_overview_page_class.return_value = mock_overview_instance

        # Mock the Extractor class method to return a newly detected village
        mock_extractor_class.village_ids_from_overview.return_value = ['12345']

        # Mock the add_village to prevent file system operations and return the updated config
        def add_village_side_effect(village_id, template):
            mock_config['villages'][village_id] = template
            return mock_config
        mock_add_village.side_effect = add_village_side_effect

        # Act
        try:
            _, updated_config = self.twb.get_overview(config=mock_config)
        except StopIteration:
            self.fail("TWB.get_overview() raised StopIteration unexpectedly on first run.")

        # Assert
        # 1. Verify that OverviewPage was instantiated
        mock_overview_page_class.assert_called_once_with(self.twb.wrapper)

        # 2. Verify that the extractor was called to find villages
        mock_extractor_class.village_ids_from_overview.assert_called_once_with("mock html content")

        # 3. Verify that add_village was called for the new village
        mock_add_village.assert_called_once()

        # 4. Check the call arguments for add_village
        args, kwargs = mock_add_village.call_args
        self.assertEqual(kwargs.get('village_id'), '12345')

        # 5. Check that the config was updated
        self.assertIn('12345', updated_config['villages'])

if __name__ == '__main__':
    unittest.main()
