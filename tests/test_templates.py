import unittest
from unittest.mock import MagicMock, patch
from core.templates import TemplateManager
from core.exceptions import InvalidJSONException

class TestTemplateManager(unittest.TestCase):
    @patch('core.filemanager.FileManager.path_exists')
    @patch('core.filemanager.FileManager.load_json_file')
    @patch('core.filemanager.FileManager.read_file')
    def test_get_template_fallback_to_txt(self, mock_read_file, mock_load_json, mock_path_exists):
        """
        Tests that get_template correctly falls back to reading a .txt file as plain text
        when JSON parsing fails.
        """
        # Arrange
        mock_path_exists.return_value = False
        mock_load_json.side_effect = InvalidJSONException
        mock_read_file.return_value = "main:20"

        # Act
        result = TemplateManager.get_template("builder", "legacy_template", output_json=True)

        # Assert
        self.assertEqual(result, "main:20")
        mock_load_json.assert_called_once_with("templates/builder/legacy_template.txt")
        mock_read_file.assert_called_once_with("templates/builder/legacy_template.txt")

if __name__ == '__main__':
    unittest.main()
