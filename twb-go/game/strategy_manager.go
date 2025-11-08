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

	return GameState{
		BuildingLevels: villageConfig.Building,
		TroopLevels:    villageConfig.Units,
		ResearchLevels: villageConfig.Research,
	}
}
