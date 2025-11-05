package game

import (
	"fmt"
	"math"
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

// GameState represents a snapshot of the village's state for heuristic evaluation.
type GameState struct {
	Resources       Resources
	BuildingLevels  map[string]int
	TroopLevels     map[string]int
	ResourceIncome  Resources
}

// Solver is the core decision-making engine.
type Solver struct {
	village         *Village
	actionGenerator *ActionGenerator
}

// NewSolver creates a new Solver.
func NewSolver(village *Village) *Solver {
	return &Solver{
		village:         village,
		actionGenerator: NewActionGenerator(),
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
			score := evaluateState(&futureState)
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
	}

	return futureState
}


// evaluateState scores a game state based on a weighted combination of metrics.
func evaluateState(state *GameState) float64 {
	// Weights for different components of the score
	economicWeight := 1.0
	strategicWeight := 2.0
	militaryWeight := 1.5

	economicScore := float64(state.ResourceIncome.Wood + state.ResourceIncome.Stone + state.ResourceIncome.Iron)
	strategicScore := calculateStrategicScore(state.BuildingLevels)
	militaryScore := calculateMilitaryScore(state.TroopLevels)

	return economicScore*economicWeight + strategicScore*strategicWeight + militaryScore*militaryWeight
}

// calculateStrategicScore scores progress towards the "Noble Rush" goal.
func calculateStrategicScore(buildingLevels map[string]int) float64 {
	score := 0.0
	score += math.Min(float64(buildingLevels["main"])/20.0, 1.0) * 200 // Heavily prioritize main building
	score += math.Min(float64(buildingLevels["smith"])/20.0, 1.0) * 100
	score += math.Min(float64(buildingLevels["market"])/10.0, 1.0) * 50 // Significantly decreased weight
	score += math.Min(float64(buildingLevels["snob"])/1.0, 1.0) * 500 // Highest weight for the academy
	return score
}

// calculateMilitaryScore scores the total population of troops.
func calculateMilitaryScore(troopLevels map[string]int) float64 {
	// This is a placeholder. A more advanced implementation would consider
	// the type of troops, their combat strength, and their purpose.
	totalPop := 0
	for _, count := range troopLevels {
		totalPop += count
	}
	return float64(totalPop)
}
