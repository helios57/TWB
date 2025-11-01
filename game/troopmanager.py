"""
Anything that has to do with the recruiting of troops
"""
import logging
import math
import random
import time

from core.extractors import Extractor
from game.resources import ResourceManager


class TroopManager:
    """
    Troopmanager class
    """
    can_recruit = True
    can_attack = True
    can_dodge = False
    can_scout = True
    can_farm = True
    can_gather = True
    can_fix_queue = True
    randomize_unit_queue = True

    queue = []
    troops = {}

    total_troops = {}

    _research_wait = 0

    wrapper = None
    village_id = None
    recruit_data = {}
    game_data = {}
    logger = None
    max_batch_size = 50

    _waits = {}

    wanted = {"barracks": {}}

    # Maps troops to the building they are created from
    unit_building = {
        "spear": "barracks",
        "sword": "barracks",
        "axe": "barracks",
        "archer": "barracks",
        "spy": "stable",
        "light": "stable",
        "marcher": "stable",
        "heavy": "stable",
        "ram": "garage",
        "catapult": "garage",
    }

    wanted_levels = {}

    last_gather = 0

    resman = None
    template = None

    def __init__(self, wrapper=None, village_id=None):
        """
        Create the troop manager
        """
        self.wrapper = wrapper
        self.village_id = village_id
        self.wait_for = {}
        self.wait_for[village_id] = {"barracks": 0, "stable": 0, "garage": 0}
        if not self.resman:
            self.resman = ResourceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )

    def decide_next_recruit(self, game_state, recruit_data, wanted_units, total_troops, disabled_units=None):
        """
        Decides on the next recruitment action based on provided data.
        """
        if disabled_units is None:
            disabled_units = []

        self.game_data = game_state
        self.recruit_data = recruit_data
        self.wanted = wanted_units
        self.total_troops = total_troops

        if not self.logger:
            village_name = self.game_data["village"]["name"]
            self.logger = logging.getLogger(f"Recruitment: {village_name}")

        for building in self.wanted:
            if self.wait_for[self.village_id][building] > time.time():
                human_ts = self.readable_ts(self.wait_for[self.village_id][building])
                self.logger.info("%s still busy for %s", building, human_ts)
                continue

            run_selection = list(self.wanted[building].keys())
            if self.randomize_unit_queue:
                random.shuffle(run_selection)

            resource_check_failed = False

            for wanted_unit in run_selection:
                if wanted_unit in disabled_units:
                    continue

                if resource_check_failed:
                    self.logger.debug("Skipping %s - insufficient resources detected", wanted_unit)
                    continue

                amount_wanted = self.wanted[building][wanted_unit]
                current_amount = self.total_troops.get(wanted_unit, 0)

                if amount_wanted > current_amount:
                    amount_to_recruit = amount_wanted - current_amount
                    recruit_action = self._decide_recruit_action(
                        wanted_unit, amount_to_recruit, building=building
                    )

                    if recruit_action["action"] == "recruit":
                        return recruit_action

                    if recruit_action.get("reason") == "insufficient_resources":
                        resource_check_failed = True

        return {"action": "idle", "intent": f"Rekrutierungs-Warteschlange aktuell."}

    def _decide_recruit_action(self, unit_type, amount=10, building="barracks"):
        """
        Makes a decision about recruiting a single unit type.
        """
        self.logger.info("Deciding recruitment for %d %s", amount, unit_type)

        if amount > self.max_batch_size:
            amount = self.max_batch_size

        if not self.recruit_data or unit_type not in self.recruit_data:
            self.logger.warning("Recruitment of %s failed: not researched or unavailable.", unit_type)
            return {"action": "research", "unit": unit_type, "intent": f"Forschung für {unit_type} benötigt."}

        resources = self.recruit_data[unit_type]
        if not resources or not resources.get("requirements_met", False):
            self.logger.warning("Recruitment of %s failed: requirements not met.", unit_type)
            return {"action": "research", "unit": unit_type, "intent": f"Forschung für {unit_type} benötigt."}

        get_min = self.get_min_possible(resources)
        if get_min == 0:
            self.logger.info("Recruitment of %s failed: not enough resources.", unit_type)
            self.reserve_resources(resources, amount, 0, unit_type)
            return {"action": "wait_resources", "reason": "insufficient_resources", "unit": unit_type, "intent": f"Warte auf Rohstoffe für {unit_type}."}

        if get_min < amount:
            self.logger.info("Recruitment of %d %s was set to %d because of resources", amount, unit_type, get_min)
            amount = get_min

        # No need to reserve resources anymore!
        if f"recruitment_{unit_type}" in self.resman.requested:
            self.resman.requested.pop(f"recruitment_{unit_type}", None)

        self.wait_for[self.village_id][building] = int(time.time()) + (amount * int(resources["build_time"]))

        return {
            "action": "recruit",
            "building": building,
            "unit": unit_type,
            "amount": amount,
            "intent": f"Rekrutiere {amount} {unit_type}."
        }

    def get_min_possible(self, entry):
        """
        Calculates which units are needed the most
        To get some balance of the total amount
        """
        return min(
            [
                math.floor(self.game_data["village"]["wood"] / entry["wood"]),
                math.floor(self.game_data["village"]["stone"] / entry["stone"]),
                math.floor(self.game_data["village"]["iron"] / entry["iron"]),
                math.floor(
                    (
                            self.game_data["village"]["pop_max"]
                            - self.game_data["village"]["pop"]
                    )
                    / entry["pop"]
                ),
            ]
        )

    def get_template_action(self, levels):
        """
        Read data from templates and determine the troops based op building progression
        """
        last = None
        wanted_upgrades = {}
        for x in self.template:
            if x["building"] not in levels:
                return last

            if x["level"] > levels[x["building"]]:
                return last

            last = x
            if "upgrades" in x:
                for unit in x["upgrades"]:
                    if (
                            unit not in wanted_upgrades
                            or x["upgrades"][unit] > wanted_upgrades[unit]
                    ):
                        wanted_upgrades[unit] = x["upgrades"][unit]

            self.wanted_levels = wanted_upgrades
        return last

    def research_time(self, time_str):
        """
        Calculates unit research time
        """
        parts = [int(x) for x in time_str.split(":")]
        return parts[2] + (parts[1] * 60) + (parts[0] * 60 * 60)

    def decide_next_research(self, smith_data):
        """
        Decides on the next research action.
        """
        self.logger.debug("Managing Upgrades")
        if self._research_wait > time.time():
            self.logger.debug(
                "Smith still busy for %d seconds", int(self._research_wait - time.time())
            )
            return {"action": "idle", "intent": "Schmiede beschäftigt."}

        unit_levels = self.wanted_levels
        if not unit_levels:
            self.logger.debug("Not upgrading because nothing is requested")
            return {"action": "idle", "intent": "Keine Upgrades benötigt."}

        if not smith_data:
            self.logger.debug("Error reading smith data")
            return {"action": "error", "intent": "Fehler beim Lesen der Schmiede-Daten."}

        for unit_type in unit_levels:
            if unit_type not in smith_data.get("available", {}):
                self.logger.warning("Unit %s not available in smith.", unit_type)
                continue

            wanted_level = unit_levels[unit_type]
            data = smith_data["available"][unit_type]
            current_level = int(data["level"])

            if current_level < wanted_level and data.get("can_research"):
                if data.get("research_error"):
                    self.logger.debug("Cannot research %s due to research error (resources?).", unit_type)
                    # Request resources if needed
                    r = True
                    if data["wood"] > self.game_data["village"]["wood"]:
                        req = data["wood"] - self.game_data["village"]["wood"]
                        self.resman.request(source="research", resource="wood", amount=req)
                        r = False
                    if data["stone"] > self.game_data["village"]["stone"]:
                        req = data["stone"] - self.game_data["village"]["stone"]
                        self.resman.request(source="research", resource="stone", amount=req)
                        r = False
                    if data["iron"] > self.game_data["village"]["iron"]:
                        req = data["iron"] - self.game_data["village"]["iron"]
                        self.resman.request(source="research", resource="iron", amount=req)
                        r = False
                    continue

                if data.get("error_buildings"):
                    self.logger.debug("Cannot research %s due to missing buildings.", unit_type)
                    continue

                if "research_time" in data:
                     self._research_wait = time.time() + self.research_time(data["research_time"])

                return {
                    "action": "research",
                    "unit": unit_type,
                    "intent": f"Erforsche {unit_type} auf Stufe {current_level + 1}."
                }

        return {"action": "idle", "intent": "Upgrade-Level aktuell."}

    def reserve_resources(self, resources, wanted_times, has_times, unit_type):
        """
        Reserve resources for a certain recruiting action
        """
        # Resources per unit, batch wanted, batch already recruiting
        create_amount = wanted_times - has_times
        self.logger.debug(f"Requesting resources to recruit %d of %s", create_amount, unit_type)
        for res in ["wood", "stone", "iron"]:
            req = resources[res] * (wanted_times - has_times)
            self.resman.request(source=f"recruitment_{unit_type}", resource=res, amount=req)

    def _unlock_gather_options(self, village_data):
        """
        Checks for locked gather options and unlocks them if resources are available.
        """
        if not village_data or 'options' not in village_data:
            return []

        unlock_actions = []
        for option_id in sorted(village_data['options'].keys()):
            option = village_data['options'][option_id]

            if option.get('is_locked') and option.get('unlock_costs'):
                costs = option['unlock_costs']
                can_afford = all(self.game_data['village'].get(res, 0) >= cost for res, cost in costs.items())

                if can_afford:
                    self.logger.info(f"Decided to unlock gather option {option_id}.")
                    unlock_actions.append({
                        "action": "unlock_gather",
                        "option_id": option_id,
                        "intent": f"Schalte Sammel-Option {option_id} frei."
                    })
                else:
                    self.logger.debug(f"Cannot afford to unlock gather option {option_id}.")

        return unlock_actions

    def decide_next_gather(self, village_data, troops_at_home, selection=1, disabled_units=None, advanced_gather=True):
        """
        Decides on the next gathering action.
        """
        if disabled_units is None:
            disabled_units = []
        if not self.can_gather:
            return []

        gather_actions = []

        # First, decide if any locked options can be unlocked
        unlock_actions = self._unlock_gather_options(village_data)
        if unlock_actions:
            return unlock_actions # Prioritize unlocking

        available_troops = troops_at_home.copy()

        haul_dict = {
            "spear": 25, "sword": 15, "heavy": 50, "axe": 10, "light": 80,
            "archer": 10, "marcher": 50
        }

        options_to_consider = list(reversed(sorted(village_data.get('options', {}).keys())))

        if advanced_gather:
            # Advanced: Assign all available troops to the best available slots
            for option_id in options_to_consider:
                option = village_data['options'][option_id]
                if int(option_id) <= selection and not option.get('is_locked') and not option.get('scavenging_squad'):
                    payload = { "squad_requests[0][option_id]": str(option_id) }
                    total_carry = 0
                    troops_assigned = False
                    
                    for unit, count in available_troops.items():
                        if unit in haul_dict and unit not in disabled_units and count > 0:
                            payload[f"squad_requests[0][candidate_squad][unit_counts][{unit}]"] = str(count)
                            total_carry += haul_dict[unit] * count
                            troops_assigned = True
                    
                    if troops_assigned:
                        payload["squad_requests[0][candidate_squad][carry_max]"] = str(total_carry)
                        gather_actions.append({
                            "action": "gather",
                            "payload": payload,
                            "intent": f"Sende alle Truppen zum Sammeln (Option {option_id})."
                        })
                        # Since we send all troops, we can break
                        break
        else:
            # Basic: Send all troops to the first available slot
            # This logic is simpler and might not be necessary if advanced is default
            pass

        return gather_actions


    def readable_ts(self, seconds):
        """
        Human readable timestamp
        """
        seconds -= time.time()
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return "%d:%02d:%02d" % (hour, minutes, seconds)
