"""
Anything with resources goes here
"""
import logging
import re
import time

from core.extractors import Extractor


class PremiumExchange:
    """
    Optimized logic for interaction with the premium exchange
    Performance improvements: Binary Search, Error-Handling
    """

    def __init__(self, wrapper, stock: dict, capacity: dict, tax: dict, constants: dict, duration: int, merchants: int):
        self.wrapper = wrapper
        self.stock = stock
        self.capacity = capacity
        self.tax = tax
        self.constants = constants
        self.duration = duration
        self.merchants = merchants

    # do not call this anihilation (calculate_cost) - i dechipered it from tribalwars js
    def calculate_cost(self, item, amount):
        """
        Stock exchange cost calculation (deciphered from TribalWars JavaScript)

        Args:
            item: Resource type (wood, stone, iron)
            amount: Positive => buy from exchange, negative => sell to exchange

        Returns:
            Signed cost in premium points (sales yield negative values)

        Raises:
            ValueError: If item not found or insufficient stock/capacity
        """
        if item not in self.stock or item not in self.capacity:
            raise ValueError(f"Invalid item: {item}")

        t = self.stock[item]
        n = self.capacity[item]

        if amount > 0 and t - amount < 0:
            raise ValueError(f"Not enough stock to buy {amount} {item} (available: {t})")
        if amount < 0 and t - amount > n:
            raise ValueError(f"Cannot sell {abs(amount)} {item}: capacity exceeded ({n})")

        tax = self.tax.get("buy", 0.0) if amount >= 0 else self.tax.get("sell", 0.0)

        price_before = self.calculate_marginal_price(t, n)
        price_after = self.calculate_marginal_price(t - amount, n)

        return (1.0 + float(tax)) * (price_before + price_after) * amount / 2.0

    def calculate_marginal_price(self, e, a):
        """
        Calculates marginal price based on stock elasticity

        Args:
            e: Current stock level
            a: Capacity

        Returns:
            Marginal price

        Raises:
            ZeroDivisionError: If denominator is zero
        """
        c = self.constants
        denominator = a + c["stock_size_modifier"]

        if denominator == 0:
            raise ZeroDivisionError("Stock size modifier results in division by zero")

        return c["resource_base_price"] - c["resource_price_elasticity"] * e / denominator

    def calculate_rate_for_one_point(self, item: str):
        """
        Findet die ungefähre Ressourcenmenge für einen Premium-Punkt.

        Args:
            item: Resource type (wood, stone, iron)

        Returns:
            Number of resources needed for ~1 premium point

        Raises:
            ValueError: If item not found in stock
        """
        if item not in self.stock:
            raise ValueError(f"Item {item} not found in stock")

        max_amount = int(self.capacity[item] - self.stock[item])
        if max_amount <= 0:
            raise ValueError(f"No capacity available for selling {item}")

        target = 1.0
        high = 1

        try:
            cost = abs(self.calculate_cost(item, -high))
        except ValueError as exc:
            raise ValueError(f"Unable to evaluate premium exchange cost: {exc}")

        # Exponentiell nach oben erweitern, bis wir >= 1 PP erreichen
        while cost < target and high < max_amount:
            high = min(max_amount, high * 2)
            try:
                cost = abs(self.calculate_cost(item, -high))
            except ValueError:
                break

        if cost < target:
            # Selbst mit maximal möglicher Menge erreichen wir keine 1 PP
            return high

        low = max(1, high // 2)
        best = high

        while low <= high:
            mid = max(1, (low + high) // 2)
            try:
                mid_cost = abs(self.calculate_cost(item, -mid))
            except ValueError:
                high = mid - 1
                continue

            if mid_cost >= target:
                best = mid
                high = mid - 1
            else:
                low = mid + 1

        return best

    @staticmethod
    def optimize_n(amount, sell_price, merchants, size=1000):
        """
        Findet eine passende Händler-Kombination für eine Ressourcenmenge.

        Args:
            amount: Verfügbare Ressourcenmenge (Überschuss)
            sell_price: Wird nicht mehr benötigt, verbleibt zur Rückwärtskompatibilität
            merchants: Anzahl verfügbarer Händler
            size: Kapazität pro Händler (Standard: 1000)

        Returns:
            dict mit: merchants (genutzt), ratio (Leerstand 0-1), sell_amount (Ressourcen)
        """
        # Schutz gegen ungültige Eingaben
        if amount <= 0 or merchants <= 0:
            return {
                "merchants": 0,
                "ratio": 1.0,
                "sell_amount": 0
            }

        def _ratio(resources, merchant_count, capacity=1000):
            """Berechnet Leerstand: 0.0 = voll ausgelastet, 1.0 = komplett leer"""
            return ((capacity * merchant_count) - resources) / capacity

        best_offer = None

        for used_merchants in range(1, merchants + 1):
            capacity = used_merchants * size
            sell_amount = min(amount, capacity)

            if sell_amount <= 0:
                continue

            ratio = _ratio(sell_amount, used_merchants, capacity=size)

            if ratio < 0:
                # Mehr Ressourcen als Kapazität – überspringen
                continue

            if best_offer is None:
                best_offer = (used_merchants, ratio, sell_amount)
                continue

            best_ratio = best_offer[1]

            if ratio < best_ratio or (abs(ratio - best_ratio) < 1e-9 and used_merchants > best_offer[0]):
                best_offer = (used_merchants, ratio, sell_amount)

        if best_offer is None:
            return {
                "merchants": 0,
                "ratio": 1.0,
                "sell_amount": 0
            }

        return {
            "merchants": best_offer[0],
            "ratio": best_offer[1],
            "sell_amount": best_offer[2]
        }


class ResourceManager:
    """
    Class to calculate, store and reserve resources for actions
    Optimized for smart premium trading
    """
    actual = {}

    requested = {}

    storage = 0
    ratio = 2.0  # Verkauft ab 50% Storage (früher und aggressiver)
    max_trade_amount = 4000
    logger = None
    # not allowed to bias
    trade_bias = 1
    last_trade = 0
    trade_max_per_hour = 1
    trade_max_duration = 2
    wrapper = None
    village_id = None
    do_premium_trade = False
    last_troop_recruit_time = 0
    income = {}

    def __init__(self, wrapper=None, village_id=None):
        """
        Create the resource manager
        Preferably used by anything that builds/recruits/sends/whatever
        """
        self.wrapper = wrapper
        self.village_id = village_id

    def calculate_income(self, game_state):
        """
        Calculates the resource income per hour for the village.
        """
        self.income['wood'] = game_state['village'].get('wood_prod', 0)
        self.income['stone'] = game_state['village'].get('stone_prod', 0)
        self.income['iron'] = game_state['village'].get('iron_prod', 0)

    def update(self, game_state):
        """
        Update the current resources based on the game state
        """
        self.actual["wood"] = game_state["village"]["wood"]
        self.actual["stone"] = game_state["village"]["stone"]
        self.actual["iron"] = game_state["village"]["iron"]
        self.actual["pop"] = (
                game_state["village"]["pop_max"] - game_state["village"]["pop"]
        )
        self.storage = game_state["village"]["storage_max"]
        self.check_state()
        store_state = game_state["village"]["name"]
        self.logger = logging.getLogger(f"Resource Manager: {store_state}")

    def do_premium_stuff(self):
        """
        Smart Premium Exchange: Verkauft Ressourcen-Überschuss für Premium-Punkte

        Neue Features:
        - Bug-Fix: Berechnet echten Überschuss (nicht API-Dummy-Wert)
        - Vorausschauend: Verkauft proaktiv wenn Storage bald voll
        - Kein Minimum: Verkauft auch kleine Mengen wenn effizient (ratio <= 0.45)
        - Detailliertes Logging für Transparenz
        """
        # Prüfe ob Premium-Trade aktiviert
        if not self.do_premium_trade:
            return

        def _format_pp(value: float) -> str:
            rounded = round(value, 2)
            if abs(rounded - round(rounded)) < 1e-6:
                return str(int(round(rounded)))
            return f"{rounded:.2f}"

        # Finde Ressource mit dem meisten Überschuss
        gpl = self.get_plenty_off()

        if not gpl:
            self.logger.debug("Premium trade: No resource with sufficient surplus")
            return

        self.logger.debug(f"[Premium] Checking premium trade for {gpl}")

        # Hole Premium Exchange Daten vom Server
        url = f"game.php?village={self.village_id}&screen=market&mode=exchange"
        res = self.wrapper.get_url(url=url)
        data = Extractor.premium_data(res.text)

        if not data:
            self.logger.warning("[Premium] Error reading premium data!")
            return

        if data["merchants"] < 1:
            self.logger.info("[Premium] Not enough merchants available!")
            return

        # Initialisiere Premium Exchange
        try:
            premium_exchange = PremiumExchange(
                wrapper=self.wrapper,
                stock=data["stock"],
                capacity=data["capacity"],
                tax=data["tax"],
                constants=data["constants"],
                duration=data["duration"],
                merchants=data["merchants"]
            )

            cost_per_point = premium_exchange.calculate_rate_for_one_point(gpl)
        except (ValueError, ZeroDivisionError) as e:
            self.logger.warning(f"[Premium] Error calculating exchange rate: {e}")
            return

        if cost_per_point <= 0:
            self.logger.debug(f"[Premium] Invalid cost per point: {cost_per_point}")
            return

        # 🔴 BUG-FIX: Berechne ECHTEN Überschuss (nicht prices[gpl]!)
        threshold = int(self.storage / self.ratio)
        current_amount = self.actual.get(gpl, 0)
        requested_amount = self.in_need_amount(gpl)

        # Verfügbarer Überschuss nach Abzug von Threshold und Reservierungen
        available_surplus = max(0, current_amount - threshold - requested_amount)

        # Logging für Transparenz
        storage_percent = (current_amount / self.storage * 100) if self.storage > 0 else 0
        self.logger.debug(
            f"[Premium] {gpl}: {current_amount}/{self.storage} ({storage_percent:.1f}%), "
            f"threshold: {threshold}, requested: {requested_amount}"
        )

        # 🚀 VORAUSSCHAU-LOGIK: Verkaufe proaktiv wenn Storage bald voll
        proactive_sell = False
        if available_surplus <= 0:
            # Noch kein Überschuss, aber prüfe ob bald voll
            proactive_threshold = int(threshold * 0.85)

            if current_amount > proactive_threshold:
                # Berechne geschätzte Produktionsrate (sehr vereinfacht)
                # In 85-100% Zone → verkaufe proaktiv etwas
                proactive_surplus = int((current_amount - proactive_threshold) * 0.5)

                if proactive_surplus >= cost_per_point:
                    available_surplus = proactive_surplus
                    proactive_sell = True
                    self.logger.info(
                        f"[Premium] Proactive sell triggered: {gpl} at {storage_percent:.1f}% "
                        f"(threshold: {proactive_threshold})"
                    )

        if available_surplus <= 0:
            self.logger.debug(
                f"[Premium] No surplus to sell: {gpl} (available: {available_surplus})"
            )
            return

        # Berechne wie viele Premium-Punkte möglich sind
        max_points = available_surplus // cost_per_point

        self.logger.info(
            f"[Premium] Available surplus: {available_surplus} {gpl} "
            f"(~{max_points} PP at {cost_per_point} {gpl}/PP)"
        )

        # Optimiere Händler-Auslastung
        gpl_data = PremiumExchange.optimize_n(
            amount=available_surplus,
            sell_price=cost_per_point,
            merchants=data["merchants"],
            size=1000
        )

        sell_amount = gpl_data.get("sell_amount", 0)
        utilization_percent = (1.0 - gpl_data["ratio"]) * 100

        self.logger.debug(
            f"[Premium] Optimized: {sell_amount} {gpl}, {gpl_data['merchants']} merchant(s), "
            f"{utilization_percent:.1f}% utilized"
        )

        # Effizienz-Check: Mindestens 55% Händler-Auslastung (ratio <= 0.45)
        if gpl_data["ratio"] > 0.45:
            self.logger.info(
                f"[Premium] Not efficient enough (ratio {gpl_data['ratio']:.2f} > 0.45, "
                f"only {utilization_percent:.1f}% utilized). Waiting for more surplus."
            )
            return

        if sell_amount < 1:
            self.logger.debug(f"[Premium] Calculated sell amount too low: {sell_amount}")
            return

        try:
            estimated_points = premium_exchange.calculate_cost(gpl, -sell_amount)
            estimated_pp = abs(estimated_points)
        except ValueError as exc:
            self.logger.warning(
                f"[Premium] Unable to estimate premium points for trade: {exc}"
            )
            return

        if estimated_pp < 1:
            self.logger.info(
                f"[Premium] Trade would yield < 1 PP (estimate: {estimated_pp:.2f}), skipping"
            )
            return

        formatted_estimate = _format_pp(estimated_pp)
        approx_prefix = "~"

        # 🎯 VERKAUFEN!
        mode_str = "proactive" if proactive_sell else "normal"
        self.logger.info(
            f"[Premium] Selling {sell_amount} {gpl} for {approx_prefix}{formatted_estimate} PP "
            f"({utilization_percent:.1f}% utilized, {mode_str} mode)"
        )

        # API Call: exchange_begin
        result = self.wrapper.get_api_action(
            self.village_id,
            action="exchange_begin",
            params={"screen": "market"},
            data={f"sell_{gpl}": sell_amount},
        )

        if not result:
            self.logger.warning(f"[Premium] Trade failed: exchange_begin error")
            return

        try:
            _rate_hash = result["response"][0]["rate_hash"]
        except (KeyError, IndexError) as e:
            self.logger.warning(f"[Premium] Trade failed: Missing rate_hash in response ({e})")
            return

        # API Call: exchange_confirm
        trade_data = {
            f"sell_{gpl}": sell_amount,
            "rate_hash": _rate_hash,
            "mb": "1"
        }

        result = self.wrapper.get_api_action(
            self.village_id,
            action="exchange_confirm",
            params={"screen": "market"},
            data=trade_data,
        )

        def _extract_premium_from_response(payload):
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(key, str) and "premium" in key.lower():
                        if isinstance(value, (int, float)):
                            return value
                        if isinstance(value, str) and value.replace(".", "", 1).isdigit():
                            try:
                                return float(value)
                            except ValueError:
                                pass
                    if isinstance(value, (dict, list)):
                        nested = _extract_premium_from_response(value)
                        if nested is not None:
                            return nested
            elif isinstance(payload, list):
                for item in payload:
                    nested = _extract_premium_from_response(item)
                    if nested is not None:
                        return nested
            return None

        if result:
            actual_pp = _extract_premium_from_response(result)
            if actual_pp is not None:
                actual_display = _format_pp(actual_pp)
                self.logger.info(
                    f"[Premium] ✅ Trade successful! Sold {sell_amount} {gpl} for {actual_display} PP"
                )
                report_amount = actual_display
            else:
                self.logger.info(
                    f"[Premium] ✅ Trade successful! Sold {sell_amount} {gpl} for "
                    f"{approx_prefix}{formatted_estimate} PP (server response did not include premium total)"
                )
                report_amount = f"{approx_prefix}{formatted_estimate}"

            # Report für Statistik
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_PREMIUM_TRADE",
                f"Sold {sell_amount} {gpl} for {report_amount} Premium Points ({mode_str})"
            )
        else:
            self.logger.warning(f"[Premium] Trade failed: exchange_confirm error")

    def check_state(self):
        """
        Removes resource requests when the amount is met
        """
        for source in self.requested:
            for res in self.requested[source]:
                if self.requested[source][res] <= self.actual[res]:
                    self.requested[source][res] = 0

    def mark_troop_recruited(self):
        """
        Marks the timestamp when troops were successfully recruited
        Used for troop prioritization system
        """
        self.last_troop_recruit_time = int(time.time())
        self.logger.debug("Marked troop recruitment at timestamp %d", self.last_troop_recruit_time)

    def can_build(self, prioritize_troops, timeout):
        """
        Checks if buildings can be constructed based on troop prioritization
        Returns False if troops should be prioritized and are waiting for resources

        Args:
            prioritize_troops: Whether troops should be prioritized over buildings
            timeout: Timeout in seconds before allowing buildings despite troop requests

        Returns:
            True if buildings can be built, False if blocked by troop priority
        """
        # If troop prioritization is disabled, always allow building
        if not prioritize_troops:
            self.logger.debug("Building allowed: troop prioritization disabled")
            return True

        # First run: no blockade (allows initial building construction)
        if self.last_troop_recruit_time == 0:
            self.logger.debug("Building allowed: first run (no troop recruitment yet)")
            return True

        # Check for active recruitment requests
        active_recruitment = False
        for key in self.requested:
            if key.startswith("recruitment_"):
                if sum(self.requested[key].values()) > 0:
                    active_recruitment = True
                    self.logger.debug("Active recruitment request found: %s", key)
                    break

        if not active_recruitment:
            self.logger.debug("Building allowed: no active recruitment requests")
            return True

        # Check timeout
        elapsed = int(time.time()) - self.last_troop_recruit_time
        if elapsed < timeout:
            self.logger.debug(
                "Building blocked: waiting for troops (%ds elapsed, %ds timeout)",
                elapsed, timeout
            )
            return False
        else:
            self.logger.info(
                "Smart-Fallback activated: allowing buildings after %ds timeout (elapsed: %ds)",
                timeout, elapsed
            )
            return True

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
        Checks of population is sufficient for recruitment
        """
        if self.actual["pop"] == 0:
            self.logger.info("Can't recruit, no room for pops!")
            for x in self.requested:
                if "recruitment" in x:
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
        Checks of there is overcapacity in a village
        """
        most_of = 0
        most = None
        for sub in self.actual:
            f = 1
            for sr in self.requested:
                if sub in self.requested[sr] and self.requested[sr][sub] > 0:
                    f = 0
            if not f:
                continue
            if sub == "pop":
                continue
            # self.logger.debug(f"We have {self.actual[sub]} {sub}. Enough? {self.actual[sub]} > {int(self.storage / self.ratio)}")
            if self.actual[sub] > int(self.storage / self.ratio):
                if self.actual[sub] > most_of:
                    most = sub
                    most_of = self.actual[sub]
        if most:
            self.logger.debug(f"We have plenty of {most}")

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
        Checks what would be needed in order to match requirements
        """
        amount = 0
        for x in self.requested:
            types = self.requested[x]
            if obj_type in types and self.requested[x][obj_type] > 0:
                amount += self.requested[x][obj_type]
        return amount

    def get_needs(self):
        """
        All of the above
        """
        needed_the_most = None
        needed_amount = 0
        for x in self.requested:
            types = self.requested[x]
            for obj_type in types:
                if (
                        self.requested[x][obj_type] > 0
                        and self.requested[x][obj_type] > needed_amount
                ):
                    needed_amount = self.requested[x][obj_type]
                    needed_the_most = obj_type
        if needed_the_most:
            return needed_the_most, needed_amount
        return None

    def trade(self, me_item, me_amount, get_item, get_amount):
        """
        Creates a new trading offer
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=own_offer"
        res = self.wrapper.get_url(url=url)
        if 'market_merchant_available_count">0' in res.text:
            self.logger.debug("Not trading because not enough merchants available")
            return False
        payload = {
            "res_sell": me_item,
            "sell": me_amount,
            "res_buy": get_item,
            "buy": get_amount,
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
                    "id_%s" % offer: "on",
                    "delete": "Verwijderen",
                    "h": self.wrapper.last_h,
                }
                self.wrapper.post_url(url=post_url, data=post)
                self.logger.info(
                    "Removing offer %s from market because it existed too long" % offer
                )

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
            self.logger.debug(f"Won't trade for {rts}")
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
                p = re.compile(
                    r"Aankomend:\s.+\"icon header (.+?)\".+?<\/span>(.+) ", re.M
                )
                incoming = p.findall(res.text)
                resource_incoming = {}
                if incoming:
                    resource_incoming[incoming[0][0].strip()] = int(
                        "".join([s for s in incoming[0][1] if s.isdigit()])
                    )
                    self.logger.info(
                        f"There are resources incoming! %s", resource_incoming
                    )

                item, how_many = need
                how_many = round(how_many, -1)
                if item in resource_incoming and resource_incoming[item] >= how_many:
                    self.logger.info(
                        f"Needed {item} already incoming! ({resource_incoming[item]} >= {how_many})"
                    )
                    return
                if how_many < 250:
                    return

                self.logger.debug("Checking current market offers")
                if self.check_other_offers(item, how_many, plenty):
                    self.logger.debug("Took market offer!")
                    return

                if how_many > self.max_trade_amount:
                    how_many = self.max_trade_amount
                    self.logger.debug(
                        "Lowering trade amount of %d to %d because of limitation", how_many, self.max_trade_amount
                    )
                biased = int(how_many * self.trade_bias)
                if self.actual[plenty] < biased:
                    self.logger.debug("Cannot trade because insufficient resources")
                    return
                self.logger.info(
                    "Adding market trade of %d %s -> %d %s", how_many, item, biased, plenty
                )
                self.wrapper.reporter.report(
                    self.village_id,
                    "TWB_MARKET",
                    "Adding market trade of %d %s -> %d %s"
                    % (how_many, item, biased, plenty),
                )

                self.trade(plenty, biased, item, how_many)

    def check_other_offers(self, item, how_many, sell):
        """
        Checks if there are offers that match our needs
        """
        url = f"game.php?village={self.village_id}&screen=market&mode=other_offer"
        res = self.wrapper.get_url(url=url)
        p = re.compile(
            r"(?:<!-- insert the offer -->\n+)\s+<tr>(.*?)<\/tr>", re.S | re.M
        )
        cur_off_tds = p.findall(res.text)
        p = re.compile(r"Aankomend:\s.+\"icon header (.+?)\".+?<\/span>(.+) ", re.M)
        incoming = p.findall(res.text)
        resource_incoming = {}
        if incoming:
            resource_incoming[incoming[0][0].strip()] = int(
                "".join([s for s in incoming[0][1] if s.isdigit()])
            )

        if item in resource_incoming:
            how_many = how_many - resource_incoming[item]
            if how_many < 1:
                self.logger.info("Requested resource already incoming!")
                return False

        willing_to_sell = self.actual[sell] - self.in_need_amount(sell)
        self.logger.debug(
            f"Found {len(cur_off_tds)} offers on market, willing to sell {willing_to_sell} {sell}"
        )

        for tds in cur_off_tds:
            res_offer = re.findall(
                r"<span class=\"icon header (.+?)\".+?>(.+?)</td>", tds
            )
            off_id = re.findall(
                r"<input type=\"hidden\" name=\"id\" value=\"(\d+)", tds
            )

            if len(off_id) < 1:
                # Not enough resources to trade
                continue

            offer = self.parse_res_offer(res_offer, off_id[0])
            if (
                    offer["offered"] == item
                    and offer["offer_amount"] >= how_many
                    and offer["wanted"] == sell
                    and offer["wanted_amount"] <= willing_to_sell
            ):
                self.logger.info(
                    f"Good offer: {offer['offer_amount']} {offer['offered']} for {offer['wanted_amount']} {offer['wanted']}"
                )
                # Take the deal!
                payload = {
                    "count": 1,
                    "id": offer["id"],
                    "h": self.wrapper.last_h,
                }
                post_url = f"game.php?village={self.village_id}&screen=market&mode=other_offer&action=accept_multi&start=0&id={offer['id']}&h={self.wrapper.last_h}"
                # print(f"Would post: {post_url} {payload}")
                self.wrapper.post_url(post_url, data=payload)
                self.last_trade = int(time.time())
                self.actual[offer["wanted"]] = (
                        self.actual[offer["wanted"]] - offer["wanted_amount"]
                )
                return True

        # No useful offers found
        return False

    def parse_res_offer(self, res_offer, id):
        """
        Parse an offer
        """
        off, want, ratio = res_offer
        res_offer, res_offer_amount = off
        res_wanted, res_wanted_amount = want

        return {
            "id": id,
            "offered": res_offer,
            "offer_amount": int("".join([s for s in res_offer_amount if s.isdigit()])),
            "wanted": res_wanted,
            "wanted_amount": int(
                "".join([s for s in res_wanted_amount if s.isdigit()])
            ),
        }
