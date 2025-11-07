package game

import (
	"testing"
	"twb-go/core"
)

func TestPlanGenerator_GeneratePlan(t *testing.T) {
	uData := map[string]core.UnitData{
		"adelsgeschlecht": {
			Prerequisites: map[string]int{
				"adelshof": 1,
				"schmiede": 20,
			},
		},
	}
	bData := map[string]core.BuildingData{}
	pg := NewPlanGenerator(uData, bData)

	currentLevels := map[string]int{
		"adelshof": 0,
		"schmiede": 18,
	}

	plan := pg.GeneratePlan("adelsgeschlecht", currentLevels)

	if len(plan) != 4 {
		t.Fatalf("Expected plan to have 4 actions, but got %d", len(plan))
	}

	if buildAction, ok := plan[0].(*BuildAction); !ok || buildAction.Building != "adelshof" || buildAction.Level != 1 {
		t.Errorf("Unexpected action at index 0: %v", plan[0])
	}
	if buildAction, ok := plan[1].(*BuildAction); !ok || buildAction.Building != "schmiede" || buildAction.Level != 19 {
		t.Errorf("Unexpected action at index 1: %v", plan[1])
	}
	if buildAction, ok := plan[2].(*BuildAction); !ok || buildAction.Building != "schmiede" || buildAction.Level != 20 {
		t.Errorf("Unexpected action at index 2: %v", plan[2])
	}
	if recruitAction, ok := plan[3].(*RecruitAction); !ok || recruitAction.Unit != "adelsgeschlecht" {
		t.Errorf("Unexpected action at index 3: %v", plan[3])
	}
}
