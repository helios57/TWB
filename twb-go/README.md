# TWB-Go

This is a Go port of the Tribal Wars Bot (TWB). It is a bot for the browser game 'Die Stämme' (Tribal Wars).

## Project Structure

- `main.go`: The main entry point for the application.
- `bot.go`: The main bot application.
- `core/`: Shared services for HTTP, caching, I/O, and notifications.
- `game/`: Implements farming, defence, recruitment, and simulation logic.
- `tests/`: Stores `unittest` suites.

## Architecture

The bot is designed with a modular architecture. The `Bot` struct is the main entry point for the application and is responsible for initializing and running the bot. The `Village` struct is the central hub of the application and is responsible for orchestrating all the managers. The managers are responsible for specific tasks, such as managing resources, buildings, and troops.

## Build, Test, and Development Commands

- `go build`: Build the bot.
- `go test ./...`: Run all tests.
- `go test -race ./...`: Run all tests with the race detector.
- `go run .`: Run the bot.
