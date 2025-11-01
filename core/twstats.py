import logging
import os
import time

import requests

from core.filemanager import FileManager


class TwStats:
    """
    TWStats API wrapper
    """

    base_url = "https://www.twstats.com/{world}/api.php?type={type}"
    building_pop = {}
    unit_pop = {}
    world = None
    logger = None

    def __init__(self, world=None):
        if world:
            self.run(world)
        self.logger = logging.getLogger("TWStats")

    def get_building_pop(self, building, level):
        """
        Get population of a building at a certain level
        :param building: building name
        :param level: building level
        :return: population
        """
        if building in self.building_pop:
            if str(level) in self.building_pop[building]:
                return self.building_pop[building][str(level)]
        return 0

    def get_unit_pop(self, unit):
        """
        Get population of a unit
        :param unit: unit name
        :return: population
        """
        if unit in self.unit_pop:
            return self.unit_pop[unit]
        return 0

    def run(self, world):
        """
        Run the TWStats API wrapper
        :param world: world to get stats for
        """
        self.world = world
        self.get_config("building")
        self.get_config("unit")

    def get_config(self, item_type):
        """
        Get config from TWStats API
        :param item_type: type of item to get config for (building or unit)
        """
        cache_path = f"cache/twstats_{self.world}_{item_type}.json"

        # Check if cache exists and is recent
        if os.path.exists(cache_path) and (time.time() - os.path.getmtime(cache_path)) < 86400:
            data = FileManager.load_json_file(cache_path)
        else:
            url = self.base_url.format(world=self.world, type=f"{item_type}config")
            try:
                response = requests.get(url)
                response.raise_for_status()
                data = self.parse_config(response.text)
                FileManager.save_json_file(data, cache_path)
                self.logger.info(f"[TWSTATS] Synced {item_type} config with twstats.com")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"[TWSTATS] Error fetching {item_type} config: {e}")
                # Try to load from cache as a fallback
                data = FileManager.load_json_file(cache_path) if os.path.exists(cache_path) else {}

        if item_type == "building":
            self.building_pop = data
        elif item_type == "unit":
            self.unit_pop = data

    def parse_config(self, text_data):
        """
        Parse config from TWStats API
        :param text_data: text data from API
        :return: parsed config
        """
        result = {}
        lines = text_data.strip().split("\n")
        headers = lines[0].split(";")

        for line in lines[1:]:
            values = line.split(";")
            row_data = dict(zip(headers, values))

            # For buildings, create a nested dictionary
            if "building" in headers:
                building_name = row_data["building"]
                if building_name not in result:
                    result[building_name] = {}
                # Assuming 'level' and 'pop' columns exist for buildings
                if "level" in row_data and "pop" in row_data:
                    result[building_name][row_data["level"]] = int(row_data["pop"])
            # For units, a simple dictionary is fine
            elif "unit" in headers:
                 unit_name = row_data["unit"]
                 if "pop" in row_data:
                     result[unit_name] = int(row_data["pop"])

        return result
