package game

import (
	"os"
	"path/filepath"
	"testing"
	"twb-go/core"
)

func TestSolver_FindsOptimalPlan(t *testing.T) {
	bData := map[string]core.BuildingData{
		"main": {
			MaxLevel: 30,
			Upgrades: []core.BuildingUpgrade{
				{Level: 1, Resources: map[string]int{"holz": 10, "lehm": 10, "eisen": 10}, BuildTime: 100},
			},
		},
		"farm": {
			MaxLevel: 30,
			Upgrades: []core.BuildingUpgrade{
				{Level: 1, Resources: map[string]int{"holz": 10, "lehm": 10, "eisen": 10}, BuildTime: 100},
			},
		},
	}
	uData := map[string]core.UnitData{}

	// Create a temporary directory for templates
	tmpDir, err := os.MkdirTemp("", "templates")
	if err != nil {
		t.Fatalf("Failed to create temporary directory: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create builder and troop template files
	builderDir := filepath.Join(tmpDir, "builder")
	os.Mkdir(builderDir, 0755)
	builderFile := filepath.Join(builderDir, "test.yaml")
	os.WriteFile(builderFile, []byte("building_levels:\n  main: 1\n"), 0644)

	troopDir := filepath.Join(tmpDir, "troops")
	os.Mkdir(troopDir, 0755)
	troopFile := filepath.Join(troopDir, "test.yaml")
	os.WriteFile(troopFile, []byte("troop_levels:\n"), 0644)

	tm := NewTemplateManager(tmpDir)
	goalState, err := tm.GetGoalFromTemplates("test", "test")
	if err != nil {
		t.Fatalf("Error getting goal from templates: %v", err)
	}

	config := &core.PlannerConfig{}
	actionGenerator := NewActionGenerator(config, nil, nil, bData, uData, nil)
	villageSimulator := NewVillageSimulator(bData, uData, nil, func(msg string) { t.Log(msg) })
	aStarSolver := NewAStarSolver(actionGenerator, villageSimulator)

	startState := GameState{
		Resources:      Resources{Wood: 100, Stone: 100, Iron: 100},
		ResourceIncome: Resources{Wood: 10, Stone: 10, Iron: 10},
		BuildingLevels: map[string]int{"main": 0, "farm": 0},
		TroopLevels:    map[string]int{},
	}

	plan, err := aStarSolver.FindOptimalPlan(startState, goalState)
	if err != nil {
		t.Fatalf("Expected a plan, but got an error: %v", err)
	}

	if len(plan) == 0 {
		t.Fatal("Expected a plan, but got an empty one")
	}

	if buildAction, ok := plan[0].(*BuildAction); !ok || buildAction.Building != "main" {
		t.Errorf("Expected the first action to be 'main', but got %v", plan[0])
	}
}
