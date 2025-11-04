package core

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
)

func TestWebWrapper(t *testing.T) {
	// Create a mock server
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/get":
			if r.Method != "GET" {
				t.Errorf("Expected GET request, got %s", r.Method)
			}
			fmt.Fprintln(w, "GET successful")
		case "/post":
			if r.Method != "POST" {
				t.Errorf("Expected POST request, got %s", r.Method)
			}
			if err := r.ParseForm(); err != nil {
				t.Fatalf("Failed to parse form: %v", err)
			}
			if r.FormValue("key") != "value" {
				t.Errorf("Expected form value 'value', got '%s'", r.FormValue("key"))
			}
			fmt.Fprintln(w, "POST successful")
		default:
			http.NotFound(w, r)
		}
	}))
	defer server.Close()

	// Create a new WebWrapper
	ww, err := NewWebWrapper(server.URL, 1, 2)
	if err != nil {
		t.Fatalf("NewWebWrapper failed: %v", err)
	}

	// Test GET request
	resp, err := ww.GetURL("/get")
	if err != nil {
		t.Fatalf("GetURL failed: %v", err)
	}
	body, err := ReadBody(resp)
	if err != nil {
		t.Fatalf("ReadBody failed: %v", err)
	}
	if body != "GET successful\n" {
		t.Errorf("Expected 'GET successful', got '%s'", body)
	}

	// Test POST request
	data := url.Values{}
	data.Set("key", "value")
	resp, err = ww.PostURL("/post", data)
	if err != nil {
		t.Fatalf("PostURL failed: %v", err)
	}
	body, err = ReadBody(resp)
	if err != nil {
		t.Fatalf("ReadBody failed: %v", err)
	}
	if body != "POST successful\n" {
		t.Errorf("Expected 'POST successful', got '%s'", body)
	}
}
