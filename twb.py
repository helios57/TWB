import coloredlogs
import json
import logging
import argparse
import sys
import time
from threading import Thread
import os

# from core.g_manager import GUIManager
from game.village import Village, VillageInitException
from game.strategic_manager import StrategicManager


class TWB:
    """
    Main class for the bot
    """
    villages = {}
    config = None
    logger = None
    wrapper = None

    def __init__(self, arguments=None):
        self.args = arguments
        self.g_manager = None
        self.stopping = False

        self.load_config()
        self.setup_logging()
        self.initialize_wrapper()

        if self.wrapper and self.wrapper.login():
            self.load_villages()
        else:
            self.logger.error("[TWB] Login failed. Please check your session.json or config.json credentials.")
            sys.exit(1)

    def load_config(self):
        """
        Loads configuration from config.json
        """
        try:
            with open("config.json") as f:
                self.config = json.load(f)
        except IOError:
            # Create a minimal config if it doesn't exist to prevent crashes
            self.config = {}
            print("[TWB] config.json not found! Please create one. Using minimal config.")

    def initialize_wrapper(self):
        """
        Initializes the Request wrapper with session or config data.
        """
        from core.request import Request as WebWrapper

        # Prioritize session.json
        if os.path.exists("session.json"):
            try:
                with open("session.json") as f:
                    session_data = json.load(f)
                self.logger.info("[AUTH] Found session.json. Attempting to login with session cookies.")
                self.wrapper = WebWrapper(
                    cookies=session_data.get("cookies"),
                    endpoint=session_data.get("endpoint")
                )
                return
            except (IOError, json.JSONDecodeError) as e:
                self.logger.warning("[AUTH] Could not load session.json: %s. Falling back to config.json.", e)

        # Fallback to config.json
        self.logger.info("[AUTH] No valid session.json found. Attempting to use config.json.")
        server_config = self.config.get("server", {})
        self.wrapper = WebWrapper(
            server=server_config.get("server"),
            world=server_config.get("world"),
            endpoint=server_config.get("endpoint")
        )

    def load_villages(self):
        """
        Loads village data from the configuration.
        """
        village_ids = self.config.get("villages", {}).keys()
        if not village_ids:
            self.logger.warning("[TWB] No villages found in config.json. The bot will have nothing to do.")

        for vil_id in village_ids:
            self.villages[vil_id] = Village(village_id=vil_id, wrapper=self.wrapper)
        self.logger.info(f"[TWB] Loaded {len(self.villages)} village(s).")


    def setup_logging(self):
        """
        Set up logging for the bot
        """
        log_level = self.config.get("bot", {}).get("log_level", "INFO")
        log_format = '%(asctime)s %(name)-25s %(levelname)-8s %(message)s'

        coloredlogs.install(level=log_level, fmt=log_format, level_styles={
            'debug': {'color': 'white', 'faint': True},
            'info': {'color': 'cyan'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red', 'bold': True},
            'critical': {'color': 'magenta', 'bold': True, 'background': 'white'}
        })

        self.logger = logging.getLogger("TribalWarsBot")

        if self.config and self.config.get("bot", {}).get("log_to_file", False):
            file_handler = logging.FileHandler('twb.log')
            file_handler.setLevel(log_level)
            formatter = logging.Formatter(log_format)
            file_handler.setFormatter(formatter)
            logging.getLogger('').addHandler(file_handler)
            self.logger.info("[TWB] Logging to file enabled.")

    def run(self):
        """
        Main loop of the bot
        """
        self.logger.info("[TWB] Bot started!")

        strategy_manager = None
        if self.config.get("strategy", {}).get("enabled", False):
            self.logger.info("[STRATEGY] Strategic Manager is enabled.")
            strategy_manager = StrategicManager(self.config, self.villages)
        else:
            self.logger.info("[STRATEGY] Strategic Manager is disabled.")

        wait_time = self.config.get("bot", {}).get("wait_time", 60)

        while not self.stopping:
            try:
                strategies = {}
                if strategy_manager:
                    strategies = strategy_manager.run()

                for vil_id, village in self.villages.items():
                    if self.stopping:
                        break

                    strategy_for_village = strategies.get(vil_id)

                    try:
                        village.run(config=self.config, strategy=strategy_for_village)
                    except VillageInitException:
                        self.logger.warning("[TWB] Village %s failed to initialize, skipping.", vil_id)

                    self.logger.info("[TWB] Sleeping for %d seconds...", wait_time)
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                self.stop()
            except Exception as e:
                self.logger.critical("[TWB] An unhandled exception occurred: %s", e, exc_info=True)
                self.stop()

        self.logger.info("[TWB] Bot stopped.")

    def stop(self):
        self.stopping = True
        self.logger.info("[TWB] Stopping bot...")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--gui", help="Use GUI", action="store_true")
    arguments = parser.parse_args()

    bot = TWB(arguments=arguments)

    # GUI logic commented out for now
    # if arguments.gui:
    #     bot.g_manager = GUIManager(bot_instance=bot)
    #     t = Thread(target=bot.run)
    #     t.start()
    #     bot.g_manager.run()
    #     t.join()
    # else:
    bot.run()
