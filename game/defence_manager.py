import logging
import re
import time
from datetime import datetime

from core.extractors import Extractor


class DefenceManager:
    """
    Defence manager for a village
    """

    village_id = None
    wrapper = None
    under_attack = False
    attacks = []
    own_units = []
    foreign_units = []
    all_units = []
    support_factor = 0.25
    map = None
    units = None
    allow_support_send = False
    allow_support_recv = False
    manage_flags_enabled = False
    auto_evacuate = False
    last_attack_check = 0
    logger = None

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def get_own_units(self):
        """
        Get own units from a village
        :return: dict with own units
        """
        return self.own_units

    def get_foreign_units(self):
        """
        Get foreign units from a village
        :return: dict with foreign units
        """
        return self.foreign_units

    def update(self, overview_html, with_defence=False):
        """
        Update the defence manager with the latest data
        """
        if not self.logger:
            self.logger = logging.getLogger(f"DefenceManager:{self.village_id}")

        if not overview_html:
            return

        if time.time() - self.last_attack_check > 30:
            self.attacks = Extractor.get_attacks(overview_html)
            self.under_attack = len(self.attacks) > 0
            self.last_attack_check = time.time()

        if with_defence:
            self.manage_area_defence()

        if self.allow_support_recv:
            self.manage_incoming_attacks()

        if self.manage_flags_enabled:
            self.manage_flags()

        if self.under_attack:
            self.logger.info(
                "[DEFENCE] Village is under attack! Attacks: %s", str(self.attacks)
            )
            if self.auto_evacuate:
                self.evacuate_fragile_units()

    def manage_area_defence(self):
        """
        Manage the defence of the area around the village
        """
        self.map.get_map()
        supported_this_run = 0
        if self.map.own_villages and self.allow_support_send:
            for village in self.map.own_villages:
                if supported_this_run >= 2:
                    self.logger.debug("[DEFENCE] Already supported 2 villages this run, ignoring further requests.")
                    break

                vid = village["id"]
                if vid == self.village_id:
                    continue

                # Fetching village overview to check for attacks
                # This is resource-intensive and should be used sparingly.
                # A better approach would be to use a shared cache.
                village_overview = self.wrapper.get_url(
                    f"game.php?village={vid}&screen=overview"
                )
                if village_overview:
                    attacks = Extractor.get_attacks(village_overview.text)
                    if attacks:
                        self.logger.info(
                            f"[DEFENCE] Ally village {village['name']} ({vid}) is under attack. Assessing support."
                        )
                        # Simplified logic: send a fixed amount of support
                        # A real implementation should calculate required support
                        if self.units.total_troops.get("spear", 0) > 100:
                            self.send_support(vid, {"spear": 100})
                            supported_this_run += 1

        else:
            self.logger.info("[DEFENCE] Area OK for village %s, nice and quiet", self.village_id)

    def manage_incoming_attacks(self):
        """
        Manage incoming attacks to the village
        """
        if not self.under_attack:
            return

        for attack in self.attacks:
            # Simplified logic: request support if any attack is incoming
            # A real implementation should analyze attack size and timing
            if self.allow_support_recv:
                self.request_support()
                self.logger.info(
                    f"[DEFENCE] Requesting support for incoming attack: {attack['id']}"
                )
                break

    def request_support(self, message="Support needed!"):
        """
        Request support from tribe members
        """
        # This requires interacting with the tribe forum or chat, which is complex.
        # Placeholder for future implementation.
        self.wrapper.reporter.report(
            self.village_id,
            "TWB_SUPPORT_REQUEST",
            f"Requesting support for village {self.village_id}. Attack imminent.",
        )

    def send_support(self, target_village_id, troops):
        """
        Send support to another village
        """
        if not self.allow_support_send:
            return

        url = f"game.php?village={self.village_id}&screen=place&target={target_village_id}"
        self.wrapper.get_url(url) # Initial GET to load the page

        form_data = {"support": "Support"}
        for unit, amount in troops.items():
            if self.units.total_troops.get(unit, 0) >= amount:
                form_data[unit] = str(amount)

        if len(form_data) > 1: # Has troops to send
            self.logger.info(
                f"[DEFENCE] Sending support to village {target_village_id} with troops: {troops}"
            )
            self.wrapper.post_url(url, data=form_data)
            # Update local troop counts
            for unit, amount in troops.items():
                self.units.total_troops[unit] -= amount

    def evacuate_fragile_units(self):
        """
        Evacuate fragile units to a nearby friendly village
        """
        if not self.auto_evacuate or not self.attacks:
            return

        # Find a safe, nearby village (simplified: first non-attacked own village)
        safe_target = None
        for village in self.map.own_villages:
            if village["id"] != self.village_id:
                # In a real scenario, you'd check if this village is also under attack
                safe_target = village
                break

        if safe_target:
            # Evacuate units that are bad on defense (e.g., axe, light)
            evac_troops = {
                "axe": self.units.total_troops.get("axe", 0),
                "light": self.units.total_troops.get("light", 0)
            }
            evac_troops = {k: v for k, v in evac_troops.items() if v > 0} # Filter empty

            if evac_troops:
                self.logger.info(
                    f"[DEFENCE] Evacuating fragile units to {safe_target['name']} ({safe_target['id']})"
                )
                self.send_support(safe_target['id'], evac_troops)

    def manage_flags(self):
        """
        Manage the flags of the village
        """
        self.logger.info("[DEFENCE] Managing flags")
        url = f"game.php?village={self.village_id}&screen=flags"
        flag_data = self.wrapper.get_url(url)
        if not flag_data:
            self.logger.warning("[DEFENCE] Error reading flag data")
            return

        flags = Extractor.get_flags(flag_data.text)
        for flag_type, flag in flags.items():
            if flag["level"] < flag["max_level"]:
                if self.wrapper.get_config(
                    "world", f"flag_{flag_type}_enabled", False
                ):
                    self.logger.warning(
                        f"[DEFENCE] Flag {flag_type} is not at max level, but upgrading is not implemented yet."
                    )
                    # Upgrade logic placeholder
                    # costs = flag['upgrade_costs']
                    # if self.units.resman.has_res(costs):
                    #     self.logger.info(f"[DEFENCE] Upgrading flag {flag_type} to level {flag['level'] + 1}")
                    #     # self.wrapper.post_url(..., data=...)
                    # else:
                    #     self.logger.info(f"[DEFENCE] Not enough resources to upgrade flag {flag_type}")

    def get_units_in_village(self, text):
        """
        Get all units in the village
        """
        self.all_units = []
        self.foreign_units = []
        self.own_units = []
        uid = Extractor.units_in_village(text)
        if uid:
            for row in uid:
                self.all_units.append(row)
                if not row["home"]["id"] == self.village_id:
                    self.foreign_units.append(row)
                else:
                    self.own_units.append(row)

        if self.foreign_units:
            self.logger.info(
                "[DEFENCE] Foreign units in village: %s", str(self.foreign_units)
            )
