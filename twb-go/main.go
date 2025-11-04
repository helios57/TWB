package main

import "log"

func main() {
	bot, err := NewBot()
	if err != nil {
		log.Fatalf("failed to create bot: %v", err)
	}
	bot.Run()
}
