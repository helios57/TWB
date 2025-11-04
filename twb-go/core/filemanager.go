package core

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
)

// FileManager provides methods for file and directory management.
type FileManager struct {
	rootDir string
}

// NewFileManager creates a new FileManager with the given root directory.
func NewFileManager(rootDir string) *FileManager {
	return &FileManager{rootDir: rootDir}
}

// GetPath returns the full path of a file or directory in the project.
func (fm *FileManager) GetPath(path string) string {
	return filepath.Join(fm.rootDir, path)
}

// PathExists returns true if the path exists, false otherwise.
func (fm *FileManager) PathExists(path string) bool {
	_, err := os.Stat(fm.GetPath(path))
	return !os.IsNotExist(err)
}

// CreateDirectory creates a directory if it does not exist.
func (fm *FileManager) CreateDirectory(directory string) error {
	path := fm.GetPath(directory)
	if !fm.PathExists(path) {
		return os.MkdirAll(path, os.ModePerm)
	}
	return nil
}

// ReadFile reads the contents of a file and returns the data.
func (fm *FileManager) ReadFile(path string) ([]byte, error) {
	fullPath := fm.GetPath(path)
	if !fm.PathExists(path) {
		return nil, os.ErrNotExist
	}
	return os.ReadFile(fullPath)
}

// LoadJSONFile loads a JSON file and unmarshals it into the provided interface.
func (fm *FileManager) LoadJSONFile(path string, v interface{}) error {
	data, err := fm.ReadFile(path)
	if err != nil {
		return err
	}
	if err := json.Unmarshal(data, v); err != nil {
		return fmt.Errorf("failed to decode JSON from %s: %w", path, err)
	}
	return nil
}

// SaveJSONFile marshals the provided interface and saves it to a JSON file.
func (fm *FileManager) SaveJSONFile(data interface{}, path string) error {
	fullPath := fm.GetPath(path)
	jsonData, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return fmt.Errorf("failed to encode data to JSON for %s: %w", path, err)
	}
	return os.WriteFile(fullPath, jsonData, 0644)
}
