import json
import logging
import re
import time
from datetime import datetime

from core.extractors import Extractor
from core.filemanager import FileManager


class ReportManager:
    """
    Report manager that can read reports from the report screen
    """

    last_reports = {}
    farm_cache = {}
    wrapper = None
    village_id = None
    logger = None
    last_run = 0

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def in_cache(self, vid):
        """
        Check if a village is in the farm cache
        :param vid: village id
        :return: farm cache entry or False
        """
        vid = str(vid)
        if vid in self.farm_cache:
            return self.farm_cache[vid]
        return False

    def sort_by_time(self, entry):
        """
        Sort reports by time
        :param entry: report entry
        :return: timestamp
        """
        # self.logger.debug(f"Considered {len(possible_reports)} reports")
        return int(entry["extra"]["when"])

    def get_newest_report(self, possible_reports):
        """
        Get the newest report from a list of reports
        :param possible_reports: list of reports
        :return: newest report
        """
        if not possible_reports:
            return None
        newest = sorted(possible_reports, key=self.sort_by_time, reverse=True)[0]
        # self.logger.debug("This is the newest? %s", datetime.fromtimestamp(int(entry["extra"]["when"])))
        return newest

    def get_last_reports_from_overview(self, overview_html):
        """
        Get last reports from overview screen
        :param overview_html: html of overview screen
        :return: list of reports
        """
        if not overview_html:
            return []
        possible_reports = Extractor.get_reports(overview_html)
        reports = []
        # sort reports by time
        sorted_reports = sorted(possible_reports, key=lambda x: x["time"], reverse=True)
        for report in sorted_reports:
            if not report["id"] in self.last_reports:
                self.last_reports[report["id"]] = report
                reports.append(report)
        return reports

    def read(self, full_run=False, overview_html=None):
        """
        Read all reports
        """
        if not self.logger:
            self.logger = logging.getLogger(f"ReportManager:{self.village_id}")

        if not self.farm_cache and not full_run:
            self.farm_cache = FileManager.load_json_file(
                f"cache/farm_cache_{self.village_id}.json"
            )
            self.logger.info("[REPORTS] First run, re-reading cache entries")
            if self.farm_cache:
                self.logger.info("[REPORTS] Got %d reports from cache", len(self.farm_cache))

        reports_to_read = []
        if overview_html:
            self.logger.debug("[REPORTS] Reading reports from cached overview_html")
            reports_to_read.extend(self.get_last_reports_from_overview(overview_html))

        if full_run or not self.last_reports:
            # Full run, get all reports
            url = f"game.php?village={self.village_id}&screen=report"
            data = self.wrapper.get_url(url)
            possible_reports = Extractor.get_reports(data.text)
            for report in possible_reports:
                if not report["id"] in self.last_reports:
                    reports_to_read.append(report)
                    self.last_reports[report["id"]] = report

        if reports_to_read:
            # sort reports by time ascending
            reports_to_read = sorted(reports_to_read, key=lambda x: x["time"])
            self.logger.debug(
                "[REPORTS] Reading %d new reports", len(reports_to_read)
            )

        for report in reports_to_read:
            self.read_report_by_id(report["id"])
            time.sleep(random.uniform(0.5, 1.5))

        self.update_farm_profiles()

    def read_report_by_id(self, report_id):
        """
        Read a single report by its ID
        """
        url = (
            f"game.php?village={self.village_id}&screen=report&mode=all&view={report_id}"
        )
        data = self.wrapper.get_url(url)
        if not data:
            return

        report_data = Extractor.get_report_details(data.text)
        if report_data:
            report_type = report_data.get("type")
            if report_type == "attack":
                self.process_attack_report(report_data)
            elif report_type == "scout":
                self.process_scout_report(report_data)

    def process_attack_report(self, report):
        """
        Process a report of type 'attack'
        """
        from_village = report["from"]["id"]
        to_village = report["to"]["id"]
        self.logger.info("[REPORTS] Attack report %s -> %s", from_village, to_village)

        # Update farm cache if it's an outgoing attack from our village
        if from_village == self.village_id:
            self.update_farm_cache(to_village, report)

    def process_scout_report(self, report):
        """
        Process a report of type 'scout'
        """
        from_village = report["from"]["id"]
        to_village = report["to"]["id"]
        self.logger.info("[REPORTS] Scout report %s -> %s", from_village, to_village)

        # Update farm cache if it's an outgoing scout from our village
        if from_village == self.village_id:
            self.update_farm_cache(to_village, report)

    def update_farm_cache(self, to_village, report):
        """
        Update the farm cache with new report data
        """
        try:
            vid = str(to_village)
            if vid not in self.farm_cache:
                self.farm_cache[vid] = {"reports": [], "stats": {"loot_history": [], "loss_history": []}}

            # Keep a limited history of reports
            self.farm_cache[vid]["reports"].insert(0, report)
            if len(self.farm_cache[vid]["reports"]) > 10:
                self.farm_cache[vid]["reports"].pop()

            # Update last attack time and resources
            self.farm_cache[vid]["last_attack"] = int(time.time())
            self.farm_cache[vid]["res"] = report.get("loot", {})
            self.farm_cache[vid]["buildings"] = report.get("buildings", {})

            # Update stats
            loot = sum(report.get("loot", {}).values())
            self.farm_cache[vid]["stats"]["loot_history"].insert(0, loot)
            if len(self.farm_cache[vid]["stats"]["loot_history"]) > 5:
                 self.farm_cache[vid]["stats"]["loot_history"].pop()

            losses = report.get("losses", {}).get("attacker", 0)
            self.farm_cache[vid]["stats"]["loss_history"].insert(0, losses)
            if len(self.farm_cache[vid]["stats"]["loss_history"]) > 5:
                self.farm_cache[vid]["stats"]["loss_history"].pop()

            FileManager.save_json_file(self.farm_cache, f"cache/farm_cache_{self.village_id}.json")
        except Exception as e:
            self.logger.warning(f"[REPORTS] Failed to update farm cache for {to_village}: {e}")

    def update_farm_profiles(self):
        """
        Update profiles for all farms in the cache based on recent stats.
        """
        for village_id, data in self.farm_cache.items():
            if not data or "stats" not in data:
                self.logger.debug(f"[REPORTS] No attack cache found for {village_id}, skipping stat update.")
                continue

            stats = data["stats"]
            loot_history = stats.get("loot_history", [])
            loss_history = stats.get("loss_history", [])

            if not loot_history:
                continue

            # Calculate average loot and loss percentage
            avg_loot = sum(loot_history) / len(loot_history)

            # Get total troops sent from the last report (simplification)
            last_report = data.get("reports", [{}])[0]
            troops_sent = last_report.get("units", {}).get("attacker", {})
            total_sent_pop = sum(self.wrapper.get_unit_info(u, 'pop') * q for u, q in troops_sent.items())

            # Calculate loss percentage
            total_lost_pop = 0
            losses = last_report.get("losses_units", {}).get("attacker", {})
            for unit, count in losses.items():
                total_lost_pop += self.wrapper.get_unit_info(unit, 'pop') * count

            percentage_lost = (total_lost_pop / total_sent_pop) * 100 if total_sent_pop > 0 else 0

            # --- Decision Logic ---
            profile = data.get("profile", "normal") # Default profile

            if percentage_lost < 5:
                # Low losses, check loot
                if avg_loot < 100 and len(loot_history) >= 3:
                    profile = "low_profile" # Consistently low loot
                    self.logger.info(f"[REPORTS] Farm {village_id} has low resources ({avg_loot:.0f} avg), setting low_profile.")
                elif avg_loot > 800:
                    profile = "high_profile" # Good loot
                    self.logger.info(f"[REPORTS] Farm {village_id} has high resources ({avg_loot:.0f} avg), setting high_profile.")
                else:
                    profile = "normal" # Reset to normal if conditions change
            elif percentage_lost > 20:
                 # High losses
                 if percentage_lost > 50:
                    profile = "disabled" # Too dangerous
                    self.logger.critical(f"[REPORTS] Farm {village_id} is unsafe ({percentage_lost:.0f}% loss), disabling farm.")
                 else:
                    profile = "low_profile" # Risky, attack less often
                    self.logger.warning(f"[REPORTS] Farm {village_id} has high losses ({percentage_lost:.0f}%), setting low_profile.")

            self.farm_cache[village_id]["profile"] = profile

        FileManager.save_json_file(self.farm_cache, f"cache/farm_cache_{self.village_id}.json")


    def get_total_loot(self, since=86400):
        """
        Get total loot from all reports since a given time
        :param since: time in seconds since now
        :return: dict with total loot
        """
        total_loot = {"wood": 0, "stone": 0, "iron": 0}
        since_time = int(time.time()) - since
        for report_id, report in self.last_reports.items():
            if report.get("time", 0) > since_time:
                loot = report.get("loot", {})
                for res, amount in loot.items():
                    total_loot[res] += amount

        self.logger.info(
            "[REPORTS] Total loot in last %d seconds: %s", since, str(total_loot)
        )
        return total_loot
