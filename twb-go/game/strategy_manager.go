package game

import (
	"twb-go/core"
)

type StrategyManager struct {
	cfg *core.ConfigManager
}

func NewStrategyManager(cfg *core.ConfigManager) *StrategyManager {
	return &StrategyManager{
		cfg: cfg,
	}
}

func (sm *StrategyManager) GenerateGoal(currentState GameState, villageID string) GameState {
	villageConfig, ok := sm.cfg.GetConfig().Villages[villageID]
	if !ok {
		return GameState{}
	}

	goal := GameState{
		BuildingLevels: make(map[string]int),
		TroopLevels:    make(map[string]int),
	}

	// Building goals
	for building, level := range villageConfig.Building {
		if currentState.BuildingLevels[building] < level {
			goal.BuildingLevels[building] = currentState.BuildingLevels[building] + 1
			return goal
		}
	}

	// Troop goals
	for unit, count := range villageConfig.Units {
		if currentState.TroopLevels[unit] < count {
			goal.TroopLevels[unit] = currentState.TroopLevels[unit] + 1
			return goal
		}
	}

	return goal
}
