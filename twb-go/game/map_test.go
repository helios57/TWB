package game

import (
	"math"
	"testing"
	"twb-go/core"
)

func TestMap(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2, "test-agent", "test-cookie")
	gameMap := NewMap(wrapper, "123")
	gameMap.myLocation = [2]int{500, 500}

	// Test GetDist
	dist := gameMap.GetDist([2]int{503, 504})
	expected := 5.0
	if math.Abs(dist-expected) > 0.001 {
		t.Errorf("Expected distance to be %f, got %f", expected, dist)
	}
}
