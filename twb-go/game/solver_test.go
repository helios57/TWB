package game

import (
	"testing"
	"twb-go/core"
)

func newTestVillageForSolver() *Village {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	tm := NewTroopManager(wrapper, "123", rm)

	bm.Costs = map[string]BuildingCost{
		"main":   {Wood: 100, Stone: 100, Iron: 100, Pop: 10},
		"smith":  {Wood: 150, Stone: 150, Iron: 150, Pop: 15},
		"market": {Wood: 200, Stone: 200, Iron: 200, Pop: 20},
		"snob":   {Wood: 1000, Stone: 1000, Iron: 1000, Pop: 100},
		"wood":   {Wood: 50, Stone: 60, Iron: 40, Pop: 5},
		"stone":  {Wood: 60, Stone: 50, Iron: 40, Pop: 5},
		"iron":   {Wood: 40, Stone: 60, Iron: 50, Pop: 5},
	}
	tm.RecruitData = map[string]UnitCost{
		"spear": {Wood: 50, Stone: 30, Iron: 10, Pop: 1, RequirementsMet: true},
	}

	village := &Village{
		ResourceManager: rm,
		BuildingManager: bm,
		TroopManager:    tm,
	}
	village.Solver = NewSolver(village)
	return village
}

func TestSolver_ChoosesBestAction(t *testing.T) {
	village := newTestVillageForSolver()
	village.ResourceManager.Update(1000, 1000, 1000, 100, 1000)
	village.BuildingManager.Levels = map[string]int{"main": 1, "smith": 1, "market": 1, "snob": 0}

	action := village.Solver.GetNextAction()

	buildAction, ok := action.(*BuildAction)
	if !ok {
		t.Fatalf("Expected a BuildAction, got %T", action)
	}
	// The solver should choose to upgrade the main building because it has a high
	// strategic weight in the heuristic function.
	if buildAction.Building != "main" {
		t.Errorf("Expected to build main, got %s", buildAction.Building)
	}
}
