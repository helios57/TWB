"""
Anything with resources goes here
"""
import logging
import re
import time

from core.extractors import Extractor


class PremiumExchange:
    """
    Logic for interaction with the premium exchange
    """

    def __init__(self, wrapper, stock: dict, capacity: dict, tax: dict, constants: dict, duration: int, merchants: int):
        self.wrapper = wrapper
        self.stock = stock
        self.capacity = capacity
        self.tax = tax
        self.constants = constants
        self.duration = duration
        self.merchants = merchants

    # --- FIX: robust marginal price with clamp & denominator check
    def calculate_marginal_price(self, stock, capacity):
        """
        Returns the marginal price for the next unit given current stock & capacity.
        price = base - elasticity * (stock / (capacity + stock_size_modifier))
        Clamped to >= 0.0 and with denominator validation.
        """
        c = self.constants
        denom = capacity + c["stock_size_modifier"]
        if denom <= 0:
            raise ValueError("Invalid capacity/stock_size_modifier (denominator <= 0).")
        price = c["resource_base_price"] - c["resource_price_elasticity"] * (stock / denom)
        return max(float(price), 0.0)

    # --- FIX: correct integration direction (selling increases market stock: t -> t + a)
    def calculate_cost(self, item, units):
        """
        Total return (in PP) for selling `units` of `item` to the premium exchange.
        Uses trapezoid approximation between price(t) and price(t + units).
        Includes sell tax.
        """
        if units <= 0:
            return 0.0
        if item not in self.stock or item not in self.capacity:
            raise ValueError(f"Invalid item: {item}")

        t = self.stock[item]
        n = self.capacity[item]
        tax = float(self.tax.get("sell", 0.0))

        p0 = self.calculate_marginal_price(t, n)
        p1 = self.calculate_marginal_price(t + units, n)  # important: +units when selling to market
        avg = 0.5 * (p0 + p1)
        multiplier = max(0.0, 1.0 - tax)  # Gebühr abziehen; nie negativ
        return multiplier * avg * units

    # --- FIX: real search (exponential bound + binary search) for largest r s.t. cost(r) <= 1.0
    def calculate_rate_for_one_point(self, item: str) -> int:
        """
        Find the largest integer r such that selling r units of `item` yields <= 1 PP.
        Monotone increasing cost -> exponential upper bound + binary search.
        """
        if item not in self.stock or item not in self.capacity:
            raise ValueError(f"Item {item} not found in stock/capacity.")

        # start estimate from current marginal price (guard against 0)
        n = max(self.calculate_marginal_price(self.stock[item], self.capacity[item]), 1e-9)
        hi = max(1, int(1.0 / n))

        # grow upper bound until cost > 1 or cap
        while self.calculate_cost(item, hi) <= 1.0 and hi < 10**7:
            hi *= 2

        # binary search for max r with cost(r) <= 1
        lo, best = 0, 0
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.calculate_cost(item, mid) <= 1.0:
                best = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    # --- FIX: linear optimization across merchants; choose i,j to minimize leftover ratio
    @staticmethod
    def optimize_n(amount, units_per_point, merchants, size=1000):
        """
        Choose number of merchants i (1..merchants) and #points j such that
        j * units_per_point fits merchant capacity size*i with minimal leftover ratio.
        `amount` is the max number of units we are willing/able to sell from inventory.
        """
        if units_per_point <= 0 or merchants <= 0 or amount <= 0:
            return {"merchants": 0, "ratio": 0.0, "n_to_sell": 0}

        max_points_by_amount = amount // units_per_point
        best = None  # (ratio, -i, i, j)
        best_ratio_val = None

        for i in range(1, merchants + 1):
            cap_units = size * i
            j = min(max_points_by_amount, cap_units // units_per_point)  # points
            leftover = cap_units - j * units_per_point
            ratio = leftover / float(max(cap_units, 1))  # 0..1, leftover relativ zur Gesamtkapazität
            cand = (ratio, -i, i, j)
            if best is None or cand < best:
                best = cand
                best_ratio_val = ratio

        if best is None:
            return {"merchants": 0, "ratio": 0.0, "n_to_sell": 0}

        _, _, i, j = best
        return {"merchants": i, "ratio": float(best_ratio_val), "n_to_sell": int(j)}


class ResourceManager:
    """
    Class to calculate, store and reserve resources for actions
    """

    def __init__(self, wrapper=None, village_id=None):
        """
        Create the resource manager
        Preferably used by anything that builds/recruits/sends/whatever
        """
        self.wrapper = wrapper
        self.village_id = village_id

        # --- FIX: instance-level state (no cross-instance leaking)
        self.actual = {}
        self.requested = {}

        self.storage = 0
        self.ratio = 2.5
        self.max_trade_amount = 4000
        self.trade_bias = 1
        self.last_trade = 0
        self.trade_max_per_hour = 1
        self.trade_max_duration = 2
        self.do_premium_trade = False
        self.merchant_carry = 1000  # capacity per merchant; adjust to world if needed

        self.logger = logging.getLogger("Resource Manager")

    def update(self, game_state):
        """
        Update the current resources based on the game state
        """
        self.actual["wood"] = game_state["village"]["wood"]
        self.actual["stone"] = game_state["village"]["stone"]
        self.actual["iron"] = game_state["village"]["iron"]
        self.actual["pop"] = game_state["village"]["pop_max"] - game_state["village"]["pop"]
        self.storage = game_state["village"]["storage_max"]
        self.check_state()
        store_state = game_state["village"]["name"]
        self.logger = logging.getLogger(f"Resource Manager: {store_state}")

    def do_premium_stuff(self):
        """
        Try premium exchange if we have a clear surplus of one resource.
        """
        gpl = self.get_plenty_off()
        self.logger.debug("Trying premium trade: gpl %s do? %s", gpl, self.do_premium_trade)
        if not (gpl and self.do_premium_trade):
            return

        # load exchange page and extract data
        url = f"game.php?village={self.village_id}&screen=market&mode=exchange"
        res = self.wrapper.get_url(url=url)
        data = Extractor.premium_data(res.text)
        if not data:
            self.logger.warning("Error reading premium data!")
            return

        premium_exchange = PremiumExchange(
            wrapper=self.wrapper,
            stock=data["stock"],
            capacity=data["capacity"],
            tax=data["tax"],
            constants=data["constants"],
            duration=data["duration"],
            merchants=data["merchants"]
        )

        # units required to get ~1 PP
        try:
            units_per_point = premium_exchange.calculate_rate_for_one_point(gpl)
        except Exception as e:
            self.logger.warning("Price calculation failed for %s: %s", gpl, e)
            return

        self.logger.debug("Units per point (%s): %s", gpl, units_per_point)
        self.logger.info("Current %s amount: %s", gpl, self.actual.get(gpl, 0))

        if data["merchants"] < 1 or units_per_point <= 0:
            self.logger.info("Not enough merchants or invalid units_per_point.")
            return

        # Optional: log 'actual premium prices' if extractor provides 'rates'
        if "rates" in data and isinstance(data.get("stock"), dict):
            price_fetch = ["wood", "stone", "iron"]
            prices = {}
            for p in price_fetch:
                if p in data["stock"] and p in data["rates"]:
                    prices[p] = data["stock"][p] * data["rates"][p]
            if prices:
                self.logger.info("Actual premium prices (debug): %s", prices)

        # Decide max safe amount to sell: don't go below "plenty" threshold and cap by merchant capacity
        keep_buffer = int(self.storage / self.ratio)  # don't sell below this
        max_sell_by_inventory = max(0, self.actual.get(gpl, 0) - keep_buffer)
        max_sell_by_capacity = data["merchants"] * self.merchant_carry
        amount_to_sell = min(max_sell_by_inventory, max_sell_by_capacity)
        if amount_to_sell <= 0:
            self.logger.debug("No safe amount to sell for %s (buffer=%s).", gpl, keep_buffer)
            return

        # Pack merchants efficiently
        plan = PremiumExchange.optimize_n(
            amount=amount_to_sell,
            units_per_point=units_per_point,
            merchants=data["merchants"],
            size=self.merchant_carry
        )

        sell_units = int(plan["n_to_sell"] * units_per_point)
        self.logger.debug("Optimized trade: %s sell_units=%s, merchants=%s, ratio=%.3f",
                          gpl, sell_units, plan["merchants"], plan["ratio"])

        # If wagons would be too empty or nothing to sell, skip
        if plan["ratio"] > 0.4 or sell_units <= 0:
            self.logger.info("Not worth trading (ratio=%.3f, sell_units=%s).", plan["ratio"], sell_units)
            return

        # Phase 1: begin exchange
        result = self.wrapper.get_api_action(
            self.village_id,
            action="exchange_begin",
            params={"screen": "market"},
            data={f"sell_{gpl}": sell_units},
        )

        if result:
            try:
                _rate_hash = result["response"][0]["rate_hash"]
            except Exception:
                self.logger.info("Trade failed (no rate_hash).")
                return

            # Phase 2: confirm
            trade_data = {
                f"sell_{gpl}": sell_units,
                "rate_hash": _rate_hash,
                "mb": "1"
            }
            result = self.wrapper.get_api_action(
                self.village_id,
                action="exchange_confirm",
                params={"screen": "market"},
                data=trade_data,
            )
            self.logger.info("Trade %s!", "successful" if result else "failed")
        else:
            self.logger.info("Trade failed!")

    def check_state(self):
        """
        Removes resource requests when the amount is met
        """
        for source in self.requested:
            for res in self.requested[source]:
                if self.requested[source][res] <= self.actual.get(res, 0):
                    self.requested[source][res] = 0

    def request(self, source="building", resource="wood", amount=1):
        """
        When called, resources can be taken from other actions
        """
        if source in self.requested:
            self.requested[source][resource] = amount
        else:
            self.requested[source] = {resource: amount}

    def can_recruit(self):
        """
        Checks if population is sufficient for recruitment
        """
        if self.actual.get("pop", 0) == 0:
            self.logger.info("Can't recruit, no room for pops!")
            # --- FIX: don't modify dict while iterating
            to_delete = [x for x in self.requested if "recruitment" in x]
            for x in to_delete:
                del self.requested[x]
            return False

        for x in self.requested:
            if "recruitment" in x:
                continue
            types = self.requested[x]
            for sub in types:
                if types[sub] > 0:
                    return False
        return True

    def get_plenty_off(self):
        """
        Checks if there is overcapacity in a village and returns the most abundant resource.
        """
        most_of = 0
        most = None
        for sub in self.actual:
            if sub == "pop":
                continue
            # skip types that are currently requested
            skip = False
            for sr in self.requested:
                if sub in self.requested[sr] and self.requested[sr][sub] > 0:
                    skip = True
                    break
            if skip:
                continue

            threshold = int(self.storage / self.ratio)
            if self.actual[sub] > threshold and self.actual[sub] > most_of:
                most = sub
                most_of = self.actual[sub]

        if most:
            self.logger.debug("We have plenty of %s", most)
        return most

    def in_need_of(self, obj_type):
        """
        Checks if the village lacks a certain resource
        """
        for x in self.requested:
            types = self.requested[x]
            if obj_type in types and self.requested[x][obj_type] > 0:
                return True
        return False

    def in_need_amount(self, obj_type):
        """
        Total requested amount for a resource
        """
        amount = 0
        for x in self.requested:
            types = self.requested[x]
            if obj_type in types and self.requested[x][obj_type] > 0:
                amount += self.requested[x][obj_type]
        return amount

    def get_needs(self):
        """
        Returns (needed_resource, amount) for the largest outstanding need or None.
        """
        needed_the_most = None
        needed_amount = 0
        for x in self.requested:
            types = self.requested[x]
            for obj_type in types:
                if types[obj_type] > 0 and types[obj_type] > needed_amount:
                    needed_amount = types[obj_type]
                    needed_the_most = obj_type
        if needed_the_most:
            return needed_the_most, needed_amount
        return None

    # --- FIX: parse merchant availability correctly from HTML
    def trade(self, me_item, me_amount, get_item, get_amount):
        """
        Creates a new trading offer
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=own_offer"
        res = self.wrapper.get_url(url=url)
        m = re.search(r'market_merchant_available_count">(\d+)<', res.text)
        available = int(m.group(1)) if m else 0
        if available == 0:
            self.logger.debug("Not trading because not enough merchants available")
            return False

        payload = {
            "res_sell": me_item,
            "sell": int(me_amount),
            "res_buy": get_item,
            "buy": int(get_amount),
            "max_time": self.trade_max_duration,
            "multi": 1,
            "h": self.wrapper.last_h,
        }
        post_url = f"game.php?village={self.village_id}&screen=market&mode=own_offer&action=new_offer"
        self.wrapper.post_url(post_url, data=payload)
        self.last_trade = int(time.time())
        return True

    def drop_existing_trades(self):
        """
        Removes an existing trade if resources are needed elsewhere or it expired
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=all_own_offer"
        data = self.wrapper.get_url(url)
        existing = re.findall(r'data-id="(\d+)".+?data-village="(\d+)"', data.text)
        for entry in existing:
            offer, village = entry
            if village == str(self.village_id):
                post_url = f"game.php?village={self.village_id}&screen=market&mode=all_own_offer&action=delete_offers"
                post = {
                    f"id_{offer}": "on",
                    "delete": "Verwijderen",
                    "h": self.wrapper.last_h,
                }
                self.wrapper.post_url(url=post_url, data=post)
                self.logger.info("Removing offer %s from market because it existed too long", offer)

    def readable_ts(self, seconds):
        """
        Human readable timestamp
        """
        seconds -= int(time.time())
        seconds = seconds % (24 * 3600)
        hour = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60

        return "%d:%02d:%02d" % (hour, minutes, seconds)

    def manage_market(self, drop_existing=True):
        """
        Manages the market for you
        """
        last = self.last_trade + int(3600 * self.trade_max_per_hour)
        if last > int(time.time()):
            rts = self.readable_ts(last)
            self.logger.debug("Won't trade for %s", rts)
            return

        get_h = time.localtime().tm_hour
        if get_h in range(0, 6) or get_h == 23:
            self.logger.debug("Not managing trades between 23h-6h")
            return

        if drop_existing:
            self.drop_existing_trades()

        plenty = self.get_plenty_off()
        if plenty and not self.in_need_of(plenty):
            need = self.get_needs()
            if need:
                # check incoming resources
                url = f"game.php?village={self.village_id}&screen=market&mode=other_offer"
                res = self.wrapper.get_url(url=url)
                p = re.compile(r"Aankomend:\s.+\"icon header (.+?)\".+?<\/span>(.+) ", re.M)
                incoming = p.findall(res.text)
                resource_incoming = {}
                if incoming:
                    resource_incoming[incoming[0][0].strip()] = int("".join([s for s in incoming[0][1] if s.isdigit()]))
                    self.logger.info("There are resources incoming! %s", resource_incoming)

                item, how_many = need
                how_many = int(round(how_many, -1))
                if item in resource_incoming and resource_incoming[item] >= how_many:
                    self.logger.info("Needed %s already incoming! (%s >= %s)", item, resource_incoming[item], how_many)
                    return
                if how_many < 250:
                    return

                self.logger.debug("Checking current market offers")
                if self.check_other_offers(item, how_many, plenty):
                    self.logger.debug("Took market offer!")
                    return

                if how_many > self.max_trade_amount:
                    self.logger.debug("Lowering trade amount of %d to %d because of limitation", how_many, self.max_trade_amount)
                    how_many = self.max_trade_amount

                biased = int(how_many * self.trade_bias)
                if self.actual.get(plenty, 0) < biased:
                    self.logger.debug("Cannot trade because insufficient resources")
                    return

                self.logger.info("Adding market trade of %d %s -> %d %s", how_many, item, biased, plenty)
                if hasattr(self.wrapper, "reporter") and self.wrapper.reporter:
                    self.wrapper.reporter.report(
                        self.village_id,
                        "TWB_MARKET",
                        "Adding market trade of %d %s -> %d %s" % (how_many, item, biased, plenty),
                    )

                self.trade(plenty, biased, item, how_many)

    def check_other_offers(self, item, how_many, sell):
        """
        Checks if there are offers that match our needs
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=other_offer"
        res = self.wrapper.get_url(url=url)
        p = re.compile(r"(?:<!-- insert the offer -->\n+)\s+<tr>(.*?)<\/tr>", re.S | re.M)
        cur_off_tds = p.findall(res.text)
        p = re.compile(r"Aankomend:\s.+\"icon header (.+?)\".+?<\/span>(.+) ", re.M)
        incoming = p.findall(res.text)
        resource_incoming = {}
        if incoming:
            resource_incoming[incoming[0][0].strip()] = int("".join([s for s in incoming[0][1] if s.isdigit()]))

        if item in resource_incoming:
            how_many = how_many - resource_incoming[item]
            if how_many < 1:
                self.logger.info("Requested resource already incoming!")
                return False

        willing_to_sell = self.actual.get(sell, 0) - self.in_need_amount(sell)
        self.logger.debug("Found %d offers on market, willing to sell %d %s", len(cur_off_tds), willing_to_sell, sell)

        for tds in cur_off_tds:
            res_offer = re.findall(r"<span class=\"icon header (.+?)\".+?>(.+?)</td>", tds)
            off_id = re.findall(r"<input type=\"hidden\" name=\"id\" value=\"(\d+)", tds)

            if len(off_id) < 1:
                # Not enough resources to trade or malformed row
                continue

            offer = self.parse_res_offer(res_offer, off_id[0])
            if (
                offer["offered"] == item
                and offer["offer_amount"] >= how_many
                and offer["wanted"] == sell
                and offer["wanted_amount"] <= willing_to_sell
            ):
                self.logger.info(
                    "Good offer: %d %s for %d %s",
                    offer["offer_amount"], offer["offered"], offer["wanted_amount"], offer["wanted"]
                )
                # Take the deal!
                payload = {
                    "count": 1,
                    "id": offer["id"],
                    "h": self.wrapper.last_h,
                }
                post_url = (
                    f"game.php?village={self.village_id}&screen=market&mode=other_offer"
                    f"&action=accept_multi&start=0&id={offer['id']}&h={self.wrapper.last_h}"
                )
                self.wrapper.post_url(post_url, data=payload)
                self.last_trade = int(time.time())
                self.actual[offer["wanted"]] = self.actual.get(offer["wanted"], 0) - offer["wanted_amount"]
                return True

        # No useful offers found
        return False

    def parse_res_offer(self, res_offer, id_):
        """
        Parse an offer row
        """
        off, want, _ratio = res_offer
        res_offer_name, res_offer_amount = off
        res_wanted_name, res_wanted_amount = want

        return {
            "id": id_,
            "offered": res_offer_name,
            "offer_amount": int("".join([s for s in res_offer_amount if s.isdigit()])),
            "wanted": res_wanted_name,
            "wanted_amount": int("".join([s for s in res_wanted_amount if s.isdigit()])),
        }
