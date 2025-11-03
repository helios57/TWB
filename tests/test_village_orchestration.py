import unittest
from unittest.mock import MagicMock, patch, call
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from game.village import Village
from game.buildingmanager import BuildingManager
from game.troopmanager import TroopManager
from core.templates import TemplateManager

class TestVillageOrchestration(unittest.TestCase):

    @patch('core.templates.TemplateManager.get_template')
    def setUp(self, mock_get_template):
        # Mock templates to prevent file I/O
        mock_get_template.side_effect = self.mock_template_loader

        self.wrapper = MagicMock()
        self.village_id = "12345"
        self.village = Village(self.village_id, self.wrapper)
        self.village.logger = MagicMock()

        # Mock managers
        self.village.builder = MagicMock(spec=BuildingManager)
        self.village.units = MagicMock(spec=TroopManager)
        self.village.resman = MagicMock()

        # Default configs
        self.village.config = {
            "villages": {
                self.village_id: {
                    "building": "noble_rush_phase1",
                    "units": "noble_rush_strategy"
                }
            },
            "building": {"default": "default_builder"},
            "units": {"default": "default_units"}
        }

    def mock_template_loader(self, category, template, output_json=False):
        templates = {
            "builder": {
                "noble_rush_phase1": "stable:3",
                "noble_rush_final": "main:20"
            },
            "troops": {
                "noble_rush_strategy": [{"building": "main", "level": 1, "build": {"spear": 10}}]
            }
        }
        if output_json:
            return templates[category].get(template, {})
        return templates[category].get(template, "")

    def test_phase_transition_from_phase1_to_final(self):
        # --- Stage 1: Village is in Phase 1 ---
        # Simulate building levels before phase transition
        self.village.builder.get_level.return_value = 2 # Stable is not yet level 3

        # Act
        self.village.run_builder()

        # Assert
        self.assertEqual(self.village.build_config, "noble_rush_phase1")
        self.assertEqual(self.village.builder.mode, "linear")
        self.assertIn("stable:3", self.village.builder.queue)

        # --- Stage 2: Village completes Phase 1 ---
        # Simulate stable reaching level 3, triggering the transition
        self.village.builder.get_level.return_value = 3

        # Act
        self.village.run_builder()

        # Assert
        # The village should detect completion and switch the build config
        self.assertEqual(self.village.build_config, "noble_rush_final")
        # The builder should now be in dynamic mode with the final targets
        self.assertEqual(self.village.builder.mode, "dynamic")
        self.assertIn("main", self.village.builder.target_levels)
        self.assertEqual(self.village.builder.target_levels["main"], 20)

if __name__ == '__main__':
    unittest.main()
