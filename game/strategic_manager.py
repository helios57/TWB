import logging

class StrategicManager:
    """
    Manages the overall bot strategy, assigning roles to villages.
    """
    def __init__(self, config, all_villages_data):
        self.logger = logging.getLogger("StrategicManager")
        self.config = config.get('strategy', {})
        self.all_villages_data = all_villages_data
        self.strategy_mode = self.config.get('mode', 'default')

    def run(self):
        """
        Determines and assigns the strategy for each village.
        Returns a dictionary mapping village_id to its strategy object.
        """
        self.logger.info(f"Running strategic manager in '{self.strategy_mode}' mode.")
        if not self.config.get('enabled', False):
            self.logger.info("Strategy manager is disabled in config.")
            return {}

        if self.strategy_mode == "noble_rush":
            return self._assign_noble_rush_strategy()
        else:  # default
            return self._assign_bootstrap_expand_strategy()

    def _assign_bootstrap_expand_strategy(self):
        strategies = {}
        core_village_id = self.config.get('core_village_id')

        if not core_village_id:
            # If no core is set, assign the first managed village as the bootstrap village
            if self.all_villages_data:
                core_village_id = list(self.all_villages_data.keys())[0]
                self.logger.warning(f"No 'core_village_id' set in strategy config. Defaulting to first village: {core_village_id}")
            else:
                self.logger.error("Strategy enabled, but no villages are managed and no core_village_id is set.")
                return {}

        for village_id in self.all_villages_data:
            if str(village_id) == str(core_village_id):
                strategies[village_id] = {
                    "role": "BOOTSTRAP",
                    "build_template": self.config.get("default_bootstrap_building", "purple_predator_into_off"),
                    "units_template": self.config.get("default_bootstrap_units", "basic_into_off"),
                    "wanted_snobs": 0 # Bootstrap villages typically don't build nobles
                }
            else:
                strategies[village_id] = {
                    "role": "DEVELOP",
                    "build_template": self.config.get("default_develop_building", "purple_predator_into_def"),
                    "units_template": self.config.get("default_develop_units", "basic_into_def"),
                    "wanted_snobs": 0 # Develop villages build nobles based on their own config
                }
        self.logger.info(f"Assigned 'Bootstrap & Expand' strategies: {strategies}")
        return strategies

    def _assign_noble_rush_strategy(self):
        strategies = {}
        core_village_id = self.config.get('core_village_id')

        if not core_village_id:
            if self.all_villages_data:
                core_village_id = list(self.all_villages_data.keys())[0]
                self.logger.warning(f"No 'core_village_id' for Noble Rush. Defaulting to first village: {core_village_id}")
            else:
                self.logger.error("Noble Rush enabled, but no villages are managed and no core_village_id is set.")
                return {}

        num_villages = len(self.all_villages_data)
        core_noble_target = self.config.get('core_noble_target', 1)

        for village_id in self.all_villages_data:
            if str(village_id) == str(core_village_id):
                 strategies[village_id] = {
                    "role": "NOBLE_RUSH_CORE",
                    "build_template": self.config.get("noble_rush_core_building", "noble_rush_core_build"),
                    "units_template": self.config.get("noble_rush_core_units", "noble_rush_core_units"),
                    "wanted_snobs": core_noble_target * num_villages
                }
            else:
                strategies[village_id] = {
                    "role": "NOBLE_RUSH_DEVELOP",
                    "build_template": self.config.get("noble_rush_develop_building", "noble_rush_develop_build"),
                    "units_template": self.config.get("noble_rush_develop_units", "noble_rush_develop_units"),
                    "wanted_snobs": 0
                }
        self.logger.info(f"Assigned 'Noble Rush' strategies: {strategies}")
        return strategies
