package web

import (
	"log"

	"github.com/gorilla/websocket"
)

// BotController defines the interface that the web package uses to interact with the bot.
// This is used to avoid circular dependencies between the web and main packages.
type BotController interface {
	// State returns a JSON-encoded representation of the current bot state.
	State() ([]byte, error)
	Pause()
	Resume()
}

// Client is a middleman between the websocket connection and the hub.
type Client struct {
	hub *Hub

	// The websocket connection.
	conn *websocket.Conn

	// Buffered channel of outbound messages.
	send chan []byte
}

// Hub maintains the set of active clients and broadcasts messages to the clients.
type Hub struct {
	// Registered clients.
	clients map[*Client]bool

	// Inbound messages from the clients.
	broadcast chan []byte

	// Register requests from the clients.
	register chan *Client

	// Unregister requests from clients.
	unregister chan *Client

	// bot is a reference to the bot, used to fetch state.
	bot BotController
}

// NewHub creates a new Hub.
func NewHub(bot BotController) *Hub {
	return &Hub{
		broadcast:  make(chan []byte),
		register:   make(chan *Client),
		unregister: make(chan *Client),
		clients:    make(map[*Client]bool),
		bot:        bot,
	}
}

// Run starts the hub's event loop.
func (h *Hub) Run() {
	for {
		select {
		case client := <-h.register:
			h.clients[client] = true
		case client := <-h.unregister:
			if _, ok := h.clients[client]; ok {
				delete(h.clients, client)
				close(client.send)
			}
		case message := <-h.broadcast:
			for client := range h.clients {
				select {
				case client.send <- message:
				default:
					close(client.send)
					delete(h.clients, client)
				}
			}
		}
	}
}

// BroadcastFullState fetches the current state from the bot and broadcasts it to all clients.
// This method is called by the bot on every tick.
func (h *Hub) BroadcastFullState() {
	if h == nil {
		return
	}
	state, err := h.bot.State()
	if err != nil {
		log.Printf("error getting bot state for broadcast: %v", err)
		return
	}
	h.broadcast <- state
}
