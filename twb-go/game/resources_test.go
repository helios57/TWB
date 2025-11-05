package game

import "testing"

func TestResourceManager_CanAfford(t *testing.T) {
	rm := NewResourceManager()
	rm.Update(100, 100, 100, 100, 100)

	testCases := []struct {
		name     string
		cost     Resources
		expected bool
	}{
		{"Can Afford", Resources{Wood: 50, Stone: 50, Iron: 50, Pop: 50}, true},
		{"Cannot Afford Wood", Resources{Wood: 150, Stone: 50, Iron: 50, Pop: 50}, false},
		{"Cannot Afford Stone", Resources{Wood: 50, Stone: 150, Iron: 50, Pop: 50}, false},
		{"Cannot Afford Iron", Resources{Wood: 50, Stone: 50, Iron: 150, Pop: 50}, false},
		{"Cannot Afford Pop", Resources{Wood: 50, Stone: 50, Iron: 50, Pop: 150}, false},
		{"Exact Amount", Resources{Wood: 100, Stone: 100, Iron: 100, Pop: 100}, true},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if rm.CanAfford(tc.cost) != tc.expected {
				t.Errorf("Expected %v, got %v", tc.expected, !tc.expected)
			}
		})
	}
}
