package game

import (
	"os"
	"path/filepath"
	"testing"
	"time"
	"twb-go/core"
)

func TestNewVillage(t *testing.T) {
	// Create a temporary directory for the test
	tmpDir, err := os.MkdirTemp("", "config-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create a dummy config file
	configContent := `
bot:
  server: http://example.com
villages:
  "123": {}
`
	configPath := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	// These would be properly initialized in a real scenario
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	cm, _ := core.NewConfigManager(configPath, nil)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	tm := NewTroopManager(wrapper, "123", rm)
	gameMap := NewMap(wrapper, "123")
	am := NewAttackManager(wrapper, "123", tm, gameMap)
	dm := NewDefenceManager(wrapper, "123", rm)

	villageID := "123"
	village, err := NewVillage(villageID, wrapper, cm, rm, bm, tm, am, dm, gameMap)
	if err != nil {
		t.Fatalf("NewVillage failed: %v", err)
	}

	if village.ID != villageID {
		t.Errorf("Expected village ID to be %s, got %s", villageID, village.ID)
	}
}

func TestVillage_CheckForcedPeace(t *testing.T) {
	// Create a temporary directory for the test
	tmpDir, err := os.MkdirTemp("", "config-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create a dummy config file
	configContent := `
bot:
  forced_peace_times:
    - start: "01.01.25 10:00:00"
      end: "01.01.25 12:00:00"
villages:
  "123": {}
`
	configPath := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	cm, _ := core.NewConfigManager(configPath, nil)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	tm := NewTroopManager(wrapper, "123", rm)
	gameMap := NewMap(wrapper, "123")
	am := NewAttackManager(wrapper, "123", tm, gameMap)
	dm := NewDefenceManager(wrapper, "123", rm)
	village, _ := NewVillage("123", wrapper, cm, rm, bm, tm, am, dm, gameMap)

	// Test forced_peace_today
	timeNow = func() time.Time { return time.Date(2025, 1, 1, 9, 0, 0, 0, time.UTC) }
	village.CheckForcedPeace()
	if !village.ForcedPeaceToday {
		t.Errorf("Expected forcedPeaceToday to be true")
	}

	// Test forced_peace
	timeNow = func() time.Time { return time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC) }
	village.CheckForcedPeace()
	if !village.ForcedPeace {
		t.Errorf("Expected forcedPeace to be true")
	}
}
