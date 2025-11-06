package game

import (
	"testing"
	"twb-go/core"
)

func TestBuildingManager_ExecuteBuildAction(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2, "test-agent", "test-cookie")
	rm := NewResourceManager()
	rm.Update(1000, 1000, 1000, 100, 1000)
	bm := NewBuildingManager(wrapper, "123", rm)

	bm.Costs["main"] = core.BuildingCost{Wood: 100, Stone: 100, Iron: 100, Pop: 10, CanBuild: true}
	action := &BuildAction{Building: "main", Level: 1}

	err := bm.ExecuteBuildAction(action)
	if err != nil {
		t.Fatalf("ExecuteBuildAction failed: %v", err)
	}

	if bm.Levels["main"] != 1 {
		t.Errorf("Expected main level to be 1, got %d", bm.Levels["main"])
	}

	expectedResources := Resources{Wood: 900, Stone: 900, Iron: 900, Pop: 90}
	if rm.Actual != expectedResources {
		t.Errorf("Expected resources to be %v, got %v", expectedResources, rm.Actual)
	}
}
