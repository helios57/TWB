package game

import (
	"testing"
	"twb-go/core"
)

func TestActionGenerator_GenerateActions(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	tm := NewTroopManager(wrapper, "123", rm)
	bm.Costs = map[string]BuildingCost{
		"main": {},
	}
	tm.RecruitData = map[string]UnitCost{
		"spear": {},
	}
	village := &Village{
		BuildingManager: bm,
		TroopManager:    tm,
	}
	ag := NewActionGenerator()

	actions := ag.GenerateActions(village)

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
			if a.Unit == "spear" {
				foundRecruitAction = true
			}
		}
	}

	if !foundBuildAction {
		t.Error("Expected to find a BuildAction for 'main'")
	}
	if !foundRecruitAction {
		t.Error("Expected to find a RecruitAction for 'spear'")
	}
}
