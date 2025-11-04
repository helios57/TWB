package game

import (
	"strconv"
	"testing"
	"twb-go/core"
)

func BenchmarkBuildingManager_GetNextBuildingAction_Linear(b *testing.B) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	bm.SetMode("linear")
	queue := []string{}
	for i := 0; i < 100; i++ {
		queue = append(queue, "main:"+strconv.Itoa(i+1))
	}
	bm.SetQueue(queue)
	bm.Costs["main"] = BuildingCost{CanBuild: true}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		bm.GetNextBuildingAction()
	}
}

func BenchmarkBuildingManager_GetNextBuildingAction_Dynamic(b *testing.B) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	bm := NewBuildingManager(wrapper, "123", rm)
	bm.SetMode("dynamic")
	targetLevels := map[string]int{}
	for i := 0; i < 20; i++ {
		targetLevels["main"+strconv.Itoa(i)] = 20
	}
	bm.SetTargetLevels(targetLevels)
	bm.Costs["main"] = BuildingCost{CanBuild: true}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		bm.GetNextBuildingAction()
	}
}
