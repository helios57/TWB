package main

import (
	"fmt"
	"time"
	"twb-go/core"
	"twb-go/game"
)

// Bot represents the main bot application.
type Bot struct {
	Wrapper       *core.WebWrapper
	ConfigManager *core.ConfigManager
	Villages      []*game.Village
}

// NewBot creates a new Bot.
func NewBot() (*Bot, error) {
	cm, err := core.NewConfigManager("config.example.json")
	if err != nil {
		return nil, fmt.Errorf("failed to create config manager: %w", err)
	}
	config := cm.GetConfig()

	wrapper, err := core.NewWebWrapper(config.Bot.Server, config.Bot.RandomDelay.MinDelay, config.Bot.RandomDelay.MaxDelay)
	if err != nil {
		return nil, fmt.Errorf("failed to create web wrapper: %w", err)
	}

	var villages []*game.Village
	for id := range config.Villages {
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

	return &Bot{
		Wrapper:       wrapper,
		ConfigManager: cm,
		Villages:      villages,
	}, nil
}

// Run starts the main loop for the bot.
func (b *Bot) Run() {
	fmt.Println("Starting bot...")
	for {
		for _, v := range b.Villages {
			fmt.Printf("Running village %s...\n", v.ID)
			v.Run()
		}
		time.Sleep(10 * time.Second)
	}
}
