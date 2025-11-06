package core

import (
	"net/http"
	"net/url"
)

type WebWrapperInterface interface {
	GetURL(url string) (*http.Response, error)
	PostURL(url string, data url.Values) (*http.Response, error)
	CheckPaused()
	SetBot(bot Pausable)
}
