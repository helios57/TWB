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
	gameMap := &Map{}
	am := NewAttackManager(wrapper, "123", tm, gameMap)
	cm := &core.ConfigManager{}
	cm.SetConfig(&core.Config{
		Planner: core.PlannerConfig{
			RecruitmentBatchSize: 5,
		},
	})

	bm.Costs = map[string]BuildingCost{
		"main": {},
	}
	tm.RecruitData = map[string]UnitCost{
		"spear": {},
	}
	village := &Village{
		BuildingManager: bm,
		TroopManager:    tm,
		AttackManager:   am,
		GameMap:         gameMap,
		ConfigManager:   cm,
	}
	config := &core.PlannerConfig{
		RecruitmentBatchSize: 5,
	}
	ag := NewActionGenerator(config, nil)

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
