package game

import (
	"fmt"
	"math"
	"twb-go/core"
)

// Action represents a task that can be executed by the bot.
type Action interface {
	Execute(village *Village) error
	GetCost(village *Village) *Resources
	fmt.Stringer
}

// BuildAction represents a building construction or upgrade task.
type BuildAction struct {
	Building string
	Level    int
}

// Execute performs the build action.
func (a *BuildAction) Execute(village *Village) error {
	return village.BuildingManager.ExecuteBuildAction(a)
}

func (a *BuildAction) String() string {
	return fmt.Sprintf("Build %s to level %d", a.Building, a.Level)
}

func (a *BuildAction) GetCost(village *Village) *Resources {
	cost := village.BuildingManager.Costs[a.Building]
	return &Resources{Wood: cost.Wood, Stone: cost.Stone, Iron: cost.Iron, Pop: cost.Pop}
}

// RecruitAction represents a troop recruitment task.
type RecruitAction struct {
	Unit   string
	Amount int
}

// Execute performs the recruit action.
func (a *RecruitAction) Execute(village *Village) error {
	return village.TroopManager.ExecuteRecruitAction(a)
}

func (a *RecruitAction) String() string {
	return fmt.Sprintf("Recruit %d %s", a.Amount, a.Unit)
}

func (a *RecruitAction) GetCost(village *Village) *Resources {
	cost := village.TroopManager.RecruitData[a.Unit]
	return &Resources{Wood: cost.Wood * a.Amount, Stone: cost.Stone * a.Amount, Iron: cost.Iron * a.Amount, Pop: cost.Pop * a.Amount}
}

// FarmAction represents a farming raid task.
type FarmAction struct {
	Target VillageInfo
}

// Execute performs the farm action.
func (a *FarmAction) Execute(village *Village) error {
	_, err := village.AttackManager.SendFarm(a.Target)
	return err
}

func (a *FarmAction) String() string {
	return fmt.Sprintf("Farm village %s", a.Target.ID)
}

func (a *FarmAction) GetCost(village *Village) *Resources {
	// Farming doesn't have a direct resource cost, but it does require troops.
	// We'll represent this as a zero-cost action for now.
	return &Resources{}
}

// GameState represents a snapshot of the village's state for heuristic evaluation.
type GameState struct {
	Resources        Resources
	BuildingLevels   map[string]int
	TroopLevels      map[string]int
	ResourceIncome   Resources
	FarmingIncome    Resources
}

// Solver is the core decision-making engine.
type Solver struct {
	village         *Village
	config          *core.SolverConfig
	actionGenerator *ActionGenerator
}

// NewSolver creates a new Solver.
func NewSolver(village *Village, config *core.SolverConfig, plannerConfig *core.PlannerConfig) *Solver {
	return &Solver{
		village:         village,
		config:          config,
		actionGenerator: NewActionGenerator(plannerConfig, village.ConfigManager.GetConfig().BuildingPrerequisites),
	}
}

// GetNextAction determines the next best action by simulating the outcome of all possible actions.
func (s *Solver) GetNextAction() Action {
	actions := s.actionGenerator.GenerateActions(s.village)

	var bestAction Action
	bestScore := -1.0

	for _, action := range actions {
		cost := action.GetCost(s.village)
		if s.village.ResourceManager.CanAfford(*cost) {
			futureState := s.simulateAction(action)
			score := s.evaluateState(&futureState, action)
			if score > bestScore {
				bestScore = score
				bestAction = action
			}
		}
	}

	return bestAction
}

