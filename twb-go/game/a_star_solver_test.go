package game

import (
	"testing"
	"twb-go/core"

	"github.com/stretchr/testify/assert"
)

func TestAStarSolver_Research(t *testing.T) {
	bData := map[string]core.BuildingData{}
	uData := map[string]core.UnitData{
		"spear": {},
	}
	rData := map[string]core.ResearchData{
		"spear": {
			MaxLevel: 3,
			Upgrades: []core.ResearchUpgrade{
				{Level: 1, Resources: map[string]int{"holz": 10, "lehm": 10, "eisen": 10}, ResearchTime: 100},
			},
		},
	}
	config := &core.PlannerConfig{}
	actionGenerator := NewActionGenerator(config, nil, nil, bData, uData, rData)
	villageSimulator := NewVillageSimulator(bData, uData, rData, func(msg string) { t.Log(msg) })
	aStarSolver := NewAStarSolver(actionGenerator, villageSimulator)

	startState := GameState{
		Resources:      Resources{Wood: 100, Stone: 100, Iron: 100},
		ResourceIncome: Resources{Wood: 10, Stone: 10, Iron: 10},
		BuildingLevels: map[string]int{},
		TroopLevels:    map[string]int{},
		ResearchLevels: map[string]int{"spear": 0},
	}
	goalState := GameState{
		ResearchLevels: map[string]int{"spear": 1},
	}

	plan, err := aStarSolver.FindOptimalPlan(startState, goalState)
	assert.NoError(t, err)
	assert.NotEmpty(t, plan)
	assert.IsType(t, &ResearchAction{}, plan[0])
	assert.Equal(t, "spear", plan[0].(*ResearchAction).Unit)
}
