package game

import (
	"testing"
	"twb-go/core"
)

func TestDefenceManager(t *testing.T) {
	wrapper, _ := core.NewWebWrapper("http://example.com", 1, 2)
	rm := NewResourceManager()
	dm := NewDefenceManager(wrapper, "123", rm)

	// Test Update
	err := dm.Update()
	if err != nil {
		t.Fatalf("Update failed: %v", err)
	}
	if dm.underAttack {
		t.Errorf("Expected village to not be under attack")
	}
}
