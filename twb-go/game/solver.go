package game

import (
	"fmt"
	"twb-go/core"
	"time"
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

type ActionGeneratorInterface interface {
	GenerateActions(village *Village) []Action
}

// Solver is the core decision-making engine.
type Solver struct {
	village         *Village
	config          *core.SolverConfig
	actionGenerator ActionGeneratorInterface
	planGenerator   *PlanGenerator
}

// NewSolver creates a new Solver.
func NewSolver(village *Village, config *core.SolverConfig, plannerConfig *core.PlannerConfig) *Solver {
	return &Solver{
		village:         village,
		config:          config,
		actionGenerator: NewActionGenerator(plannerConfig, village.ConfigManager.GetConfig().BuildingPrerequisites),
		planGenerator:   NewPlanGenerator(village.TroopManager.Data, village.BuildingManager.Data),
	}
}

// GetNextAction determines the next best action by finding the fastest plan to recruit a nobleman.
func (s *Solver) GetNextAction() Action {
	possibleNextActions := s.actionGenerator.GenerateActions(s.village)
	var bestPlan []Action
	var shortestTime time.Duration

	for _, nextAction := range possibleNextActions {
		if _, ok := nextAction.(*BuildAction); !ok {
			continue // For now, only consider build actions as the next step
		}

		hypotheticalVillage := s.createHypotheticalVillage(nextAction)
		plan := s.planGenerator.GeneratePlan("adelsgeschlecht", hypotheticalVillage.BuildingManager.Levels)
		fullPlan := append([]Action{nextAction}, plan...)

		simulator := NewVillageSimulator(s.village.BuildingManager.Data, s.village.TroopManager.Data, s.village.logger)
		totalTime, err := simulator.Simulate(s.village, fullPlan)
		if err != nil {
			s.village.logger(fmt.Sprintf("Simulation error for plan starting with '%s': %v", nextAction, err))
			continue
		}

		s.village.logger(fmt.Sprintf("Plan starting with '%s' takes %v", nextAction, totalTime))
		if shortestTime == 0 || totalTime < shortestTime {
			shortestTime = totalTime
			bestPlan = fullPlan
		}
	}

	if len(bestPlan) > 0 {
		return bestPlan[0]
	}

	return nil
}

// createHypotheticalVillage creates a copy of the village with a build action applied.
func (s *Solver) createHypotheticalVillage(action Action) *Village {
	hypotheticalVillage := &Village{
		BuildingManager: &BuildingManager{
			Levels: make(map[string]int),
		},
	}
	for b, l := range s.village.BuildingManager.Levels {
		hypotheticalVillage.BuildingManager.Levels[b] = l
	}
	if buildAction, ok := action.(*BuildAction); ok {
		hypotheticalVillage.BuildingManager.Levels[buildAction.Building] = buildAction.Level
	}
	return hypotheticalVillage
}

