package core

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"strings"
	"sync"

	"gopkg.in/yaml.v3"
)

// PlannerConfig holds the configuration for the Planner.
type PlannerConfig struct {
	RecruitmentGoals      map[string]int `yaml:"recruitment_goals"`
	RecruitmentBatchSize int            `yaml:"recruitment_batch_size"`
}

// SolverConfig holds the configuration for the Solver.
type SolverConfig struct {
	EconomicWeight  float64 `yaml:"economic_weight"`
	StrategicWeight float64 `yaml:"strategic_weight"`
	MilitaryWeight  float64 `yaml:"military_weight"`
}

// Config corresponds to the structure of the YAML config file.
type Config struct {
	Bot                   BotConfig                       `yaml:"bot"`
	WebManager            WebManagerConfig                `yaml:"webmanager"`
	Solver                SolverConfig                    `yaml:"solver"`
	Planner               PlannerConfig                   `yaml:"planner"`
	BuildingPrerequisites map[string]map[string]int       `yaml:"building_prerequisites"`
	Villages              map[string]VillageConfig        `yaml:"villages"`
	Credentials           map[string]string               `yaml:"credentials"`
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
func NewConfigManager(path string, reader io.Reader) (*ConfigManager, error) {
	cm := &ConfigManager{
		configPath: path,
	}

	for {
		exists, err := cm.LoadConfig()
		if err != nil {
			return nil, err
		}
		if !exists {
			if reader == nil {
				tty, err := os.Open("/dev/tty")
				if err != nil {
					return nil, fmt.Errorf("failed to open tty: %w", err)
				}
				defer tty.Close()
				reader = tty
			}
			bufReader := bufio.NewReader(reader)
			newConfig, err := createConfig(bufReader)
			if err != nil {
				return nil, fmt.Errorf("failed to create config: %w", err)
			}
			cm.config = newConfig
			if err := cm.SaveConfig(); err != nil {
				return nil, fmt.Errorf("failed to save config: %w", err)
			}
			continue
		}
		if err := cm.Validate(); err != nil {
			fmt.Println("Configuration is invalid, please re-enter details.")
			if reader == nil {
				tty, err := os.Open("/dev/tty")
				if err != nil {
					return nil, fmt.Errorf("failed to open tty: %w", err)
				}
				defer tty.Close()
				reader = tty
			}
			bufReader := bufio.NewReader(reader)
			newConfig, err := createConfig(bufReader)
			if err != nil {
				return nil, fmt.Errorf("failed to create config: %w", err)
			}
			cm.config = newConfig
			if err := cm.SaveConfig(); err != nil {
				return nil, fmt.Errorf("failed to save config: %w", err)
			}
			continue
		}
		break
	}

	return cm, nil
}

// Validate checks if the essential configuration values are set.
func (cm *ConfigManager) Validate() error {
	cm.lock.Lock()
	defer cm.lock.Unlock()

	if cm.config.Bot.Server == "" {
		return fmt.Errorf("server URL is not set")
	}
	if cm.config.Credentials["user_agent"] == "" {
		return fmt.Errorf("user_agent is not set")
	}
	if cm.config.Credentials["cookie"] == "" {
		return fmt.Errorf("cookie is not set")
	}
	return nil
}

func createConfig(reader *bufio.Reader) (*Config, error) {
	fmt.Print("Enter server URL: ")
	server, _ := reader.ReadString('\n')
	fmt.Print("Enter User-Agent: ")
	userAgent, _ := reader.ReadString('\n')
	fmt.Print("Enter Cookie: ")
	cookie, _ := reader.ReadString('\n')

	return &Config{
		Bot: BotConfig{
			Server: strings.TrimSpace(server),
			RandomDelay: RandomDelayConfig{
				MinDelay: 1,
				MaxDelay: 5,
			},
		},
		WebManager: WebManagerConfig{
			Host: "127.0.0.1",
			Port: 8080,
		},
		Solver: SolverConfig{
			EconomicWeight:  1.0,
			StrategicWeight: 2.0,
			MilitaryWeight:  1.5,
		},
		Planner: PlannerConfig{
			RecruitmentGoals: map[string]int{
				"spear": 250,
			},
			RecruitmentBatchSize: 10,
		},
		BuildingPrerequisites: map[string]map[string]int{
			"snob": {
				"main":   20,
				"smith":  20,
				"market": 10,
			},
		},
		Villages: map[string]VillageConfig{
			"123": {
				Building: "default",
				Units:    "default",
			},
		},
		Credentials: map[string]string{
			"user_agent": strings.TrimSpace(userAgent),
			"cookie":     strings.TrimSpace(cookie),
		},
	}, nil
}

// LoadConfig loads the configuration from the specified YAML file.
func (cm *ConfigManager) LoadConfig() (bool, error) {
	cm.lock.Lock()
	defer cm.lock.Unlock()

	file, err := os.ReadFile(cm.configPath)
	if err != nil {
		if os.IsNotExist(err) {
			return false, nil
		}
		return false, fmt.Errorf("failed to read config file: %w", err)
	}

	var config Config
	if err := yaml.Unmarshal(file, &config); err != nil {
		return false, fmt.Errorf("failed to decode YAML from config file: %w", err)
	}
	cm.config = &config
	return true, nil
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

// SetConfig sets the configuration for testing purposes.
func (cm *ConfigManager) SetConfig(config *Config) {
	cm.config = config
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
