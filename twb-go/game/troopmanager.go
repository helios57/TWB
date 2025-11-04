package game

import (
	"fmt"
	"strconv"
	"strings"
	"sync"
	"twb-go/core"

	"github.com/PuerkitoBio/goquery"
)

// UnitCost represents the resource cost of a unit.
type UnitCost struct {
	Wood            int
	Stone           int
	Iron            int
	Pop             int
	RequirementsMet bool
}

// TroopManager manages the troops in a village.
type TroopManager struct {
	wrapper      *core.WebWrapper
	villageID    string
	resman       *ResourceManager
	troops       map[string]int
	TotalTroops  map[string]int
	RecruitData  map[string]UnitCost
	wanted       map[string]map[string]int
	wantedLevels map[string]int
	smithData    map[string]map[string]string
	lock         sync.Mutex
}

// NewTroopManager creates a new TroopManager.
func NewTroopManager(wrapper *core.WebWrapper, villageID string, resman *ResourceManager) *TroopManager {
	return &TroopManager{
		wrapper:      wrapper,
		villageID:    villageID,
		resman:       resman,
		troops:       make(map[string]int),
		TotalTroops:  make(map[string]int),
		RecruitData:  make(map[string]UnitCost),
		wanted:       make(map[string]map[string]int),
		wantedLevels: make(map[string]int),
		smithData:    make(map[string]map[string]string),
	}
}

// GetTroops returns a copy of the current troops in the village.
func (tm *TroopManager) GetTroops() map[string]int {
	tm.lock.Lock()
	defer tm.lock.Unlock()
	// Return a copy to prevent race conditions and unintended modifications
	newMap := make(map[string]int)
	for k, v := range tm.troops {
		newMap[k] = v
	}
	return newMap
}

// UpdateTroops modifies the troop counts, for example after sending an army.
// If decrement is true, it subtracts the counts; otherwise, it adds them.
func (tm *TroopManager) UpdateTroops(changes map[string]int, decrement bool) {
	tm.lock.Lock()
	defer tm.lock.Unlock()
	for unit, count := range changes {
		if decrement {
			tm.troops[unit] -= count
			tm.TotalTroops[unit] -= count
		} else {
			tm.troops[unit] += count
			tm.TotalTroops[unit] += count
		}
	}
}

// UpdateTotals updates the total amount of recruited units.
func (tm *TroopManager) UpdateTotals(html string) error {
	tm.lock.Lock()
	defer tm.lock.Unlock()

	doc, err := goquery.NewDocumentFromReader(strings.NewReader(html))
	if err != nil {
		return fmt.Errorf("failed to create goquery document: %w", err)
	}

	units := make(map[string]int)
	doc.Find("#units_home tr:nth-child(2) td.unit-item").Each(func(i int, s *goquery.Selection) {
		class, _ := s.Attr("class")
		parts := strings.Split(class, " ")
		unit := strings.TrimPrefix(parts[1], "unit-item-")
		count, _ := strconv.Atoi(s.Text())
		units[unit] = count
	})
	tm.troops = units
	tm.TotalTroops = units

	return nil
}

// SetWanted sets the target troop levels.
func (tm *TroopManager) SetWanted(wanted map[string]map[string]int) {
	tm.lock.Lock()
	defer tm.lock.Unlock()
	tm.wanted = wanted
}

// Recruit recruits a certain amount of a unit.
func (tm *TroopManager) Recruit(building string) error {
	tm.lock.Lock()
	defer tm.lock.Unlock()

	for unit, wantedAmount := range tm.wanted[building] {
		currentAmount, ok := tm.TotalTroops[unit]
		if !ok {
			currentAmount = 0
		}

		if wantedAmount > currentAmount {
			amountToRecruit := wantedAmount - currentAmount
			err := tm.recruit(unit, amountToRecruit)
			if err != nil {
				return err
			}
		}
	}

	return nil
}

// recruit sends a recruit request for the given unit.
func (tm *TroopManager) recruit(unitType string, amount int) error {
	// In a real implementation, this would send a recruit request.
	// For now, we'll just simulate it.
	cost, ok := tm.RecruitData[unitType]
	if !ok {
		return fmt.Errorf("unit %s not found in recruit data", unitType)
	}

	if !cost.RequirementsMet {
		return fmt.Errorf("requirements not met for unit %s", unitType)
	}

	if !tm.resman.CanAfford(Resources{Wood: cost.Wood * amount, Stone: cost.Stone * amount, Iron: cost.Iron * amount, Pop: cost.Pop * amount}) {
		return fmt.Errorf("not enough resources to recruit %d of %s", amount, unitType)
	}

	// Simulate resource deduction
	tm.resman.Actual.Wood -= cost.Wood * amount
	tm.resman.Actual.Stone -= cost.Stone * amount
	tm.resman.Actual.Iron -= cost.Iron * amount
	tm.resman.Actual.Pop -= cost.Pop * amount

	tm.TotalTroops[unitType] += amount
	return nil
}

// GetPlannedActions returns a list of the next planned troop-related actions.
func (tm *TroopManager) GetPlannedActions() []string {
	var actions []string

	// Planned Recruitment
	for _, units := range tm.wanted {
		for unit, wantedAmount := range units {
			currentAmount := tm.TotalTroops[unit]
			if wantedAmount > currentAmount {
				amountToRecruit := wantedAmount - currentAmount
				actions = append(actions, fmt.Sprintf("Recruit %d %s (Target: %d)", amountToRecruit, strings.Title(unit), wantedAmount))
			}
		}
	}

	// Planned Upgrades
	if len(tm.wantedLevels) > 0 {
		for unit, wantedLevel := range tm.wantedLevels {
			currentLevel := 0
			if tm.smithData != nil {
				if unitData, ok := tm.smithData[unit]; ok {
					if level, ok := unitData["level"]; ok {
						currentLevel, _ = strconv.Atoi(level)
					}
				}
			}

			if wantedLevel > currentLevel {
				actions = append(actions, fmt.Sprintf("Research %s to level %d", strings.Title(unit), wantedLevel))
			}
		}
	}

	return actions
}
