package game

import (
	"fmt"
	"time"
	"twb-go/core"
)

var timeNow = time.Now

// Village represents a single village and orchestrates the bot's logic.
type Village struct {
	ID                     string
	Wrapper                core.WebWrapperInterface
	ConfigManager          *core.ConfigManager
	ResourceManager        *ResourceManager
	BuildingManager        *BuildingManager
	TroopManager           *TroopManager
	AttackManager          *AttackManager
	DefenceManager         *DefenceManager
	TemplateManager        *TemplateManager
	StrategyManager        *StrategyManager
	GameMap                *Map
	Solver                 *Solver
	ForcedPeace            bool
	ForcedPeaceToday       bool
	ForcedPeaceTodayStart time.Time
	logger                 func(string)
	LastAction             Action
}

// NewVillage creates a new Village.
func NewVillage(id string, wrapper core.WebWrapperInterface, cm *core.ConfigManager, rm *ResourceManager, bm *BuildingManager, tm *TroopManager, am *AttackManager, dm *DefenceManager, gameMap *Map) (*Village, error) {
	if id == "" {
		return nil, fmt.Errorf("village ID cannot be empty")
	}

	village := &Village{
		ID:              id,
		Wrapper:         wrapper,
		ConfigManager:   cm,
		ResourceManager: rm,
		BuildingManager: bm,
		TroopManager:    tm,
		AttackManager:   am,
		DefenceManager:  dm,
		TemplateManager: NewTemplateManager("templates"),
		StrategyManager: NewStrategyManager(cm),
		GameMap:         gameMap,
		logger:          func(msg string) { fmt.Println(msg) },
	}
	village.Solver = NewSolver(village, &cm.GetConfig().Solver, &cm.GetConfig().Planner)
	return village, nil
}

// Run starts the main loop for the village.
func (v *Village) Run() {
	fmt.Printf("Running village %s\n", v.ID)
	_, err := v.fetchAndupdateState()
	if err != nil {
		fmt.Printf("Error fetching and updating state: %v\n", err)
		return
	}

	// 3. Get next action from solver and execute it
	initialState := v.Solver.createInitialState()
	goal := v.StrategyManager.GenerateGoal(initialState, v.ID)
	action := v.Solver.GetNextAction(goal)
	if action != nil {
		fmt.Printf("Executing action: %s\n", action)
		err := action.Execute(v)
		if err != nil {
			fmt.Printf("Error executing action: %v\n", err)
		}
		v.LastAction = action
	} else {
		fmt.Println("No action to execute.")
	}
}

func (v *Village) fetchAndupdateState() (*core.GameState, error) {
	// 1. Fetch game state
	resp, err := v.Wrapper.GetURL(fmt.Sprintf("game.php?village=%s&screen=overview", v.ID))
	if err != nil {
		return nil, fmt.Errorf("error fetching game state: %w", err)
	}
	overviewBody, err := core.ReadBody(resp)
	if err != nil {
		return nil, fmt.Errorf("error reading response body: %w", err)
	}

	// 2. Update managers with new data
	gameState, err := core.Extractor.GameState(overviewBody)
	if err != nil {
		return nil, fmt.Errorf("error parsing game state: %w", err)
	}
	buildingQueue, err := core.Extractor.BuildingQueue(overviewBody)
	if err != nil {
		return nil, fmt.Errorf("error parsing building queue: %w", err)
	}
	v.BuildingManager.Queue = buildingQueue
	recruitQueues, err := core.Extractor.RecruitQueues(overviewBody)
	if err != nil {
		return nil, fmt.Errorf("error parsing recruit queues: %w", err)
	}
	v.TroopManager.Queue = recruitQueues
	resp, err = v.Wrapper.GetURL(fmt.Sprintf("game.php?village=%s&screen=main", v.ID))
	if err != nil {
		return nil, fmt.Errorf("error fetching game state: %w", err)
	}
	mainBody, err := core.ReadBody(resp)
	if err != nil {
		return nil, fmt.Errorf("error reading response body: %w", err)
	}
	buildingCosts, err := core.Extractor.BuildingCosts(mainBody)
	if err != nil {
		return nil, fmt.Errorf("error parsing building costs: %w", err)
	}
	v.BuildingManager.UpdateBuildingCosts(buildingCosts)
	recruitData := make(map[string]core.UnitCost)
	for _, screen := range []string{"train", "stable", "garage"} {
		resp, err := v.Wrapper.GetURL(fmt.Sprintf("game.php?village=%s&screen=%s", v.ID, screen))
		if err != nil {
			fmt.Printf("Error fetching %s screen: %v\n", screen, err)
			continue
		}
		recruitBody, err := core.ReadBody(resp)
		if err != nil {
			fmt.Printf("Error reading %s screen body: %v\n", screen, err)
			continue
		}
		data, err := core.Extractor.RecruitData(recruitBody)
		if err != nil {
			fmt.Printf("Error parsing %s screen: %v\n", screen, err)
			continue
		}
		for unit, cost := range data {
			recruitData[unit] = cost
		}
	}
	v.TroopManager.UpdateRecruitData(recruitData)
	v.ResourceManager.Update(
		int(gameState.Village.Wood),
		int(gameState.Village.Stone),
		int(gameState.Village.Iron),
		gameState.Village.Pop,
		gameState.Village.PopMax,
	)
	v.BuildingManager.UpdateBuildingLevels(gameState.Village.Buildings)

	units, err := core.Extractor.UnitsInVillage(overviewBody)
	if err == nil {
		v.TroopManager.UpdateTroops(units, false)
	}
	resp, err = v.Wrapper.GetURL(fmt.Sprintf("game.php?village=%s&screen=smith", v.ID))
	if err != nil {
		return nil, fmt.Errorf("error fetching smith screen: %w", err)
	}
	smithBody, err := core.ReadBody(resp)
	if err != nil {
		return nil, fmt.Errorf("error reading smith screen body: %w", err)
	}
	if err := v.TroopManager.UpdateResearchLevels(smithBody); err != nil {
		return nil, fmt.Errorf("error updating research levels: %w", err)
	}
	return gameState, nil
}

// CheckForcedPeace checks if farming is disabled for the current time.
func (v *Village) CheckForcedPeace() {
	config := v.ConfigManager.GetConfig()
	if config == nil {
		return
	}

	v.ForcedPeace = false
	v.ForcedPeaceToday = false

	for _, timePair := range config.Bot.ForcedPeaceTimes {
		start, err := time.Parse("02.01.06 15:04:05", timePair.Start)
		if err != nil {
			continue
		}
		end, err := time.Parse("02.01.06 15:04:05", timePair.End)
		if err != nil {
			continue
		}
		now := timeNow()
		if now.Year() == start.Year() && now.Month() == start.Month() && now.Day() == start.Day() {
			v.ForcedPeaceToday = true
			v.ForcedPeaceTodayStart = start
		}
		if now.After(start) && now.Before(end) {
			v.ForcedPeace = true
			break
		}
	}
}

// SetFarmOptions sets various options for farming management.
func (v *Village) SetFarmOptions() {
	// ... to be implemented
}

// CheckAndHandleTemplateSwitch checks both unit and building templates for a 'next_template' directive
// and updates the village config if the condition is met.
func (v *Village) CheckAndHandleTemplateSwitch() {
	// ... to be implemented
}
