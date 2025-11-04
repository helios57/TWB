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

// WebWrapper is an object for sending HTTP requests.
type WebWrapper struct {
	client      *http.Client
	headers     http.Header
	Endpoint    string
	delay       time.Duration
	minDelay    time.Duration
	maxDelay    time.Duration
	lastH       string // To store the 'h' parameter
	lastResponse *http.Response
}

// NewWebWrapper creates a new WebWrapper.
func NewWebWrapper(endpoint string, minDelay, maxDelay int) (*WebWrapper, error) {
	jar, err := cookiejar.New(nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create cookie jar: %w", err)
	}

	return &WebWrapper{
		client: &http.Client{
			Jar: jar,
		},
		headers: http.Header{
			"User-Agent":                []string{"Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"},
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

// GetURL fetches a URL using a GET request.
func (ww *WebWrapper) GetURL(path string) (*http.Response, error) {
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

	resp, err := ww.client.Do(req)
	if err != nil {
		log.Printf("GET %s failed: %v", path, err)
		return nil, err
	}
	ww.lastResponse = resp
	log.Printf("GET %s [%d]", path, resp.StatusCode)
	return resp, nil
}

// PostURL sends a POST request with form data.
func (ww *WebWrapper) PostURL(path string, data url.Values) (*http.Response, error) {
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

	resp, err := ww.client.Do(req)
	if err != nil {
		log.Printf("POST %s failed: %v", path, err)
		return nil, err
	}
	ww.lastResponse = resp
	log.Printf("POST %s %s [%d]", path, data.Encode(), resp.StatusCode)
	return resp, nil
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
