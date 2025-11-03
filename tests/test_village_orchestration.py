import unittest
from unittest.mock import MagicMock, patch
from game.village import Village
from tests.helpers import get_mock_data

class TestVillageOrchestration(unittest.TestCase):

    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = "55555"
        self.village = Village(self.village_id, self.wrapper)

        # Mock managers
        self.village.builder = MagicMock()
        self.village.snobman = MagicMock()
        self.village.units = MagicMock()
        self.village.logger = MagicMock()

        # Load mock config
        import json
        with open('tests/mock_data/config.json', 'r') as f:
            self.village.config = json.load(f)

    def test_phase_transition(self):
        # Scenario: Builder is using phase1 template and stable is at level 3
        self.village.build_config = "noble_rush_phase1"
        self.village.builder.get_level.return_value = 3 # Stable is level 3

        # We need to mock TemplateManager.get_template to return something
        with patch('game.village.TemplateManager.get_template') as mock_get_template:
            mock_get_template.return_value = "main:20\nbarracks:25" # Mock content of final template

            self.village.run_builder()

            # Assert that the build_config was changed and builder mode was set to dynamic
            self.assertEqual(self.village.build_config, "noble_rush_final")
            self.assertEqual(self.village.builder.mode, "dynamic")

    def test_hoard_mode_activation(self):
        # Scenario: SnobManager reports that it's incomplete
        self.village.snobman.is_incomplete = True
        self.village.builder.get_level.return_value = 1 # Snob is built

        self.village.run_snob_recruit()

        # Assert that hoard_mode is activated
        self.assertTrue(self.village.hoard_mode)

        # Now test that the builder does not run in hoard mode
        self.village.run_builder()
        self.village.builder.start_update.assert_not_called()

if __name__ == '__main__':
    unittest.main()
