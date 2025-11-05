package game

import "twb-go/core"

// ActionGenerator generates all possible actions for a given game state.
type ActionGenerator struct {
	config                *core.PlannerConfig
	buildingPrerequisites map[string]map[string]int
}

// NewActionGenerator creates a new ActionGenerator.
func NewActionGenerator(config *core.PlannerConfig, buildingPrerequisites map[string]map[string]int) *ActionGenerator {
	return &ActionGenerator{
		config:                config,
		buildingPrerequisites: buildingPrerequisites,
	}
}

// GenerateActions returns a list of all possible actions.
func (ag *ActionGenerator) GenerateActions(village *Village) []Action {
	var actions []Action

	// Generate BuildActions
	for building := range village.BuildingManager.Costs {
		if prereqs, ok := ag.buildingPrerequisites[building]; ok {
			allPrereqsMet := true
			for prereqBuilding, prereqLevel := range prereqs {
				if village.BuildingManager.Levels[prereqBuilding] < prereqLevel {
					allPrereqsMet = false
					break
				}
			}
			if !allPrereqsMet {
				continue
			}
		}
		currentLevel := village.BuildingManager.Levels[building]
		// A simple heuristic: only consider upgrading buildings by one level
		actions = append(actions, &BuildAction{Building: building, Level: currentLevel + 1})
	}

	// Generate RecruitActions
	for unit := range village.TroopManager.RecruitData {
		actions = append(actions, &RecruitAction{Unit: unit, Amount: ag.config.RecruitmentBatchSize})
	}

	// Generate FarmActions
	for _, target := range village.AttackManager.Targets {
		actions = append(actions, &FarmAction{Target: target})
	}

	return actions
}
