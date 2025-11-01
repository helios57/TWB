import logging
import re
import time
from datetime import datetime, timedelta

from core.templates import TemplateManager


class BuildingManager:
    """
    Building manager that can upgrade the buildings in a village
    """

    resman = None
    levels = {}
    waits = {}
    vil_id = None
    wrapper = None
    queue = None
    logger = None
    game_state = None
    last_gamedata_build_check = None

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.vil_id = village_id
        self.queue = TemplateManager.get_template("builder", "default")

    def get_level(self, building, next_level=False):
        """
        :param building: building name
        :param next_level: get next level instead of current
        :return: level
        """
        if building in self.levels:
            if next_level:
                return self.levels[building] + 1
            return self.levels[building]
        return 0

    def get_build_queue(self, data):
        """
        Get the current build queue, including finish times
        """
        pq = re.search(r"var building_orders = (.+?);", data)
        if pq:
            pq_str = pq.group(1).replace("false", "False").replace("true", "True")
            try:
                build_queue = eval(pq_str)
            except Exception as e:
                build_queue = []
        else:
            build_queue = []
        return build_queue

    def update_building_levels(self, game_state):
        """
        Update the building levels for this village
        """
        vname = game_state['village']['name']
        if not self.logger:
            self.logger = logging.getLogger(fr"Builder: {vname}")

        if not self.last_gamedata_build_check or time.time() - self.last_gamedata_build_check > 30:
            self.levels = game_state["village"]["buildings"]
            self.last_gamedata_build_check = time.time()

        self.logger.debug("[BUILD] Updating building levels")
        return self.levels

    def get_finish_time(self, build_queue, new_level):
        """
        Get the timestamp for when a building upgrade finishes
        """
        ts = int(time.time())
        finish_time = ts
        if build_queue:
            last_build = build_queue[-1]
            finish_time = int(last_build["finished"])

        if finish_time < ts:
            self.logger.info(
                "[BUILD] Finish time is in the past! last_build: %s, finish_time: %s, ts: %s",
                str(build_queue[-1] if build_queue else None),
                str(finish_time),
                str(ts),
            )
            finish_time = ts

        return finish_time

    def get_queue_timestamp(self, build_queue, build_time):
        f_time = self.get_finish_time(build_queue, 0)
        td = timedelta(seconds=int(build_time))
        f_time_dt = datetime.fromtimestamp(f_time)
        queue_timestamp = f_time_dt + td
        self.logger.debug("[BUILD] Building finish time: %s", str(f_time))
        return int(queue_timestamp.timestamp())

    def add_to_resman(self, costs, entry, new_level, queue_timestamp, build_time):
        self.resman.add_request(
            vil_id=self.vil_id,
            prio=3,
            req_id=entry + "_" + str(new_level),
            w_time=queue_timestamp,
            wait_time=build_time,
            res=costs,
        )

    def is_building_in_queue(self, entry, new_level):
        if self.resman.check_request(self.vil_id, entry + "_" + str(new_level)):
            return True
        return False

    def check_farm_priority(self, entry, check):
        if check and self.get_level("farm") < 20 and not entry == "farm":
            if (
                    self.game_state["village"]["pop"]
                    > self.game_state["village"]["pop_max"] * 0.95
            ):
                return {
                    "action": "prioritize",
                    "building_name": "farm",
                    "intent": "Prioritizing farm due to low population."
                }
        return None

    def check_storage_priority(self, entry, check):
        if check and self.get_level("storage") < 20 and not entry == "storage":
            storage_prio = ["main", "barracks", "stable", "garage", "smith", "market", "snob"]
            if entry in storage_prio:
                self.logger.info(
                    "[BUILD] Building %s has storage prio, current capacity: %d, max: %d",
                    entry,
                    self.game_state["village"]["storage_max"],
                    self.resman.max_res,
                )
                if (
                        self.game_state["village"]["storage_max"]
                        > self.resman.max_res * 0.95
                ):
                    return {
                        "action": "prioritize",
                        "building_name": "storage",
                        "intent": "Prioritizing storage due to high capacity."
                    }
        return None

    def remove_from_waits(self, entry):
        if entry in self.waits:
            self.waits.pop(entry)

    def can_build(self, entry, new_level):
        if self.is_building_in_queue(entry, new_level):
            return False
        if entry in self.waits:
            wait_for = self.waits[entry]
            if time.time() < wait_for:
                return False
            else:
                self.remove_from_waits(entry)
        return True

    def process_queue_entry(self, entry, check, build_queue, game_state):
        new_level = self.get_level(entry, next_level=True)
        if new_level <= check["max_level"] and self.can_build(entry, new_level):
            if new_level > self.get_level(entry):
                if check and all(
                    self.get_level(req) >= check["requirements"][req]
                    for req in check["requirements"]
                ):
                    costs = check["costs"][str(new_level)]
                    if self.resman.has_res(costs):
                        self.last_gamedata_build_check = 0
                        queue_timestamp = self.get_queue_timestamp(
                            build_queue, check["build_times"][str(new_level)]
                        )
                        self.remove_from_waits(entry)
                        return {
                            "action": "build",
                            "build_link": check["build_link"],
                            "building_name": entry,
                            "new_level": new_level,
                            "finish_time": queue_timestamp
                        }
                    else:
                        self.logger.debug(f"[BUILD] Cannot build {entry}, requirements not met.")
                        self.add_to_resman(
                            costs=costs,
                            entry=entry,
                            new_level=new_level,
                            queue_timestamp=self.get_queue_timestamp(build_queue, 0),
                            build_time=check["build_times"][str(new_level)],
                        )
                        return {
                            "action": "wait_resources",
                            "building_name": entry,
                            "intent": f"Waiting for resources for {entry}."
                        }
        return None

    def decide_next_build(self, game_state, building_data, queue, current_levels, build_enabled=False):
        self.game_state = game_state
        self.levels = current_levels

        if not build_enabled:
            return {"action": "none", "intent": "Building management is disabled."}

        build_queue = self.get_build_queue(building_data)
        if len(build_queue) >= 5:
            return {"action": "none", "intent": "Build queue is full."}

        # Check for priority buildings (farm, storage)
        priority_action = self.check_farm_priority("any", True)
        if priority_action:
            return priority_action

        priority_action = self.check_storage_priority("any", True)
        if priority_action:
            return priority_action

        # Process the main building queue
        for entry in queue:
            if not entry in building_data:
                self.logger.debug("[BUILD] Ignoring %s because not yet available", entry)
                continue

            check = building_data[entry]

            action = self.process_queue_entry(entry, check, build_queue, game_state)
            if action:
                return action

        return {"action": "none", "intent": "All buildings are at their target levels."}
