import logging
import random
import time
from datetime import datetime

from core.extractors import Extractor


class ResourceManager:
    """
    Resource manager that keeps track of resources
    """

    village_id = None
    wrapper = None
    game_state = None
    requested = {}
    last_update = 0
    actual = {}
    storage = 0
    max_res = 0
    production = {}
    ratio = 1.05
    do_premium_trade = False
    trade_bias = 1.0
    trade_max_per_hour = 1
    trade_max_duration = 1
    total_merchants = 0
    available_merchants = 0
    last_troop_recruit_time = 0
    prioritize_troops = False
    logger = None

    def __init__(self, wrapper=None, village_id=None):
        self.wrapper = wrapper
        self.village_id = village_id

    def get_res(self):
        """
        Get current resources
        :return: dict with current resources
        """
        self.update()
        return self.actual

    def get_available_storage(self):
        """
        Get available storage
        :return: available storage
        """
        return self.storage - sum(self.actual.values())

    def get_max_build(self, cost, compensate_missing=False):
        """
        Get maximum amount of times something can be build
        :param cost: cost of the build
        :param compensate_missing: compensate missing resources with premium trade
        :return: maximum amount of times something can be build
        """
        max_build = -1
        for res in cost:
            if res in self.actual:
                amount = int(self.actual[res] / cost[res]) if cost[res] else 0
                if max_build == -1 or amount < max_build:
                    max_build = amount
        return max_build

    def has_res(self, cost):
        """
        Check if there are enough resources for a build
        :param cost: cost of the build
        :return: True if enough resources, False otherwise
        """
        for res in cost:
            if res in self.actual:
                if self.actual[res] < cost[res]:
                    return False
        return True

    def get_carry(self, troops):
        """
        Get carry capacity of troops
        :param troops: troops to check
        :return: carry capacity
        """
        carry = 0
        if not troops:
            return 0

        for troop in troops:
            if troop in self.game_state["unit_info"]:
                carry += (
                    self.game_state["unit_info"][troop]["carry"] * troops[troop]
                )
        return carry

    def update(self, game_state=None):
        """
        Update the resource manager with the latest data
        """
        if game_state:
            self.game_state = game_state
        if not self.game_state:
            return

        state = self.game_state
        if state and "village" in state:
            self.actual = {
                "wood": float(state["village"]["wood"]),
                "stone": float(state["village"]["stone"]),
                "iron": float(state["village"]["iron"]),
            }
            self.storage = int(state["village"]["storage_max"])
            self.production = {
                "wood": float(state["village"]["wood_prod"]),
                "stone": float(state["village"]["stone_prod"]),
                "iron": float(state["village"]["iron_prod"]),
            }
            self.total_merchants = int(
                state["village"]["buildings"].get("market", 0)
            )
            self.last_update = int(time.time())

            store_state = f"{int(sum(self.actual.values()))}/{self.storage}"
            if not self.logger:
                self.logger = logging.getLogger(f"ResourceManager:{self.village_id} ({store_state})")
            else:
                self.logger.name = f"ResourceManager:{self.village_id} ({store_state})"


    def do_premium_stuff(self):
        """
        Manage premium trading
        """
        if not self.do_premium_trade:
            return

        gpl = self.game_state["player"]["pp"]
        if gpl < 10:
            return

        # Check if there is a surplus of any resource
        surplus_res = None
        for res, amount in self.actual.items():
            if amount > self.storage * 0.9:
                surplus_res = res
                break

        if not surplus_res:
            self.logger.debug("[PREMIUM] No resource with sufficient surplus for premium trade.")
            return

        self.logger.debug(f"[PREMIUM] Checking premium trade for {gpl} premium points.")
        url = f"game.php?village={self.village_id}&screen=premium&mode=exchange"
        premium_data = self.wrapper.get_url(url)
        if not premium_data:
            self.logger.warning("[PREMIUM] Error reading premium data!")
            return

        if "Keine Händler verfügbar!" in premium_data.text:
            self.logger.info("[PREMIUM] Not enough merchants available!")
            return

        try:
            capacity = Extractor.premium_exchange_capacity(premium_data.text)
            rates = Extractor.premium_exchange_rates(premium_data.text)

            # Simple strategy: sell the surplus resource
            sell_resource = surplus_res

            # Buy the resource with the lowest amount
            buy_resource = min(self.actual, key=self.actual.get)

            if sell_resource == buy_resource:
                 other_res = [res for res in self.actual if res != sell_resource]
                 buy_resource = min(other_res, key=lambda r: self.actual[r])

            rate_sell = rates[sell_resource]
            rate_buy = rates[buy_resource]

            # Simplified cost calculation
            cost_per_point = (rate_sell + rate_buy) / 2
        except Exception as e:
            self.logger.warning(f"[PREMIUM] Error calculating exchange rate: {e}")
            return

        if cost_per_point < 1.0 or cost_per_point > 1.2:
            self.logger.debug(f"[PREMIUM] Invalid cost per point: {cost_per_point}")
            return

        self.logger.debug(
            f"[PREMIUM] Capacity: {capacity}, Rates: {rates}, Cost per PP: {cost_per_point}"
        )

        # Determine how much to sell
        sell_amount = int(self.actual[sell_resource] - (self.storage * 0.8))
        if sell_amount > capacity[0]: # wood capacity
            sell_amount = capacity[0]

        if sell_amount < 1000:
            return # Don't trade small amounts

        # How much we'll get
        buy_amount = int(sell_amount * (rates[sell_resource] / rates[buy_resource]))

        if self.actual[buy_resource] + buy_amount > self.storage:
            self.logger.info(
                f"[PREMIUM] Trade would overfill storage for {buy_resource}. Adjusting sell amount."
            )
            buy_amount = self.storage - self.actual[buy_resource]
            sell_amount = int(buy_amount * (rates[buy_resource] / rates[sell_resource]))


        if sell_amount > 1000:
            self.logger.info(
                f"[PREMIUM] Trading {sell_amount} {sell_resource} for {buy_amount} {buy_resource}"
            )
            self.premium_trade_begin(sell_amount, sell_resource, buy_resource)
        else:
             self.logger.debug(f"[PREMIUM] Calculated sell amount too low: {sell_amount}")

    def premium_trade_begin(self, sell_amount, sell_resource, buy_resource):
        """
        Execute the first step of premium trading
        """
        try:
            self.logger.warning(
                f"[PREMIUM] THIS IS THE PREMIUM TRADE, VILLAGE {self.village_id}"
            )
            # Step 1: Get rate hash
            self.logger.info(
                f"[PREMIUM] Executing trade: {sell_amount} {sell_resource} for {buy_resource}"
            )

            data = {
                "sell_type": sell_resource,
                "sell_amount": sell_amount,
                "buy_type": buy_resource,
            }
            begin_trade = self.wrapper.get_api_action(
                action="exchange_begin",
                params={"screen": "premium"},
                data=data,
                village_id=self.village_id,
            )
            if not begin_trade or "response" not in begin_trade:
                 self.logger.warning(f"[PREMIUM] Trade failed: exchange_begin error")
                 return

            response_data = begin_trade["response"]
            rate_hash = response_data.get("rate_hash")
            if not rate_hash:
                 raise ValueError("Missing rate_hash in response")

            self.premium_trade_confirm(rate_hash)

        except (ValueError, KeyError) as e:
            self.logger.warning(f"[PREMIUM] Trade failed: Missing rate_hash in response ({e})")
        except Exception as e:
            self.logger.critical(f"[PREMIUM] An unexpected error occurred during premium trade: {e}", exc_info=True)


    def premium_trade_confirm(self, rate_hash):
        """
        Execute the second step of premium trading
        """
        try:
            # Step 2: Confirm trade
            confirm_data = {"rate_hash": rate_hash}
            confirm_trade = self.wrapper.get_api_action(
                action="exchange_confirm",
                params={"screen": "premium"},
                data=confirm_data,
                village_id=self.village_id,
            )
            if confirm_trade and "response" in confirm_trade:
                # Update local resources based on the response
                new_res = confirm_trade["response"].get("resources", {})
                if new_res:
                    self.actual["wood"] = new_res.get("wood", self.actual["wood"])
                    self.actual["stone"] = new_res.get("stone", self.actual["stone"])
                    self.actual["iron"] = new_res.get("iron", self.actual["iron"])
                    self.logger.info(
                        f"[PREMIUM] Trade successful. New resources: {self.actual}"
                    )
                else:
                    self.logger.info("[PREMIUM] Trade confirmed, but no resource data in response.")
            else:
                 self.logger.warning(f"[PREMIUM] Trade failed: exchange_confirm error")
        except Exception as e:
            self.logger.critical(f"[PREMIUM] An unexpected error occurred during premium trade confirmation: {e}", exc_info=True)


    def set_last_troop_recruit(self, timestamp):
        """
        Set the last troop recruitment time
        :param timestamp: timestamp of last recruitment
        """
        self.last_troop_recruit_time = timestamp
        self.logger.debug("[SYSTEM] Marked troop recruitment at timestamp %d", self.last_troop_recruit_time)

    def can_build_building(self):
        """
        Check if a building can be built
        :return: True if building can be built, False otherwise
        """
        if not self.prioritize_troops:
            self.logger.debug("[BUILD] Allowed: troop prioritization disabled")
            return True

        if self.last_troop_recruit_time == 0:
            self.logger.debug("[BUILD] Allowed: first run (no troop recruitment yet)")
            return True

        # Check for active troop recruitment requests
        if self.village_id in self.requested:
            for key in self.requested[self.village_id]:
                if key.startswith("recruit_"):
                    self.logger.debug("[BUILD] Blocked: active recruitment request found: %s", key)
                    return False

        self.logger.debug("[BUILD] Allowed: no active recruitment requests")
        return True

    def can_recruit_troops(self):
        """
        Check if troops can be recruited
        :return: True if troops can be recruited, False otherwise
        """
        if self.prioritize_troops:
            self.logger.debug("[TROOPS] Recruitment allowed by prioritization setting.")
            return True

        pop_max = self.game_state["village"].get("pop_max", 0)
        pop_current = self.game_state["village"].get("pop", 0)

        if pop_max - pop_current < 1:
            self.logger.info("[TROOPS] Can't recruit, no room for pops!")
            return False

        return True

    def get_market_data(self):
        """
        Get market data
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=exchange"
        market_data = self.wrapper.get_url(url)
        if market_data:
            self.available_merchants = Extractor.current_merchants(market_data.text)
            return Extractor.market_offers(market_data.text)
        return []

    def manage_market(self, drop_existing=False):
        """
        Manage the market
        """
        most, least, sub = self.get_most_least_produced()
        if self.actual[most] > self.storage / self.ratio:
            self.logger.debug(f"[MARKET] We have plenty of {most}")
            if self.available_merchants > 0:
                offers = self.get_market_data()
                self.create_market_offer(
                    offers=offers, most=most, least=least, drop_existing=drop_existing
                )

    def get_most_least_produced(self):
        """
        Get the most, least and sub-least produced resources
        """
        most = max(self.production, key=self.production.get)
        least = min(self.production, key=self.production.get)
        sub = sorted(self.production, key=self.production.get)[1]
        return most, least, sub

    def create_market_offer(self, offers, most, least, drop_existing=False):
        """
        Create a market offer
        """
        if self.available_merchants == 0:
            self.logger.debug("[MARKET] Not trading because not enough merchants available.")
            return

        if drop_existing:
            for offer in offers:
                if offer["own"]:
                    url = f"game.php?village={self.village_id}&screen=market&mode=exchange&action=cancel&offer_id={offer['id']}"
                    self.wrapper.get_url(url)

        amount = int(
            (self.actual[most] - (self.storage / self.ratio)) / self.available_merchants
        )
        if amount > 1000:
            for rts in [least]:
                if self.production[most] / self.production[rts] > self.trade_bias:
                    self.logger.info(
                        f"[MARKET] Creating offer: {amount} {most} for {rts}"
                    )
                    self.do_create_offer(amount, most, amount, rts)

    def do_create_offer(self, sell_amount, sell_res, buy_amount, buy_res):
        """
        Execute the creation of a market offer
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=exchange"
        data = {
            "sell-amount": sell_amount,
            "sell-res": sell_res,
            "buy-amount": buy_amount,
            "buy-res": buy_res,
            "max_time": self.trade_max_duration,
            "action": "create_offer",
        }
        self.wrapper.post_url(url, data=data)

    def accept_market_offer(self, offer, wanted):
        """
        Accept a market offer
        """
        # Not implemented yet
        pass

    def add_request(self, vil_id, prio, req_id, w_time, wait_time, res):
        """
        Add a resource request
        """
        vil_id = str(vil_id)
        if vil_id not in self.requested:
            self.requested[vil_id] = {}

        self.requested[vil_id][req_id] = {
            "prio": prio,
            "res": res,
            "w_time": w_time,
            "wait_time": wait_time,
        }

    def check_request(self, vil_id, req_id):
        """
        Check if a resource request exists
        """
        vil_id = str(vil_id)
        if vil_id in self.requested and req_id in self.requested[vil_id]:
            return self.requested[vil_id][req_id]
        return None
