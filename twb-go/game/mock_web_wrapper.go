package game

import (
	"net/http"
	"net/url"
	"twb-go/core"
)

type MockWebWrapper struct {
	GetURLFunc  func(url string) (*http.Response, error)
	PostURLFunc func(url string, data url.Values) (*http.Response, error)
}

func (m *MockWebWrapper) GetURL(url string) (*http.Response, error) {
	if m.GetURLFunc != nil {
		return m.GetURLFunc(url)
	}
	return &http.Response{}, nil
}

func (m *MockWebWrapper) PostURL(url string, data url.Values) (*http.Response, error) {
	if m.PostURLFunc != nil {
		return m.PostURLFunc(url, data)
	}
	return &http.Response{}, nil
}

func (m *MockWebWrapper) CheckPaused() {}

func (m *MockWebWrapper) SetBot(bot core.Pausable) {}
