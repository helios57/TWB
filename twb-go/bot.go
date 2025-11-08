package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"math/rand"
	"os"
	"strings"
	"sync"
	"time"
	"twb-go/core"
	"twb-go/game"
	"twb-go/web"
)

// Bot represents the main bot application.
type Bot struct {
	Wrapper       core.WebWrapperInterface
	ConfigManager *core.ConfigManager
	Villages      []*game.Village
	paused        bool
	lock          sync.Mutex
	Hub           *web.Hub
}

// SerializableVillage is a representation of a village that is safe to serialize to JSON.
type SerializableVillage struct {
	ID            string
	Resources     *game.ResourceManager
	BuildingQueue []core.QueueItem
	TroopQueue    map[string][]core.QueueItem
	LastAction    game.Action
}

// newBotWithDeps creates a new Bot with dependencies.
func newBotWithDeps(cm *core.ConfigManager, wrapper core.WebWrapperInterface) (*Bot, error) {
	var villages []*game.Village

	// If we are in dry-run mode (using a mock wrapper), create a mock village
	// for UI testing purposes. Otherwise, fetch villages from the server.
	if _, ok := wrapper.(*game.MockWebWrapper); ok {
		rm := game.NewResourceManager()
		bm := game.NewBuildingManager(wrapper, "123", rm)
		tm := game.NewTroopManager(wrapper, "123", rm)
		gameMap := game.NewMap(wrapper, "123")
		am := game.NewAttackManager(wrapper, "123", tm, gameMap)
		dm := game.NewDefenceManager(wrapper, "123", rm)
		village, err := game.NewVillage("123", wrapper, cm, rm, bm, tm, am, dm, gameMap)
		if err != nil {
			return nil, fmt.Errorf("failed to create mock village: %w", err)
		}
		villages = append(villages, village)
	} else {
		resp, err := wrapper.GetURL("game.php?screen=overview_villages")
		if err != nil {
			return nil, fmt.Errorf("failed to get villages: %w", err)
		}
		body, err := core.ReadBody(resp)
		if err != nil {
			return nil, fmt.Errorf("failed to read villages response body: %w", err)
		}
		if strings.Contains(body, "Deine Session ist abgelaufen") {
			return nil, core.ErrSessionExpired
		}
		villageIDs, err := core.Extractor.VillageIDs(body)
		if err != nil {
			return nil, fmt.Errorf("failed to extract village IDs: %w", err)
		}

		for _, id := range villageIDs {
			rm := game.NewResourceManager()
			bm := game.NewBuildingManager(wrapper, id, rm)
			if err := bm.LoadBuildingData(); err != nil {
				return nil, fmt.Errorf("failed to load building data: %w", err)
			}
			tm := game.NewTroopManager(wrapper, id, rm)
			if err := tm.LoadUnitData(); err != nil {
				return nil, fmt.Errorf("failed to load unit data: %w", err)
			}
			gameMap := game.NewMap(wrapper, id)
			am := game.NewAttackManager(wrapper, id, tm, gameMap)
			dm := game.NewDefenceManager(wrapper, id, rm)
			village, err := game.NewVillage(id, wrapper, cm, rm, bm, tm, am, dm, gameMap)
			if err != nil {
				return nil, fmt.Errorf("failed to create village: %w", err)
			}
			villages = append(villages, village)
		}
	}

	bot := &Bot{
		Wrapper:       wrapper,
		ConfigManager: cm,
		Villages:      villages,
	}
	wrapper.SetBot(bot)
	log.Printf("Managing %d villages.", len(villages))
	return bot, nil
}

// NewBot creates a new Bot.
func NewBot(configPath string, reader io.Reader, wrapper core.WebWrapperInterface) (*Bot, error) {
	cm, err := core.NewConfigManager(configPath, reader)
	if err != nil {
		return nil, fmt.Errorf("failed to create config manager: %w", err)
	}
	config := cm.GetConfig()

	if wrapper == nil {
		wrapper, err = core.NewWebWrapper(
			config.Bot.Server,
			config.Bot.RandomDelay.MinDelay,
			config.Bot.RandomDelay.MaxDelay,
			config.Credentials["user_agent"],
			config.Credentials["cookie"],
		)
		if err != nil {
			return nil, fmt.Errorf("failed to create web wrapper: %w", err)
		}
	}

	for {
		bot, err := newBotWithDeps(cm, wrapper)
		if err != nil {
			if err == core.ErrSessionExpired {
				log.Println("Session expired. Please enter a new cookie:")
				reader := bufio.NewReader(os.Stdin)
				cookie, _ := reader.ReadString('\n')
				cm.GetConfig().Credentials["cookie"] = strings.TrimSpace(cookie)
				if err := cm.SaveConfig(); err != nil {
					return nil, fmt.Errorf("failed to save config: %w", err)
				}
				continue
			}
			return nil, err
		}
		hub := web.NewHub(bot)
		bot.Hub = hub
		return bot, nil
	}
}


// Run starts the main loop for the bot.
func (b *Bot) Run() {
	log.Println("Starting bot...")
	rand.Seed(time.Now().UnixNano())

	for {
		b.lock.Lock()
		if b.paused {
			b.lock.Unlock()
			log.Println("Bot is paused. Press Enter to continue...")
			fmt.Scanln()
			continue
		}
		b.lock.Unlock()

		b.Wrapper.CheckPaused()
		log.Println("Bot tick...")
		for _, v := range b.Villages {
			v.Run()
		}
		log.Println("Bot tick finished.")

		if b.Hub != nil {
			b.Hub.BroadcastFullState()
		}

		minTick := b.ConfigManager.GetConfig().Bot.MinTickInterval
		maxTick := b.ConfigManager.GetConfig().Bot.MaxTickInterval
		nextTickIn := minTick + time.Duration(rand.Int63n(int64(maxTick-minTick)))
		log.Printf("Waiting for next tick... (interval: %s)", nextTickIn)
		time.Sleep(nextTickIn)
	}
}

// Pause pauses the bot.
func (b *Bot) Pause() {
	b.lock.Lock()
	defer b.lock.Unlock()
	b.paused = true
}

// Resume resumes the bot.
func (b *Bot) Resume() {
	b.lock.Lock()
	defer b.lock.Unlock()
	b.paused = false
}

// IsPaused returns true if the bot is paused.
func (b *Bot) IsPaused() bool {
	b.lock.Lock()
	defer b.lock.Unlock()
	return b.paused
}

// State returns a JSON-encoded representation of the current bot state.
func (b *Bot) State() ([]byte, error) {
	b.lock.Lock()
	defer b.lock.Unlock()

	state := make(map[string]interface{})
	villages := make(map[string]SerializableVillage)
	for _, v := range b.Villages {
		villages[v.ID] = SerializableVillage{
			ID:            v.ID,
			Resources:     v.ResourceManager,
			BuildingQueue: v.BuildingManager.Queue,
			TroopQueue:    v.TroopManager.Queue,
			LastAction:    v.LastAction,
		}
	}
	state["Villages"] = villages
	return json.Marshal(state)
}
