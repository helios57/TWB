import coloredlogs
import json
import logging
import argparse
import sys
import time
from threading import Thread

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

        # Load configuration
        try:
            with open("config.json") as f:
                self.config = json.load(f)
        except IOError:
            print("[TWB] config.json not found! Please create one.")
            sys.exit(1)

        self.setup_logging()

        from core.request import Request as WebWrapper
        self.wrapper = WebWrapper(
            cookies=self.config.get("cookie"),
            server=self.config["server"]["server"],
            world=self.config["server"]["world"],
        )
        if self.wrapper:
            for vil in self.config["villages"]:
                self.villages[vil] = Village(village_id=vil, wrapper=self.wrapper)
        else:
            self.logger.error("[TWB] Login failed, please check your cookie!")
            sys.exit(1)

    def setup_logging(self):
        """
        Set up logging for the bot
        """
        log_level = self.config.get("bot", {}).get("log_level", "INFO")
        log_format = '%(asctime)s %(name)-25s %(levelname)-8s %(message)s'

        # Use coloredlogs for console output
        coloredlogs.install(level=log_level, fmt=log_format, level_styles={
            'debug': {'color': 'white', 'faint': True},
            'info': {'color': 'cyan'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red', 'bold': True},
            'critical': {'color': 'magenta', 'bold': True, 'background': 'white'}
        })

        self.logger = logging.getLogger("TribalWarsBot")

        # Optional: Add a file handler
        if self.config.get("bot", {}).get("log_to_file", False):
            file_handler = logging.FileHandler('twb.log')
            file_handler.setLevel(log_level)
            formatter = logging.Formatter(log_format)
            file_handler.setFormatter(formatter)
            logging.getLogger('').addHandler(file_handler) # Add to root logger
            self.logger.info("[TWB] Logging to file enabled.")

    def run(self):
        """
        Main loop of the bot
        """
        self.logger.info("[TWB] Bot started!")

        # Initialize Strategic Manager if enabled
        strategy_manager = None
        if self.config.get("strategy", {}).get("enabled", False):
            self.logger.info("[STRATEGY] Strategic Manager is enabled.")
            strategy_manager = StrategicManager(self.config, self.villages)
        else:
            self.logger.info("[STRATEGY] Strategic Manager is disabled.")

        wait_time = self.config.get("bot", {}).get("wait_time", 60)

        while not self.stopping:
            try:
                # Get strategies from the strategic manager
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

    # if arguments.gui:
    #     bot.g_manager = GUIManager(bot_instance=bot)
    #     t = Thread(target=bot.run)
    #     t.start()
    #     bot.g_manager.run()
    #     t.join()
    # else:
    bot.run()
