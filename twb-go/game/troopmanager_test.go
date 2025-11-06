package game

import (
	"io"
	"net/http"
	"strings"
	"testing"
	"twb-go/core"
)

func TestTroopManager_ExecuteRecruitAction(t *testing.T) {
	wrapper := &MockWebWrapper{}
	wrapper.GetURLFunc = func(url string) (*http.Response, error) {
		return &http.Response{
			Body: io.NopCloser(strings.NewReader(`<html><body><input type="hidden" name="h" value="12345" /></body></html>`)),
		}, nil
	}
	rm := NewResourceManager()
	rm.Update(10000, 10000, 10000, 1000, 10000)
	tm := NewTroopManager(wrapper, "123", rm)

	tm.RecruitData["spear"] = core.UnitCost{Wood: 50, Stone: 30, Iron: 10, Pop: 1, RequirementsMet: true}
	action := &RecruitAction{Unit: "spear", Amount: 100}

	err := tm.ExecuteRecruitAction(action)
	if err != nil {
		t.Fatalf("ExecuteRecruitAction failed: %v", err)
	}

	if tm.TotalTroops["spear"] != 100 {
		t.Errorf("Expected spear to be 100, got %d", tm.TotalTroops["spear"])
	}

	expectedResources := Resources{Wood: 5000, Stone: 7000, Iron: 9000, Pop: 900}
	if rm.Actual != expectedResources {
		t.Errorf("Expected resources to be %v, got %v", expectedResources, rm.Actual)
	}
}
