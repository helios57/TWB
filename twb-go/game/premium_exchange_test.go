package game

import (
	"math"
	"testing"
	"twb-go/core"
)

func TestPremiumExchange(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	stock := map[string]int{"wood": 1000}
	capacity := map[string]int{"wood": 2000}
	tax := map[string]float64{"buy": 0.1, "sell": 0.2}
	constants := map[string]float64{
		"stock_size_modifier":    1000.0,
		"resource_base_price":    1.0,
		"resource_price_elasticity": 0.5,
	}
	pe := NewPremiumExchange(wrapper, stock, capacity, tax, constants)

	// Test CalculateCost (buy)
	cost, err := pe.CalculateCost("wood", 100)
	if err != nil {
		t.Fatalf("CalculateCost failed: %v", err)
	}
	expected := 92.583333
	if math.Abs(cost-expected) > 0.001 {
		t.Errorf("Expected cost to be %f, got %f", expected, cost)
	}

	// Test CalculateCost (sell)
	cost, err = pe.CalculateCost("wood", -100)
	if err != nil {
		t.Fatalf("CalculateCost failed: %v", err)
	}
	expected = -99.0
	if math.Abs(cost-expected) > 0.001 {
		t.Errorf("Expected cost to be %f, got %f", expected, cost)
	}
}
