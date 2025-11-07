package game

import "twb-go/core"

// ActionGenerator generates all possible actions for a given game state.
type ActionGenerator struct {
	config                *core.PlannerConfig
	buildingPrerequisites map[string]map[string]int
	buildingData          map[string]core.BuildingData
	unitData              map[string]core.UnitData
}

// NewActionGenerator creates a new ActionGenerator.
func NewActionGenerator(config *core.PlannerConfig, buildingPrerequisites map[string]map[string]int, bData map[string]core.BuildingData, uData map[string]core.UnitData) *ActionGenerator {
	return &ActionGenerator{
		config:                config,
		buildingPrerequisites: buildingPrerequisites,
		buildingData:          bData,
		unitData:              uData,
	}
}

// GenerateActionsFromState returns a list of all possible actions from a given state.
func (ag *ActionGenerator) GenerateActionsFromState(state GameState) []Action {
	var actions []Action

	// Generate BuildActions
	for building, data := range ag.buildingData {
		currentLevel := state.BuildingLevels[building]
		if currentLevel >= data.MaxLevel {
			continue
		}

		if prereqs, ok := ag.buildingPrerequisites[building]; ok {
			allPrereqsMet := true
			for prereqBuilding, prereqLevel := range prereqs {
				if state.BuildingLevels[prereqBuilding] < prereqLevel {
					allPrereqsMet = false
					break
				}
			}
			if !allPrereqsMet {
				continue
			}
		}

		actions = append(actions, &BuildAction{Building: building, Level: currentLevel + 1})
	}

	// Generate RecruitActions
	for unit := range ag.unitData {
		actions = append(actions, &RecruitAction{Unit: unit, Amount: ag.config.RecruitmentBatchSize})
	}

	return actions
}
