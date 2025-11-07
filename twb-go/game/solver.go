package game

import (
	"fmt"
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
	village    *Village
	aStarSolver *AStarSolver
}

// NewSolver creates a new Solver.
func NewSolver(village *Village, config *core.SolverConfig, plannerConfig *core.PlannerConfig) *Solver {
	actionGenerator := NewActionGenerator(plannerConfig, village.ConfigManager.GetConfig().BuildingPrerequisites, village.BuildingManager.Data, village.TroopManager.Data)
	villageSimulator := NewVillageSimulator(village.BuildingManager.Data, village.TroopManager.Data, village.logger)
	return &Solver{
		village:    village,
		aStarSolver: NewAStarSolver(actionGenerator, villageSimulator),
	}
}

// GetNextAction determines the next best action by finding the optimal plan to reach the given goal.
func (s *Solver) GetNextAction(goal GameState) Action {
	startState := s.createInitialState()

	plan, err := s.aStarSolver.FindOptimalPlan(startState, goal)
	if err != nil {
		s.village.logger(fmt.Sprintf("Error finding optimal plan: %v", err))
		return nil
	}

	if len(plan) > 0 {
		return plan[0]
	}

	return nil
}

func (s *Solver) createInitialState() GameState {
	return GameState{
		Resources:      s.village.ResourceManager.Actual,
		ResourceIncome: s.village.ResourceManager.Income.Total,
		BuildingLevels: s.village.BuildingManager.Levels,
		TroopLevels:    s.village.TroopManager.TotalTroops,
	}
}