// simulateAction creates a hypothetical future state by applying an action.
func (s *Solver) simulateAction(action Action) GameState {
	// Create a copy of the current state
	futureState := GameState{
		Resources:       s.village.ResourceManager.Actual,
		BuildingLevels:  make(map[string]int),
		TroopLevels:     make(map[string]int),
		ResourceIncome:  s.village.ResourceManager.Income.Total,
	}
	for k, v := range s.village.BuildingManager.Levels {
		futureState.BuildingLevels[k] = v
	}
	for k, v := range s.village.TroopManager.TotalTroops {
		futureState.TroopLevels[k] = v
	}

	// Apply the action's effects
	cost := action.GetCost(s.village)
	futureState.Resources.Wood -= cost.Wood
	futureState.Resources.Stone -= cost.Stone
	futureState.Resources.Iron -= cost.Iron
	futureState.Resources.Pop -= cost.Pop

	switch a := action.(type) {
	case *BuildAction:
		futureState.BuildingLevels[a.Building]++
	case *RecruitAction:
		futureState.TroopLevels[a.Unit] += a.Amount
	case *FarmAction:
		// This is a placeholder. A real implementation would have a more sophisticated model.
		expectedLoot := 1000
		futureState.FarmingIncome.Wood += expectedLoot / 3
		futureState.FarmingIncome.Stone += expectedLoot / 3
		futureState.FarmingIncome.Iron += expectedLoot / 3
	}

	return futureState
}

// getProduction returns the resource production for a given level.
func getProduction(level int) int {
	if level == 0 {
		return 5 // Base production
	}
	// Simplified production formula based on Tribal Wars' exponential growth.
	return int(30 * math.Pow(1.16314, float64(level-1)))
}

// evaluateState scores a game state based on a weighted combination of metrics.
func (s *Solver) evaluateState(state *GameState, action Action) float64 {
	economicScore := float64(state.ResourceIncome.Wood + state.ResourceIncome.Stone + state.ResourceIncome.Iron + state.FarmingIncome.Wood + state.FarmingIncome.Stone + state.FarmingIncome.Iron)
	strategicScore := calculateStrategicScore(state.BuildingLevels)
	militaryScore := calculateMilitaryScore(state.TroopLevels, s.village.TroopManager.RecruitData)
	roiScore := 0.0

	if buildAction, ok := action.(*BuildAction); ok {
		switch buildAction.Building {
		case "wood", "stone", "iron":
			cost := buildAction.GetCost(s.village)
			totalCost := cost.Wood + cost.Stone + cost.Iron
			if totalCost > 0 {
				oldLevel := s.village.BuildingManager.Levels[buildAction.Building]
				newLevel := state.BuildingLevels[buildAction.Building]
				incomeIncrease := float64(getProduction(newLevel) - getProduction(oldLevel))
				roiScore = (incomeIncrease / float64(totalCost)) * 100 // Reduced multiplier
			}
		}
	} else if farmAction, ok := action.(*FarmAction); ok {
		// A simple heuristic for farming: the value of the raid is the expected loot
		// divided by the travel time.
		// This is a placeholder, a real implementation would have a more sophisticated model.
		distance := s.village.GameMap.GetDist(farmAction.Target.Location)
		travelTime := distance * 10 // Placeholder for travel time calculation
		expectedLoot := 1000        // Placeholder for expected loot
		if travelTime > 0 {
			roiScore = float64(expectedLoot) / travelTime * 100
		}
	}

	return economicScore*s.config.EconomicWeight + strategicScore*s.config.StrategicWeight + militaryScore*s.config.MilitaryWeight + roiScore
}

// calculateStrategicScore scores progress towards the "Noble Rush" goal.
func calculateStrategicScore(buildingLevels map[string]int) float64 {
	score := 0.0
	score += math.Min(float64(buildingLevels["main"])/20.0, 1.0) * 300 // Further increased weight
	score += math.Min(float64(buildingLevels["smith"])/20.0, 1.0) * 100
	score += math.Min(float64(buildingLevels["market"])/10.0, 1.0) * 50
	score += math.Min(float64(buildingLevels["snob"])/1.0, 1.0) * 500
	return score
}

// calculateMilitaryScore scores the total population of troops.
func calculateMilitaryScore(troopLevels map[string]int, recruitData map[string]UnitCost) float64 {
	totalPop := 0
	for unit, count := range troopLevels {
		if data, ok := recruitData[unit]; ok {
			totalPop += count * data.Pop
		}
	}
	return float64(totalPop)
}
