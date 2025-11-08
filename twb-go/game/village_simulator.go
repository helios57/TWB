package game

import (
	"fmt"
	"math"
	"time"
	"twb-go/core"
)

// VillageSimulator simulates village development over time.
type VillageSimulator struct {
	buildingData map[string]core.BuildingData
	unitData     map[string]core.UnitData
	logger       func(string)
}

// NewVillageSimulator creates a new simulator with the necessary game data.
func NewVillageSimulator(bData map[string]core.BuildingData, uData map[string]core.UnitData, logger func(string)) *VillageSimulator {
	return &VillageSimulator{
		buildingData: bData,
		unitData:     uData,
		logger:       logger,
	}
}

// CalculateNextState calculates the next game state after performing an action.
func (vs *VillageSimulator) CalculateNextState(currentState GameState, action Action) (GameState, float64, error) {
	nextState := vs.copyState(currentState)
	var timeToAction time.Duration
	var err error

	switch a := action.(type) {
	case *BuildAction:
		timeToAction, err = vs.calculateTimeForBuildAction(nextState, *a)
		if err != nil {
			return GameState{}, 0, err
		}
		vs.accumulateResources(&nextState, timeToAction)
		vs.applyBuildAction(&nextState, *a)
		vs.updateIncome(&nextState)

	case *RecruitAction:
		timeToAction, err = vs.calculateTimeForRecruitAction(nextState, *a)
		if err != nil {
			return GameState{}, 0, err
		}
		vs.accumulateResources(&nextState, timeToAction)
		vs.applyRecruitAction(&nextState, *a)
	}

	return nextState, timeToAction.Seconds(), nil
}

// CalculatePlanTime runs a simulation for a given village and build order,
// returning the total time taken to complete the order.
func (vs *VillageSimulator) CalculatePlanTime(village *Village, buildOrder []Action) (time.Duration, error) {
	state := vs.copyInitialState(village)
	queue := make([]Action, len(buildOrder))
	copy(queue, buildOrder)
	totalTime := time.Duration(0)

	for len(queue) > 0 {
		nextAction := queue[0]
		var timeToAction time.Duration
		var err error

		switch action := nextAction.(type) {
		case *BuildAction:
			timeToAction, err = vs.calculateTimeForBuildAction(state, *action)
			if err != nil {
				return 0, err
			}
			vs.accumulateResources(&state, timeToAction)
			vs.applyBuildAction(&state, *action)
			vs.updateIncome(&state)

		case *RecruitAction:
			timeToAction, err = vs.calculateTimeForRecruitAction(state, *action)
			if err != nil {
				return 0, err
			}
			vs.accumulateResources(&state, timeToAction)
			vs.applyRecruitAction(&state, *action)
		}

		totalTime += timeToAction
		queue = queue[1:]
	}

	return totalTime, nil
}

func (vs *VillageSimulator) copyInitialState(village *Village) GameState {
	gs := GameState{
		Resources:      village.ResourceManager.Actual,
		ResourceIncome: village.ResourceManager.Income.Total,
		BuildingLevels: make(map[string]int),
		TroopLevels:    make(map[string]int),
	}
	for b, l := range village.BuildingManager.Levels {
		gs.BuildingLevels[b] = l
	}
	for u, c := range village.TroopManager.TotalTroops {
		gs.TroopLevels[u] = c
	}
	return gs
}

func (vs *VillageSimulator) copyState(state GameState) GameState {
	newState := GameState{
		Resources:      state.Resources,
		ResourceIncome: state.ResourceIncome,
		BuildingLevels: make(map[string]int),
		TroopLevels:    make(map[string]int),
		BuildingQueue:  make([]core.QueueItem, len(state.BuildingQueue)),
		RecruitQueues:  make(map[string][]core.QueueItem),
	}
	for b, l := range state.BuildingLevels {
		newState.BuildingLevels[b] = l
	}
	for u, c := range state.TroopLevels {
		newState.TroopLevels[u] = c
	}
	copy(newState.BuildingQueue, state.BuildingQueue)
	for k, v := range state.RecruitQueues {
		newState.RecruitQueues[k] = make([]core.QueueItem, len(v))
		copy(newState.RecruitQueues[k], v)
	}
	return newState
}

func (vs *VillageSimulator) calculateTimeForBuildAction(state GameState, action BuildAction) (time.Duration, error) {
	if len(state.BuildingQueue) > 0 {
		return time.Duration(math.Inf(1)), nil
	}
	timeToAfford, err := vs.calculateTimeToAfford(state, action)
	if err != nil {
		return 0, err
	}

	buildingData := vs.buildingData[action.Building]
	mainBuildingLevel := state.BuildingLevels["hauptgebaude"]
	if mainBuildingLevel == 0 {
		mainBuildingLevel = 1
	}

	var baseBuildTime float64
	for _, upgrade := range buildingData.Upgrades {
		if upgrade.Level == action.Level {
			baseBuildTime = float64(upgrade.BuildTime)
			break
		}
	}

	buildTimeFactor := 1.05
	buildTime := baseBuildTime * math.Pow(buildTimeFactor, float64(mainBuildingLevel-1))

	return timeToAfford + time.Duration(buildTime)*time.Second, nil
}

