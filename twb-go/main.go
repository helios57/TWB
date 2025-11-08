package main

import (
	"flag"
	"log"
	"twb-go/core"
	"twb-go/game"
	"twb-go/web"
)

func main() {
	dryRun := flag.Bool("dry-run", false, "run the bot with a mock web wrapper for UI testing")
	flag.Parse()

	var wrapper core.WebWrapperInterface
	if *dryRun {
		log.Println("Running in dry-run mode")
		wrapper = game.NewMockWebWrapper()
	}

	bot, err := NewBot("config.yaml", nil, wrapper)
	if err != nil {
		log.Fatalf("failed to create bot: %v", err)
	}
	go web.StartServer(bot)
	bot.Run()
}
