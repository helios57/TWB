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
	if config.Bot.MinTickInterval.Seconds() != 30 {
		t.Errorf("Expected MinTickInterval to be 30, got %f", config.Bot.MinTickInterval.Seconds())
	}
	if config.Bot.MaxTickInterval.Seconds() != 300 {
		t.Errorf("Expected MaxTickInterval to be 300, got %f", config.Bot.MaxTickInterval.Seconds())
	}

	// Test with a config file that has a tick_interval
	configContentWithTickInterval := `
bot:
  server: http://example.com
  min_tick_interval: 15s
  max_tick_interval: 150s
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
	if configWithTickInterval.Bot.MinTickInterval.Seconds() != 15 {
		t.Errorf("Expected MinTickInterval to be 15, got %f", configWithTickInterval.Bot.MinTickInterval.Seconds())
	}
	if configWithTickInterval.Bot.MaxTickInterval.Seconds() != 150 {
		t.Errorf("Expected MaxTickInterval to be 150, got %f", configWithTickInterval.Bot.MaxTickInterval.Seconds())
	}
}
