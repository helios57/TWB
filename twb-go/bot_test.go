package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"twb-go/core"
	"twb-go/game"
)

func TestBot(t *testing.T) {
	// Create a temporary directory for the test
	tmpDir, err := os.MkdirTemp("", "config-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	// Create a dummy config file
	configContent := `
bot:
  server: http://example.com
`
	configPath := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	// Create a mock server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var html string
		if strings.Contains(r.URL.String(), "overview_villages") {
			html = `
				<a href="game.php?village=123&screen=overview">Village 1</a>
				<a href="game.php?village=456&screen=overview">Village 2</a>
			`
		} else {
			html = `
				<script>
					TribalWars.updateGameData({
						"village": {
							"id": 123,
							"name": "Test Village",
							"wood": 5000.5,
							"stone": 5000.2,
							"iron": 5000.8,
							"pop": 100,
							"pop_max": 1000,
							"storage_max": 2000,
							"buildings": {
								"main": "1",
								"barracks": "1",
								"smith": "1",
								"market": "1",
								"snob": "0"
							}
						}
					});
				</script>
				<table id="units_home">
					<tr><th>Unit</th><th>Count</th></tr>
					<tr>
						<td class="unit-item unit-item-spear">100</td>
						<td class="unit-item unit-item-sword">50</td>
						<td class="unit-item unit-item-axe">25</td>
					</tr>
				</table>
			`
		}
		fmt.Fprintln(w, html)
	}))
	defer server.Close()

	// Create a ConfigManager and WebWrapper
	cm, err := core.NewConfigManager(configPath, strings.NewReader("http://test.com\ntest-agent\ntest-cookie\n"))
	if err != nil {
		t.Fatalf("NewConfigManager failed: %v", err)
	}
	wrapper, err := core.NewWebWrapper(server.URL, 0, 0)
	if err != nil {
		t.Fatalf("NewWebWrapper failed: %v", err)
	}

	// Create a new Bot
	bot, err := newBotWithDeps(cm, wrapper)
	if err != nil {
		t.Fatalf("newBotWithDeps failed: %v", err)
	}

	// Assert that the villages are discovered correctly
	if len(bot.Villages) != 2 {
		t.Fatalf("Expected 2 villages, got %d", len(bot.Villages))
	}
	if bot.Villages[0].ID != "123" {
		t.Errorf("Expected village ID to be 123, got %s", bot.Villages[0].ID)
	}
	if bot.Villages[1].ID != "456" {
		t.Errorf("Expected village ID to be 456, got %s", bot.Villages[1].ID)
	}

	// Run the bot
	bot.Villages[0].BuildingManager.Costs["main"] = game.BuildingCost{Wood: 100, Stone: 100, Iron: 100, Pop: 10, CanBuild: true}
	for _, v := range bot.Villages {
		v.Run()
	}

	// Assert that the managers' states are updated correctly
	village := bot.Villages[0]
	if village.ResourceManager.Actual.Wood != 4900 {
		t.Errorf("Expected wood to be 4900, got %d", village.ResourceManager.Actual.Wood)
	}
	if village.BuildingManager.Levels["main"] != 2 {
		t.Errorf("Expected main level to be 2, got %d", village.BuildingManager.Levels["main"])
	}
}
