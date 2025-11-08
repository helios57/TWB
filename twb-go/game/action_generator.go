package game

import "twb-go/core"

// ActionGenerator generates all possible actions for a given game state.
type ActionGenerator struct {
	config                *core.PlannerConfig
	buildingPrerequisites map[string]map[string]int
	researchPrerequisites map[string]map[string]int
	buildingData          map[string]core.BuildingData
	unitData              map[string]core.UnitData
	researchData          map[string]core.ResearchData
	mockActions           []Action
}

// NewActionGenerator creates a new ActionGenerator.
func NewActionGenerator(config *core.PlannerConfig, buildingPrerequisites, researchPrerequisites map[string]map[string]int, bData map[string]core.BuildingData, uData map[string]core.UnitData, rData map[string]core.ResearchData) *ActionGenerator {
	return &ActionGenerator{
		config:                config,
		buildingPrerequisites: buildingPrerequisites,
		researchPrerequisites: researchPrerequisites,
		buildingData:          bData,
		unitData:              uData,
		researchData:          rData,
	}
}

// GenerateActionsFromState returns a list of all possible actions from a given state.
func (ag *ActionGenerator) GenerateActionsFromState(state GameState) []Action {
	if ag.mockActions != nil {
		return ag.mockActions
	}
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
		if state.ResearchLevels[unit] > 0 {
			actions = append(actions, &RecruitAction{Unit: unit, Amount: ag.config.RecruitmentBatchSize})
		}
	}

	// Generate ResearchActions
	for unit := range ag.unitData {
		currentLevel := state.ResearchLevels[unit]
		if researchData, ok := ag.researchData[unit]; ok && currentLevel < researchData.MaxLevel {
			if prereqs, ok := ag.researchPrerequisites[unit]; ok {
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
			actions = append(actions, &ResearchAction{Unit: unit, Level: currentLevel + 1})
		}
	}

	return actions
}
