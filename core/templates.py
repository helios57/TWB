"""
Manages template files
"""
from core.filemanager import FileManager


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
            return FileManager.load_json_file(path) # Fallback for .txt files with JSON

        return FileManager.read_file(path)
