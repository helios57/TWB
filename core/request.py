import logging
import random
import re
import time
from urllib.parse import urlparse, urlunparse
import json

import requests
from requests.adapters import HTTPAdapter, Retry

from core.reporter import Reporter


class Request:
    """
    Wrapper for requests module
    """

    session = None
    last_h = None
    reporter = Reporter()
    delay = 1.0
    min_delay = 2
    max_delay = 20
    last_response = None
    endpoint = None
    logger = None

    # Static headers that are always sent
    static_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1"
    }

    def __init__(self, cookies=None, server=None, world=None, endpoint=None, reporter=None):
        self.session = requests.Session()
        self.session.headers.update(self.static_headers)

        # Configure retries
        retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

        if cookies:
            self.session.cookies.update(cookies)

        if reporter:
            self.reporter = reporter

        if endpoint:
            # Ensure endpoint is just the base URL (e.g., https://de247.die-staemme.de/)
            parsed_url = urlparse(endpoint)
            self.endpoint = urlunparse((parsed_url.scheme, parsed_url.netloc, '', '', '', ''))
        elif server and world:
            self.endpoint = f"https://{server}{world}.tribalwars.co.uk/"
        else:
            raise ValueError("Either 'endpoint' or both 'server' and 'world' must be provided.")

        self.logger = logging.getLogger("Request")

    def set_h(self, text):
        """
        Set the CSRF token
        """
        h_val = re.search(r'var csrf_token = \'(\w+)\'', text)
        if h_val:
            self.last_h = h_val.group(1)
            self.session.headers.update({"TribalWars-Ajax-Token": self.last_h})
            self.logger.debug("[REQUEST] Set CSRF token")

    def _make_request(self, method, url, **kwargs):
        """
        Internal method to make a request with some common error handling.
        """
        # Ensure the URL is absolute
        if not url.startswith("http"):
            # Safely join the endpoint and the relative URL
            url = self.endpoint + "/" + url.lstrip("/")

        # Apply delay
        time.sleep(random.uniform(self.min_delay, self.max_delay))

        try:
            response = self.session.request(method, url, timeout=15, **kwargs)
            response.raise_for_status()

            self.logger.debug(f"[REQUEST] {method.upper()} {url} [{response.status_code}]")

            if "bot_protection" in response.url:
                self.logger.warning("[REQUEST] Bot protection hit! Cannot continue.")
                return None

            if response.text:
                self.set_h(response.text)

            self.last_response = response
            return response

        except requests.exceptions.RequestException as e:
            self.logger.warning(f"[REQUEST] {method.upper()} {url}: {e}")
            return None

    def get_url(self, url, params=None):
        """
        Get a URL
        """
        return self._make_request("GET", url, params=params)

    def post_url(self, url, data=None, params=None):
        """
        Post to a URL
        """
        if self.last_h:
            data = data or {}
            data['h'] = self.last_h

        return self._make_request("POST", url, data=data, params=params)

    def login(self, username=None, password=None):
        """
        Login to the game using credentials or verify existing session
        """
        # If username and password are provided, perform a full login
        if username and password:
            login_url = "index.php?action=login"
            login_data = {"user": username, "password": password, "cookie": "true"}
            response = self.post_url(login_url, data=login_data)

            if response and "game.php" in response.url:
                self.logger.info(f"[AUTH] Successfully logged in as {username}")
                return True
            else:
                self.logger.warning("[AUTH] Login failed. Check credentials or server status.")
                return False

        # Otherwise, verify if the current session (from cookies) is valid
        else:
            overview_page = self.get_url("game.php?screen=overview")
            if overview_page and "game.php" in overview_page.url:
                self.logger.info("[AUTH] Session is valid.")
                return True
            else:
                self.logger.warning("[AUTH] Session is invalid or expired.")
                return False

    def get_api_action(self, village_id, action, params=None, data=None):
        """
        Make a request to the API
        """
        api_url = "game.php"

        base_params = {
            "village": village_id,
            "ajax": action
        }
        if params:
            base_params.update(params)

        if not data:
            response = self.get_url(api_url, params=base_params)
        else:
            response = self.post_url(api_url, data=data, params=base_params)

        if response:
            try:
                return response.json()
            except json.JSONDecodeError:
                self.logger.warning("[API] Failed to decode JSON from API response for action: %s", action)
                return None
        return None

    def post_api_data(self, village_id, action, params=None, data=None):
        """
        Alias for POSTing data to the API, ensuring it's a POST request.
        """
        return self.get_api_action(village_id, action, params, data=data or {'h': self.last_h})

    def get_api_data(self, village_id, action, params=None):
        """
        Alias for GETting data from the API, ensuring it's a GET request.
        """
        return self.get_api_action(village_id, action, params, data=None)

    def get_unit_info(self, unit_name, key):
        """
        Get information about a unit
        """
        # This should ideally be loaded from world config, but hardcoding for now
        unit_data = {
            "spear": {"pop": 1, "carry": 25},
            "sword": {"pop": 1, "carry": 15},
            "axe": {"pop": 1, "carry": 10},
            "archer": {"pop": 1, "carry": 10},
            "spy": {"pop": 2, "carry": 0},
            "light": {"pop": 4, "carry": 80},
            "marcher": {"pop": 5, "carry": 50},
            "heavy": {"pop": 6, "carry": 50},
            "ram": {"pop": 5, "carry": 0},
            "catapult": {"pop": 8, "carry": 0},
            "knight": {"pop": 10, "carry": 100},
            "snob": {"pop": 100, "carry": 0},
        }
        return unit_data.get(unit_name, {}).get(key, 0)
