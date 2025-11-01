import logging
import random
import time
from datetime import datetime

from core.filemanager import FileManager


class AttackManager:
    """
    Attack manager that can send attacks from the rally point
    """

    village_id = None
    wrapper = None
    troopmanager = None
    map = None
    repman = None
    template = None
    target_list = []
    farm_bag_limit_reached = False
    farm_bag_limit_checked = False
    last_farm_bag_state = None
    forced_peace_time = None
    ignore_list = None
    logger = None

    # Configurable parameters
    target_high_points = False
    farm_minpoints = 24
    farm_maxpoints = 1080
    farm_radius = 50
    farm_default_wait = 1200
    farm_high_prio_wait = 1800
    farm_low_prio_wait = 7200
    scout_farm_amount = 5
    extra_farm = []
    max_farms = 25

    def __init__(self, wrapper=None, village_id=None, troopmanager=None, map=None):
        self.wrapper = wrapper
        self.village_id = village_id
        self.troopmanager = troopmanager
        self.map = map

    def get_ignored_farms(self):
        """
        Get list of farms that are being ignored
        :return: list of farms
        """
        if self.ignore_list is None:
            self.ignore_list = FileManager.load_json_file(
                f"cache/ignored_farms_{self.village_id}.json"
            )
        return self.ignore_list

    def set_ignored_farm(self, vid, reason, away_time=1800):
        """
        Ignore a farm for some time
        :param vid: village id to ignore
        :param reason: reason why the village is ignored
        :param away_time: time to ignore the farm
        """
        self.ignore_list = self.get_ignored_farms()
        self.ignore_list[vid] = {
            "reason": reason,
            "time": int(time.time()),
            "away_time": away_time,
        }
        FileManager.save_json_file(self.ignore_list, f"cache/ignored_farms_{self.village_id}.json")

    def sort_targets(self, targets):
        """
        Sort targets by distance and optional by points
        :param targets: list of targets
        :return: sorted list
        """
        if self.target_high_points:
            return sorted(
                targets,
                key=lambda x: (
                    self.map.get_distance(x["x"], x["y"]),
                    -int(x["points"]),
                ),
            )
        return sorted(targets, key=lambda x: (self.map.get_distance(x["x"], x["y"])))

    def get_targets(self):
        """
        Get all targets and sort them by distance
        :return: list of targets
        """
        if not self.target_list:
            self.target_list = self.sort_targets(
                self.map.get_possible_farms(
                    min_points=self.farm_minpoints,
                    max_points=self.farm_maxpoints,
                    farm_radius=self.farm_radius,
                )
            )
            for farm in self.extra_farm:
                farm_data = self.map.get_village_data_by_id(farm)
                if farm_data:
                    self.logger.debug(
                        "[FARM] Added extra farm target %s at %s|%s",
                        farm_data["name"],
                        farm_data["x"],
                        farm_data["y"],
                    )
                    self.target_list.insert(0, farm_data)

        return self.target_list

    def can_farm_bag_be_used(self):
        if self.farm_bag_limit_reached and not self.farm_bag_limit_checked:
            # Re-check if the farm bag limit is still active
            self.farm_bag_limit_checked = True
            # Fetch overview to update farm bag status (this is a simplification)
            self.wrapper.get_action(village_id=self.village_id, action="overview")

        if self.farm_bag_limit_reached:
            self.logger.debug("[FARM] Skipping farm target because farm bag limit was reached earlier.")
            return False
        return True

    def is_target_eligible(self, target):
        vid = str(target["id"])
        if vid == self.village_id:
            return False, "self"

        if int(target["id"]) in self.extra_farm:
            self.logger.info(
                "[FARM] Target %s (%s|%s) is an extra farm, always eligible.",
                target["name"],
                target["x"],
                target["y"],
            )
            return True, "extra_farm"

        if "last_report" in target and target["last_report"]:
            last_report = target["last_report"]
            if last_report["dot"] in ["red", "yellow"]:
                return False, f"bad_report_{last_report['dot']}"

        return True, "eligible"

    def manage_ignore_list(self):
        """
        Clean up the ignore list from villages that are no longer ignored
        """
        self.ignore_list = self.get_ignored_farms()
        to_del = []
        for vid in self.ignore_list:
            entry = self.ignore_list[vid]
            if (entry["time"] + entry["away_time"]) < time.time():
                to_del.append(vid)
        if to_del:
            self.logger.debug(
                "[FARM] Removing %d villages from ignore list", len(to_del)
            )
            for vid in to_del:
                self.ignore_list.pop(vid)
                self.logger.debug("[FARM] Removed %s from farm ignore list", vid)

    def run(self):
        """
        Run the attack manager
        """
        if not self.logger:
            self.logger = logging.getLogger(f"AttackManager:{self.village_id}")

        self.manage_ignore_list()
        self.get_targets()
        self.logger.info(
            "[FARM] Starting farm run. Targets found: %d. Max farms: %d",
            len(self.target_list),
            self.max_farms
        )

        place_data = self.wrapper.get_url(
            f"game.php?village={self.village_id}&screen=place&mode=units"
        ).text
        troops_in_village = self.troopmanager.units_in_village_file

        i = 0
        for target in self.target_list:
            if i >= self.max_farms:
                break

            if not self.can_farm_bag_be_used():
                break

            vid = str(target["id"])
            if vid in self.ignore_list:
                self.logger.debug(
                    "[FARM] Skipping target %s, is in ignore list.", vid
                )
                continue

            eligible, reason = self.is_target_eligible(target)
            if not eligible:
                if reason != "self":
                    self.set_ignored_farm(vid, reason, self.farm_low_prio_wait)
                continue

            # SCOUT LOGIC
            cache_entry = self.repman.in_cache(vid)
            should_scout = False

            if not cache_entry:
                should_scout = True
            else:
                last_attack = cache_entry.get("last_attack", 0)
                if time.time() - last_attack > self.farm_high_prio_wait:
                    self.logger.debug(f"[FARM] Attacked long ago {datetime.fromtimestamp(last_attack)}, trying scout attack")
                    should_scout = True

                res = cache_entry.get("res")
                if res and sum(res.values()) > self.troopmanager.resman.get_carry(self.template) * 0.1:
                    # Farm has resources, attack it
                    should_scout = False
                elif res and sum(res.values()) == 0:
                    self.logger.warning(
                        "[FARM] Farm %s has no resources, ignoring for now", vid
                    )
                    self.set_ignored_farm(vid, "no_res", self.farm_low_prio_wait)
                    continue

            if should_scout and self.troopmanager.can_scout:
                if self.troopmanager.total_troops.get("spy", 0) >= self.scout_farm_amount:
                    self.logger.info(
                        f"[FARM] Scouting target {target['name']} ({target['x']}|{target['y']})"
                    )
                    self.send_attack(target, {"spy": self.scout_farm_amount})
                    self.set_ignored_farm(vid, "scouted", 120)
                else:
                    self.logger.info(f"[FARM] Not enough scouts to check {vid}")

            # ATTACK LOGIC
            elif cache_entry:
                if cache_entry.get("last_attack", 0) > time.time() - self.farm_high_prio_wait:
                    self.logger.info(f"[FARM] Farm {vid} was attacked recently, skipping.")
                    continue

                self.logger.info(
                    "[FARM] Attacking target %s (%s|%s)",
                    target["name"],
                    target["x"],
                    target["y"],
                )
                self.attack_farm(target)
            else:
                self.logger.debug(
                    "[FARM] No valid action for target %s, no cache entry and no scout sent.", vid
                )

            i += 1

    def attack_farm(self, target):
        """
        Attack a farm
        :param target: farm data
        """
        vid = str(target["id"])
        cache_entry = self.repman.in_cache(vid)
        res = cache_entry.get("res", {"wood": 0, "stone": 0, "iron": 0})

        if cache_entry and sum(res.values()) > self.troopmanager.resman.get_carry(self.template) * 1.5:
             self.logger.debug(f"[FARM] Draining farm of resources! Sending attack to get {res}.")
             self.send_attack(target, self.template)
        elif self.troopmanager.resman.get_carry(self.template) > 0:
            self.logger.debug(
                "[FARM] Sending default attack to %s", vid
            )
            self.send_attack(target, self.template)

        self.set_ignored_farm(
            vid=vid,
            reason="attacked",
            away_time=self.farm_default_wait,
        )

    def send_attack(self, target, troops):
        """
        Send an attack to a village
        :param target: target data
        :param troops: troops to send
        """
        if not self.logger:
            self.logger = logging.getLogger(f"AttackManager:{self.village_id}")

        vid = str(target["id"])
        if vid == self.village_id:
            return

        url = f"game.php?village={self.village_id}&screen=place&target={vid}"
        data = self.wrapper.get_url(url)
        form_data = {"x": target["x"], "y": target["y"], "attack": "Angreifen"}

        for unit in troops:
            if unit in self.troopmanager.total_troops:
                available = self.troopmanager.total_troops[unit]
                if available >= troops[unit]:
                    form_data[unit] = str(troops[unit])
                else:
                    form_data[unit] = "0"
            else:
                form_data[unit] = "0"

        # Check if any troops are being sent
        if all(unit not in form_data or form_data[unit] == "0" for unit in self.troopmanager.total_troops.keys()):
            return

        # Check for forced peace time
        if self.forced_peace_time:
            # This is a simplification. Real calculation requires unit speed.
            dist = self.map.get_distance(target['x'], target['y'])
            if dist > 20: # Crude check for long travel times
                travel_time = dist * 20 * 60 # Rough estimate
                if datetime.now().timestamp() + travel_time > self.forced_peace_time.timestamp():
                    self.logger.info("[FARM] Attack would arrive after the forced peace timer, not sending attack!")
                    return

        self.logger.info(
            "[FARM] Sending attack to %s (%s|%s) with troops: %s",
            target["name"],
            target["x"],
            target["y"],
            str({k: v for k, v in form_data.items() if k not in ["x", "y", "attack"]}),
        )

        res = self.wrapper.post_url(url, data=form_data)

        # Update troops in village after sending attack
        for unit, amount in troops.items():
            if unit in self.troopmanager.total_troops:
                self.troopmanager.total_troops[unit] -= int(amount)

        # Check for farm bag limit after attack
        if "farm_limit_reached_warning" in res.text:
            self.farm_bag_limit_reached = True
            self.last_farm_bag_state = { "current": 100, "max": 100, "pct": 1.0 } # Placeholder
            self.logger.warning("[FARM] Farm bag limit reached!")
            self.wrapper.reporter.report(self.village_id, "TWB_FARM_LIMIT", "Farm bag limit reached")

        # Update last farm bag state from response
        # This requires an extractor similar to the one in village.py
        # For now, this part is omitted for simplicity.

    def get_last_farm_run(self):
        """
        Get the last time the farm run was executed
        :return: last farm run state
        """
        return self.last_farm_bag_state

    def update_farm_bag_state(self, state):
        """
        Update the farm bag state
        :param state: new farm bag state
        """
        self.last_farm_bag_state = state
        if state and state.get("pct", 0) >= 1.0:
            self.farm_bag_limit_reached = True
        else:
            self.farm_bag_limit_reached = False
        self.logger.info("[FARM] Farm bag state updated: %s", str(state))
