package game

import (
	"strings"
	"testing"
	"twb-go/core"
)

func TestTroopManager(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	rm.Update(10000, 10000, 10000, 1000, 10000)
	tm := NewTroopManager(wrapper, "123", rm)
	tm.RecruitData["spear"] = UnitCost{Wood: 50, Stone: 30, Iron: 10, Pop: 1, RequirementsMet: true}

	// Test UpdateTotals
	err := tm.UpdateTotals("")
	if err != nil {
		t.Fatalf("UpdateTotals failed: %v", err)
	}
	if tm.troops["spear"] != 0 {
		t.Errorf("Expected 100 spear, got %d", tm.troops["spear"])
	}
	if tm.TotalTroops["spear"] != 0 {
		t.Errorf("Expected 150 total spear, got %d", tm.TotalTroops["spear"])
	}

	// Test SetWanted
	wanted := map[string]map[string]int{
		"barracks": {
			"spear": 200,
		},
	}
	tm.SetWanted(wanted)
	if tm.wanted["barracks"]["spear"] != 200 {
		t.Errorf("Expected wanted spear to be 200, got %d", tm.wanted["barracks"]["spear"])
	}

	// Test Recruit
	err = tm.Recruit("barracks")
	if err != nil {
		t.Fatalf("Recruit failed: %v", err)
	}
	if tm.TotalTroops["spear"] != 200 {
		t.Errorf("Expected 200 total spear, got %d", tm.TotalTroops["spear"])
	}
}

func TestTroopManager_GetPlannedActions(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	tm := NewTroopManager(wrapper, "123", rm)

	tm.wantedLevels = map[string]int{"axe": 1, "light": 1}
	tm.smithData = map[string]map[string]string{
		"axe":   {"level": "1"},
		"light": {"level": "0"},
	}

	actions := tm.GetPlannedActions()

	foundLight := false
	for _, action := range actions {
		if strings.Contains(action, "Research Light to level 1") {
			foundLight = true
		}
		if strings.Contains(action, "Research Axe to level 1") {
			t.Errorf("Found unexpected action: %s", action)
		}
	}
	if !foundLight {
		t.Errorf("Expected to find 'Research Light to level 1'")
	}
}
