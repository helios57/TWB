package core

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestConfigManager(t *testing.T) {
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
  random_delay:
    min_delay: 1
    max_delay: 5
webmanager:
  host: 127.0.0.1
  port: 8080
credentials:
  user_agent: "test-agent"
  cookie: "test-cookie"
`
	configPath := filepath.Join(tmpDir, "config.yaml")
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	// Test NewConfigManager and LoadConfig
	cm, err := NewConfigManager(configPath, strings.NewReader("http://test.com\ntest-agent\ntest-cookie\n"))
	if err != nil {
		t.Fatalf("NewConfigManager failed: %v", err)
	}

	config := cm.GetConfig()
	if config.Bot.RandomDelay.MinDelay != 1 {
		t.Errorf("Expected MinDelay to be 1, got %d", config.Bot.RandomDelay.MinDelay)
	}
	if config.WebManager.Port != 8080 {
		t.Errorf("Expected Port to be 8080, got %d", config.WebManager.Port)
	}
}
