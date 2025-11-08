package game

import (
	"fmt"
	"sync"
	"time"
)

// ReportCache is a placeholder for the report cache.
type ReportCache struct {
	// ... to be implemented
}

// Resources represents the amount of each resource available.
type Resources struct {
	Wood  int `json:"Wood"`
	Stone int `json:"Stone"`
	Iron  int `json:"Iron"`
	Pop   int `json:"Pop"`
}

// Income represents the resource income per hour.
type Income struct {
	Mines   Resources `json:"Mines"`
	Farming Resources `json:"Farming"`
	Total   Resources `json:"Total"`
}

// ResourceManager manages the resources for a village.
type ResourceManager struct {
	Actual          Resources `json:"Actual"`
	requested       map[string]Resources
	storage         int
	Income          Income `json:"Income"`
	doPremiumTrade  bool
	tradeBias       float64
	lastTrade       int64
	tradeMaxPerHour int
	tradeMaxDuration int
	lock            sync.Mutex
}

// NewResourceManager creates a new ResourceManager.
func NewResourceManager() *ResourceManager {
	return &ResourceManager{
		requested:       make(map[string]Resources),
		doPremiumTrade:  false,
		tradeBias:       1.0,
		tradeMaxPerHour: 1,
		tradeMaxDuration: 2,
	}
}

// Update updates the current resources.
func (rm *ResourceManager) Update(wood, stone, iron, pop, storage int) {
	rm.lock.Lock()
	defer rm.lock.Unlock()
	rm.Actual.Wood = wood
	rm.Actual.Stone = stone
	rm.Actual.Iron = iron
	rm.Actual.Pop = pop
	rm.storage = storage
}

// CalculateIncome calculates the resource income per hour.
func (rm *ResourceManager) CalculateIncome(woodProd, stoneProd, ironProd int, reportCache *ReportCache) {
	// In a real implementation, this would fetch and parse the reports.
	// For now, we'll just simulate it.
	rm.lock.Lock()
	defer rm.lock.Unlock()

	rm.Income.Mines = Resources{Wood: woodProd, Stone: stoneProd, Iron: ironProd}
	rm.Income.Farming = Resources{Wood: 100, Stone: 100, Iron: 100} // Dummy data
	rm.Income.Total = Resources{
		Wood:  rm.Income.Mines.Wood + rm.Income.Farming.Wood,
		Stone: rm.Income.Mines.Stone + rm.Income.Farming.Stone,
		Iron:  rm.Income.Mines.Iron + rm.Income.Farming.Iron,
	}
}

// CanAfford checks if there are enough resources for a given cost.
func (rm *ResourceManager) CanAfford(cost Resources) bool {
	rm.lock.Lock()
	defer rm.lock.Unlock()
	return rm.Actual.Wood >= cost.Wood &&
		rm.Actual.Stone >= cost.Stone &&
		rm.Actual.Iron >= cost.Iron &&
		rm.Actual.Pop >= cost.Pop
}

// Request requests a certain amount of resources for a specific purpose.
func (rm *ResourceManager) Request(source string, cost Resources) {
	rm.lock.Lock()
	defer rm.lock.Unlock()
	rm.requested[source] = cost
}

// CancelRequest cancels a resource request.
func (rm *ResourceManager) CancelRequest(source string) {
	rm.lock.Lock()
	defer rm.lock.Unlock()
	delete(rm.requested, source)
}

// ManageMarket manages the market.
func (rm *ResourceManager) ManageMarket(dropExisting bool) {
	last := rm.lastTrade + int64(3600*rm.tradeMaxPerHour)
	if last > time.Now().Unix() {
		return
	}

	hour := time.Now().Hour()
	if hour >= 23 || hour < 6 {
		return
	}

	if dropExisting {
		// ... to be implemented
	}

	plenty := rm.getPlentyOff()
	if plenty != "" && !rm.inNeedOf(plenty) {
		item, howMany := rm.getNeeds()
		if item != "" {
			// ... to be implemented
			fmt.Printf("Need %d of %s\n", howMany, item)
		}
	}
}

func (rm *ResourceManager) getPlentyOff() string {
	// ... to be implemented
	return ""
}

func (rm *ResourceManager) inNeedOf(item string) bool {
	// ... to be implemented
	return false
}

func (rm *ResourceManager) getNeeds() (string, int) {
	// ... to be implemented
	return "", 0
}
