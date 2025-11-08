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

	// Test case 1: Building goal
	currentState1 := GameState{
		BuildingLevels: map[string]int{"main": 1},
		TroopLevels:    map[string]int{},
	}
	villageID1 := "123"
	goal1 := sm.GenerateGoal(currentState1, villageID1)
	assert.Equal(t, 2, goal1.BuildingLevels["main"])

	// Test case 2: Troop goal
	currentState2 := GameState{
		BuildingLevels: map[string]int{"main": 5, "barracks": 1},
		TroopLevels:    map[string]int{"spear": 0},
	}
	villageID2 := "123"
	goal2 := sm.GenerateGoal(currentState2, villageID2)
	assert.Equal(t, 1, goal2.TroopLevels["spear"])

	// Test case 3: No goal
	currentState3 := GameState{
		BuildingLevels: map[string]int{"main": 5, "barracks": 1},
		TroopLevels:    map[string]int{"spear": 10},
	}
	villageID3 := "123"
	goal3 := sm.GenerateGoal(currentState3, villageID3)
	assert.Empty(t, goal3.BuildingLevels)
	assert.Empty(t, goal3.TroopLevels)
}
