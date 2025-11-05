package main

import (
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
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
villages:
  "123": {}
`
	configPath := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	// Create a mock server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		html := `
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
		fmt.Fprintln(w, html)
	}))
	defer server.Close()

	// Create a new Bot
	bot, err := NewBot(configPath, strings.NewReader("http://test.com\ntest-agent\ntest-cookie\n"))
	if err != nil {
		t.Fatalf("NewBot failed: %v", err)
	}
	bot.Wrapper.Endpoint = server.URL
	bot.Villages[0].BuildingManager.Costs["main"] = game.BuildingCost{Wood: 100, Stone: 100, Iron: 100, Pop: 10, CanBuild: true}

	// Run the bot
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
