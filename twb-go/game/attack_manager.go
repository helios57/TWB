package game

import (
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"path/filepath"
	"time"
	"twb-go/core"
)

// AttackManager handles sending farm attacks and other attack-related logic.
type AttackManager struct {
	Wrapper           *core.WebWrapper
	VillageID         string
	TroopManager      *TroopManager
	Map               *Map
	Targets           []VillageInfo
	Logger            *log.Logger
	MaxFarms          int
	FarmRadius        float64
	Templates         []TroopTemplate
	FarmMinPoints     int
	FarmMaxPoints     int
	ScoutFarmAmount   int
	farmBagLimitReached bool
	ignored           map[string]bool // Using a map for efficient lookups
}

// TroopTemplate defines the structure for farming templates.
type TroopTemplate struct {
	Condition string            `json:"condition"`
	Units     map[string]int    `json:"units"`
	Calculate string            `json:"calculate,omitempty"`
}

// AttackCacheEntry stores information about the last attack on a village.
type AttackCacheEntry struct {
	LastAttack   int64 `json:"last_attack"`
	Scout        bool  `json:"scout"`
	Safe         bool  `json:"safe"`
	HighProfile  bool  `json:"high_profile"`
	LowProfile   bool  `json:"low_profile"`
}

// NewAttackManager creates and initializes an AttackManager.
func NewAttackManager(wrapper *core.WebWrapper, villageID string, troopManager *TroopManager, gameMap *Map) *AttackManager {
	return &AttackManager{
		Wrapper:           wrapper,
		VillageID:         villageID,
		TroopManager:      troopManager,
		Map:               gameMap,
		Logger:            log.New(os.Stdout, "[Attack] ", log.LstdFlags),
		MaxFarms:          15,
		FarmRadius:        50,
		FarmMinPoints:     0,
		FarmMaxPoints:     1000,
		ScoutFarmAmount:   5,
		ignored:           make(map[string]bool),
	}
}

// FindFarmTargets finds all barbarian villages within the farm radius.
func (am *AttackManager) FindFarmTargets() {
	am.Targets = []VillageInfo{}
	for _, village := range am.Map.Villages {
		if village.Owner == "0" && am.Map.GetDist(village.Location) <= am.FarmRadius {
			am.Targets = append(am.Targets, village)
		}
	}
}

// SendFarm sends a farming attack to a specific target village.
// This is a simplified port of the core logic. The actual attack HTTP requests are complex
// and will be handled by a dedicated `attack` method (currently a placeholder).
func (am *AttackManager) SendFarm(target VillageInfo) (bool, error) {
	if am.farmBagLimitReached {
		am.Logger.Printf("Skipping farm to %s: farm bag limit reached.", target.ID)
		return false, nil
	}

	chosenTemplate := am.getTemplateForTarget(target.ID)
	if chosenTemplate == nil {
		am.Logger.Printf("No suitable farm template found for target %s", target.ID)
		return false, nil
	}

	troopsToSend := make(map[string]int)
	for unit, count := range chosenTemplate.Units {
		troopsToSend[unit] = count
	}

	// This block handles the dynamic C-Farm logic from the Python version.
	// It requires a ReportManager, which is not yet ported. Placeholder for now.
	if chosenTemplate.Calculate == "total_res_div_80" {
		// totalResources := am.ReportManager.GetScoutedResources(target.ID)
		totalResources := 0 // Placeholder
		if totalResources > 0 {
			numLCNeeded := int(math.Ceil(float64(totalResources) / 80.0))
			availableLC := am.TroopManager.GetTroops()["light"]
			troopsToSend["light"] = min(numLCNeeded, availableLC)
			if troopsToSend["light"] == 0 {
				am.Logger.Printf("Skipping C-type farm on %s: not enough light cavalry.", target.ID)
				return false, nil
			}
		} else {
			am.Logger.Printf("Skipping C-type farm on %s due to no scout info.", target.ID)
			// In a full implementation, we might send a scout here.
			return false, nil
		}
	}

	// Partial sending logic
	finalTroopsToSend := make(map[string]int)
	isMissingUnits := false
	for unit, required := range troopsToSend {
		available := am.TroopManager.GetTroops()[unit]
		if available < required {
			isMissingUnits = true
		}
		finalTroopsToSend[unit] = min(available, required)
	}

	if isMissingUnits {
		am.Logger.Printf("Partial farm to %s: Not enough units for full template. Sending available.", target.ID)
	}

	// Check if we are sending any troops at all
	totalTroops := 0
	for _, count := range finalTroopsToSend {
		totalTroops += count
	}
	if totalTroops == 0 {
		am.Logger.Printf("Not enough units to farm %s: All required units are zero.", target.ID)
		return false, nil
	}

	// The actual attack execution would happen here.
	// success := am.attack(target.ID, finalTroopsToSend)
	success := true // Placeholder
	if !success {
		am.Logger.Printf("Failed to send attack to %s", target.ID)
		return false, nil
	}

	am.Logger.Printf("Attack sent to %s with troops: %v", target.ID, finalTroopsToSend)
	// Update local troop counts after sending
	am.TroopManager.UpdateTroops(finalTroopsToSend, true) // true for decrement
	am.attacked(target.ID, true, true)

	return true, nil
}

// getTemplateForTarget selects the appropriate farming template (A/B/C logic).
// This requires a ReportManager, so it's simplified for now.
func (am *AttackManager) getTemplateForTarget(targetID string) *TroopTemplate {
	// This is a placeholder. A full implementation needs ReportManager
	// to check last haul status and scouted resources.
	// For now, it just returns the default template.
	for _, t := range am.Templates {
		if t.Condition == "default" {
			return &t
		}
	}
	// Fallback to the first template if no default is found
	if len(am.Templates) > 0 {
		return &am.Templates[0]
	}
	return nil
}

// attacked updates the attack cache for a village.
func (am *AttackManager) attacked(villageID string, scout, safe bool) error {
	cacheDir := filepath.Join("cache", "attacks")
	if err := os.MkdirAll(cacheDir, 0755); err != nil {
		return fmt.Errorf("could not create cache directory: %w", err)
	}

	entry := AttackCacheEntry{
		LastAttack: time.Now().Unix(),
		Scout:      scout,
		Safe:       safe,
	}

	filePath := filepath.Join(cacheDir, fmt.Sprintf("%s.json", villageID))
	data, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("failed to marshal cache entry: %w", err)
	}

	return os.WriteFile(filePath, data, 0644)
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
