package game

import "twb-go/core"

// PlanGenerator creates a sequence of actions to achieve a goal.
type PlanGenerator struct {
	unitData     map[string]core.UnitData
	buildingData map[string]core.BuildingData
}

// NewPlanGenerator creates a new PlanGenerator.
func NewPlanGenerator(uData map[string]core.UnitData, bData map[string]core.BuildingData) *PlanGenerator {
	return &PlanGenerator{
		unitData:     uData,
		buildingData: bData,
	}
}

// GeneratePlan creates a plan to recruit a target unit.
func (pg *PlanGenerator) GeneratePlan(targetUnit string, currentLevels map[string]int) []Action {
	var plan []Action
	uData, ok := pg.unitData[targetUnit]
	if !ok {
		return plan
	}

	maxLevel := 0
	for _, level := range uData.Prerequisites {
		if level > maxLevel {
			maxLevel = level
		}
	}

	for l := 1; l <= maxLevel; l++ {
		for building, targetLevel := range uData.Prerequisites {
			if l <= targetLevel && l > currentLevels[building] {
				plan = append(plan, &BuildAction{Building: building, Level: l})
			}
		}
	}

	plan = append(plan, &RecruitAction{Unit: targetUnit, Amount: 1})
	return plan
}
