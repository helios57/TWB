import json
import logging
import time
import re
from codecs import decode
from datetime import datetime

from core.extractors import Extractor
from core.filemanager import FileManager
from core.templates import TemplateManager
from core.twstats import TwStats
from game.attack import AttackManager
from game.buildingmanager import BuildingManager
from game.defence_manager import DefenceManager
from game.map import Map
from game.reports import ReportManager
from game.resources import ResourceManager
from game.snobber import SnobManager
from game.troopmanager import TroopManager
from core.exceptions import *


class Village:
    village_id = None
    builder = None
    units = None
    wrapper = None
    resources = {}
    game_data = {}
    logger = None
    force_troops = False
    area = None
    snobman = None
    attack = None
    resman = None
    def_man = None
    rep_man = None
    config = None
    forced_peace_today = False
    village_set_name = None
    last_attack = None
    build_config = None
    current_unit_entry = None
    forced_peace = False
    forced_peace_today_start = None
    disabled_units = []
    overview_html = None

    # --- NEW ---
    strategy = None
    current_builder_intent = "Initialisiere..."
    current_troops_intent = "Initialisiere..."
    # --- END NEW ---

    twp = TwStats()

    def __init__(self, village_id=None, wrapper=None):
        self.village_id = village_id
        self.wrapper = wrapper
        # New properties for transparency
        self.strategy = None
        self.current_builder_intent = "Initialisiere..."
        self.current_troops_intent = "Initialisiere..."

    def get_config(self, section, parameter, default=None):
        if section not in self.config:
            self.logger.warning("[SYSTEM] Configuration section %s does not exist!", section)
            return default
        if parameter not in self.config[section]:
            self.logger.warning(
                "[SYSTEM] Configuration parameter %s:%s does not exist!", section, parameter
            )
            return default
        return self.config[section][parameter]

    def get_village_config(self, village_id, parameter, default=None):
        if village_id not in self.config["villages"]:
            return default
        vdata = self.config["villages"][village_id]
        if parameter not in vdata:
            self.logger.warning(
                "[SYSTEM] Village %s configuration parameter %s does not exist!",
                village_id, parameter
            )
            return default
        return vdata[parameter]

    def village_init(self):
        """
        Init the village entry and send first request
        """
        url = "game.php?screen=overview&intro"
        if self.village_id:
            url = f"game.php?village={self.village_id}&screen=overview"

        data = self.wrapper.get_url(url)

        if data:
            self.game_data = Extractor.game_state(data)
            self.overview_html = data.text

        if self.game_data:
            if not self.village_id:
                self.village_id = str(self.game_data["village"]["id"])

            self.logger = logging.getLogger(
                "Village %s" % self.game_data["village"]["name"]
            )
            self.logger.info("[SYSTEM] Initialized")

            self.wrapper.reporter.report(
                self.village_id,
                "TWB_START",
                "Starting run for village: %s" % self.game_data["village"]["name"],
            )
        else:
            self.logger = logging.getLogger(f"Village {self.village_id}")
            self.logger.error("[SYSTEM] Could not read game state for village")

        if (
                self.village_set_name
                and self.game_data and "village" in self.game_data
                and self.game_data["village"]["name"] != self.village_set_name
        ):
            self.logger.name = f"Village {self.village_set_name}"

        return data

    def set_world_config(self):
        """
        Sets basic world options
        """
        self.disabled_units = []
        if not self.get_config(
                section="world", parameter="archers_enabled", default=True
        ):
            self.disabled_units.extend(["archer", "marcher"])

        if not self.get_config(
                section="world", parameter="building_destruction_enabled", default=True
        ):
            self.disabled_units.extend(["ram", "catapult"])

        if not self.get_config(
                section="world", parameter="spy_enabled", default=True
        ):
            self.disabled_units.append("spy")

        if self.get_config(
                section="server", parameter="server_on_twstats", default=False
        ):
            self.twp.run(world=self.get_config(section="server", parameter="server"))

    def update_pre_run(self):
        """
        Manage defence, resources and reports
        """
        if not self.resman:
            self.resman = ResourceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
        self.resman.update(self.game_data)
        self.wrapper.reporter.report(
            self.village_id, "TWB_PRE_RESOURCE", str(self.resman.actual)
        )

        if not self.rep_man:
            self.rep_man = ReportManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
        self.rep_man.read(full_run=False, overview_html=self.overview_html)

        if not self.def_man:
            self.def_man = DefenceManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
            self.def_man.map = self.area

        if not self.def_man.units and self.units:
            self.def_man.units = self.units

    def setup_defence_manager(self, data):
        """
        Set-up the defence manager
        """
        self.def_man.manage_flags_enabled = self.get_config(
            section="world", parameter="flags_enabled", default=False
        )
        self.def_man.support_factor = self.get_village_config(
            self.village_id, "support_others_factor", default=0.25
        )
        self.def_man.allow_support_send = self.get_village_config(
            self.village_id, parameter="support_others", default=False
        )
        self.def_man.allow_support_recv = self.get_village_config(
            self.village_id, parameter="request_support_on_attack", default=False
        )
        self.def_man.auto_evacuate = self.get_village_config(
            self.village_id, parameter="evacuate_fragile_units_on_attack", default=False
        )
        self.def_man.update(
            self.overview_html,
            with_defence=self.get_config(
                section="units", parameter="manage_defence", default=False
            ),
        )

        if self.def_man.under_attack and not self.last_attack:
            self.logger.warning("[DEFENCE] Village under attack!")
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_ATTACK",
                "Village: %s under attack" % self.game_data["village"]["name"],
                )
        self.last_attack = self.def_man.under_attack

    def run_quest_actions(self, config):
        if self.get_config(section="world", parameter="quests_enabled", default=False):
            if self.get_quests():
                self.logger.info("[SYSTEM] Completed quests found, re-running village loop.")
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Completed quest"
                )
                return self.run(config=config)

            if self.get_quest_rewards():
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Collected quest reward(s)"
                )

            daily_reward = Extractor.get_daily_reward(self.wrapper.last_response)
            if daily_reward:
                self.logger.info("[SYSTEM] Collecting daily reward.")
                self.wrapper.get_api_action(
                    action="collect_daily_reward",
                    params={"screen": "daily_bonus", "type": daily_reward},
                    village_id=self.village_id,
                )

    def units_get_template(self):
        """
        Fetches the unit template, prioritizing the one from the strategy.
        """
        if not self.units:
            self.units = TroopManager(wrapper=self.wrapper, village_id=self.village_id)
            self.units.resman = self.resman
        self.units.max_batch_size = self.get_config("units", "batch_size", 25)

        unit_config = None
        if self.strategy and 'units_template' in self.strategy:
            unit_config = self.strategy['units_template']
        else:
            unit_config = self.get_village_config(self.village_id, "units")
            if not unit_config:
                self.logger.warning("[SYSTEM] Village %s does not have 'units' config override, falling back to default.", self.village_id)
                unit_config = self.get_config("units", "default", "basic")

        try:
            self.units.template = TemplateManager.get_template(
                category="troops", template=unit_config, output_json=True
            )
        except Exception as e:
            self.logger.error("[TROOPS] Could not load unit template file '%s': %s", unit_config, e)
            raise InvalidUnitTemplateException

    def _complete_actions(self, text):
        """
        (Orchestrator) Automatically finish a building if the world allows it
        """
        res = re.search(
            r'(?s)(\d+),\s*\'BuildInstantFree.+?data-available-from="(\d+)"', text
        )
        if res and int(res.group(2)) <= time.time():
            quickbuild_url = f"game.php?village={self.village_id}&screen=main&ajaxaction=build_order_reduce"
            quickbuild_url += f"&h={self.wrapper.last_h}&id={res.group(1)}&destroy=0"
            result = self.wrapper.get_url(quickbuild_url)
            self.logger.debug("[BUILD] Quick build action was completed")
            return result
        return None

    def go_manage_market(self):
        """
        Manages the market
        """
        if self.get_config(
                section="market", parameter="auto_trade", default=False
        ) and self.builder.get_level("market"):
            self.logger.info("[MARKET] Managing market...")
            self.resman.trade_max_per_hour = self.get_config(
                section="market", parameter="trade_max_per_hour", default=1
            )
            self.resman.trade_max_duration = self.get_config(
                section="market", parameter="max_trade_duration", default=1
            )
            if self.get_config(
                    section="market", parameter="trade_multiplier", default=False
            ):
                self.resman.trade_bias = self.get_config(
                    section="market", parameter="trade_multiplier_value", default=1.0
                )
            self.resman.manage_market(
                drop_existing=self.get_config(
                    section="market", parameter="auto_remove", default=True
                )
            )

        res = self.wrapper.get_action(village_id=self.village_id, action="overview")
        self.game_data = Extractor.game_state(res)
        self.resman.update(self.game_data)
        if self.get_config(
                section="world", parameter="trade_for_premium", default=False
        ) and self.get_village_config(
            self.village_id, parameter="trade_for_premium", default=False
        ):
            # Set the parameter correctly when the config says so.
            self.resman.do_premium_trade = True
            self.resman.do_premium_stuff()

    def do_gather(self):
        """
        Orchestrates the gathering of resources.
        """
        if not self.get_village_config(self.village_id, parameter="gather_enabled", default=False):
            return

        if self.def_man and self.def_man.under_attack:
            self.logger.info("[GATHER] Skipping gathering due to incoming attack.")
            return

        # 1. Fetch & Parse Data
        gather_page = self.wrapper.get_url(f"game.php?village={self.village_id}&screen=place&mode=scavenge")
        village_data = Extractor.village_data(gather_page)

        place_data = self.wrapper.get_url(f"game.php?village={self.village_id}&screen=place&mode=units")
        troops_at_home = {k: int(v) for k, v in Extractor.units_in_village(place_data.text)}

        # 2. Get Decisions
        gather_actions = self.units.decide_next_gather(
            village_data=village_data,
            troops_at_home=troops_at_home,
            selection=self.get_village_config(self.village_id, "gather_selection", 1),
            disabled_units=self.disabled_units,
            advanced_gather=self.get_village_config(self.village_id, "advanced_gather", True)
        )

        # 3. Execute Actions
        for action in gather_actions:
            if action["action"] == "unlock_gather":
                self.logger.info(f"[GATHER] Executing unlock gather option: {action['option_id']}")
                self.wrapper.get_api_action(
                    action="unlock_option",
                    params={"screen": "scavenge_api"},
                    data={"option_id": action['option_id'], "h": self.wrapper.last_h},
                    village_id=self.village_id,
                )
                # After unlocking, we should refetch and re-decide, so we'll stop here for this cycle
                break

            elif action["action"] == "gather":
                self.logger.info(f"[GATHER] {action['intent']}")
                payload = action['payload']
                payload["h"] = self.wrapper.last_h
                payload["squad_requests[0][village_id]"] = self.village_id
                payload["squad_requests[0][use_premium]"] = "false"

                self.wrapper.get_api_action(
                    action="send_squads",
                    params={"screen": "scavenge_api"},
                    data=payload,
                    village_id=self.village_id,
                )

    def run_farming(self):
        """
        Runs the farming logic
        """
        if not self.forced_peace and self.units.can_attack:
            if not self.area:
                self.area = Map(wrapper=self.wrapper, village_id=self.village_id)
            self.area.get_map()
            if self.area.villages:
                self.units.can_scout = self.get_config(
                    section="farms", parameter="force_scout_if_available", default=True
                )
                self.logger.info(
                    "[FARM] %d villages from map cache, (your location: %s)",
                    len(self.area.villages),
                    ":".join([str(x) for x in self.area.my_location])
                )
                if not self.attack:
                    self.attack = AttackManager(
                        wrapper=self.wrapper,
                        village_id=self.village_id,
                        troopmanager=self.units,
                        map=self.area,
                    )
                    self.attack.repman = self.rep_man

                if self.forced_peace_today:
                    self.logger.info("[FARM] Forced peace time coming up today!")
                    self.attack.forced_peace_time = self.forced_peace_today_start

                self.attack.target_high_points = self.get_config("farms", "attack_higher_points", False)
                self.attack.farm_minpoints = self.get_config("farms", "min_points", 24)
                self.attack.farm_maxpoints = self.get_config("farms", "max_points", 1080)
                self.attack.farm_radius = self.get_config("farms", "search_radius", 50)
                self.attack.farm_default_wait = self.get_config("farms", "default_away_time", 1200)
                self.attack.farm_high_prio_wait = self.get_config("farms", "full_loot_away_time", 1800)
                self.attack.farm_low_prio_wait = self.get_config("farms", "low_loot_away_time", 7200)
                self.attack.scout_farm_amount = self.get_config("farms", "farm_scout_amount", 5)

                if self.current_unit_entry:
                    self.attack.template = self.current_unit_entry["farm"]

                if (
                        self.get_config(section="farms", parameter="farm", default=False)
                        and not self.def_man.under_attack
                ):
                    self.attack.extra_farm = self.get_village_config(
                        self.village_id, parameter="additional_farms", default=[]
                    )
                    self.attack.max_farms = self.get_config(
                        section="farms", parameter="max_farms", default=25
                    )
                    self.attack.run()

    def check_forced_peace(self):
        # Set timeslots in order to prevent farming during events like national holidays
        forced_peace_times = self.get_config(section="farms", parameter="forced_peace_times", default=[])
        self.forced_peace = False
        self.forced_peace_today = False
        self.forced_peace_today_start = None
        for time_pairs in forced_peace_times:
            start_dt = datetime.strptime(time_pairs["start"], "%d.%m.%y %H:%M:%S")
            end_dt = datetime.strptime(time_pairs["end"], "%d.%m.%y %H:%M:%S")
            now = datetime.now()
            if start_dt.date() == now.date():
                self.forced_peace_today = True
                self.forced_peace_today_start = start_dt
            if start_dt < now < end_dt:
                self.logger.debug("[SYSTEM] Currently in a forced peace time! No attacks will be send.")
                self.forced_peace = True
                break

    def set_unit_wanted_levels(self):
        """
        Fetches wanted units for the current buildings
        """
        self.current_unit_entry = self.units.get_template_action(self.builder.levels)
        if self.current_unit_entry and self.units.wanted != self.current_unit_entry["build"]:
            self.logger.info(
                "[TROOPS] Set wanted units: %s", str(self.current_unit_entry["build"])
            )
            self.units.wanted = self.current_unit_entry["build"]
        if self.units.wanted_levels != {}:
            for disabled in self.disabled_units:
                self.units.wanted_levels.pop(disabled, None)
            self.logger.info(
                "[TROOPS] Set wanted research levels: %s", str(self.units.wanted_levels)
            )

    def manage_local_resources(self):
        to_dell = []
        for x in self.resman.requested:
            if all(res == 0 for res in self.resman.requested[x].values()):
                to_dell.append(x)
        for x in to_dell:
            self.resman.requested.pop(x)
        self.logger.debug("[RESOURCE] Current resources: %s", str(self.resman.actual))
        self.logger.debug("[RESOURCE] Requested resources: %s", str(self.resman.requested))

    def run(self, config=None, first_run=False, strategy=None):
        self.config = config
        self.strategy = strategy
        self.wrapper.delay = self.get_config(
            section="bot", parameter="delay_factor", default=1.0
        )

        data = self.village_init()
        if not self.game_data:
            raise VillageInitException

        self.set_world_config()
        vdata = self.get_config(section="villages", parameter=self.village_id)
        if not self.get_village_config(self.village_id, parameter="managed", default=False):
            return False

        self.update_pre_run()
        self.setup_defence_manager(data=data)
        self.run_quest_actions(config=config)

        # 1. FETCH & PARSE DATA
        main_data_text = self.wrapper.get_action(village_id=self.village_id, action="main").text
        building_data = Extractor.building_data(main_data_text)
        current_levels = self.game_data["village"]["buildings"]

        # Initialize Managers
        if not self.builder:
            self.builder = BuildingManager(wrapper=self.wrapper, village_id=self.village_id)
            self.builder.resman = self.resman

        self.units_get_template()
        self.set_unit_wanted_levels()

        # 2. GET DECISIONS (BLL)
        # Builder Decision
        if self.strategy and 'build_template' in self.strategy:
            build_config_name = self.strategy['build_template']
        else:
            build_config_name = self.get_village_config(self.village_id, "building", self.get_config("building", "default", "purple_predator"))

        new_queue = TemplateManager.get_template(category="builder", template=build_config_name)
        self.builder.queue = new_queue

        build_action = self.builder.decide_next_build(
            game_state=self.game_data,
            building_data=building_data,
            queue=self.builder.queue,
            current_levels=current_levels,
            build_enabled=self.get_config("building", "manage_buildings", True)
        )
        self.current_builder_intent = build_action.get("intent", "OK")
        self.logger.info(f"[BUILD] Intent: {self.current_builder_intent}")

        # Troop/Upgrade Decision (with prioritization)
        recruit_action = None
        research_action = None

        # Resource & Snob Prioritization Logic
        prioritize_building = self.get_village_config(self.village_id, "prioritize_building", False) and build_action["action"] == "wait_resources"

        prioritize_snob_check = self.get_village_config(self.village_id, "prioritize_snob", False)
        if self.strategy and self.strategy.get('role', '').startswith("NOBLE_RUSH") and self.snobman and self.snobman.wanted > 0:
            prioritize_snob_check = True

        if prioritize_building:
            self.current_troops_intent = "Pausiert (Priorität Gebäude)"
        elif prioritize_snob_check and self.snobman and self.snobman.can_snob and self.snobman.is_incomplete:
            self.current_troops_intent = "Pausiert (Priorität AG-Produktion)"
        else:
            # Decide on recruitment
            recruit_data = Extractor.recruit_data(main_data_text)

            # This needs to be fetched, can't be in TroopManager
            place_data = self.wrapper.get_url(f"game.php?village={self.village_id}&screen=place&mode=units")
            total_troops = {k: v for k, v in Extractor.units_in_village(place_data.text)}

            recruit_action = self.units.decide_next_recruit(
                game_state=self.game_data,
                recruit_data=recruit_data,
                wanted_units=self.units.wanted,
                total_troops=total_troops,
                disabled_units=self.disabled_units
            )
            self.current_troops_intent = recruit_action.get("intent", "Warte...")

            # Decide on research
            smith_page = self.wrapper.get_action(village_id=self.village_id, action="smith")
            smith_data = Extractor.smith_data(smith_page)
            research_action = self.units.decide_next_research(smith_data)
            # Research intent could also be displayed, but troop intent is likely more important for now
        self.logger.info(f"[TROOPS] Intent: {self.current_troops_intent}")

        # 3. EXECUTE ACTIONS
        # Execute Build Action
        if build_action["action"] == "build":
            self.logger.info(f"[BUILD] Executing: Build {build_action['building_name']} to level {build_action['new_level']}")
            response = self.wrapper.get_url(build_action["build_link"])

            # Logic from `complete_actions`
            completed_response = self._complete_actions(response.text)
            if completed_response:
                # If an action was completed, we should ideally refetch data and re-run the logic
                # For simplicity now, we'll just log it. A full re-run might be better.
                self.logger.info("[BUILD] Instantly completed a building, state has changed.")

        elif build_action["action"] == "prioritize":
            # Logic to handle prioritization is already in the manager (modifies queue)
            self.logger.info(f"[BUILD] Prioritizing {build_action['building_name']} as per manager decision.")

        # Execute Recruit Action
        if recruit_action and recruit_action["action"] == "recruit":
            self.logger.info(f"[TROOPS] Executing: Recruit {recruit_action['amount']}x {recruit_action['unit']}")
            self.wrapper.get_api_action(
                village_id=self.village_id,
                action="train",
                params={"screen": recruit_action['building'], "mode": "train"},
                data={"units[%s]" % recruit_action['unit']: str(recruit_action['amount'])},
            )

        # Execute Research Action
        if research_action and research_action["action"] == "research":
            self.logger.info(f"[TROOPS] Executing: Research {research_action['unit']}")
            self.wrapper.get_api_action(
                village_id=self.village_id,
                action="research",
                params={"screen": "smith"},
                data={"tech_id": research_action['unit'], "source": self.village_id, "h": self.wrapper.last_h},
            )

        # Snob manager run (needs its own refactoring later, but works for now)
        if self.get_village_config(self.village_id, "snobs") and current_levels.get("snob", 0) > 0:
            if not self.snobman:
                self.snobman = SnobManager(wrapper=self.wrapper, village_id=self.village_id)
                self.snobman.troop_manager = self.units
                self.snobman.resman = self.resman
            self.snobman.wanted = self.get_village_config(self.village_id, "snobs", 0)
            self.snobman.building_level = self.builder.get_level("snob")
            self.snobman.run()

        # Other actions that are not yet refactored
        self.manage_local_resources()
        self.check_forced_peace()
        self.run_farming()
        self.do_gather()
        self.go_manage_market()

        self.set_cache_vars()
        self.logger.info("[SYSTEM] Village cycle done.")

        # Reporting
        self.wrapper.reporter.report(self.village_id, "TWB_POST_RESOURCE", str(self.resman.actual))
        self.wrapper.reporter.add_data(self.village_id, "village.resources", json.dumps(self.resman.actual))
        self.wrapper.reporter.add_data(self.village_id, "village.buildings", json.dumps(self.builder.levels))
        # self.wrapper.reporter.add_data(self.village_id, "village.troops", json.dumps(self.units.total_troops))
        self.wrapper.reporter.add_data(self.village_id, "village.config", json.dumps(vdata))


    def get_quests(self):
        result = Extractor.get_quests(self.wrapper.last_response)
        if result:
            qres = self.wrapper.get_api_action(
                action="quest_complete",
                village_id=self.village_id,
                params={"quest": result, "skip": "false"},
            )
            if qres:
                self.logger.info("[SYSTEM] Completed quest: %s", str(result))
                return True
        self.logger.debug("[SYSTEM] No completed quests found.")
        return False

    def get_quest_rewards(self):
        result = self.wrapper.get_api_data(
            action="quest_popup",
            village_id=self.village_id,
            params={"screen": 'new_quests', "tab": "main-tab", "quest": 0},
        )
        if result is None:
            self.logger.warning("[SYSTEM] Failed to fetch quest reward data from API.")
            return False
        # The data is escaped for JS, so unescape it before sending it to the extractor.
        rewards = Extractor.get_quest_rewards(decode(result["response"]["dialog"], 'unicode-escape'))
        for reward in rewards:
            # First check if there is enough room for storing the reward
            for t_resource in reward["reward"]:
                if self.resman.storage - self.resman.actual[t_resource] < reward["reward"][t_resource]:
                    self.logger.info("[SYSTEM] Not enough room to store the %s part of the reward", t_resource)
                    return False

            qres = self.wrapper.post_api_data(
                action="claim_reward",
                village_id=self.village_id,
                params={"screen": "new_quests"},
                data={"reward_id": reward["id"]}
            )
            if qres:
                if not qres['response']:
                    self.logger.debug("[SYSTEM] Error getting reward! %s", qres)
                    return False
                else:
                    self.logger.info("[SYSTEM] Claimed quest reward: %s", str(reward))
                    for t_resource in reward["reward"]:
                        self.resman.actual[t_resource] += reward["reward"][t_resource]

        self.logger.debug("[SYSTEM] No (more) quest rewards to claim.")
        return len(rewards) > 0

    def set_cache_vars(self):
        village_entry = {
            "name": self.game_data["village"]["name"],
            "public": self.area.in_cache(self.village_id) if self.area else None,
            "resources": self.resman.actual,
            "required_resources": self.resman.requested,
            "available_troops": self.units.troops if self.units else {},
            "building_levels": self.builder.levels if self.builder else {},
            "building_queue_from_template": self.builder.queue if self.builder else [],
            "troops": self.units.total_troops if self.units else {},
            "under_attack": self.def_man.under_attack if self.def_man else False,
            "last_run": int(time.time()),
            # --- STRATEGY & INTENT ---
            "strategy_role": self.strategy.get('role', 'Statisch') if self.strategy else 'Statisch',
            "intent_building": self.current_builder_intent,
            "intent_troops": self.current_troops_intent,
            # --- ACTION PLAN ---
            "action_plan_build": self.builder.queue if self.builder else [],
            "action_plan_recruit": self.units.wanted if self.units else {},
            "action_plan_research": self.units.wanted_levels if self.units else {}
        }

        # Add live building queue from game
        main_data_text = self.wrapper.get_action(village_id=self.village_id, action="main").text
        village_entry["building_queue_live"] = self.builder.get_build_queue(main_data_text) if self.builder else []


        if self.attack and self.attack.last_farm_bag_state:
            current = self.attack.last_farm_bag_state.get("current")
            maximum = self.attack.last_farm_bag_state.get("max")
            if current is not None and maximum is not None:
                pct = (current / maximum) if maximum else 0
                village_entry["farm_bag"] = {
                    "current": current,
                    "max": maximum,
                    "pct": pct,
                }
            else:
                village_entry["farm_bag"] = None
        else:
            village_entry["farm_bag"] = None
        FileManager.save_json_file(village_entry, f"cache/managed/{self.village_id}.json")
