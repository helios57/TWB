package main

import (
	"fmt"
	"io"
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

// NewBot creates a new Bot.
func NewBot(configPath string, reader io.Reader) (*Bot, error) {
	cm, err := core.NewConfigManager(configPath, reader)
	if err != nil {
		return nil, fmt.Errorf("failed to create config manager: %w", err)
	}
	config := cm.GetConfig()

	wrapper, err := core.NewWebWrapper(config.Bot.Server, config.Bot.RandomDelay.MinDelay, config.Bot.RandomDelay.MaxDelay)
	if err != nil {
		return nil, fmt.Errorf("failed to create web wrapper: %w", err)
	}
	return NewBotWithDeps(cm, wrapper)
}

// NewBotWithDeps creates a new Bot with dependencies.
func NewBotWithDeps(cm *core.ConfigManager, wrapper *core.WebWrapper) (*Bot, error) {
	resp, err := wrapper.GetURL("game.php?screen=overview_villages")
	if err != nil {
		return nil, fmt.Errorf("failed to get villages: %w", err)
	}
	body, err := core.ReadBody(resp)
	if err != nil {
		return nil, fmt.Errorf("failed to read villages response body: %w", err)
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
	return bot, nil
}

// Run starts the main loop for the bot.
func (b *Bot) Run() {
	fmt.Println("Starting bot...")
	for {
		b.lock.Lock()
		if b.paused {
			b.lock.Unlock()
			fmt.Println("Bot is paused. Press Enter to continue...")
			fmt.Scanln()
			continue
		}
		b.lock.Unlock()

		for _, v := range b.Villages {
			fmt.Printf("Running village %s...\n", v.ID)
			v.Run()
		}
		time.Sleep(10 * time.Second)
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
