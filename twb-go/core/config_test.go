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
	configContent := `{
    "bot": {
        "random_delay": {
            "min_delay": 1,
            "max_delay": 5
        },
        "attack_timing": {
            "default": 100
        }
    },
    "webmanager": {
        "host": "127.0.0.1",
        "port": 8080,
        "refresh": 5
    },
    "villages": {
        "123": {
            "building": "default_template",
            "units": "default_units"
        }
    },
    "credentials": {
        "user": "test_user"
    }
}`
	configPath := filepath.Join(tmpDir, "config.json")
	if err := os.WriteFile(configPath, []byte(configContent), 0644); err != nil {
		t.Fatalf("Failed to write dummy config file: %v", err)
	}

	// Test NewConfigManager and LoadConfig
	cm, err := NewConfigManager(configPath)
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
	if config.Villages["123"].Building != "default_template" {
		t.Errorf("Expected building template to be 'default_template', got '%s'", config.Villages["123"].Building)
	}

	// Test UpdateVillageConfig and SaveConfig
	cm.UpdateVillageConfig("123", "building", "new_template")
	updatedConfig := cm.GetConfig()
	if updatedConfig.Villages["123"].Building != "new_template" {
		t.Errorf("Expected building template to be 'new_template', got '%s'", updatedConfig.Villages["123"].Building)
	}

	// Verify the file was saved correctly
	cm2, err := NewConfigManager(configPath)
	if err != nil {
		t.Fatalf("NewConfigManager (reload) failed: %v", err)
	}
	reloadedConfig := cm2.GetConfig()
	if reloadedConfig.Villages["123"].Building != "new_template" {
		t.Errorf("Expected reloaded building template to be 'new_template', got '%s'", reloadedConfig.Villages["123"].Building)
	}
}
