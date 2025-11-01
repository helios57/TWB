"""
Manages building management manager
"""
import logging
import random
import re
import time

from core.extractors import Extractor


class BuildingManager:
    """
    Core class for building management
    """
    logger = None
    levels = {}

    # Amount of building in the queue to look ahead into
    # Increasing this will gain massive points but lack of resources
    max_lookahead = 2

    queue: list[str] = []
    waits: list[float] = []
    waits_building: list[str] = []

    costs = {}

    wrapper = None
    village_id = None
    game_state = {}

    # Can be increased with a premium account
    max_queue_len = 2
    resman = None
    raw_template = None

    can_build_three_min = False

    def __init__(self, wrapper, village_id):
        """
        Create the building manager
        """
        self.wrapper = wrapper
        self.village_id = village_id

    def decide_next_build(self, game_state, building_data, queue, current_levels, build_enabled=False):
        """
        Decides on the next building action based on provided data.
        """
        self.game_state = game_state
        self.costs = building_data
        self.queue = queue
        self.levels = current_levels

        vname = self.game_state["village"]["name"]
        if not self.logger:
            self.logger = logging.getLogger(fr"Builder: {vname}")

        if self.resman:
            self.resman.update(self.game_state)
            if "building" in self.resman.requested:
                # new run, remove request
                self.resman.requested["building"] = {}

        self.logger.debug("Updating building levels")
        tmp = self.game_state["village"]["buildings"]
        for e in tmp:
            tmp[e] = int(tmp[e])
        self.levels = tmp

        # This logic is now handled by the orchestrator (village.py)
        # existing_queue = Extractor.active_building_queue(main_data_text)
        # if existing_queue == 0:
        #     self.waits = []
        #     self.waits_building = []

        if self.is_queued():
            self.logger.info(
                "No build operation was decided: queue full, %d left", len(self.queue)
            )
            return {"action": "wait_queue", "intent": "Warte auf Bau-Warteschlange."}

        if not build_enabled:
            return {"action": "idle", "intent": "Gebäudebau deaktiviert."}

        # The loop for multiple builds is now handled by the orchestrator
        return self.get_next_building_action()


    def put_wait(self, wait_time):
        """
        Puts an item in the active building queue
        Blocking entries until the building is completed
        """
        self.is_queued()
        if len(self.waits) == 0:
            f_time = time.time() + wait_time
            self.waits.append(f_time)
            return f_time
        else:
            lastw = self.waits[-1]
            f_time = lastw + wait_time
            self.waits.append(f_time)
            self.logger.debug("Building finish time: %s", str(f_time))
            return f_time

    def is_queued(self):
        """
        Checks if a building is already queued
        """
        if len(self.waits) == 0:
            return False
        for w in list(self.waits):
            if w < time.time():
                self.waits.pop(0)
        return len(self.waits) >= self.max_queue_len

    def has_enough(self, build_item):
        """
        Checks if there are enough resources to queue a building
        """
        if (
                build_item["iron"] > self.resman.storage
                or build_item["wood"] > self.resman.storage
                or build_item["stone"] > self.resman.storage
        ):
            build_data = "storage:%d" % (int(self.levels["storage"]) + 1)
            if (
                    len(self.queue)
                    and "storage"
                    not in [x.split(":")[0] for x in self.queue[0: self.max_lookahead]]
                    and int(self.levels["storage"]) != 30
            ):
                self.queue.insert(0, build_data)
                self.logger.info(
                    "Adding storage in front of queue because queue item exceeds storage capacity"
                )
                return {
                    "action": "prioritize",
                    "building_name": "storage",
                    "intent": "Baue Lager: Benötige mehr Speicherplatz."
                }


        r = True
        if build_item["wood"] > self.game_state["village"]["wood"]:
            req = build_item["wood"] - self.game_state["village"]["wood"]
            self.resman.request(source="building", resource="wood", amount=req)
            r = False
        if build_item["stone"] > self.game_state["village"]["stone"]:
            req = build_item["stone"] - self.game_state["village"]["stone"]
            self.resman.request(source="building", resource="stone", amount=req)
            r = False
        if build_item["iron"] > self.game_state["village"]["iron"]:
            req = build_item["iron"] - self.game_state["village"]["iron"]
            self.resman.request(source="building", resource="iron", amount=req)
            r = False
        if build_item["pop"] > (
                self.game_state["village"]["pop_max"] - self.game_state["village"]["pop"]
        ):
            req = build_item["pop"] - (
                    self.game_state["village"]["pop_max"]
                    - self.game_state["village"]["pop"]
            )
            self.resman.request(source="building", resource="pop", amount=req)
            r = False
        if not r:
            self.logger.debug(f"Requested resources: {self.resman.requested}")
        return r

    def get_level(self, building):
        """
        Gets a building level
        """
        if building not in self.levels:
            return 0
        return self.levels[building]

    def readable_ts(self, seconds):
        """
        Makes stuff more human
        """
        seconds -= time.time()
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def get_next_building_action(self, index=0):
        """
        Calculates the next best possible building action and returns it as a dictionary.
        """
        if index >= len(self.queue) or index >= self.max_lookahead:
            self.logger.debug("Not building anything because insufficient resources or index out of range")
            return {"action": "idle", "intent": "Keine weiteren Gebäude in der Bauschleife."}

        queue_check = self.is_queued()
        if queue_check:
            self.logger.debug("Not building because of queued items: %s", self.waits)
            return {"action": "wait_queue", "intent": "Warte auf Bau-Warteschlange."}


        if self.resman and self.resman.in_need_of("pop"):
            build_data = "farm:%d" % (int(self.levels["farm"]) + 1)
            if (
                    len(self.queue)
                    and "farm"
                    not in [x.split(":")[0] for x in self.queue[0: self.max_lookahead]]
                    and int(self.levels["farm"]) != 30
            ):
                self.queue.insert(0, build_data)
                self.logger.info("Adding farm in front of queue because low on pop")
                return {
                    "action": "prioritize",
                    "building_name": "farm",
                    "intent": "Baue Farm: Benötige mehr Bevölkerung."
                }


        if len(self.queue):
            entry = self.queue[index]
            entry, min_lvl = entry.split(":")
            min_lvl = int(min_lvl)

            if min_lvl <= self.levels[entry]:
                self.queue.pop(index)
                return self.get_next_building_action(index)

            if entry not in self.costs:
                self.logger.debug("Ignoring %s because not yet available", entry)
                return self.get_next_building_action(index + 1)

            check = self.costs[entry]
            if "max_level" in check and min_lvl > check["max_level"]:
                self.logger.debug(
                    "Removing entry %s because max_level exceeded", entry
                )
                self.queue.pop(index)
                return self.get_next_building_action(index)

            # Check for storage capacity before checking other resources
            has_enough_check = self.has_enough(check)
            if isinstance(has_enough_check, dict): # Prioritize action was returned
                return has_enough_check

            if check["can_build"] and has_enough_check and "build_link" in check:
                queue_timestamp = self.put_wait(check["build_time"])
                new_level = self.levels[entry] + 1

                self.logger.info(
                    "Decided to build %s %d -> %d (finishes: %s)"
                    % (
                        entry,
                        self.levels[entry],
                        new_level,
                        self.readable_ts(queue_timestamp),
                    )
                )

                return {
                    "action": "build",
                    "build_link": check["build_link"].replace("amp;", ""),
                    "building_name": entry,
                    "new_level": new_level,
                    "finish_time": queue_timestamp,
                    "intent": f"Baue {entry} (Stufe {new_level}) gemäß Strategie."
                }
            else:
                if not check["can_build"]:
                    self.logger.debug(f"Cannot build {entry}, requirements not met.")
                    return self.get_next_building_action(index + 1)
                else:
                    self.logger.info(f"Not enough resources for {entry}")
                    return {
                        "action": "wait_resources",
                        "building_name": entry,
                        "intent": f"Warte auf Rohstoffe für {entry}."
                    }
        return {"action": "idle", "intent": "Bauschleife aktuell."}
