package game

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"sync"
	"twb-go/core"
)

// Building represents a building in the village with its current level.
type Building struct {
	Name  string
	Level int
}

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
	wrapper          *core.WebWrapper
	villageID        string
	resman           *ResourceManager
	Levels           map[string]int
	Costs            map[string]BuildingCost
	queue            []string
	targetLevels     map[string]int
	mode             string
	troopQueueStatus map[string]int
	lock             sync.Mutex
}

// NewBuildingManager creates a new BuildingManager.
func NewBuildingManager(wrapper *core.WebWrapper, villageID string, resman *ResourceManager) *BuildingManager {
	return &BuildingManager{
		wrapper:          wrapper,
		villageID:        villageID,
		resman:           resman,
		Levels:           make(map[string]int),
		Costs:            make(map[string]BuildingCost),
		targetLevels:     make(map[string]int),
		mode:             "linear",
		troopQueueStatus: make(map[string]int),
	}
}

// SetMode sets the building mode (linear or dynamic).
func (bm *BuildingManager) SetMode(mode string) {
	bm.mode = mode
}

// SetQueue sets the building queue for linear mode.
func (bm *BuildingManager) SetQueue(queue []string) {
	bm.queue = queue
}

// SetTargetLevels sets the target building levels for dynamic mode.
func (bm *BuildingManager) SetTargetLevels(targetLevels map[string]int) {
	bm.targetLevels = targetLevels
}

// SetTroopQueueStatus sets the troop queue status for dynamic mode.
func (bm *BuildingManager) SetTroopQueueStatus(status map[string]int) {
	bm.troopQueueStatus = status
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

// BuildNext determines and builds the next building.
func (bm *BuildingManager) BuildNext() (string, error) {
	return bm.GetNextBuildingAction()
}

// GetNextBuildingAction determines the next building to build based on the current mode.
func (bm *BuildingManager) GetNextBuildingAction() (string, error) {
	bm.lock.Lock()
	defer bm.lock.Unlock()

	if bm.mode == "linear" {
		return bm.getNextLinearAction()
	}
	return bm.getNextDynamicAction()
}

// getNextLinearAction returns the next building to build in linear mode.
func (bm *BuildingManager) getNextLinearAction() (string, error) {
	if len(bm.queue) == 0 {
		return "", nil
	}

	for i, item := range bm.queue {
		parts := strings.Split(item, ":")
		if len(parts) != 2 {
			return "", fmt.Errorf("invalid queue item: %s", item)
		}
		building := parts[0]
		level, err := strconv.Atoi(parts[1])
		if err != nil {
			return "", fmt.Errorf("invalid level in queue item: %s", item)
		}

		if bm.Levels[building] >= level {
			bm.queue = append(bm.queue[:i], bm.queue[i+1:]...)
			return bm.getNextLinearAction()
		}

		if cost, ok := bm.Costs[building]; ok && cost.CanBuild {
			return bm._build(building)
		}
	}

	return "", nil
}

// getNextDynamicAction returns the next building to build in dynamic mode.
func (bm *BuildingManager) getNextDynamicAction() (string, error) {
	academyPrereqs := map[string]int{"main": 20, "smith": 20, "market": 10}

	// Priority 1: Maintain 24/7 Troop Queues
	if bm.troopQueueStatus["stable_queue_time"] < 3600 {
		if bm.Levels["stable"] < bm.targetLevels["stable"] {
			return bm._build("stable")
		}
	}
	if bm.troopQueueStatus["barracks_queue_time"] < 3600 {
		if bm.Levels["barracks"] < bm.targetLevels["barracks"] {
			return bm._build("barracks")
		}
	}

	// Priority 2: Strategic Goals (Academy Rush)
	for building, requiredLevel := range academyPrereqs {
		if bm.Levels[building] < requiredLevel {
			if _, ok := bm.targetLevels[building]; ok && bm.Levels[building] < bm.targetLevels[building] {
				return bm._build(building)
			}
		}
	}

	if bm.Levels["main"] >= 20 && bm.Levels["smith"] >= 20 && bm.Levels["market"] >= 10 {
		if _, ok := bm.targetLevels["snob"]; ok && bm.Levels["snob"] < bm.targetLevels["snob"] {
			return bm._build("snob")
		}
	}

	// ... (rest of the dynamic logic to be implemented)

	return "", nil
}

// GetPlannedDynamicActions returns a list of the next planned building actions in dynamic mode.
func (bm *BuildingManager) GetPlannedDynamicActions() []string {
	var actions []string

	addAction := func(building string, targetLevel int, reason string) bool {
		currentLevel := bm.Levels[building]
		if currentLevel < targetLevel {
			actions = append(actions, fmt.Sprintf("Build %s to level %d (Reason: %s)", strings.Title(building), currentLevel+1, reason))
			return true
		}
		return false
	}

	academyPrereqs := map[string]int{"main": 20, "smith": 20, "market": 10}

	// Priority 1: Troop Queues
	if bm.troopQueueStatus["stable_queue_time"] < 3600 {
		if addAction("stable", bm.targetLevels["stable"], "Stable queue running low") {
			return actions
		}
	}
	if bm.troopQueueStatus["barracks_queue_time"] < 3600 {
		if addAction("barracks", bm.targetLevels["barracks"], "Barracks queue running low") {
			return actions
		}
	}

	// Priority 2: Strategic Goals (Academy Rush)
	for building, requiredLevel := range academyPrereqs {
		if bm.Levels[building] < requiredLevel {
			if addAction(building, requiredLevel, "Academy prerequisite") {
				return actions
			}
		}
	}

	if bm.Levels["main"] >= 20 && bm.Levels["smith"] >= 20 && bm.Levels["market"] >= 10 {
		if addAction("snob", bm.targetLevels["snob"], "Build Academy") {
			return actions
		}
	}

	// Priority 3: JIT Provisioning
	if bm.resman.storage < 140000*1.1 {
		if addAction("storage", bm.targetLevels["storage"], "Warehouse too small for Nobleman") {
			return actions
		}
	}

	// Priority 4: Resource Sink
	if float64(bm.resman.Actual.Wood) > float64(bm.resman.storage)*0.95 {
		pits := []string{"wood", "stone", "iron"}
		sort.Slice(pits, func(i, j int) bool {
			return bm.Levels[pits[i]] < bm.Levels[pits[j]]
		})
		if addAction(pits[0], bm.targetLevels[pits[0]], "Resource storage full") {
			return actions
		}
	}

	return actions
}

// _build sends a build request for the given building.
func (bm *BuildingManager) _build(building string) (string, error) {
	// In a real implementation, this would send a build request.
	// For now, we'll just simulate it.
	cost := bm.Costs[building]
	if !bm.resman.CanAfford(Resources{Wood: cost.Wood, Stone: cost.Stone, Iron: cost.Iron, Pop: cost.Pop}) {
		return "", fmt.Errorf("not enough resources to build %s", building)
	}

	// Simulate resource deduction
	bm.resman.Actual.Wood -= cost.Wood
	bm.resman.Actual.Stone -= cost.Stone
	bm.resman.Actual.Iron -= cost.Iron
	bm.resman.Actual.Pop -= cost.Pop

	bm.Levels[building]++
	return building, nil
}
