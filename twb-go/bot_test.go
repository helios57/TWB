package main

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"twb-go/core"
)

func TestBot_Captcha(t *testing.T) {
	// Create a mock server that returns a captcha
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "captcha")
	}))
	defer server.Close()

	// Create a new Bot
	wrapper, err := core.NewWebWrapper(server.URL, 0, 0, "test-agent", "test-cookie")
	if err != nil {
		t.Fatalf("NewWebWrapper failed: %v", err)
	}
	bot := &Bot{
		Wrapper: wrapper,
	}
	wrapper.SetBot(bot)

	// Check for captcha
	wrapper.GetURL("/")

	// Assert that the bot is paused
	if !bot.IsPaused() {
		t.Error("Expected bot to be paused, but it is not")
	}
}
