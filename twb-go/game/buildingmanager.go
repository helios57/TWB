package game

import (
	"fmt"
	"strconv"
	"sync"
	"twb-go/core"
)

// BuildingCost represents the resource cost of a building.
type BuildingCost struct {
	Wood      int
	Stone     int
	Iron      int
	Pop       int
	CanBuild  bool
	BuildLink string
}

// BuildingManager manages the buildings in a village.
type BuildingManager struct {
	wrapper   *core.WebWrapper
	villageID string
	resman    *ResourceManager
	Levels    map[string]int
	Costs     map[string]BuildingCost
	lock      sync.Mutex
}

// NewBuildingManager creates a new BuildingManager.
func NewBuildingManager(wrapper *core.WebWrapper, villageID string, resman *ResourceManager) *BuildingManager {
	return &BuildingManager{
		wrapper:   wrapper,
		villageID: villageID,
		resman:    resman,
		Levels:    make(map[string]int),
		Costs:     make(map[string]BuildingCost),
	}
}

// UpdateBuildingLevels updates the building levels from a map.
func (bm *BuildingManager) UpdateBuildingLevels(levels map[string]string) {
	bm.lock.Lock()
	defer bm.lock.Unlock()
	for b, l := range levels {
		level, _ := strconv.Atoi(l)
		bm.Levels[b] = level
	}
}

// ExecuteBuildAction builds the building specified in the action.
func (bm *BuildingManager) ExecuteBuildAction(action *BuildAction) error {
	bm.lock.Lock()
	defer bm.lock.Unlock()

	cost := bm.Costs[action.Building]
	if !bm.resman.CanAfford(Resources{Wood: cost.Wood, Stone: cost.Stone, Iron: cost.Iron, Pop: cost.Pop}) {
		return fmt.Errorf("not enough resources to build %s", action.Building)
	}

	// Simulate resource deduction
	bm.resman.Actual.Wood -= cost.Wood
	bm.resman.Actual.Stone -= cost.Stone
	bm.resman.Actual.Iron -= cost.Iron
	bm.resman.Actual.Pop -= cost.Pop

	bm.Levels[action.Building]++
	fmt.Printf("Building %s to level %d\n", action.Building, bm.Levels[action.Building])
	return nil
}
