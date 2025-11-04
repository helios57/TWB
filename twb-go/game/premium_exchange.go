package game

import (
	"fmt"
	"twb-go/core"
)

// PremiumExchange handles the logic for interacting with the premium exchange.
type PremiumExchange struct {
	wrapper   *core.WebWrapper
	stock     map[string]int
	capacity  map[string]int
	tax       map[string]float64
	constants map[string]float64
}

// NewPremiumExchange creates a new PremiumExchange.
func NewPremiumExchange(wrapper *core.WebWrapper, stock, capacity map[string]int, tax, constants map[string]float64) *PremiumExchange {
	return &PremiumExchange{
		wrapper:   wrapper,
		stock:     stock,
		capacity:  capacity,
		tax:       tax,
		constants: constants,
	}
}

// CalculateCost calculates the cost of buying or selling a certain amount of a resource.
func (pe *PremiumExchange) CalculateCost(item string, amount int) (float64, error) {
	stock, ok := pe.stock[item]
	if !ok {
		return 0, fmt.Errorf("invalid item: %s", item)
	}
	capacity, ok := pe.capacity[item]
	if !ok {
		return 0, fmt.Errorf("invalid item: %s", item)
	}

	if amount > 0 && stock-amount < 0 {
		return 0, fmt.Errorf("not enough stock to buy %d %s", amount, item)
	}
	if amount < 0 && stock-amount > capacity {
		return 0, fmt.Errorf("cannot sell %d %s: capacity exceeded", -amount, item)
	}

	tax := pe.tax["buy"]
	if amount < 0 {
		tax = pe.tax["sell"]
	}

	priceBefore, err := pe.calculateMarginalPrice(stock, capacity)
	if err != nil {
		return 0, err
	}
	priceAfter, err := pe.calculateMarginalPrice(stock-amount, capacity)
	if err != nil {
		return 0, err
	}

	return (1.0 + tax) * (priceBefore + priceAfter) * float64(amount) / 2.0, nil
}

// calculateMarginalPrice calculates the marginal price of a resource.
func (pe *PremiumExchange) calculateMarginalPrice(e, a int) (float64, error) {
	c := pe.constants
	denominator := float64(a) + c["stock_size_modifier"]
	if denominator == 0 {
		return 0, fmt.Errorf("stock size modifier results in division by zero")
	}
	return c["resource_base_price"] - c["resource_price_elasticity"]*float64(e)/denominator, nil
}
