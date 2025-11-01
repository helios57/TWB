import logging
import re

from game.resources import ResourceManager as Resources


class SnobManager:
    """
    Snob manager that can recruit nobles
    """

    village_id = None
    wrapper = None
    resman = None
    troop_manager = None
    wanted = 0
    building_level = 0
    storage_item = None
    coin_item = None
    can_snob = False
    is_incomplete = False
    logger = None

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def _parse_snob_content(self, snob_content):
        """
        (Private) Parses the HTML content of the snob recruitment page.
        """
        if not self.logger:
            self.logger = logging.getLogger(f"SnobManager:{self.village_id}")

        try:
            current_snobs = int(re.search(r'Gepr.gte Adelsgeschlechter:.+?<b>(\d+)</b>', snob_content).group(1))
            max_snobs = int(re.search(r'Maximal m.gliche Adelsgeschlechter:.+?<b>(\d+)</b>', snob_content).group(1))

            self.storage_item = re.search(r'M.nzspeicher.+?\((\d+)\)', snob_content).group(1)
            self.coin_item = re.search(r'M.nzpr.gung.+?\((\d+)\)', snob_content).group(1)

            can_build_match = re.search(r'nicht gen.gend Rohstoffe', snob_content)
            self.can_snob = can_build_match is None

            self.is_incomplete = current_snobs < max_snobs

            return {"current": current_snobs, "max": max_snobs}

        except (AttributeError, IndexError) as e:
            self.logger.warning("[SNOB] Error parsing snob content: %s", e)
            return None

    def _calculate_snob_costs(self):
        """
        (Private) Calculates the resource cost for the next set of coins/storage items.
        """
        # This is a simplified cost calculation. Real costs increase per item.
        # A more accurate implementation would parse these from the snob page.
        base_costs = {
            "storage": {"wood": 28000, "stone": 30000, "iron": 25000},
            "coin": {"wood": 30000, "stone": 30000, "iron": 30000}
        }

        # Assume costs increase by 10% for each existing item (very rough estimate)
        multiplier_storage = 1.1 ** int(self.storage_item)
        multiplier_coin = 1.1 ** int(self.coin_item)

        costs = {
            "storage_cost": {res: int(cost * multiplier_storage) for res, cost in base_costs["storage"].items()},
            "coin_cost": {res: int(cost * multiplier_coin) for res, cost in base_costs["coin"].items()}
        }
        return costs

    def _add_resource_requests(self, costs):
        """
        (Private) Adds resource requests to the ResourceManager.
        """
        if int(self.storage_item) < self.building_level:
            self.logger.debug("[SNOB] Requesting resources for snob storage item.")
            self.resman.add_request(
                vil_id=self.village_id, prio=1, req_id="snob_storage", w_time=0, wait_time=0, res=costs["storage_cost"]
            )

        if int(self.coin_item) < self.building_level * int(self.storage_item):
            self.logger.debug("[SNOB] Requesting resources for snob coin item.")
            self.resman.add_request(
                vil_id=self.village_id, prio=1, req_id="snob_coin", w_time=0, wait_time=0, res=costs["coin_cost"]
            )

        if not self.resman.has_res(costs["storage_cost"]) or not self.resman.has_res(costs["coin_cost"]):
            self.logger.debug("[SNOB] Not enough resources available for snob production.")

    def _recruit_noble(self, current_snobs):
        """
        (Private) Executes the noble recruitment if possible.
        """
        if self.troop_manager and "snob" in self.troop_manager.wanted:
            snobs_in_village = self.troop_manager.total_troops.get("snob", 0)
            if snobs_in_village < self.troop_manager.wanted["snob"]:
                self.logger.debug(
                    f"[SNOB] Village has {snobs_in_village}/{self.troop_manager.wanted['snob']} nobles. Recruiting another."
                )
                if self.resman.has_res(self.troop_manager.game_state["unit_info"]["snob"]["cost"]):
                    self.wrapper.get_api_action(
                        village_id=self.village_id,
                        action="train",
                        params={"screen": "snob", "mode": "train"},
                        data={"units[snob]": "1"},
                    )
                else:
                    self.logger.warning("[SNOB] Not enough resources to recruit noble unit.")
            else:
                 self.logger.debug(f"[SNOB] Noble unit count ({snobs_in_village}) meets target.")


    def run(self):
        """
        Run the snob manager
        """
        if self.wanted == 0:
            return

        url = f"game.php?village={self.village_id}&screen=snob"
        snob_page = self.wrapper.get_url(url)
        if not snob_page:
            self.logger.warning("[SNOB] Could not fetch snob page.")
            return

        parsed_data = self._parse_snob_content(snob_page.text)
        if not parsed_data:
            return

        current = parsed_data["current"]
        maximum = parsed_data["max"]

        if current >= self.wanted:
            self.logger.info("[SNOB] Snob goal reached (%d/%d)", current, self.wanted)
            return

        if self.is_incomplete:
            costs = self._calculate_snob_costs()

            # Decide whether to mint coins or build storage
            if int(self.storage_item) < self.building_level:
                # Prioritize storage
                if self.resman.has_res(costs["storage_cost"]):
                    self.logger.info("[SNOB] Building snob storage item.")
                    self.wrapper.get_api_action(
                        village_id=self.village_id,
                        action="store",
                        params={"screen": "snob"},
                        data={"h": self.wrapper.last_h},
                    )
            elif int(self.coin_item) < self.building_level * int(self.storage_item):
                 # Mint coins
                 if self.resman.has_res(costs["coin_cost"]):
                    self.logger.info("[SNOB] Minting snob coin item.")
                    self.wrapper.get_api_action(
                        village_id=self.village_id,
                        action="coin",
                        params={"screen": "snob"},
                        data={"h": self.wrapper.last_h},
                    )
            else:
                self.logger.debug("[SNOB] All coins and storage items for the current level are built.")

            self._add_resource_requests(costs)

        elif current < maximum:
            # We have all coins, now recruit the noble unit
            self._recruit_noble(current)

        else:
            self.logger.info("[SNOB] Snob up-to-date (%d/%d)", current, self.wanted)
