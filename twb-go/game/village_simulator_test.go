package game

import (
	"math"
	"testing"
	"time"
	"twb-go/core"

	"github.com/stretchr/testify/assert"
)

func TestCalculateTimeForBuildAction_QueueFull(t *testing.T) {
	vs := NewVillageSimulator(nil, nil, nil, func(s string) {})
	state := GameState{
		BuildingQueue: []core.QueueItem{
			{},
			{},
		},
	}
	action := BuildAction{Building: "kaserne", Level: 1}

	duration, err := vs.calculateTimeForBuildAction(state, action)

	assert.NoError(t, err)
	assert.Equal(t, time.Duration(math.MaxInt64), duration, "Expected infinite duration when build queue is full")
}

func TestCalculateTimeForRecruitAction_QueueFull(t *testing.T) {
	vs := NewVillageSimulator(
		nil,
		map[string]core.UnitData{
			"spear": {Prerequisites: map[string]int{"kaserne": 1}},
		},
		nil,
		func(s string) {},
	)
	state := GameState{
		RecruitQueues: map[string][]core.QueueItem{
			"kaserne": {
				{},
				{},
			},
		},
	}
	action := RecruitAction{Unit: "spear", Amount: 1}

	duration, err := vs.calculateTimeForRecruitAction(state, action)

	assert.NoError(t, err)
	assert.Equal(t, time.Duration(math.MaxInt64), duration, "Expected infinite duration when recruit queue is full")
}

func TestApplyResearchAction(t *testing.T) {
	vs := NewVillageSimulator(
		nil,
		nil,
		map[string]core.ResearchData{
			"spear": {
				Upgrades: []core.ResearchUpgrade{
					{Level: 1, Resources: map[string]int{"holz": 50, "lehm": 50, "eisen": 50}},
				},
			},
		},
		func(s string) {},
	)
	state := GameState{
		Resources:      Resources{Wood: 100, Stone: 100, Iron: 100},
		ResearchLevels: make(map[string]int),
	}
	action := ResearchAction{Unit: "spear", Level: 1}

	vs.applyResearchAction(&state, action)

	assert.Equal(t, 1, state.ResearchLevels["spear"])
	assert.Equal(t, 50, state.Resources.Wood)
	assert.Equal(t, 50, state.Resources.Stone)
	assert.Equal(t, 50, state.Resources.Iron)
}

func TestCalculateTimeForResearchAction(t *testing.T) {
	vs := NewVillageSimulator(
		nil,
		nil,
		map[string]core.ResearchData{
			"spear": {
				Upgrades: []core.ResearchUpgrade{
					{Level: 1, Resources: map[string]int{"holz": 50, "lehm": 50, "eisen": 50}, ResearchTime: 1800},
				},
			},
		},
		func(s string) {},
	)
	state := GameState{
		Resources:      Resources{Wood: 0, Stone: 0, Iron: 0},
		ResourceIncome: Resources{Wood: 10, Stone: 10, Iron: 10},
		BuildingLevels: map[string]int{"smith": 1},
	}
	action := ResearchAction{Unit: "spear", Level: 1}

	duration, err := vs.calculateTimeForResearchAction(state, action)

	assert.NoError(t, err)
	assert.InDelta(t, 18000+1800, duration.Seconds(), 1.0) // 5 hours to afford + 30 minutes to research
}
