package game

import (
	"testing"
	"twb-go/core"

	"github.com/stretchr/testify/assert"
)

func TestGenerateActionsFromState(t *testing.T) {
	testCases := []struct {
		name                  string
		plannerConfig         *core.PlannerConfig
		buildingPrerequisites map[string]map[string]int
		researchPrerequisites map[string]map[string]int
		buildingData          map[string]core.BuildingData
		unitData              map[string]core.UnitData
		researchData          map[string]core.ResearchData
		initialState          GameState
		expectedAction        Action
		actionShouldBePresent bool
	}{
		{
			name: "Generate BuildAction",
			plannerConfig: &core.PlannerConfig{},
			buildingData: map[string]core.BuildingData{
				"main": {MaxLevel: 30},
			},
			initialState: GameState{
				BuildingLevels: map[string]int{"main": 1},
			},
			expectedAction:        &BuildAction{Building: "main", Level: 2},
			actionShouldBePresent: true,
		},
		{
			name: "Generate RecruitAction",
			plannerConfig: &core.PlannerConfig{RecruitmentBatchSize: 10},
			unitData: map[string]core.UnitData{
				"spear": {},
			},
			initialState: GameState{
				ResearchLevels: map[string]int{"spear": 1},
			},
			expectedAction:        &RecruitAction{Unit: "spear", Amount: 10},
			actionShouldBePresent: true,
		},
		{
			name: "Generate ResearchAction with met prerequisites",
			plannerConfig: &core.PlannerConfig{},
			researchPrerequisites: map[string]map[string]int{
				"spear": {"smith": 1},
			},
			unitData: map[string]core.UnitData{
				"spear": {},
			},
			researchData: map[string]core.ResearchData{
				"spear": {MaxLevel: 3},
			},
			initialState: GameState{
				BuildingLevels: map[string]int{"smith": 1},
				ResearchLevels: map[string]int{"spear": 0},
			},
			expectedAction:        &ResearchAction{Unit: "spear", Level: 1},
			actionShouldBePresent: true,
		},
		{
			name: "Do not generate ResearchAction with unmet prerequisites",
			plannerConfig: &core.PlannerConfig{},
			researchPrerequisites: map[string]map[string]int{
				"spear": {"smith": 1},
			},
			unitData: map[string]core.UnitData{
				"spear": {},
			},
			researchData: map[string]core.ResearchData{
				"spear": {MaxLevel: 3},
			},
			initialState: GameState{
				BuildingLevels: map[string]int{"smith": 0},
				ResearchLevels: map[string]int{"spear": 0},
			},
			expectedAction:        &ResearchAction{Unit: "spear", Level: 1},
			actionShouldBePresent: false,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			ag := NewActionGenerator(
				tc.plannerConfig,
				tc.buildingPrerequisites,
				tc.researchPrerequisites,
				tc.buildingData,
				tc.unitData,
				tc.researchData,
			)
			actions := ag.GenerateActionsFromState(tc.initialState)

			foundAction := false
			for _, action := range actions {
				if assert.ObjectsAreEqual(tc.expectedAction, action) {
					foundAction = true
					break
				}
			}
			assert.Equal(t, tc.actionShouldBePresent, foundAction)
		})
	}
}
