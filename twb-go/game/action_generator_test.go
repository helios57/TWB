package game

import (
	"testing"
	"twb-go/core"
)

func TestActionGenerator_GenerateActionsFromState(t *testing.T) {
	config := &core.PlannerConfig{
		RecruitmentBatchSize: 5,
	}
	buildingData := map[string]core.BuildingData{
		"main": {MaxLevel: 30},
	}
	unitData := map[string]core.UnitData{
		"spear": {},
	}

	ag := NewActionGenerator(config, nil, buildingData, unitData)

	state := GameState{
		BuildingLevels: map[string]int{
			"main": 1,
		},
		TroopLevels: map[string]int{
			"spear": 10,
		},
	}

	actions := ag.GenerateActionsFromState(state)

	if len(actions) != 2 {
		t.Fatalf("Expected 2 actions, got %d", len(actions))
	}

	foundBuildAction := false
	foundRecruitAction := false
	for _, action := range actions {
		switch a := action.(type) {
		case *BuildAction:
			if a.Building == "main" {
				foundBuildAction = true
			}
		case *RecruitAction:
			if a.Unit == "spear" && a.Amount == 5 {
				foundRecruitAction = true
			}
		}
	}

	if !foundBuildAction {
		t.Error("Expected to find a BuildAction for 'main'")
	}
	if !foundRecruitAction {
		t.Error("Expected to find a RecruitAction for 'spear' with amount 5")
	}
}
