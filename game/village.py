import json
import logging
import time
from codecs import decode
from datetime import datetime

from core.configmanager import ConfigManager
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
from game.gamestate import GameState
from game.solver import MultiActionPlanner
from game.action_generator import ActionGenerator
from core.exceptions import *
from game.farm_optimizer import FarmOptimizer
from game.scavenge_optimizer import ScavengeOptimizer
from game.resource_allocation import ResourceAllocationSolver


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
    forced_peace = False
    forced_peace_today_start = None
    disabled_units = []
    hoard_mode = False
    hoard_for_research = False
    _priority_research_unaffordable = False
    # --- PERFORMANCE (POINT 2) ---
    overview_html = None
    # --- END PERFORMANCE ---

    twp = TwStats()

    def __init__(self, village_id=None, wrapper=None, config_manager=None):
        self.village_id = village_id
        self.wrapper = wrapper
        if config_manager:
            self.config_manager = config_manager
        else:
            try:
                self.config_manager = ConfigManager()
            except FileNotFoundError:
                # This can happen in tests, where config.json might not exist.
                self.config_manager = None
        self.current_unit_entry = None
        self.status = "Initializing..."
        self.game_state_model = GameState(village_id=village_id)
        # Initialize the AI components
        self.action_generator = ActionGenerator()
        self.solver = MultiActionPlanner(self.action_generator)
        self.farm_optimizer = None
        self.scavenge_optimizer = None
        self.resource_solver = None


    def get_config(self, section, parameter, default=None):
        if section not in self.config:
            self.logger.warning("Configuration section %s does not exist!", section)
            return default
        if parameter not in self.config[section]:
            self.logger.warning(
                "Configuration parameter %s:%s does not exist!", section, parameter
            )
            return default
        return self.config[section][parameter]

    def get_village_config(self, village_id, parameter, default=None):
        if village_id not in self.config["villages"]:
            return default
        vdata = self.config["villages"][village_id]
        if parameter not in vdata:
            self.logger.warning(
                "Village %s configuration parameter %s does not exist!",
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
            # --- PERFORMANCE (POINT 2) ---
            self.overview_html = data.text
            # --- END PERFORMANCE ---

        if self.game_data:
            if not self.village_id:
                self.village_id = str(self.game_data["village"]["id"])

            self.logger = logging.getLogger(
                "Village %s" % self.game_data["village"]["name"]
            )
            self.logger.info("Read game state for village")

            self.wrapper.reporter.report(
                self.village_id,
                "TWB_START",
                "Starting run for village: %s" % self.game_data["village"]["name"],
            )
        else:
            self.logger = logging.getLogger(f"Village {self.village_id}")
            self.logger.error("Could not read game state for village")

        if (
                self.village_set_name
                and self.game_data and "village" in self.game_data
                and self.game_data["village"]["name"] != self.village_set_name
        ):
            self.logger.name = f"Village {self.village_set_name}"

        # Return raw response object for setup_defence_manager
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

        # --- PERFORMANCE (POINT 2) ---
        # Pass cached game_data
        self.resman.update(self.game_data)
        self.resman.update_game_state(self.game_state_model, self.game_data)
        # --- END PERFORMANCE ---

        self.wrapper.reporter.report(
            self.village_id, "TWB_PRE_RESOURCE", str(self.resman.actual)
        )

        if not self.rep_man:
            self.rep_man = ReportManager(
                wrapper=self.wrapper, village_id=self.village_id
            )

        # --- PERFORMANCE (POINT 2) ---
        # Pass cached overview_html to avoid re-fetching page 0
        self.rep_man.read(full_run=False, overview_html=self.overview_html)
        # --- END PERFORMANCE ---

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

        # --- PERFORMANCE (POINT 2) ---
        # Pass cached overview_html
        self.def_man.update(
            self.overview_html,
            with_defence=self.get_config(
                section="units", parameter="manage_defence", default=False
            ),
        )
        # --- END PERFORMANCE ---

        if self.def_man.under_attack and not self.last_attack:
            self.logger.warning("Village under attack!")
            self.wrapper.reporter.report(
                self.village_id,
                "TWB_ATTACK",
                "Village: %s under attack" % self.game_data["village"]["name"],
                )
        self.last_attack = self.def_man.under_attack

    def run_quest_actions(self, config):
        if self.get_config(section="world", parameter="quests_enabled", default=False):
            if self.get_quests():
                self.logger.info("There where completed quests, re-running function")
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Completed quest"
                )
                return self.run(config=config)

            if self.get_quest_rewards():
                self.wrapper.reporter.report(
                    self.village_id, "TWB_QUEST", "Collected quest reward(s)"
                )

    def units_get_template(self):
        """
        Fetches the unit template
        """
        if not self.units:
            self.units = TroopManager(wrapper=self.wrapper, village_id=self.village_id, village=self)
            self.units.resman = self.resman
        self.units.max_batch_size = self.get_config(
            section="units", parameter="batch_size", default=25
        )

        # set village templates
        unit_config = self.get_village_config(
            self.village_id, parameter="units", default=None
        )
        if not unit_config:
            self.logger.warning(
                "Village %s does not have 'units' config override!", self.village_id
            )
            unit_config = self.get_config(
                section="units", parameter="default", default="basic"
            )
        try:
            template_content = TemplateManager.get_template(
                category="troops", template=unit_config, output_json=True
            )
            if isinstance(template_content, dict) and "template_data" in template_content:
                self.units.template = template_content["template_data"]
                self.unit_template_full = template_content
            else:
                # Legacy support
                self.units.template = template_content
                self.unit_template_full = {"template_data": template_content}

        except Exception as e:
            self.logger.error(
                "Looks like the unit template file %s is either missing or corrupted: %s", unit_config, e
            )
            raise InvalidUnitTemplateException

    def run_builder(self):
        """
        Run building construction actions
        """
        if self.hoard_mode:
            self.logger.info("Hoard mode is active, skipping building.")
            return

        if not self.builder:
            self.builder = BuildingManager(
                wrapper=self.wrapper, village_id=self.village_id
            )
            self.builder.resman = self.resman

        self.build_config = self.get_village_config(
            self.village_id, parameter="building", default=None
        )
        if self.build_config is False:
            self.logger.debug("Builder is disabled for village %s", self.village_id)
            return
        if not self.build_config:
            self.logger.warning(
                "Village %s does not have 'building' config override!", self.village_id
            )
            self.build_config = self.get_config(
                section="building", parameter="default", default="purple_predator"
            )

        new_template_data = TemplateManager.get_template(
            category="builder", template=self.build_config, output_json=True
        )

        # Handle JSON (new) vs. legacy string/list formats
        if isinstance(new_template_data, dict):
            # New JSON format
            self.build_template_full = new_template_data
            template_lines = new_template_data.get("template_data", [])
            self.builder.mode = new_template_data.get("mode", "linear")
        else:
            # Legacy format
            self.build_template_full = {"template_data": new_template_data}
            template_lines = new_template_data.splitlines() if isinstance(new_template_data, str) else new_template_data
            self.builder.mode = "dynamic" if "final" in self.build_config else "linear"


        if not template_lines:
            self.logger.error(f"Building template '{self.build_config}' not found or is empty.")
            return

        # Configure builder based on mode
        if self.builder.mode == "dynamic":
            self.builder.target_levels = {line.split(':')[0]: int(line.split(':')[1]) for line in template_lines if ':' in line and not line.startswith('#')}
        else: # linear
            self.builder.queue = [line for line in template_lines if ':' in line and not line.startswith('#')]

        self.builder.raw_template = template_lines

        self.builder.max_lookahead = self.get_config(
            section="building", parameter="max_lookahead", default=2
        )
        self.builder.max_queue_len = self.get_config(
            section="building", parameter="max_queued_items", default=2
        )

        # Pass troop queue status to the builder for dynamic mode
        self.builder.troop_queue_status = self.units.get_queue_times()

        self.builder.start_update(
            overview_game_data=self.game_data,
            overview_html=self.overview_html,
            build=self.get_config(
                section="building", parameter="manage_buildings", default=True
            ),
            set_village_name=self.village_set_name,
        )
        self.builder.update_game_state(self.game_state_model)

    def run_snob_recruit(self):
        """
        Uses the snob to mint coins, store resources and recruit snobs
        """
        if (
                self.get_village_config(self.village_id, parameter="snobs", default=None)
                and self.builder.get_level("snob") > 0
        ):
            if not self.snobman:
                self.snobman = SnobManager(
                    wrapper=self.wrapper, village_id=self.village_id
                )
                self.snobman.troop_manager = self.units
                self.snobman.resman = self.resman
            self.snobman.wanted = self.get_village_config(
                self.village_id, parameter="snobs", default=0
            )
            self.snobman.building_level = self.builder.get_level("snob")
            self.snobman.run()

            if self.snobman.is_incomplete:
                self.logger.info("Activating hoard mode to save for nobleman.")
                self.hoard_mode = True
            else:
                self.hoard_mode = False

    def do_recruit(self):
        """
        Recruits new units
        """
        if self.hoard_mode:
            self.logger.info("Hoard mode is active, skipping recruitment.")
            return

        if self.get_config(section="units", parameter="recruit", default=False):
            self.units.can_fix_queue = self.get_config(
                section="units", parameter="remove_manual_queued", default=False
            )
            self.units.randomize_unit_queue = self.get_config(
                section="units", parameter="randomize_unit_queue", default=True
            )
            # Automated Prioritization Logic
            # With the new smart fallback, we can simplify this.
            # We'll still prioritize snobs, but the builder/recruitment lock is now handled by can_build.
            if self.snobman and self.snobman.is_incomplete:
                self.logger.info("Automated Priority: Pausing recruitment to save for nobleman.")
                # Clear any existing recruitment resource requests
                for x in list(self.resman.requested.keys()):
                    if "recruitment_" in x:
                        self.resman.requested.pop(f"{x}", None)
                return

            # If neither of the above conditions are met, proceed with recruitment.
            for building in self.units.wanted:
                    if not self.builder.get_level(building):
                        self.logger.debug(
                            "Recruit of %s will be ignored because building is not (yet) available", building
                        )
                        continue
                    recruited = self.units.start_update(building, self.disabled_units)

    def check_forced_peace(self):
        """
        Checks if farming is disabled for the current time
        """
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
                self.logger.debug("Currently in a forced peace time! No attacks will be send.")
                self.forced_peace = True
                break

    def set_unit_wanted_levels(self):
        """
        Fetches wanted units for the current buildings
        """
        self.current_unit_entry = self.units.get_template_action(self.builder.levels)

        if self.current_unit_entry and 'build' in self.current_unit_entry and self.units.wanted != self.current_unit_entry["build"]:
            # update wanted units if template has changed
            self.logger.info(
                "%s as wanted units for current village", str(self.current_unit_entry["build"])
            )
            self.units.wanted = self.current_unit_entry["build"]

        if self.units.wanted_levels != {}:
            # Remove disabled units
            for disabled in self.disabled_units:
                self.units.wanted_levels.pop(disabled, None)
            self.logger.info(
                "%s as wanted upgrades for current village", str(self.units.wanted_levels)
            )

    def run_unit_upgrades(self):
        """
        Uses smith to research or upgrade units
        """
        if (
                self.get_config(section="units", parameter="upgrade", default=False)
                and self.units.wanted_levels != {}
        ):
            self.units.attempt_upgrade()

    def manage_local_resources(self):
        to_dell = []
        for x in self.resman.requested:
            if all(res == 0 for res in self.resman.requested[x].values()):
                # remove empty requests!
                to_dell.append(x)

        for x in to_dell:
            self.resman.requested.pop(x)

        self.logger.debug("Current resources: %s", str(self.resman.actual))
        self.logger.debug("Requested resources: %s", str(self.resman.requested))

    def set_farm_options(self):
        """
        Sets various options for farming management
        """
        self.attack.target_high_points = self.get_config(
            section="farms", parameter="attack_higher_points", default=False
        )
        self.attack.farm_minpoints = self.get_config(
            section="farms", parameter="min_points", default=24
        )
        self.attack.farm_maxpoints = self.get_config(
            section="farms", parameter="max_points", default=1080
        )
        self.attack.farm_radius = self.get_config(
            section="farms", parameter="search_radius", default=50
        )
        self.attack.farm_default_wait = self.get_config(
            section="farms", parameter="default_away_time", default=1200
        )
        self.attack.farm_high_prio_wait = self.get_config(
            section="farms", parameter="full_loot_away_time", default=1800
        )
        self.attack.farm_low_prio_wait = self.get_config(
            section="farms", parameter="low_loot_away_time", default=7200
        )
        self.attack.scout_farm_amount = self.get_config(
            section="farms", parameter="farm_scout_amount", default=5
        )
        farm_limit_enabled = self.get_config(
            section="world", parameter="farm_bag_limit_enabled", default=False
        )
        override = self.get_village_config(
            self.village_id, parameter="farm_bag_limit_override", default=None
        )
        if override is not None:
            farm_limit_enabled = override
        self.attack.farm_bag_limit_enabled = bool(farm_limit_enabled)
        self.attack.farm_bag_block_scouts = self.get_config(
            section="world", parameter="farm_bag_block_scouts", default=True
        )
        margin = self.get_config(
            section="bot", parameter="farm_bag_limit_margin", default=0.02
        )
        try:
            margin = float(margin)
        except (TypeError, ValueError):
            margin = 0.02
        self.attack.farm_bag_limit_margin = max(0.0, min(0.2, margin))

    def go_manage_market(self):
        """
        Manages the market
        """
        if self.get_config(
                section="market", parameter="auto_trade", default=False
        ) and self.builder.get_level("market"):
            self.logger.info("Managing market")
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

    def run(self, config=None, first_run=False):
        # setup and check if village still exists / is accessible
        self.config = config
        self.wrapper.delay = self.get_config(
            section="bot", parameter="delay_factor", default=1.0
        )

        self.status = "Reading game state..."
        data = self.village_init()

        if not self.game_data:
            self.logger.error(
                "Error reading game data for village %s", self.village_id
            )
            self.status = "Error: Could not read game state."
            self.set_cache_vars()
            raise VillageInitException

        self.set_world_config()

        if not self.get_config(section="villages", parameter=self.village_id):
            raise VillageInitException

        vdata = self.get_config(section="villages", parameter=self.village_id)
        if not self.get_village_config(
                self.village_id, parameter="managed", default=False
        ):
            self.status = "Idle: Village not managed."
            self.set_cache_vars()
            return False
        if not self.game_data:
            raise InvalidGameStateException

        self.status = "Updating resources and reports..."
        self.update_pre_run()
        self.resman.calculate_income(self.game_data)

        self.status = "Checking for incoming attacks..."
        self.setup_defence_manager(data=data)
        if self.def_man.under_attack:
            self.status = "Under Attack!"
        else:
            self.status = "Idle"

        self.run_quest_actions(config=config)

        # The TroopManager needs to be initialized to get troop queue times
        self.units_get_template()

        # The BuildingManager needs to be run to populate building levels
        self.status = "Managing building queue..."
        self.run_builder()

        # Update total troop counts before making recruitment decisions
        self.units.update_totals(self.game_data, self.overview_html)
        self.units.update_game_state(self.game_state_model)


        # --- New Optimizing Agent Logic ---
        if not self.area:
            self.area = Map(wrapper=self.wrapper, village_id=self.village_id)
        self.area.get_map()
        if not self.attack:
            self.attack = AttackManager(
                wrapper=self.wrapper,
                village_id=self.village_id,
                troopmanager=self.units,
                map=self.area,
            )
            self.attack.repman = self.rep_man

        if not self.farm_optimizer:
            self.farm_optimizer = FarmOptimizer(self.units, self.rep_man, self.area)
        if not self.scavenge_optimizer:
            self.scavenge_optimizer = ScavengeOptimizer(self.units)
        if not self.resource_solver:
            self.resource_solver = ResourceAllocationSolver(self.farm_optimizer, self.scavenge_optimizer)

        farm_targets = self.attack.get_targets()
        scavenge_options = Extractor.village_data(self.wrapper.get_url(f"game.php?village={self.village_id}&screen=place&mode=scavenge"))

        marginal_incomes = self.resource_solver.calculate_unified_marginal_income(self.units.troops, farm_targets, scavenge_options)

        self.action_generator.update_data(
            building_templates=self.build_template_full,
            troop_templates=self.unit_template_full,
            building_costs=self.builder.costs,
            recruit_costs=self.units.recruit_data,
            research_costs=self.units._smith_data,
        )
        planned_actions = self.solver.plan_actions(self.game_state_model, marginal_incomes)

        if planned_actions:
            self.logger.info(f"Optimal plan: {[a.name for a in planned_actions]}")
            for action in planned_actions:
                cost = action.cost()
                if all(self.resman.actual.get(res, 0) >= cost.get(res, 0) for res in cost):
                    self.logger.info(f"Executing planned action: {action.name}")
                    if self.execute_action(action):
                        for res, amount in cost.items():
                            self.resman.actual[res] -= amount
                    else:
                        self.logger.warning(f"Failed to execute planned action: {action.name}. Stopping.")
                        break
                else:
                    self.logger.warning(f"Could not afford action '{action.name}'. Stopping.")
                    break
        else:
            self.logger.info("No optimal actions could be determined in this cycle.")

        # --- Resource Gathering ---
        prioritize_gathering = self.get_village_config(
            self.village_id, parameter="prioritize_gathering", default=False
        )

        if not self.forced_peace and self.units.can_attack:
            if prioritize_gathering:
                self.logger.info("Prioritizing gathering: executing scavenging-only plan.")
                plan = self.scavenge_optimizer.create_optimal_plan(
                    self.units.troops, scavenge_options
                )
                if plan:
                    self.logger.info(
                        f"Executing optimal scavenging plan with {len(plan)} squads."
                    )
                    for scavenge_cmd in plan:
                        self._execute_scavenge_squad(
                            scavenge_cmd["option_id"], scavenge_cmd["troops"]
                        )
            else:
                strategy, plan = self.resource_solver.determine_best_strategy(
                    self.units.troops, farm_targets, scavenge_options
                )
                if strategy == "farming":
                    self.logger.info(
                        f"Executing optimal farming plan with {len(plan)} attacks."
                    )
                    for attack_cmd in plan:
                        self.attack.attack(
                            attack_cmd["target_id"], troops=attack_cmd["troops"]
                        )
                elif strategy == "scavenging":
                    self.logger.info(
                        f"Executing optimal scavenging plan with {len(plan)} squads."
                    )
                    for scavenge_cmd in plan:
                        self._execute_scavenge_squad(
                            scavenge_cmd["option_id"], scavenge_cmd["troops"]
                        )

        self.status = "Managing market..."
        self.go_manage_market()

        self.status = "Idle"
        self.set_cache_vars()
        self.logger.info("Village cycle done, returning to overview")
        self.wrapper.reporter.report(
            self.village_id, "TWB_POST_RESOURCE", str(self.resman.actual)
        )
        self.wrapper.reporter.add_data(
            self.village_id,
            data_type="village.resources",
            data=json.dumps(self.resman.actual),
        )
        self.wrapper.reporter.add_data(
            self.village_id,
            data_type="village.buildings",
            data=json.dumps(self.builder.levels),
        )
        self.wrapper.reporter.add_data(
            self.village_id,
            data_type="village.troops",
            data=json.dumps(self.units.total_troops),
        )
        self.wrapper.reporter.add_data(
            self.village_id, data_type="village.config", data=json.dumps(vdata)
        )

    def execute_action(self, action):
        """
        Executes a given action.
        """
        if action.name.startswith("Build"):
            return self.builder._build(action.building)
        elif action.name.startswith("Recruit"):
            building = self.units.unit_building.get(action.unit)
            if building:
                return self.units.recruit(action.unit, action.amount, building=building)
        elif action.name.startswith("Research"):
            return self.units.attempt_research(action.unit)
        return False

    def _execute_scavenge_squad(self, option_id, troops):
        """
        Sends a single squad to a scavenging mission.
        """
        payload = {
            "squad_requests[0][village_id]": self.village_id,
            "squad_requests[0][option_id]": str(option_id),
            "squad_requests[0][use_premium]": "false",
        }
        total_carry = 0
        for unit, count in troops.items():
            payload[f"squad_requests[0][candidate_squad][unit_counts][{unit}]"] = str(count)
            total_carry += self.scavenge_optimizer.unit_capacity.get(unit, 0) * count

        payload["squad_requests[0][candidate_squad][carry_max]"] = str(total_carry)
        payload["h"] = self.wrapper.last_h

        self.wrapper.get_api_action(
            action="send_squads",
            params={"screen": "scavenge_api"},
            data=payload,
            village_id=self.village_id,
        )
        self.logger.info(f"Sent scavenge squad to option {option_id} with troops: {troops}")


    def calculate_resource_forecast(self):
        """
        Calculates the total resource cost of all planned actions.
        """
        forecast = {'wood': 0, 'clay': 0, 'iron': 0}
        if not self.builder or not self.units:
            return forecast

        # Building costs
        if self.builder.costs:
            planned_buildings = self.builder.get_planned_actions()
            for action in planned_buildings:
                # Expected format: "Build Main to level 2"
                parts = action.split()
                if len(parts) >= 2 and parts[0] == "Build":
                    building_name = parts[1].lower()
                    if building_name in self.builder.costs:
                        cost = self.builder.costs[building_name]
                        forecast['wood'] += cost.get('wood', 0)
                        forecast['clay'] += cost.get('stone', 0)
                        forecast['iron'] += cost.get('iron', 0)

        # Recruitment costs
        if self.units.recruit_data:
            planned_recruits = self.units.get_planned_actions(self.disabled_units)
            for action in planned_recruits:
                # Expected format: "Recruit 10 Spear (Target: 100)"
                parts = action.split()
                if len(parts) >= 3 and parts[0] == "Recruit":
                    amount = int(parts[1])
                    unit_name = parts[2].lower()
                    if unit_name in self.units.recruit_data:
                        cost = self.units.recruit_data[unit_name]
                        forecast['wood'] += cost.get('wood', 0) * amount
                        forecast['clay'] += cost.get('stone', 0) * amount
                        forecast['iron'] += cost.get('iron', 0) * amount

        return forecast

    def get_quests(self):
        result = Extractor.get_quests(self.wrapper.last_response)
        if result:
            qres = self.wrapper.get_api_action(
                action="quest_complete",
                village_id=self.village_id,
                params={"quest": result, "skip": "false"},
            )
            if qres:
                self.logger.info("Completed quest: %s", str(result))
                return True
        self.logger.debug("There where no completed quests")
        return False

    def get_quest_rewards(self):
        result = self.wrapper.get_api_data(
            action="quest_popup",
            village_id=self.village_id,
            params={"screen": 'new_quests', "tab": "main-tab", "quest": 0},
        )
        if result is None:
            self.logger.warning("Failed to fetch quest reward data from API")
            return False
        # The data is escaped for JS, so unescape it before sending it to the extractor.
        rewards = Extractor.get_quest_rewards(decode(result["response"]["dialog"], 'unicode-escape'))
        for reward in rewards:
            # First check if there is enough room for storing the reward
            for t_resource in reward["reward"]:
                if self.resman.storage - self.resman.actual[t_resource] < reward["reward"][t_resource]:
                    self.logger.info("Not enough room to store the %s part of the reward", t_resource)
                    return False

            qres = self.wrapper.post_api_data(
                action="claim_reward",
                village_id=self.village_id,
                params={"screen": "new_quests"},
                data={"reward_id": reward["id"]}
            )
            if qres:
                if not qres['response']:
                    self.logger.debug("Error getting reward! %s", qres)
                    return False
                else:
                    self.logger.info("Got quest reward: %s", str(reward))
                    for t_resource in reward["reward"]:
                        self.resman.actual[t_resource] += reward["reward"][t_resource]

        self.logger.debug("There where no (more) quest rewards")
        return len(rewards) > 0

    def set_cache_vars(self):
        village_entry = {
            "name": self.game_data["village"]["name"] if self.game_data else self.village_set_name,
            "public": self.area.in_cache(self.village_id) if self.area else None,
            "resources": self.resman.actual if self.resman else {},
            "required_resources": self.resman.requested if self.resman else {},
            "available_troops": self.units.troops if self.units else {},
            "building_levels": self.builder.levels if self.builder else {},
            "building_queue": self.builder.queue if self.builder else [],
            "troops": self.units.total_troops if self.units else {},
            "under_attack": self.def_man.under_attack if self.def_man else False,
            "last_run": int(time.time()),
            "status": self.status,
            "planned_actions": (self.builder.get_planned_actions() or []) + (self.units.get_planned_actions(self.disabled_units) or []) if self.builder and self.units else [],
            "income": self.resman.income if self.resman else {},
            "forecast": self.calculate_resource_forecast(),
        }
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

    def _check_and_handle_template_switch(self):
        """
        Checks both unit and building templates for a 'next_template' directive
        and updates the village config if the condition is met.
        """
        # Check Unit Template
        if hasattr(self, 'unit_template_full') and 'next_template' in self.unit_template_full:
            self._evaluate_and_switch('units', self.unit_template_full['next_template'])

        if hasattr(self, 'build_template_full') and 'next_template' in self.build_template_full:
            # In linear mode, the queue must be empty to switch
            if self.builder.mode == 'linear' and not self.builder.queue:
                self._evaluate_and_switch('building', self.build_template_full['next_template'])
            # In dynamic mode, all target levels must be met
            elif self.builder.mode == 'dynamic':
                all_met = all(self.builder.get_level(b) >= lv for b, lv in self.builder.target_levels.items())
                if all_met:
                    self._evaluate_and_switch('building', self.build_template_full['next_template'])

    def _evaluate_and_switch(self, config_key, switch_info):
        """
        Evaluates a template switch condition and executes it if met.
        """
        condition = switch_info.get('condition', {})
        target_building = condition.get('building')
        target_level = condition.get('level')
        new_template = switch_info.get('template_name')

        if not new_template:
            self.logger.debug(f"Invalid 'next_template' definition for {config_key}: missing 'template_name'.")
            return

        # If condition is not specified, switch immediately
        if not condition or not all([target_building, target_level]):
            self.logger.info(
                f"Conditionless template switch for '{config_key}'. Switching to '{new_template}'."
            )
            self.config_manager.update_village_config(self.village_id, config_key, new_template)
            return

        current_level = self.builder.get_level(target_building)
        if current_level >= target_level:
            self.logger.info(
                f"Condition met for '{config_key}' template switch: "
                f"{target_building} level is {current_level} (>= {target_level}). "
                f"Switching to '{new_template}'."
            )
            self.config_manager.update_village_config(
                self.village_id, config_key, new_template
            )
