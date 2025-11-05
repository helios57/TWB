package main

import "log"

func main() {
	bot, err := NewBot("config.yaml", nil)
	if err != nil {
		log.Fatalf("failed to create bot: %v", err)
	}
	bot.Run()
}
