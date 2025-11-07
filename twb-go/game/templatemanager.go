package game

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// TemplateManager handles loading and parsing of game templates.
type TemplateManager struct {
	templateDir string
}

// NewTemplateManager creates a new TemplateManager.
func NewTemplateManager(templateDir string) *TemplateManager {
	return &TemplateManager{
		templateDir: templateDir,
	}
}

// GetGoalFromTemplates loads and merges building and troop templates into a single GameState goal.
func (tm *TemplateManager) GetGoalFromTemplates(buildingTemplate, troopTemplate string) (GameState, error) {
	goal := GameState{
		BuildingLevels: make(map[string]int),
		TroopLevels:    make(map[string]int),
	}

	// Load building template
	buildingPath := filepath.Join(tm.templateDir, "builder", fmt.Sprintf("%s.yaml", buildingTemplate))
	buildingFile, err := os.ReadFile(buildingPath)
	if err != nil {
		return GameState{}, fmt.Errorf("failed to read building template file: %w", err)
	}

	var buildingGoal struct {
		BuildingLevels map[string]int `yaml:"building_levels"`
	}
	if err := yaml.Unmarshal(buildingFile, &buildingGoal); err != nil {
		return GameState{}, fmt.Errorf("failed to decode YAML from building template: %w", err)
	}
	for building, level := range buildingGoal.BuildingLevels {
		goal.BuildingLevels[building] = level
	}

	// Load troop template
	troopPath := filepath.Join(tm.templateDir, "troops", fmt.Sprintf("%s.yaml", troopTemplate))
	troopFile, err := os.ReadFile(troopPath)
	if err != nil {
		return GameState{}, fmt.Errorf("failed to read troop template file: %w", err)
	}

	var troopGoal struct {
		TroopLevels map[string]int `yaml:"troop_levels"`
	}
	if err := yaml.Unmarshal(troopFile, &troopGoal); err != nil {
		return GameState{}, fmt.Errorf("failed to decode YAML from troop template: %w", err)
	}
	for unit, count := range troopGoal.TroopLevels {
		goal.TroopLevels[unit] = count
	}

	return goal, nil
}
