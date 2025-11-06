package core

import (
	"testing"
	"time"
)

func TestExtractor_GameState(t *testing.T) {
	timeout := time.After(10 * time.Second)
	done := make(chan bool)

	go func() {
		html := `
		<script>
			TribalWars.updateGameData({
				"village": {
					"id": 123,
					"name": "Test Village",
					"wood": 100.5,
					"stone": 200.2,
					"iron": 300.8,
					"pop": 100,
					"pop_max": 1000,
					"storage_max": 2000,
					"buildings": {
						"main": "1",
						"barracks": "2"
					}
				}
			});
		</script>
	`

	gameState, err := Extractor.GameState(html)
	if err != nil {
		t.Fatalf("GameState failed: %v", err)
	}

	if gameState.Village.ID != 123 {
		t.Errorf("Expected village ID to be 123, got %d", gameState.Village.ID)
	}
	if gameState.Village.Name != "Test Village" {
		t.Errorf("Expected village name to be 'Test Village', got '%s'", gameState.Village.Name)
	}
	if gameState.Village.Wood != 100.5 {
		t.Errorf("Expected wood to be 100.5, got %f", gameState.Village.Wood)
	}
		done <- true
	}()

	select {
	case <-timeout:
		t.Fatal("Test timed out")
	case <-done:
	}
}

func TestExtractor_UnitsInVillage(t *testing.T) {
	timeout := time.After(10 * time.Second)
	done := make(chan bool)

	go func() {
		html := `
		<table id="units_home">
			<tr><th>Unit</th><th>Count</th></tr>
			<tr>
				<td class="unit-item unit-item-spear">100</td>
				<td class="unit-item unit-item-sword">50</td>
				<td class="unit-item unit-item-axe">25</td>
			</tr>
		</table>
	`

	units, err := Extractor.UnitsInVillage(html)
	if err != nil {
		t.Fatalf("UnitsInVillage failed: %v", err)
	}

	if units["spear"] != 100 {
		t.Errorf("Expected spear to be 100, got %d", units["spear"])
	}
	if units["sword"] != 50 {
		t.Errorf("Expected sword to be 50, got %d", units["sword"])
	}
	if units["axe"] != 25 {
		t.Errorf("Expected axe to be 25, got %d", units["axe"])
	}
		done <- true
	}()

	select {
	case <-timeout:
		t.Fatal("Test timed out")
	case <-done:
	}
}

func TestExtractor_VillageIDs(t *testing.T) {
	timeout := time.After(10 * time.Second)
	done := make(chan bool)

	go func() {
		html := `
		<div id="menu_row2_village">
			<a href="game.php?village=123&screen=overview">Village 1</a>
			<a href="game.php?village=456&screen=overview">Village 2</a>
		</div>
		<a href="game.php?village=789&screen=overview">Some other link</a>
	`

	villageIDs, err := Extractor.VillageIDs(html)
	if err != nil {
		t.Fatalf("VillageIDs failed: %v", err)
	}

	if len(villageIDs) != 2 {
		t.Fatalf("Expected 2 village IDs, got %d", len(villageIDs))
	}
	if villageIDs[0] != "123" {
		t.Errorf("Expected village ID to be 123, got %s", villageIDs[0])
	}
	if villageIDs[1] != "456" {
		t.Errorf("Expected village ID to be 456, got %s", villageIDs[1])
	}
		done <- true
	}()

	select {
	case <-timeout:
		t.Fatal("Test timed out")
	case <-done:
	}
}
