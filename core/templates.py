"""
Manages template files
"""
from core.filemanager import FileManager
from core.exceptions import InvalidJSONException


class TemplateManager:
    """
    Template manager file
    """
    @staticmethod
    def get_template(category, template="basic", output_json=False):
        """
        Reads a specific text file with arguments
        TODO: switch to improved FileManager
        """
        if isinstance(template, list):
            return template

        path = f"templates/{category}/{template}.txt"
        if output_json:
            json_path = f"templates/{category}/{template}.json"
            if FileManager.path_exists(json_path):
                return FileManager.load_json_file(json_path)
            try:
                # Fallback for .txt files that might contain JSON
                return FileManager.load_json_file(path)
            except InvalidJSONException:
                # If JSON parsing fails, it's a legacy text file. Read as plain text.
                return FileManager.read_file(path)

        return FileManager.read_file(path)
