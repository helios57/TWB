package game

import (
	"testing"
	"twb-go/core"
)

func TestTroopManager_ExecuteRecruitAction(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	rm.Update(10000, 10000, 10000, 1000, 10000)
	tm := NewTroopManager(wrapper, "123", rm)

	tm.RecruitData["spear"] = UnitCost{Wood: 50, Stone: 30, Iron: 10, Pop: 1, RequirementsMet: true}
	action := &RecruitAction{Unit: "spear", Amount: 100}

	err := tm.ExecuteRecruitAction(action)
	if err != nil {
		t.Fatalf("ExecuteRecruitAction failed: %v", err)
	}

	if tm.TotalTroops["spear"] != 100 {
		t.Errorf("Expected spear to be 100, got %d", tm.TotalTroops["spear"])
	}

	expectedResources := Resources{Wood: 5000, Stone: 7000, Iron: 9000, Pop: 900}
	if rm.Actual != expectedResources {
		t.Errorf("Expected resources to be %v, got %v", expectedResources, rm.Actual)
	}
}
