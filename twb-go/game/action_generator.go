package game

// ActionGenerator generates all possible actions for a given game state.
type ActionGenerator struct{}

// NewActionGenerator creates a new ActionGenerator.
func NewActionGenerator() *ActionGenerator {
	return &ActionGenerator{}
}

// GenerateActions returns a list of all possible actions.
func (ag *ActionGenerator) GenerateActions(village *Village) []Action {
	var actions []Action

	// Generate BuildActions
	for building := range village.BuildingManager.Costs {
		if building == "snob" {
			if village.BuildingManager.Levels["main"] < 20 || village.BuildingManager.Levels["smith"] < 20 || village.BuildingManager.Levels["market"] < 10 {
				continue
			}
		}
		currentLevel := village.BuildingManager.Levels[building]
		// A simple heuristic: only consider upgrading buildings by one level
		actions = append(actions, &BuildAction{Building: building, Level: currentLevel + 1})
	}

	// Generate RecruitActions
	for unit := range village.TroopManager.RecruitData {
		// A simple heuristic: recruit in batches of 10
		actions = append(actions, &RecruitAction{Unit: unit, Amount: 10})
	}

	return actions
}
