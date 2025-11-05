package game

import (
	"testing"
	"twb-go/core"
)

func newTestVillageWithConfigs(plannerConfig *core.PlannerConfig, solverConfig *core.SolverConfig, buildingPrerequisites map[string]map[string]int) *Village {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	tm := NewTroopManager(wrapper, "123", rm)
	gameMap := &Map{
		Villages: map[string]VillageInfo{
			"target1": {ID: "target1", Location: [2]int{51, 51}},
		},
		myLocation: [2]int{50, 50},
	}
	am := NewAttackManager(wrapper, "123", tm, gameMap)
	am.Targets = []VillageInfo{gameMap.Villages["target1"]}
	cm := &core.ConfigManager{}
	cm.SetConfig(&core.Config{
		BuildingPrerequisites: buildingPrerequisites,
		Solver:                *solverConfig,
		Planner:               *plannerConfig,
	})

	bm.Costs = map[string]BuildingCost{
		"main": {Wood: 10000, Stone: 10000, Iron: 10000, Pop: 10}, // High cost to make it unattractive
	}
	tm.RecruitData = map[string]UnitCost{
		"spear": {Wood: 5000, Stone: 3000, Iron: 1000, Pop: 1, RequirementsMet: true}, // High cost
	}

	village := &Village{
		ResourceManager: rm,
		BuildingManager: bm,
		TroopManager:    tm,
		AttackManager:   am,
		ConfigManager:   cm,
		GameMap:         gameMap,
	}
	village.Solver = NewSolver(village, solverConfig, plannerConfig)
	return village
}

func TestSolver_ChoosesFarmAction(t *testing.T) {
	plannerConfig := &core.PlannerConfig{}
	solverConfig := &core.SolverConfig{EconomicWeight: 1, StrategicWeight: 0, MilitaryWeight: 0} // Isolate economic score
	village := newTestVillageWithConfigs(plannerConfig, solverConfig, nil)
	village.ResourceManager.Update(100, 100, 100, 100, 1000) // Not enough for anything else

	action := village.Solver.GetNextAction()

	if _, ok := action.(*FarmAction); !ok {
		t.Errorf("Expected a FarmAction, but got %T", action)
	}
}
