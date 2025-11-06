package core

import (
	"fmt"
	"io"
	"log"
	"math/rand"
	"net/http"
	"net/http/cookiejar"
	"net/url"
	"strings"
	"time"
)

// Pausable defines the interface for an object that can be paused.
type Pausable interface {
	Pause()
	IsPaused() bool
}

// WebWrapper is an object for sending HTTP requests.
type WebWrapper struct {
	client       *http.Client
	headers      http.Header
	Endpoint     string
	delay        time.Duration
	minDelay     time.Duration
	maxDelay     time.Duration
	lastH        string // To store the 'h' parameter
	lastResponse *http.Response
	Bot          Pausable
}

// NewWebWrapper creates a new WebWrapper.
func NewWebWrapper(endpoint string, minDelay, maxDelay int, userAgent, cookie string) (*WebWrapper, error) {
	jar, err := cookiejar.New(nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create cookie jar: %w", err)
	}

	return &WebWrapper{
		client: &http.Client{
			Jar: jar,
		},
		headers: http.Header{
			"User-Agent":                []string{userAgent},
			"Cookie":                    []string{cookie},
			"Upgrade-Insecure-Requests": []string{"1"},
		},
		Endpoint: endpoint,
		minDelay: time.Duration(minDelay) * time.Second,
		maxDelay: time.Duration(maxDelay) * time.Second,
	}, nil
}

// setRefererAndOrigin updates the Referer and Origin headers based on the last response URL.
func (ww *WebWrapper) setRefererAndOrigin(req *http.Request) {
	if ww.lastResponse != nil {
		req.Header.Set("Referer", ww.lastResponse.Request.URL.String())
	}
	originURL, err := url.Parse(ww.Endpoint)
	if err == nil {
		req.Header.Set("Origin", originURL.Scheme+"://"+originURL.Host)
	}
}

// randomDelay introduces a random delay before making a request.
func (ww *WebWrapper) randomDelay() {
	if ww.minDelay > 0 && ww.maxDelay > 0 {
		delay := time.Duration(rand.Int63n(int64(ww.maxDelay-ww.minDelay)) + int64(ww.minDelay))
		time.Sleep(delay)
	}
}

// SetBot sets the bot instance for the WebWrapper.
func (ww *WebWrapper) SetBot(bot Pausable) {
	ww.Bot = bot
}

// GetURL fetches a URL using a GET request.
func (ww *WebWrapper) GetURL(path string) (*http.Response, error) {
	if ww.Bot != nil {
		for ww.Bot.IsPaused() {
			time.Sleep(1 * time.Second)
		}
	}
	ww.randomDelay()
	fullURL, err := url.Parse(ww.Endpoint)
	if err != nil {
		return nil, fmt.Errorf("invalid endpoint URL: %w", err)
	}
	fullURL, err = fullURL.Parse(path)
	if err != nil {
		return nil, fmt.Errorf("failed to parse path: %w", err)
	}

	req, err := http.NewRequest("GET", fullURL.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create GET request: %w", err)
	}
	req.Header = ww.headers
	ww.setRefererAndOrigin(req)

	log.Printf("GET %s [User-Agent: %s] [Cookie: %s]", path, req.Header.Get("User-Agent"), req.Header.Get("Cookie"))
	resp, err := ww.client.Do(req)
	if err != nil {
		log.Printf("GET %s failed: %v", path, err)
		return nil, err
	}
	ww.lastResponse = resp
	log.Printf("GET %s [%d]", path, resp.StatusCode)
	if resp.StatusCode != http.StatusOK {
		body, _ := ReadBody(resp)
		log.Printf("Response body: %s", body)
		// Restore the body for subsequent reads
		resp.Body = io.NopCloser(strings.NewReader(body))
	}
	ww.checkForCaptcha(resp)
	return resp, nil
}

// PostURL sends a POST request with form data.
func (ww *WebWrapper) PostURL(path string, data url.Values) (*http.Response, error) {
	if ww.Bot != nil {
		for ww.Bot.IsPaused() {
			time.Sleep(1 * time.Second)
		}
	}
	ww.randomDelay()
	fullURL, err := url.Parse(ww.Endpoint)
	if err != nil {
		return nil, fmt.Errorf("invalid endpoint URL: %w", err)
	}
	fullURL, err = fullURL.Parse(path)
	if err != nil {
		return nil, fmt.Errorf("failed to parse path: %w", err)
	}

	req, err := http.NewRequest("POST", fullURL.String(), strings.NewReader(data.Encode()))
	if err != nil {
		return nil, fmt.Errorf("failed to create POST request: %w", err)
	}
	req.Header = ww.headers
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	ww.setRefererAndOrigin(req)

	log.Printf("POST %s [User-Agent: %s] [Cookie: %s]", path, req.Header.Get("User-Agent"), req.Header.Get("Cookie"))
	resp, err := ww.client.Do(req)
	if err != nil {
		log.Printf("POST %s failed: %v", path, err)
		return nil, err
	}
	ww.lastResponse = resp
	log.Printf("POST %s %s [%d]", path, data.Encode(), resp.StatusCode)
	if resp.StatusCode != http.StatusOK {
		body, _ := ReadBody(resp)
		log.Printf("Response body: %s", body)
		// Restore the body for subsequent reads
		resp.Body = io.NopCloser(strings.NewReader(body))
	}
	ww.checkForCaptcha(resp)
	return resp, nil
}

// checkForCaptcha checks the response for a captcha and pauses the bot if found.
func (ww *WebWrapper) checkForCaptcha(resp *http.Response) {
	if ww.Bot == nil {
		return
	}
	body, err := ReadBody(resp)
	if err != nil {
		log.Printf("failed to read response body: %v", err)
		return
	}
	// Restore the body for subsequent reads
	resp.Body = io.NopCloser(strings.NewReader(body))

	if strings.Contains(strings.ToLower(body), "captcha") {
		log.Println("Captcha detected! Pausing bot.")
		log.Printf("Response body: %s", body)
		ww.Bot.Pause()
	}
}

// ReadBody reads the response body and returns it as a string.
func ReadBody(resp *http.Response) (string, error) {
	if resp == nil {
		return "", fmt.Errorf("response is nil")
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response body: %w", err)
	}
	return string(body), nil
}
