import json
import logging
import os
import time

from core.filemanager import FileManager


class Reporter:
    """
    Reporting engine that can report to different sources like discord, file, mysql etc.
    """

    webhook_url = None
    file_log = False
    file_log_path = None
    mysql = False
    mysql_con = None
    mysql_insert_queue = []
    logger = None

    def __init__(self, webhook_url=None, file_log=False, file_log_path=None, mysql=False, mysql_con=None):
        self.webhook_url = webhook_url
        self.file_log = file_log
        self.file_log_path = file_log_path
        self.mysql = mysql
        if mysql_con:
            self.setup_mysql(mysql_con)

        self.logger = logging.getLogger("Reporter")

    def report(self, village_id, r_type, message, data=None):
        """
        Report a message to the different sources
        :param village_id: village id
        :param r_type: report type
        :param message: message to report
        :param data: optional data to report
        """
        if self.file_log:
            self.report_to_file(village_id, r_type, message, data)
        if self.mysql and self.mysql_con:
            self.report_to_mysql(village_id, r_type, message, data)
        # Discord reporting can be added here if needed

    def add_data(self, village_id, key, data):
        """
        Add data to the data cache
        :param village_id: village id
        :param key: key to store the data under
        :param data: data to store
        """
        if self.mysql and self.mysql_con:
            self.add_data_mysql(village_id, key, data)

    def report_to_file(self, village_id, r_type, message, data=None):
        """
        Report a message to a file
        :param village_id: village id
        :param r_type: report type
        :param message: message to report
        :param data: optional data to report
        """
        if not self.file_log_path:
            return

        log_entry = {
            "timestamp": time.time(),
            "village_id": village_id,
            "type": r_type,
            "message": message,
            "data": data
        }

        # Append to a general log file
        with open(os.path.join(self.file_log_path, "reporter.log"), "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    def add_data_mysql(self, village_id, key, data):
        """
        Add data to the data cache in mysql
        :param village_id: village id
        :param key: key to store the data under
        :param data: data to store
        """
        ts = int(time.time())
        query = "INSERT INTO `data` (`village_id`, `key`, `value`, `timestamp`) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE value = %s, timestamp = %s"
        self.mysql_insert_queue.append((query, (village_id, key, data, ts, data, ts)))
        self.process_mysql_queue()

    def report_to_mysql(self, village_id, r_type, message, data=None):
        """
        Report a message to mysql
        :param village_id: village id
        :param r_type: report type
        :param message: message to report
        :param data: optional data to report
        """
        ts = int(time.time())
        query = "INSERT INTO `logs` (`village_id`, `type`, `message`, `data`, `timestamp`) VALUES (%s, %s, %s, %s, %s)"
        log_data = (village_id, r_type, message, json.dumps(data) if data else None, ts)
        self.mysql_insert_queue.append((query, log_data))
        self.process_mysql_queue()

    def process_mysql_queue(self, force=False):
        """
        Process the mysql insert queue
        :param force: force processing the queue
        """
        if not self.mysql_con or not self.mysql:
            return

        if len(self.mysql_insert_queue) > 10 or force:
            try:
                cursor = self.mysql_con.cursor()
                for query, data in self.mysql_insert_queue:
                    cursor.execute(query, data)
                self.mysql_con.commit()
                self.mysql_insert_queue = []
            except Exception as e:
                self.logger.error("[REPORTER] Error processing MySQL queue: %s", e)

    def setup_mysql(self, mysql_con):
        """
        Setup the mysql database
        :param mysql_con: mysql connection data
        """
        try:
            import pymysql
        except ImportError:
            self.logger.error("[REPORTER] pymysql is required for MYSQL logging. You can install it using: pip install pymysql")
            self.mysql = False
            return

        try:
            self.mysql_con = pymysql.connect(
                host=mysql_con["host"],
                user=mysql_con["user"],
                password=mysql_con["password"],
                database=mysql_con["database"],
                port=mysql_con.get("port", 3306)
            )

            cursor = self.mysql_con.cursor()

            # Create logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `logs` (
                    `id` INT NOT NULL AUTO_INCREMENT,
                    `village_id` VARCHAR(10) NOT NULL,
                    `type` VARCHAR(50) NOT NULL,
                    `message` TEXT,
                    `data` JSON,
                    `timestamp` INT NOT NULL,
                    PRIMARY KEY (`id`),
                    INDEX `village_id` (`village_id`),
                    INDEX `type` (`type`)
                )
            """)

            # Create data table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS `data` (
                    `village_id` VARCHAR(10) NOT NULL,
                    `key` VARCHAR(50) NOT NULL,
                    `value` JSON,
                    `timestamp` INT NOT NULL,
                    PRIMARY KEY (`village_id`, `key`)
                )
            """)

            self.mysql_con.commit()
            self.logger.info("[REPORTER] MySQL set-up complete.")
        except Exception as e:
            self.logger.error("[REPORTER] Unable to set-up MySQL logging, disabling! Error: %s", e)
            self.mysql = False

    def __del__(self):
        """
        Destructor to ensure the queue is processed before exit
        """
        self.process_mysql_queue(force=True)
        if self.mysql_con:
            self.mysql_con.close()
