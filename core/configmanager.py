import json
import logging
import threading

logger = logging.getLogger(__name__)

class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path='config.json'):
        if not hasattr(self, 'initialized'):
            self.config_path = config_path
            self.config = None
            self.load_config()
            self.initialized = True

    def load_config(self):
        """Loads the configuration from the specified JSON file."""
        with self._lock:
            try:
                with open(self.config_path, 'r') as f:
                    self.config = json.load(f)
                logger.debug(f"Configuration loaded from {self.config_path}")
            except FileNotFoundError:
                logger.error(f"Config file not found at {self.config_path}")
                # Exit or handle as per application requirements
                raise
            except json.JSONDecodeError:
                logger.error(f"Error decoding JSON from {self.config_path}")
                raise

    def save_config(self):
        """Saves the current configuration to the JSON file."""
        with self._lock:
            try:
                with open(self.config_path, 'w') as f:
                    json.dump(self.config, f, indent=4)
                logger.debug(f"Configuration saved to {self.config_path}")
            except IOError as e:
                logger.error(f"Could not write to config file {self.config_path}: {e}")

    def get_config(self):
        """Returns the entire configuration dictionary."""
        return self.config

    def update_village_config(self, village_id, key, value):
        """
        Updates a specific configuration key for a village and saves the config.
        """
        if not self.config:
            self.load_config()

        village_id_str = str(village_id)
        if 'villages' in self.config and village_id_str in self.config['villages']:
            if self.config['villages'][village_id_str].get(key) == value:
                logger.debug(f"No change needed for village {village_id_str}, key '{key}'.")
                return

            self.config['villages'][village_id_str][key] = value
            logger.info(f"Updated config for village {village_id_str}: set '{key}' to '{value}'.")
            self.save_config()
        else:
            logger.warning(f"Village ID {village_id_str} not found in config. Cannot update.")
