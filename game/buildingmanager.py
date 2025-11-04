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
    target_levels: dict = {}
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
    mode = "linear" # Can be 'linear' or 'dynamic'

    can_build_three_min = False

    # For dynamic mode
    troop_queue_status = {}
    farming_income_rate = 0

    def __init__(self, wrapper, village_id):
        """
        Create the building manager
        """
        self.wrapper = wrapper
        self.village_id = village_id
        self.last_status = None

    def create_update_links(self, extracted_buildings):
        """
        Creates update links for a building
        """
        link = self.game_state["link_base_pure"] + "main&action=upgrade_building"

        for building in extracted_buildings:
            _id = extracted_buildings[building]["id"]
            _link = link + "&id=" + _id + "&type=main&h=" + self.game_state["csrf"]

            extracted_buildings[building]["build_link"] = _link

        return extracted_buildings

    def start_update(self, overview_game_data, overview_html, build=False, set_village_name=None):
        """
        Start a building manager run
        """
        main_data = self.wrapper.get_action(village_id=self.village_id, action="main")
        main_data_text = main_data.text

        self.game_state = overview_game_data or Extractor.game_state(main_data_text) or (
            Extractor.game_state(overview_html) if overview_html else None
        ) or (
            Extractor.game_state(self.wrapper.last_response) if getattr(self.wrapper, "last_response", None) else None
        )

        if not self.game_state or "village" not in self.game_state:
            if not self.logger:
                self.logger = logging.getLogger("Builder")
            self.logger.error("Game state could not be determined; skipping builder update")
            return False

        vname = self.game_state["village"].get("name", str(self.village_id))

        if not self.logger:
            self.logger = logging.getLogger(fr"Builder: {vname}")

        if self.complete_actions(main_data_text):
            return self.start_update(
                overview_game_data=Extractor.game_state(self.wrapper.last_response),
                overview_html=self.wrapper.last_response.text,
                build=build,
                set_village_name=set_village_name
            )

        self.costs = Extractor.building_data(main_data_text)
        if self.costs is None:
            self.logger.error("Failed to extract building data from main screen")
            return False
        self.costs = self.create_update_links(self.costs)

        if self.resman:
            self.resman.update(self.game_state)
            if "building" in self.resman.requested:
                self.resman.requested["building"] = {}
        if set_village_name and vname != set_village_name:
            self.wrapper.post_url(
                url=f"game.php?village={self.village_id}&screen=main&action=change_name",
                data={"name": set_village_name, "h": self.wrapper.last_h},
            )

        self.logger.debug("Updating building levels")
        tmp = self.game_state["village"]["buildings"]
        for e in tmp:
            tmp[e] = int(tmp[e])
        self.levels = tmp
        existing_queue = Extractor.active_building_queue(main_data_text)
        if existing_queue == 0:
            self.waits = []
            self.waits_building = []
        if self.is_queued():
            self.logger.info(
                "No build operation was executed: queue full, %d left", len(self.queue)
            )
            self.last_status = "Building queue is full."
            return False
        if not build:
            self.last_status = "Building is disabled."
            return False

        r = self.max_queue_len - len(self.waits)
        for x in range(r):
            result = self.get_next_building_action()
            if not result:
                self.logger.info("No more build operations were executed.")
                self.last_status = "Nothing to build."
                return False

        main_data = self.wrapper.get_action(village_id=self.village_id, action="main")
        if self.complete_actions(main_data.text):
            self.can_build_three_min = True
            return self.start_update(
                overview_game_data=Extractor.game_state(self.wrapper.last_response),
                overview_html=self.wrapper.last_response.text,
                build=build,
                set_village_name=set_village_name
            )
        return True

    def complete_actions(self, text):
        """
        Automatically finish a building if the world allows it
        """
        res = re.search(
            r'(?s)(\d+),\s*\'BuildInstantFree.+?data-available-from="(\d+)"', text
        )
        if res and int(res.group(2)) <= time.time():
            quickbuild_url = f"game.php?village={self.village_id}&screen=main&ajaxaction=build_order_reduce"
            quickbuild_url += f"&h={self.wrapper.last_h}&id={res.group(1)}&destroy=0"
            result = self.wrapper.get_url(quickbuild_url)
            self.logger.debug("Quick build action was completed, re-running function")
            return result
        return False

    def put_wait(self, wait_time):
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
        if len(self.waits) == 0:
            return False
        for w in list(self.waits):
            if w < time.time():
                self.waits.pop(0)
        return len(self.waits) >= self.max_queue_len

    def has_enough(self, build_item):
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
            self.last_status = f"Waiting for resources to build {build_item['name'].title()}..."
        return r

    def get_level(self, building):
        return self.levels.get(building, 0)

    def readable_ts(self, seconds):
        seconds -= time.time()
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def _build(self, building_name):
        if building_name not in self.costs: return False
        check = self.costs[building_name]
        if check["can_build"] and self.has_enough(check) and "build_link" in check:
            self.last_status = f"Building {building_name.title()}..."
            queue = self.put_wait(check["build_time"])
            self.logger.info(
                "Building %s %d -> %d (finishes: %s)"
                % (
                    building_name,
                    self.get_level(building_name),
                    self.get_level(building_name) + 1,
                    self.readable_ts(queue),
                )
            )
            self.levels[building_name] += 1
            response = self.wrapper.get_url(check["build_link"].replace("amp;", ""))
            self.game_state = Extractor.game_state(response)
            self.costs = Extractor.building_data(response)
            if self.costs is None:
                self.logger.error("Failed to extract building data after building action")
                return False
            self.costs = self.create_update_links(self.costs)
            return True
        return False

    def get_next_building_action(self):
        if self.is_queued():
            return False

        if self.mode == 'linear':
            return self._get_next_linear_action()
        elif self.mode == 'dynamic':
            return self._get_next_dynamic_action()
        return False

    def _get_next_linear_action(self, index=0):
        if index >= len(self.queue):
            # --- FALLBACK LOGIC ---
            # If the queue is empty, upgrade the lowest level resource pit
            self.logger.info("Main building queue is empty. Looking for a resource pit to upgrade.")

            resource_pits = ["wood", "stone", "iron"]
            # Find the pit with the lowest current level
            lowest_pit = min(resource_pits, key=lambda pit: self.get_level(pit))

            self.logger.info(f"Identified '{lowest_pit}' as the lowest level resource pit. Attempting to upgrade.")
            return self._build(lowest_pit)
            # --- END FALLBACK LOGIC ---

        entry, min_lvl = self.queue[index].split(":")
        min_lvl = int(min_lvl)

        if min_lvl <= self.get_level(entry):
            self.queue.pop(index)
            return self._get_next_linear_action(index)

        if entry not in self.costs or not self.costs[entry]["can_build"]:
            return self._get_next_linear_action(index + 1)

        return self._build(entry)

    def _get_next_dynamic_action(self):
        # Define Academy prerequisites for clarity
        academy_prereqs = {"main": 20, "smith": 20, "market": 10}

        # --- Priority 1: Maintain 24/7 Troop Queues ---
        # If troop queues are running low, prioritize upgrading the relevant building.
        # This now correctly checks against target levels.
        if self.troop_queue_status.get("stable_queue_time", 9999) < 3600:
            if self.get_level("stable") < self.target_levels.get("stable", 0):
                if self._build("stable"):
                    return True
        if self.troop_queue_status.get("barracks_queue_time", 9999) < 3600:
            if self.get_level("barracks") < self.target_levels.get("barracks", 0):
                if self._build("barracks"):
                    return True

        # --- Priority 2: Strategic Goals (Academy Rush) ---
        # This logic remains the same: meet prerequisites, then build the academy.
        for building, required_level in academy_prereqs.items():
            if self.get_level(building) < required_level:
                # Check if this prerequisite is even in our target plan
                if building in self.target_levels and self.get_level(building) < self.target_levels[building]:
                    if self._build(building):
                        return True

        if all(self.get_level(b) >= lv for b, lv in academy_prereqs.items()):
            if "snob" in self.target_levels and self.get_level("snob") < self.target_levels["snob"]:
                if self._build("snob"):
                    return True

        # --- Priority 3: Just-in-Time Provisioning (Warehouse & Farm) ---
        # Dynamically determine the next major cost instead of hardcoding.
        next_major_cost = 0
        for b, target_lvl in self.target_levels.items():
            current_lvl = self.get_level(b)
            if current_lvl < target_lvl and b in self.costs:
                cost_sum = sum(self.costs[b][res] for res in ['wood', 'stone', 'iron'])
                if cost_sum > next_major_cost:
                    next_major_cost = cost_sum

        # Add nobleman costs if academy is a goal
        if "snob" in self.target_levels:
            noble_cost = 140000
            coin_cost = 83000
            next_major_cost = max(next_major_cost, noble_cost, coin_cost)

        if self.resman and self.resman.storage < next_major_cost:
            if "storage" in self.target_levels and self.get_level("storage") < self.target_levels["storage"]:
                if self._build("storage"):
                    return True

        # Check if the farm needs upgrading based on current and queued population.
        if self.game_state:
            current_pop = self.game_state["village"]["pop"]
            max_pop = self.game_state["village"]["pop_max"]
            # Estimate population from building queue
            queued_pop = 0
            # A simple estimate; a more accurate one would inspect the actual queue
            if len(self.waits) > 0:
                 queued_pop = 5 * len(self.waits)

            if (max_pop - (current_pop + queued_pop)) < 100:
                if "farm" in self.target_levels and self.get_level("farm") < self.target_levels["farm"]:
                    if self._build("farm"):
                        return True

        # --- Priority 4: Resource Pits (as a resource sink) ---
        # If resources are about to overflow, upgrade the lowest-level pit.
        if self.resman and (
            self.resman.actual["wood"] > self.resman.storage * 0.98
            or self.resman.actual["stone"] > self.resman.storage * 0.98
            or self.resman.actual["iron"] > self.resman.storage * 0.98
        ):
            pits = ["wood", "stone", "iron"]
            pits.sort(key=lambda p: self.get_level(p))
            for pit in pits:
                if pit in self.target_levels and self.get_level(pit) < self.target_levels[pit]:
                    if self._build(pit):
                        return True

        # --- Priority 5 (Fallback): General Progress ---
        # Build the cheapest building that is below its target level.
        cheapest_building = None
        min_cost = float('inf')

        for building, target_level in self.target_levels.items():
            if self.get_level(building) < target_level and building in self.costs:
                if self.costs[building].get("can_build", False):
                    cost = sum(self.costs[building][res] for res in ['wood', 'stone', 'iron'])
                    if cost < min_cost:
                        min_cost = cost
                        cheapest_building = building

        if cheapest_building:
            if self._build(cheapest_building):
                return True

        return False

    def get_planned_actions(self):
        """
        Returns a list of the next planned building actions.
        This is a "dry run" and does not execute any actions.
        """
        if self.mode == "linear":
            return self._get_planned_linear_actions()
        elif self.mode == "dynamic":
            return self._get_planned_dynamic_actions()
        return []

    def _get_planned_linear_actions(self):
        actions = []
        # Show the next 3 items in the queue
        for item in self.queue[:3]:
            entry, min_lvl = item.split(":")
            actions.append(f"Build {entry.title()} to level {min_lvl}")
        return actions

    def _get_planned_dynamic_actions(self):
        actions = []

        def _add_action(building, target_level, reason):
            current_level = self.get_level(building)
            if current_level < target_level:
                actions.append(
                    f"Build {building.title()} to level {current_level + 1} (Reason: {reason})"
                )
                return True
            return False

        # Define Academy prerequisites
        academy_prereqs = {"main": 20, "smith": 20, "market": 10}

        # --- Priority 1: Troop Queues ---
        if self.troop_queue_status.get("stable_queue_time", 9999) < 3600:
            if _add_action("stable", self.target_levels.get("stable", 30), "Stable queue running low"): return actions
        if self.troop_queue_status.get("barracks_queue_time", 9999) < 3600:
            if _add_action("barracks", self.target_levels.get("barracks", 30), "Barracks queue running low"): return actions

        # --- Priority 2: Strategic Goals (Academy Rush) ---
        for building, required_level in academy_prereqs.items():
            if self.get_level(building) < required_level:
                 if _add_action(building, required_level, "Academy prerequisite"): return actions

        if all(self.get_level(b) >= lv for b, lv in academy_prereqs.items()):
            if _add_action("snob", self.target_levels.get("snob", 1), "Build Academy"): return actions

        # --- Priority 3: JIT Provisioning ---
        coin_cost = 84000
        noble_cost = 120000
        next_major_cost = max(coin_cost, noble_cost)
        if self.resman and self.resman.storage < (next_major_cost * 1.1):
            if _add_action("storage", self.target_levels.get("storage", 30), "Warehouse too small for Nobleman"): return actions

        if self.game_state:
            current_pop = self.game_state["village"]["pop"]
            max_pop = self.game_state["village"]["pop_max"]
            if max_pop - current_pop < 250:
                if _add_action("farm", self.target_levels.get("farm", 30), "Low population headroom"): return actions

        # --- Priority 4: Resource Sink ---
        if self.resman and (
            self.resman.actual["wood"] > self.resman.storage * 0.95
            or self.resman.actual["stone"] > self.resman.storage * 0.95
            or self.resman.actual["iron"] > self.resman.storage * 0.95
        ):
            pits = ["wood", "stone", "iron"]
            pits.sort(key=lambda p: self.get_level(p))
            if _add_action(pits[0], self.target_levels.get(pits[0], 30), "Resource storage full"): return actions

        # --- Fallback: General Goals ---
        for building, target_level in sorted(self.target_levels.items(), key=lambda item: self.get_level(item[0])):
            if self.get_level(building) < target_level:
                if _add_action(building, target_level, "Working towards final village plan"): return actions

        return actions
