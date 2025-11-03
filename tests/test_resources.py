import unittest
from unittest.mock import MagicMock, patch
from game.resources import ResourceManager

class TestResourceManager(unittest.TestCase):
    def setUp(self):
        self.wrapper = MagicMock()
        self.village_id = 123
        self.resource_manager = ResourceManager(self.wrapper, self.village_id)
        self.resource_manager.logger = MagicMock()
        self.resource_manager.actual = {'wood': 1000, 'stone': 1000, 'iron': 1000}
        self.resource_manager.storage = 2000
        self.resource_manager.ratio = 2.0
        self.resource_manager.requested = {}

    def test_get_plenty_off_returns_correct_surplus_resources(self):
        """
        Tests that get_plenty_off correctly identifies and sorts surplus resources.
        """
        # Arrange
        self.resource_manager.actual = {'wood': 1500, 'stone': 500, 'iron': 1200}
        self.resource_manager.storage = 2000
        self.resource_manager.ratio = 2.0 # Threshold = 1000

        # Act
        surplus = self.resource_manager.get_plenty_off()

        # Assert
        self.assertEqual(surplus, ['wood', 'iron'])

    @patch('game.resources.ResourceManager.trade')
    @patch('game.resources.ResourceManager.check_other_offers', return_value=False)
    @patch('game.resources.ResourceManager.drop_existing_trades')
    def test_manage_market_initiates_trade_on_surplus_and_need(self, mock_drop, mock_check, mock_trade):
        """
        Tests that manage_market initiates a trade when there is a clear
        surplus and a clear need.
        """
        # Arrange
        self.resource_manager.actual = {'wood': 1500, 'stone': 500, 'iron': 500}
        self.resource_manager.storage = 2000
        self.resource_manager.ratio = 2.0 # Threshold = 1000
        self.resource_manager.requested = {"building": {"iron": 300}}
        self.resource_manager.last_trade = 0 # Ensure trade is not on cooldown
        self.wrapper.get_url.return_value.text = "mock html"

        # Act
        self.resource_manager.manage_market()

        # Assert
        mock_trade.assert_called_once_with('wood', 300, 'iron', 300)

if __name__ == '__main__':
    unittest.main()
