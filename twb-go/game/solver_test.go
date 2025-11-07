package game

import (
	"testing"
	"twb-go/core"
)

type mockActionGenerator struct {
	actions []Action
}

func (m *mockActionGenerator) GenerateActions(village *Village) []Action {
	return m.actions
}

func TestSolver_FindsFastestPlan(t *testing.T) {
	bData := map[string]core.BuildingData{
		"holzfallerlager": {
			Upgrades: []core.BuildingUpgrade{
				{Level: 1, Production: map[string]int{"holz": 30}},
				{Level: 2, Production: map[string]int{"holz": 35}, Resources: map[string]int{"holz": 50, "lehm": 60, "eisen": 40}},
			},
		},
		"adelshof": {
			Upgrades: []core.BuildingUpgrade{
				{Level: 1, Resources: map[string]int{"holz": 1000, "lehm": 1000, "eisen": 1000}},
			},
		},
	}
	uData := map[string]core.UnitData{
		"adelsgeschlecht": {
			Prerequisites: map[string]int{"adelshof": 1},
			BuildTime:     100,
			Resources:     map[string]int{"holz": 100, "lehm": 100, "eisen": 100},
		},
	}

	village := &Village{
		ResourceManager: &ResourceManager{
			Actual: Resources{Wood: 0, Stone: 0, Iron: 0},
			Income: Income{Total: Resources{Wood: 30, Stone: 30, Iron: 30}},
		},
		BuildingManager: &BuildingManager{
			Levels: map[string]int{"holzfallerlager": 1, "lehmgrube": 1, "eisenmine": 1, "adelshof": 0},
			Data:   bData,
		},
		TroopManager: &TroopManager{
			TotalTroops: make(map[string]int),
			Data:        uData,
		},
		logger: func(msg string) { t.Log(msg) },
	}
	village.Solver = &Solver{
		village: village,
		actionGenerator: &mockActionGenerator{
			actions: []Action{
				&BuildAction{Building: "adelshof", Level: 1},
				&BuildAction{Building: "holzfallerlager", Level: 2},
			},
		},
		planGenerator: NewPlanGenerator(uData, bData),
	}

	action := village.Solver.GetNextAction()

	if action == nil {
		t.Fatal("Expected an action, but got nil")
	}

	if buildAction, ok := action.(*BuildAction); !ok || buildAction.Building != "holzfallerlager" {
		t.Errorf("Expected solver to choose 'holzfallerlager' as the first step, but got %v", action)
	}
}
