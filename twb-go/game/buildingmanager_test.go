package game

import (
	"strings"
	"testing"
	"twb-go/core"
)

func TestBuildingManager(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	rm.Update(1000, 1000, 1000, 100, 1000)
	bm := NewBuildingManager(wrapper, "123", rm)

	// Test SetMode
	bm.SetMode("dynamic")
	if bm.mode != "dynamic" {
		t.Errorf("Expected mode to be 'dynamic', got '%s'", bm.mode)
	}
	bm.SetMode("linear")

	// Test SetQueue
	queue := []string{"main:1", "barracks:1"}
	bm.SetQueue(queue)
	if len(bm.queue) != 2 {
		t.Errorf("Expected queue length to be 2, got %d", len(bm.queue))
	}

	// Test GetNextBuildingAction (linear mode)
	bm.Costs["main"] = BuildingCost{Wood: 100, Stone: 100, Iron: 100, Pop: 10, CanBuild: true}
	next, err := bm.GetNextBuildingAction()
	if err != nil {
		t.Fatalf("GetNextBuildingAction failed: %v", err)
	}
	if next != "main" {
		t.Errorf("Expected next building to be 'main', got '%s'", next)
	}
	if bm.Levels["main"] != 1 {
		t.Errorf("Expected main level to be 1, got %d", bm.Levels["main"])
	}

	// Test SetTargetLevels
	targetLevels := map[string]int{"main": 20, "barracks": 10}
	bm.SetTargetLevels(targetLevels)
	if bm.targetLevels["main"] != 20 {
		t.Errorf("Expected target level for main to be 20, got %d", bm.targetLevels["main"])
	}
}

func TestBuildingManagerDynamicMode(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	rm.Update(50000, 50000, 50000, 1000, 80000)
	bm := NewBuildingManager(wrapper, "12345", rm)
	bm.SetMode("dynamic")

	// Test Priority 1: Troop Queues
	bm.SetTargetLevels(map[string]int{"stable": 20, "barracks": 20})
	bm.Levels = map[string]int{"stable": 10, "barracks": 15}
	bm.SetTroopQueueStatus(map[string]int{"stable_queue_time": 3000, "barracks_queue_time": 4000})
	actions := bm.GetPlannedDynamicActions()
	if !strings.Contains(actions[0], "Build Stable to level 11 (Reason: Stable queue running low)") {
		t.Errorf("Test Priority 1 failed. Got: %s", actions[0])
	}

	bm.SetTroopQueueStatus(map[string]int{"stable_queue_time": 4000, "barracks_queue_time": 3000})
	actions = bm.GetPlannedDynamicActions()
	if !strings.Contains(actions[0], "Build Barracks to level 16 (Reason: Barracks queue running low)") {
		t.Errorf("Test Priority 1 failed. Got: %s", actions[0])
	}

	// Test Priority 2: Academy Prereqs
	bm.SetTargetLevels(map[string]int{"main": 20, "smith": 20, "market": 10, "snob": 1})
	bm.Levels = map[string]int{"main": 15, "smith": 20, "market": 10}
	bm.SetTroopQueueStatus(map[string]int{"stable_queue_time": 9999, "barracks_queue_time": 9999})
	actions = bm.GetPlannedDynamicActions()
	if !strings.Contains(actions[0], "Build Main to level 16 (Reason: Academy prerequisite)") {
		t.Errorf("Test Priority 2 failed. Got: %s", actions[0])
	}

	// Test Priority 3: JIT Provisioning
	bm.SetTargetLevels(map[string]int{"storage": 30, "farm": 30, "snob": 1})
	bm.Levels = map[string]int{"main": 20, "smith": 20, "market": 10, "snob": 1, "storage": 15, "farm": 20}
	bm.SetTroopQueueStatus(map[string]int{"stable_queue_time": 9999, "barracks_queue_time": 9999})
	rm.storage = 80000
	actions = bm.GetPlannedDynamicActions()
	if !strings.Contains(actions[0], "Build Storage to level 16 (Reason: Warehouse too small for Nobleman)") {
		t.Errorf("Test Priority 3 failed. Got: %s", actions[0])
	}

	// Test Priority 4: Resource Sink
	bm.SetTargetLevels(map[string]int{"wood": 30, "stone": 30, "iron": 30, "snob": 1})
	bm.Levels = map[string]int{"main": 20, "smith": 20, "market": 10, "snob": 1, "storage": 30, "farm": 30, "wood": 10, "stone": 12, "iron": 11}
	bm.SetTroopQueueStatus(map[string]int{"stable_queue_time": 9999, "barracks_queue_time": 9999})
	rm.storage = 100000
	rm.Actual = Resources{Wood: 98000, Stone: 50000, Iron: 50000}
	actions = bm.GetPlannedDynamicActions()
	if !strings.Contains(actions[0], "Build Wood to level 11 (Reason: Resource storage full)") {
		t.Errorf("Test Priority 4 failed. Got: %s", actions[0])
	}
}
