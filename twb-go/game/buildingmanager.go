package game

import (
	"fmt"
	"strconv"
	"sync"
	"twb-go/core"
)

// BuildingManager manages the buildings in a village.
type BuildingManager struct {
	wrapper   core.WebWrapperInterface
	villageID string
	resman    *ResourceManager
	Levels    map[string]int
	Costs     map[string]core.BuildingCost
	lock      sync.Mutex
}

// NewBuildingManager creates a new BuildingManager.
func NewBuildingManager(wrapper core.WebWrapperInterface, villageID string, resman *ResourceManager) *BuildingManager {
	return &BuildingManager{
		wrapper:   wrapper,
		villageID: villageID,
		resman:    resman,
		Levels:    make(map[string]int),
		Costs:     make(map[string]core.BuildingCost),
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

// UpdateBuildingCosts updates the building costs from a map.
func (bm *BuildingManager) UpdateBuildingCosts(costs map[string]core.BuildingCost) {
	bm.lock.Lock()
	defer bm.lock.Unlock()
	bm.Costs = costs
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

	if cost.BuildLink != "" {
		_, err := bm.wrapper.GetURL(cost.BuildLink)
		if err != nil {
			return fmt.Errorf("failed to execute build action: %w", err)
		}
	}
	return nil
}
