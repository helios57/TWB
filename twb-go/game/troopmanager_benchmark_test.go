package game

import (
	"strconv"
	"testing"
	"twb-go/core"
)

func BenchmarkTroopManager_Recruit(b *testing.B) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	tm := NewTroopManager(wrapper, "123", rm)
	tm.RecruitData["spear"] = UnitCost{Wood: 50, Stone: 30, Iron: 10, Pop: 1, RequirementsMet: true}
	wanted := make(map[string]map[string]int)
	wanted["barracks"] = make(map[string]int)
	for i := 0; i < 100; i++ {
		wanted["barracks"]["spear"+strconv.Itoa(i)] = 1
	}
	tm.SetWanted(wanted)

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		tm.Recruit("barracks")
	}
}
