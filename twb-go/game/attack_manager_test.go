package game

import (
	"log"
	"os"
	"path/filepath"
	"testing"
)

// setupAttackManager creates a new AttackManager with mocked dependencies for testing.
func setupAttackManager() (*AttackManager, *TroopManager, *Map) {
	// Mock TroopManager
	rm := NewResourceManager()
	tm := NewTroopManager(nil, "village1", rm)
	initialTroops := map[string]int{
		"spear": 100,
		"sword": 100,
		"light": 50,
		"spy":   10,
	}
	tm.UpdateTroops(initialTroops, false) // false = add troops

	// Mock Map
	gameMap := &Map{
		Villages: map[string]VillageInfo{
			"village1": {ID: "village1", Name: "My Village", Location: [2]int{50, 50}, Owner: "1", Points: 1000},
			"target1":  {ID: "target1", Name: "Barbarian Village", Location: [2]int{51, 51}, Owner: "0", Points: 50},
			"target2":  {ID: "target2", Name: "Too Far", Location: [2]int{100, 100}, Owner: "0", Points: 50},
			"target3":  {ID: "target3", Name: "Player Village", Location: [2]int{52, 52}, Owner: "2", Points: 50},
		},
		myLocation: [2]int{50, 50},
	}

	am := NewAttackManager(nil, "village1", tm, gameMap)
	am.Logger = log.New(os.Stdout, "[TestAttack] ", log.LstdFlags)

	// Define some farm templates
	am.Templates = []TroopTemplate{
		{
			Condition: "default",
			Units:     map[string]int{"light": 5, "spy": 1},
		},
	}

	// Create cache directory for tests
	os.MkdirAll(filepath.Join("cache", "attacks"), 0755)

	return am, tm, gameMap
}

// cleanupAttackCache removes test cache files.
func cleanupAttackCache(targetID string) {
	os.Remove(filepath.Join("cache", "attacks", targetID+".json"))
}

func TestAttackManager_FindFarmTargets(t *testing.T) {
	am, _, gameMap := setupAttackManager()
	am.Map = gameMap
	am.FarmRadius = 10

	am.FindFarmTargets()

	if len(am.Targets) != 1 {
		t.Fatalf("Expected 1 target, got %d", len(am.Targets))
	}
	if am.Targets[0].ID != "target1" {
		t.Errorf("Expected target to be 'target1', got '%s'", am.Targets[0].ID)
	}
}

func TestSendFarm_Success_FullAttack(t *testing.T) {
	am, tm, _ := setupAttackManager()
	target := am.Map.Villages["target1"]

	initialLightCav := tm.GetTroops()["light"]
	initialSpies := tm.GetTroops()["spy"]

	success, err := am.SendFarm(target)
	if err != nil {
		t.Fatalf("SendFarm failed unexpectedly: %v", err)
	}
	if !success {
		t.Fatalf("SendFarm returned false, expected true")
	}

	expectedLightCav := initialLightCav - 5
	expectedSpies := initialSpies - 1

	if tm.GetTroops()["light"] != expectedLightCav {
		t.Errorf("Expected light cavalry to be %d, but got %d", expectedLightCav, tm.GetTroops()["light"])
	}
	if tm.GetTroops()["spy"] != expectedSpies {
		t.Errorf("Expected spies to be %d, but got %d", expectedSpies, tm.GetTroops()["spy"])
	}

	// Verify cache was written
	if _, err := os.Stat(filepath.Join("cache", "attacks", target.ID+".json")); os.IsNotExist(err) {
		t.Errorf("Attack cache file was not created for target %s", target.ID)
	}

	cleanupAttackCache(target.ID)
}

func TestSendFarm_Success_PartialAttack(t *testing.T) {
	am, tm, _ := setupAttackManager()
	target := am.Map.Villages["target1"]

	// Set troops for a partial attack scenario
	tm.UpdateTroops(tm.GetTroops(), true) // Zero out all troops first
	tm.UpdateTroops(map[string]int{"light": 3, "spy": 0}, false) // Set specific counts

	success, err := am.SendFarm(target)
	if err != nil {
		t.Fatalf("SendFarm failed unexpectedly: %v", err)
	}
	if !success {
		t.Fatalf("SendFarm returned false, expected true")
	}

	// Should send all 3 available light cavalry and 0 spies
	if tm.GetTroops()["light"] != 0 {
		t.Errorf("Expected light cavalry to be 0, but got %d", tm.GetTroops()["light"])
	}
	if tm.GetTroops()["spy"] != 0 {
		t.Errorf("Expected spies to be 0, but got %d", tm.GetTroops()["spy"])
	}

	t.Logf("Troops after partial attack: %v", tm.GetTroops())

	cleanupAttackCache(target.ID)
}

func TestSendFarm_Failure_NotEnoughUnits(t *testing.T) {
	am, tm, _ := setupAttackManager()
	target := am.Map.Villages["target1"]

	// Set required troops to zero
	tm.UpdateTroops(tm.GetTroops(), true) // Decrement all troops to zero

	success, err := am.SendFarm(target)
	if err != nil {
		t.Fatalf("SendFarm failed unexpectedly: %v", err)
	}
	if success {
		t.Fatalf("SendFarm returned true, expected false because no units were available")
	}
}
