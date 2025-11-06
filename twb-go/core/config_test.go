package core

import (
	"os"
	"path/filepath"
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
	cm, err := NewConfigManager(configPath, nil)
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
	if config.Bot.TickInterval.Seconds() != 10 {
		t.Errorf("Expected TickInterval to be 10, got %f", config.Bot.TickInterval.Seconds())
	}

	// Test with a config file that has a tick_interval
	configContentWithTickInterval := `
bot:
  server: http://example.com
  tick_interval: 15s
credentials:
  user_agent: "test-agent"
  cookie: "test-cookie"
`
	configPathWithTickInterval := filepath.Join(tmpDir, "config_with_tick_interval.yaml")
	if err := os.WriteFile(configPathWithTickInterval, []byte(configContentWithTickInterval), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	cmWithTickInterval, err := NewConfigManager(configPathWithTickInterval, nil)
	if err != nil {
		t.Fatalf("NewConfigManager failed: %v", err)
	}

	configWithTickInterval := cmWithTickInterval.GetConfig()
	if configWithTickInterval.Bot.TickInterval.Seconds() != 15 {
		t.Errorf("Expected TickInterval to be 15, got %f", configWithTickInterval.Bot.TickInterval.Seconds())
	}
}
