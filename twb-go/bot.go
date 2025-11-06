package main

import (
	"bufio"
	"fmt"
	"io"
	"log"
	"os"
	"strings"
	"sync"
	"time"
	"twb-go/core"
	"twb-go/game"
)

// Bot represents the main bot application.
type Bot struct {
	Wrapper       *core.WebWrapper
	ConfigManager *core.ConfigManager
	Villages      []*game.Village
	paused        bool
	lock          sync.Mutex
}

// newBotWithDeps creates a new Bot with dependencies.
func newBotWithDeps(cm *core.ConfigManager, wrapper *core.WebWrapper) (*Bot, error) {
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

	var villages []*game.Village
	for _, id := range villageIDs {
		rm := game.NewResourceManager()
		bm := game.NewBuildingManager(wrapper, id, rm)
		tm := game.NewTroopManager(wrapper, id, rm)
		gameMap := game.NewMap(wrapper, id)
		am := game.NewAttackManager(wrapper, id, tm, gameMap)
		dm := game.NewDefenceManager(wrapper, id, rm)
		village, err := game.NewVillage(id, wrapper, cm, rm, bm, tm, am, dm, gameMap)
		if err != nil {
			return nil, fmt.Errorf("failed to create village: %w", err)
		}
		villages = append(villages, village)
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
func NewBot(configPath string, reader io.Reader, wrapper *core.WebWrapper) (*Bot, error) {
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
		return bot, nil
	}
}


// Run starts the main loop for the bot.
func (b *Bot) Run() {
	log.Println("Starting bot...")
	ticker := time.NewTicker(b.ConfigManager.GetConfig().Bot.TickInterval)
	defer ticker.Stop()

	for range ticker.C {
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
		log.Printf("Waiting for next tick... (interval: %s)", b.ConfigManager.GetConfig().Bot.TickInterval)
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
