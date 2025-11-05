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
	wrapper     *core.WebWrapper
	villageID   string
	resman      *ResourceManager
	troops      map[string]int
	TotalTroops map[string]int
	RecruitData map[string]UnitCost
	smithData   map[string]map[string]string
	lock        sync.Mutex
}

// NewTroopManager creates a new TroopManager.
func NewTroopManager(wrapper *core.WebWrapper, villageID string, resman *ResourceManager) *TroopManager {
	return &TroopManager{
		wrapper:     wrapper,
		villageID:   villageID,
		resman:      resman,
		troops:      make(map[string]int),
		TotalTroops: make(map[string]int),
		RecruitData: make(map[string]UnitCost),
		smithData:   make(map[string]map[string]string),
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

// ExecuteRecruitAction recruits the troops specified in the action.
func (tm *TroopManager) ExecuteRecruitAction(action *RecruitAction) error {
	tm.lock.Lock()
	defer tm.lock.Unlock()

	cost, ok := tm.RecruitData[action.Unit]
	if !ok {
		return fmt.Errorf("unit %s not found in recruit data", action.Unit)
	}

	if !cost.RequirementsMet {
		return fmt.Errorf("requirements not met for unit %s", action.Unit)
	}

	if !tm.resman.CanAfford(Resources{Wood: cost.Wood * action.Amount, Stone: cost.Stone * action.Amount, Iron: cost.Iron * action.Amount, Pop: cost.Pop * action.Amount}) {
		return fmt.Errorf("not enough resources to recruit %d of %s", action.Amount, action.Unit)
	}

	// Simulate resource deduction
	tm.resman.Actual.Wood -= cost.Wood * action.Amount
	tm.resman.Actual.Stone -= cost.Stone * action.Amount
	tm.resman.Actual.Iron -= cost.Iron * action.Amount
	tm.resman.Actual.Pop -= cost.Pop * action.Amount

	tm.TotalTroops[action.Unit] += action.Amount
	fmt.Printf("Recruiting %d %s\n", action.Amount, action.Unit)
	return nil
}