func (vs *VillageSimulator) calculateTimeToAfford(state GameState, action BuildAction) (time.Duration, error) {
	var cost *core.BuildingUpgrade
	for _, upgrade := range vs.buildingData[action.Building].Upgrades {
		if upgrade.Level == action.Level {
			cost = &upgrade
			break
		}
	}
	if cost == nil {
		return 0, fmt.Errorf("could not find upgrade data for %s level %d", action.Building, action.Level)
	}

	maxWaitSeconds := 0.0
	for resource, amount := range cost.Resources {
		var currentAmount, income int
		switch resource {
		case "holz":
			currentAmount = state.Resources.Wood
			income = state.ResourceIncome.Wood
		case "lehm":
			currentAmount = state.Resources.Stone
			income = state.ResourceIncome.Stone
		case "eisen":
			currentAmount = state.Resources.Iron
			income = state.ResourceIncome.Iron
		}
		needed := float64(amount) - float64(currentAmount)
		if needed > 0 {
			if income <= 0 {
				return time.Duration(math.Inf(1)), nil
			}
			maxWaitSeconds = math.Max(maxWaitSeconds, needed/float64(income)*3600)
		}
	}
	return time.Duration(maxWaitSeconds) * time.Second, nil
}

func (vs *VillageSimulator) accumulateResources(state *GameState, duration time.Duration) {
	hours := duration.Seconds() / 3600.0
	state.Resources.Wood += int(float64(state.ResourceIncome.Wood) * hours)
	state.Resources.Stone += int(float64(state.ResourceIncome.Stone) * hours)
	state.Resources.Iron += int(float64(state.ResourceIncome.Iron) * hours)
}

func (vs *VillageSimulator) applyBuildAction(state *GameState, action BuildAction) {
	var cost *core.BuildingUpgrade
	for _, upgrade := range vs.buildingData[action.Building].Upgrades {
		if upgrade.Level == action.Level {
			cost = &upgrade
			break
		}
	}
	state.Resources.Wood -= cost.Resources["holz"]
	state.Resources.Stone -= cost.Resources["lehm"]
	state.Resources.Iron -= cost.Resources["eisen"]
	state.Resources.Pop += cost.Population
	state.BuildingLevels[action.Building] = action.Level
	state.BuildingQueue = append(state.BuildingQueue, core.QueueItem{
		Building: action.Building,
		Level:    action.Level,
	})
}

func (vs *VillageSimulator) updateIncome(state *GameState) {
	state.ResourceIncome = Resources{Wood: 5, Stone: 5, Iron: 5} // Base production
	for building, level := range state.BuildingLevels {
		if data, ok := vs.buildingData[building]; ok && level > 0 {
			if building == "holzfallerlager" || building == "lehmgrube" || building == "eisenmine" {
				for _, upgrade := range data.Upgrades {
					if upgrade.Level == level {
						if prod, ok := upgrade.Production["holz"]; ok {
							state.ResourceIncome.Wood += prod
						}
						if prod, ok := upgrade.Production["lehm"]; ok {
							state.ResourceIncome.Stone += prod
						}
						if prod, ok := upgrade.Production["eisen"]; ok {
							state.ResourceIncome.Iron += prod
						}
						break
					}
				}
			}
		}
	}
}

func (vs *VillageSimulator) calculateTimeForRecruitAction(state GameState, action RecruitAction) (time.Duration, error) {
	building := vs.unitData[action.Unit].Prerequisites
	var buildingName string
	for k := range building {
		buildingName = k
		break
	}
	if queue, ok := state.RecruitQueues[buildingName]; ok && len(queue) > 0 {
		return time.Duration(math.Inf(1)), nil
	}
	timeToAfford, err := vs.calculateTimeToRecruit(state, action)
	if err != nil {
		return 0, err
	}

	recruitTime := time.Duration(vs.unitData[action.Unit].BuildTime*action.Amount) * time.Second
	return timeToAfford + recruitTime, nil
}

func (vs *VillageSimulator) calculateTimeToRecruit(state GameState, action RecruitAction) (time.Duration, error) {
	cost := vs.unitData[action.Unit]
	maxWaitSeconds := 0.0
	for resource, amount := range cost.Resources {
		var currentAmount, income int
		switch resource {
		case "holz":
			currentAmount = state.Resources.Wood
			income = state.ResourceIncome.Wood
		case "lehm":
			currentAmount = state.Resources.Stone
			income = state.ResourceIncome.Stone
		case "eisen":
			currentAmount = state.Resources.Iron
			income = state.ResourceIncome.Iron
		}
		needed := float64(amount*action.Amount) - float64(currentAmount)
		if needed > 0 {
			if income <= 0 {
				return time.Duration(math.Inf(1)), nil
			}
			maxWaitSeconds = math.Max(maxWaitSeconds, needed/float64(income)*3600)
		}
	}
	return time.Duration(maxWaitSeconds) * time.Second, nil
}

func (vs *VillageSimulator) applyRecruitAction(state *GameState, action RecruitAction) {
	cost := vs.unitData[action.Unit]
	state.Resources.Wood -= cost.Resources["holz"] * action.Amount
	state.Resources.Stone -= cost.Resources["lehm"] * action.Amount
	state.Resources.Iron -= cost.Resources["eisen"] * action.Amount
	state.Resources.Pop += cost.Population * action.Amount
	building := vs.unitData[action.Unit].Prerequisites
	var buildingName string
	for k := range building {
		buildingName = k
		break
	}
	state.TroopLevels[action.Unit] += action.Amount
	if state.RecruitQueues == nil {
		state.RecruitQueues = make(map[string][]core.QueueItem)
	}
	state.RecruitQueues[buildingName] = append(state.RecruitQueues[buildingName], core.QueueItem{
		Unit:  action.Unit,
		Count: action.Amount,
	})
}
