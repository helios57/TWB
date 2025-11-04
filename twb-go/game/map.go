package game

import (
	"math"
	"sync"
	"twb-go/core"
)

// VillageInfo represents the information about a village on the map.
type VillageInfo struct {
	ID       string `json:"id"`
	Name     string `json:"name"`
	Location [2]int `json:"location"`
	Points   int    `json:"points"`
	Owner    string `json:"owner"`
}

// Map represents the game map.
type Map struct {
	wrapper    *core.WebWrapper
	villageID  string
	Villages   map[string]VillageInfo
	myLocation [2]int
	lock       sync.Mutex
}

// NewMap creates a new Map.
func NewMap(wrapper *core.WebWrapper, villageID string) *Map {
	return &Map{
		wrapper:   wrapper,
		villageID: villageID,
		Villages:  make(map[string]VillageInfo),
	}
}

// GetMap fetches and parses the map data.
func (m *Map) GetMap() error {
	// In a real implementation, this would fetch and parse the map data.
	// For now, we'll just simulate it.
	m.lock.Lock()
	defer m.lock.Unlock()

	m.myLocation = [2]int{500, 500}
	m.Villages = map[string]VillageInfo{
		"1": {ID: "1", Name: "Barbarian Village 1", Location: [2]int{501, 501}, Points: 100, Owner: "0"},
		"2": {ID: "2", Name: "Barbarian Village 2", Location: [2]int{499, 499}, Points: 150, Owner: "0"},
		"3": {ID: "3", Name: "Player Village", Location: [2]int{500, 501}, Points: 200, Owner: "1"},
	}
	return nil
}

// GetDist calculates the distance from the player's village to the given coordinates.
func (m *Map) GetDist(extLoc [2]int) float64 {
	return math.Sqrt(math.Pow(float64(m.myLocation[0]-extLoc[0]), 2) + math.Pow(float64(m.myLocation[1]-extLoc[1]), 2))
}
