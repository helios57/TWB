package core

import (
	"fmt"
	"os"
	"sync"
	"gopkg.in/yaml.v3"
)

// PlannerConfig holds the configuration for the Planner.
type PlannerConfig struct {
	RecruitmentGoals map[string]int `yaml:"recruitment_goals"`
}

// Config corresponds to the structure of the YAML config file.
type Config struct {
	Bot         BotConfig                `yaml:"bot"`
	WebManager  WebManagerConfig         `yaml:"webmanager"`
	Planner     PlannerConfig            `yaml:"planner"`
	Villages    map[string]VillageConfig `yaml:"villages"`
	Credentials map[string]string        `yaml:"credentials"`
}

// BotConfig holds bot-related settings.
type BotConfig struct {
	Server           string            `yaml:"server"`
	RandomDelay      RandomDelayConfig `yaml:"random_delay"`
	AttackTiming     map[string]int    `yaml:"attack_timing"`
	ForcedPeaceTimes []PeaceTime       `yaml:"forced_peace_times"`
}

// PeaceTime represents a period of forced peace.
type PeaceTime struct {
	Start string `yaml:"start"`
	End   string `yaml:"end"`
}

// RandomDelayConfig specifies the min/max delay for requests.
type RandomDelayConfig struct {
	MinDelay int `yaml:"min_delay"`
	MaxDelay int `yaml:"max_delay"`
}

// WebManagerConfig holds web UI related settings.
type WebManagerConfig struct {
	Host    string `yaml:"host"`
	Port    int    `yaml:"port"`
	Refresh int    `yaml:"refresh"`
}

// VillageConfig holds settings specific to a village.
type VillageConfig struct {
	Building string `yaml:"building"`
	Units    string `yaml:"units"`
}

// ConfigManager handles loading and saving of the bot's configuration.
type ConfigManager struct {
	configPath string
	config     *Config
	lock       sync.Mutex
}

// NewConfigManager creates and initializes a new ConfigManager.
func NewConfigManager(path string) (*ConfigManager, error) {
	cm := &ConfigManager{
		configPath: path,
	}
	err := cm.LoadConfig()
	if err != nil {
		return nil, err
	}
	return cm, nil
}

// LoadConfig loads the configuration from the specified YAML file.
func (cm *ConfigManager) LoadConfig() error {
	cm.lock.Lock()
	defer cm.lock.Unlock()

	file, err := os.ReadFile(cm.configPath)
	if err != nil {
		return fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := yaml.Unmarshal(file, &config); err != nil {
		return fmt.Errorf("failed to decode YAML from config file: %w", err)
	}
	cm.config = &config
	return nil
}

// saveConfig is the internal, non-locking implementation of saving the configuration.
func (cm *ConfigManager) saveConfig() error {
	data, err := yaml.Marshal(cm.config)
	if err != nil {
		return fmt.Errorf("failed to encode config to YAML: %w", err)
	}

	if err := os.WriteFile(cm.configPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write to config file: %w", err)
	}
	return nil
}

// SaveConfig saves the current configuration to the YAML file.
func (cm *ConfigManager) SaveConfig() error {
	cm.lock.Lock()
	defer cm.lock.Unlock()
	return cm.saveConfig()
}

// GetConfig returns the entire configuration.
func (cm *ConfigManager) GetConfig() *Config {
	return cm.config
}

// UpdateVillageConfig updates a specific key for a village and saves the config.
func (cm *ConfigManager) UpdateVillageConfig(villageID, key string, value interface{}) {
	cm.lock.Lock()
	defer cm.lock.Unlock()

	if village, ok := cm.config.Villages[villageID]; ok {
		switch key {
		case "building":
			village.Building = value.(string)
		case "units":
			village.Units = value.(string)
		}
		cm.config.Villages[villageID] = village
		cm.saveConfig() // Call the internal, non-locking save
	}
}
