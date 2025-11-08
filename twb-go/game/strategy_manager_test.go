package game

import (
	"os"
	"testing"
	"twb-go/core"

	"github.com/stretchr/testify/assert"
)

func TestStrategyManager_GenerateGoal(t *testing.T) {
	configContent := `
bot:
  server: "http://test.server"
credentials:
  user_agent: "test-agent"
  cookie: "test-cookie"
villages:
  "123":
    building:
      main: 5
      barracks: 1
    units:
      spear: 10
`
	tmpfile, err := os.CreateTemp("", "config.yaml")
	assert.NoError(t, err)
	defer os.Remove(tmpfile.Name())
	_, err = tmpfile.WriteString(configContent)
	assert.NoError(t, err)
	assert.NoError(t, tmpfile.Close())

	cm, err := core.NewConfigManager(tmpfile.Name(), nil)
	assert.NoError(t, err)
	sm := NewStrategyManager(cm)

	// Test that the SM returns the full goal from the config, regardless of the current state.
	// The A* solver is responsible for figuring out the path.
	currentState := GameState{
		BuildingLevels: map[string]int{"main": 1},
		TroopLevels:    map[string]int{},
	}
	villageID := "123"
	goal := sm.GenerateGoal(currentState, villageID)

	expectedBuildingGoals := map[string]int{
		"main":     5,
		"barracks": 1,
	}
	expectedUnitGoals := map[string]int{
		"spear": 10,
	}

	assert.Equal(t, expectedBuildingGoals, goal.BuildingLevels)
	assert.Equal(t, expectedUnitGoals, goal.TroopLevels)

	// Test case: No config for village
	goalNoConfig := sm.GenerateGoal(currentState, "456")
	assert.Empty(t, goalNoConfig.BuildingLevels)
	assert.Empty(t, goalNoConfig.TroopLevels)
}
