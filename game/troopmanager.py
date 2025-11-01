import logging
import time
from datetime import datetime

from game.resources import ResourceManager as Resources


class TroopManager:
    """
    Recruitment manager that handles everything about troops
    """

    resman = None
    troops = {}
    total_troops = {}
    wanted = {}
    wanted_levels = {}
    template = {}
    vil_id = None
    wrapper = None
    can_attack = False
    can_farm = False
    can_scout = True
    max_batch_size = 25
    units_in_village_file = {}
    logger = None
    is_recruiting = False

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def time_til_finished(self, f_time):
        """
        :param f_time: timestamp for when a recruitment is finished
        :return: string with human readable time
        """
        f_time = int(f_time)
        return str(datetime.fromtimestamp(f_time) - datetime.fromtimestamp(time.time()))

    def has_building_level(self, building, level):
        """
        Check if a building has the required level
        """
        if self.resman:
            if building in self.resman.game_state["village"]["buildings"]:
                if (
                        self.resman.game_state["village"]["buildings"][building] >= level
                ):
                    return True
        return False

    def recruit_is_possible(self, building, unit):
        """
        Check if a recruitment is possible
        """
        if building in self.is_recruiting:
            return False
        return True

    def _should_recruit(self, wanted_unit):
        """
        (Private) Determines if a unit type should be recruited based on current troop levels.
        """
        if wanted_unit not in self.wanted or self.wanted[wanted_unit] == 0:
            return False

        current_amount = self.total_troops.get(wanted_unit, 0)

        # Simple case: if we have fewer than wanted, recruit
        if current_amount < self.wanted[wanted_unit]:
            return True

        # Advanced case for "-1" (fill rest of farm space)
        # This logic is complex and might be better handled in the decision method itself.
        # For now, we'll just say yes if it's -1 and we have *some* troops of that type.
        if self.wanted[wanted_unit] == -1 and current_amount > 0:
            return True # This is a simplification, actual logic is in `decide_next_recruit`

        return False

    def _decide_recruit_action(self, game_state, recruit_data, unit_type, amount):
        """
        (Private) Creates a recruit action dictionary if recruitment is possible.
        """
        village_name = game_state['village']['name']
        if not self.logger:
            # Note: The logger name is based on the first village that uses this manager.
            # This is acceptable as the manager instance is per-village.
            self.logger = logging.getLogger(f"Recruitment: {village_name}")

        building = recruit_data[unit_type]["building"]
        if recruit_data[unit_type]["in_recruitment"]:
            finish_time = recruit_data[unit_type]["recruitment_finish_time"]
            human_ts = self.time_til_finished(finish_time)
            intent = f"{building.capitalize()} is busy for {human_ts}"
            self.logger.info(f"[TROOPS] {intent}")
            return {"action": "wait", "building": building, "intent": intent}

        if not self.total_troops:
             self.total_troops = {k: 0 for k in recruit_data.keys()}

        max_build = {}
        for wanted_unit in self.wanted:
            if self._should_recruit(wanted_unit):
                costs = recruit_data[wanted_unit]["costs"]
                can_build = self.resman.get_max_build(costs)
                if can_build == 0:
                    self.logger.debug(f"[TROOPS] Skipping {wanted_unit} - insufficient resources detected")
                    continue
                max_build[wanted_unit] = can_build

        if not max_build:
            return {"action": "wait_resources", "intent": "Waiting for resources for all wanted units."}

        # Determine which unit to prioritize (for now, the one we can build most of)
        # This can be made more sophisticated later
        if not unit_type or unit_type not in max_build:
            unit_type = max(max_build, key=max_build.get)

        get_min = max_build[unit_type]

        # Respect the batch size limit
        if get_min > self.max_batch_size:
            get_min = self.max_batch_size

        if not recruit_data[unit_type]["is_researched"]:
            intent = f"Cannot recruit {unit_type}: not researched."
            self.logger.warning(f"[TROOPS] {intent}")
            return {"action": "none", "intent": intent}

        if not all(self.has_building_level(req, recruit_data[unit_type]["requirements"][req]) for req in recruit_data[unit_type]["requirements"]):
            intent = f"Cannot recruit {unit_type}: requirements not met."
            self.logger.warning(f"[TROOPS] {intent}")
            return {"action": "none", "intent": intent}

        if get_min > 0:
            intent = f"Recruiting {get_min}x {unit_type}"
            return {
                "action": "recruit",
                "building": recruit_data[unit_type]["building"],
                "unit": unit_type,
                "amount": get_min,
                "intent": intent
            }
        else:
            return {
                "action": "wait_resources",
                "unit": unit_type,
                "intent": f"Waiting for resources for {unit_type}."
            }

    def get_template_action(self, building_levels):
        """
        Gets the current troop goals based on building levels from a staged template.
        """
        if not self.logger:
            self.logger = logging.getLogger(f"TroopManager:{self.village_id}")

        if isinstance(self.template, dict) and "stages" in self.template:
            self.logger.debug("[TROOPS] Processing new staged unit template.")
            # New template format with stages

            # Sort stages just in case they are not in order
            sorted_stages = sorted(self.template["stages"], key=lambda x: x["stage"])

            # Find the highest stage that meets prerequisites
            active_stage = None
            for stage in reversed(sorted_stages):
                prereqs = stage.get("prerequisites", {})
                if all(building_levels.get(b, 0) >= prereqs[b] for b in prereqs):
                    active_stage = stage
                    break

            if active_stage:
                self.logger.info(f"[TROOPS] Current active unit stage: {active_stage['name']} (Stage {active_stage['stage']})")
                self.wanted = active_stage.get("build", {})
                self.wanted_levels = active_stage.get("upgrade", {})
                self.can_farm = active_stage.get("farm", False)
                self.can_attack = active_stage.get("attack", False)
                return active_stage
            else:
                self.logger.warning("[TROOPS] No stage prerequisites met in the unit template.")
                return None
        else:
            # Legacy template support (or non-staged dict)
            self.logger.debug("[TROOPS] Processing legacy or non-staged unit template.")
            template_dict = self.template if isinstance(self.template, dict) else {}
            self.wanted = template_dict.get("build", {})
            self.wanted_levels = template_dict.get("upgrade", {})
            self.can_farm = template_dict.get("farm", False)
            self.can_attack = template_dict.get("attack", False)
            return template_dict

    def decide_next_research(self, smith_data):
        """
        (BLL) Decides the next unit to research based on wanted levels.
        Returns a research_action dictionary.
        """
        self.logger.debug("[TROOPS] Managing Upgrades")
        if not self.wanted_levels:
            self.logger.debug("[TROOPS] Not upgrading because nothing is requested in template.")
            return {"action": "none", "intent": "No research goals defined."}

        if not smith_data:
            self.logger.debug("[TROOPS] Error reading smith data.")
            return {"action": "none", "intent": "Could not read smith data."}

        for unit_type, target_level in self.wanted_levels.items():
            if unit_type not in smith_data:
                self.logger.warning(f"[TROOPS] Unit {unit_type} not available in smith.")
                continue

            current_level = smith_data[unit_type]["level"]
            if current_level < target_level:
                # Check if we can research the *next* level
                next_level_data = smith_data[unit_type].get(str(current_level + 1), {})

                if not next_level_data:
                     continue # Max level reached or data missing

                if next_level_data.get("can_research", False):
                    costs = next_level_data["costs"]
                    if self.resman.has_res(costs):
                        return {
                            "action": "research",
                            "unit": unit_type,
                            "intent": f"Researching {unit_type} to level {current_level + 1}"
                        }
                    else:
                        # Don't block other research, just note we're waiting
                        continue

        return {"action": "none", "intent": "All research goals met or waiting for resources."}


    def _add_recruit_resource_request(self, recruit_data, unit_type, create_amount):
        """
        (Private) Adds a resource request to the ResourceManager for recruitment.
        """
        if create_amount > 0 and unit_type in recruit_data:
            costs = recruit_data[unit_type]["costs"]
            res_needed = {res: costs[res] * create_amount for res in costs}
            self.logger.debug(f"[TROOPS] Requesting resources to recruit {create_amount} of {unit_type}")
            self.resman.add_request(
                vil_id=self.village_id,
                prio=5,
                req_id=f"recruit_{unit_type}",
                w_time=int(time.time() + 3600),  # Request for an hour from now
                wait_time=3600,
                res=res_needed,
            )

    def decide_next_gather(self, village_data, troops_at_home, selection, disabled_units, advanced_gather):
        actions = []
        scavenging_squads = village_data.get("scavenging_squads", {})

        for option_id, option_data in village_data.get("scavenging_options", {}).items():
            if option_data["is_locked"]:
                if advanced_gather and self.resman.has_res(option_data["unlock_costs"]):
                    self.logger.info(f"[GATHER] Decided to unlock gather option {option_id}.")
                    actions.append({"action": "unlock_gather", "option_id": option_id})
                else:
                    self.logger.debug(f"[GATHER] Cannot afford to unlock gather option {option_id}.")
                continue

            if not option_data.get("squad_id") and option_id not in scavenging_squads:
                # This option is available, let's decide if we send troops

                # Simple strategy: send all available troops of a certain type
                # More complex strategies can be added later

                # Determine candidate units (not disabled, present at home)
                candidate_units = {
                    unit: troops_at_home[unit]
                    for unit in option_data["allowed_units"]
                    if unit not in disabled_units and troops_at_home.get(unit, 0) > 0
                }

                if not candidate_units:
                    continue # No suitable troops for this option

                # Simple selection logic: use the most numerous unit
                unit_to_send = max(candidate_units, key=candidate_units.get)
                amount_to_send = candidate_units[unit_to_send]

                # Ensure we don't send more than the capacity allows
                unit_carry = village_data["unit_carry"][unit_to_send]
                if amount_to_send * unit_carry > option_data["carry_max"]:
                    amount_to_send = option_data["carry_max"] // unit_carry

                if amount_to_send > 0:
                    payload = {
                        "squad_requests[0][option_id]": option_id,
                        f"squad_requests[0][unit_counts][{unit_to_send}]": amount_to_send,
                    }
                    intent = f"Sending {amount_to_send} {unit_to_send} to gather."
                    actions.append({"action": "gather", "intent": intent, "payload": payload})

                    # Assume we can only send one squad per cycle for simplicity
                    return actions

        return actions

    def decide_next_recruit(self, game_state, recruit_data, wanted_units, total_troops, disabled_units):
        """
        (BLL) Main decision-making function for recruitment.
        """
        self.total_troops = total_troops
        self.wanted = wanted_units

        # Remove disabled units from wanted list to prevent errors
        for unit in disabled_units:
            self.wanted.pop(unit, None)

        # Find the unit with the biggest deficit
        best_unit = None
        max_deficit = 0

        for unit, target_amount in self.wanted.items():
            if target_amount == 0:
                continue

            current_amount = self.total_troops.get(unit, 0)

            if target_amount == -1: # Fill farm space logic
                # This is complex. For now, we'll treat it as a low-priority goal.
                # A better implementation would calculate remaining farm space.
                deficit = 1 # Small deficit to give it some priority
            else:
                deficit = target_amount - current_amount

            if deficit > max_deficit:
                max_deficit = deficit
                best_unit = unit

        if not best_unit:
            return {"action": "none", "intent": "All troop goals met."}

        # Now, get the specific action for the prioritized unit
        action = self._decide_recruit_action(
            game_state=game_state,
            recruit_data=recruit_data,
            unit_type=best_unit,
            amount=max_deficit  # The 'amount' is recalculated inside based on resources
        )

        # If we are waiting for resources, add a request to resman
        if action.get("action") == "wait_resources" and "unit" in action:
            self._add_recruit_resource_request(recruit_data, action["unit"], self.max_batch_size)

        return action
