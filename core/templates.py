from core.filemanager import FileManager
import json

class TemplateManager:
    """
    Template manager that can read and parse templates
    """

    @staticmethod
    def get_template(category, template, output_json=False):
        """
        Get a template from the templates folder
        :param category: category of the template
        :param template: name of the template
        :param output_json: whether to output as json or as a list
        :return: template
        """
        path = f"templates/{category}/{template}"
        if not path.endswith(".txt") and not path.endswith(".json"):
            path += ".txt" # Assume .txt if no extension

        content = FileManager.read_file(path)
        if not content:
            return [] if not output_json else {}

        if output_json or path.endswith(".json"):
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {} # Return empty dict on error
        else:
            return content.strip().split()
