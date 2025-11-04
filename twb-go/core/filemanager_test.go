package core

import (
	"os"
	"path/filepath"
	"testing"
)

func TestFileManager(t *testing.T) {
	// Create a temporary directory for the test
	tmpDir, err := os.MkdirTemp("", "filemanager-test")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}
	defer os.RemoveAll(tmpDir)

	fm := NewFileManager(tmpDir)

	// Test CreateDirectory
	dirPath := "test-dir"
	if err := fm.CreateDirectory(dirPath); err != nil {
		t.Fatalf("CreateDirectory failed: %v", err)
	}
	if !fm.PathExists(dirPath) {
		t.Errorf("Expected directory '%s' to exist", dirPath)
	}

	// Test SaveJSONFile and LoadJSONFile
	type TestData struct {
		Name  string `json:"name"`
		Value int    `json:"value"`
	}
	testData := TestData{Name: "test", Value: 123}
	filePath := filepath.Join(dirPath, "test.json")

	if err := fm.SaveJSONFile(testData, filePath); err != nil {
		t.Fatalf("SaveJSONFile failed: %v", err)
	}

	var loadedData TestData
	if err := fm.LoadJSONFile(filePath, &loadedData); err != nil {
		t.Fatalf("LoadJSONFile failed: %v", err)
	}

	if loadedData.Name != testData.Name || loadedData.Value != testData.Value {
		t.Errorf("Loaded data does not match saved data. Got %+v, want %+v", loadedData, testData)
	}
}
