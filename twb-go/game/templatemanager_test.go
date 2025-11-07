package game

import (
	"os"
	"path/filepath"
	"testing"
)

func TestTemplateManager_GetGoalFromTemplates(t *testing.T) {
	// Create a temporary directory for templates
	tmpDir, err := os.MkdirTemp("", "templates")
	if err != nil {
		t.Fatalf("Failed to create temporary directory: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create builder and troop template files
	builderDir := filepath.Join(tmpDir, "builder")
	os.Mkdir(builderDir, 0755)
	builderFile := filepath.Join(builderDir, "test.yaml")
	os.WriteFile(builderFile, []byte("building_levels:\n  main: 20\n"), 0644)

	troopDir := filepath.Join(tmpDir, "troops")
	os.Mkdir(troopDir, 0755)
	troopFile := filepath.Join(troopDir, "test.yaml")
	os.WriteFile(troopFile, []byte("troop_levels:\n  spear: 100\n"), 0644)

	// Create a new TemplateManager
	tm := NewTemplateManager(tmpDir)

	// Get the goal from the templates
	goal, err := tm.GetGoalFromTemplates("test", "test")
	if err != nil {
		t.Fatalf("Expected no error, but got: %v", err)
	}

	// Check the building levels
	if goal.BuildingLevels["main"] != 20 {
		t.Errorf("Expected main building level to be 20, but got %d", goal.BuildingLevels["main"])
	}

	// Check the troop levels
	if goal.TroopLevels["spear"] != 100 {
		t.Errorf("Expected spear troop level to be 100, but got %d", goal.TroopLevels["spear"])
	}
}
