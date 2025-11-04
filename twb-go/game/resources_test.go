package game

import (
	"strconv"
	"sync"
	"testing"
)

func TestResourceManager(t *testing.T) {
	rm := NewResourceManager()

	// Test Update
	rm.Update(100, 100, 100, 10, 1000)
	if rm.Actual.Wood != 100 || rm.Actual.Stone != 100 || rm.Actual.Iron != 100 || rm.Actual.Pop != 10 {
		t.Errorf("Update failed. Got %+v", rm.Actual)
	}

	// Test CalculateIncome
	reportCache := &ReportCache{} // Placeholder
	rm.CalculateIncome(200, 200, 200, reportCache)
	if rm.income.Mines.Wood != 200 {
		t.Errorf("Expected mines income to be 200, got %d", rm.income.Mines.Wood)
	}
	if rm.income.Total.Wood != 300 {
		t.Errorf("Expected total income to be 300, got %d", rm.income.Total.Wood)
	}

	// Test CanAfford
	affordable := Resources{Wood: 50, Stone: 50, Iron: 50, Pop: 5}
	if !rm.CanAfford(affordable) {
		t.Errorf("CanAfford failed for affordable resources.")
	}
	unaffordable := Resources{Wood: 150, Stone: 50, Iron: 50, Pop: 5}
	if rm.CanAfford(unaffordable) {
		t.Errorf("CanAfford failed for unaffordable resources.")
	}

	// Test Request and CancelRequest
	request := Resources{Wood: 20, Stone: 20, Iron: 20, Pop: 2}
	rm.Request("building", request)
	if _, ok := rm.requested["building"]; !ok {
		t.Errorf("Request failed. Request not found.")
	}
	rm.CancelRequest("building")
	if _, ok := rm.requested["building"]; ok {
		t.Errorf("CancelRequest failed. Request still exists.")
	}

	// Test ManageMarket
	rm.ManageMarket(true)
}

func TestResourceManagerConcurrency(t *testing.T) {
	rm := NewResourceManager()
	rm.Update(10000, 10000, 10000, 1000, 10000)

	var wg sync.WaitGroup
	for i := 0; i < 100; i++ {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			source := "building" + strconv.Itoa(i)
			cost := Resources{Wood: 10, Stone: 10, Iron: 10, Pop: 1}
			rm.Request(source, cost)
			rm.lock.Lock()
			if rm.Actual.Wood >= cost.Wood && rm.Actual.Stone >= cost.Stone && rm.Actual.Iron >= cost.Iron && rm.Actual.Pop >= cost.Pop {
				rm.Actual.Wood -= cost.Wood
				rm.Actual.Stone -= cost.Stone
				rm.Actual.Iron -= cost.Iron
				rm.Actual.Pop -= cost.Pop
			}
			rm.lock.Unlock()
			rm.ManageMarket(true)
		}(i)
	}
	wg.Wait()
}
