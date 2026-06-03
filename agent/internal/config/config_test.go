package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestLoadSaveConfig(t *testing.T) {
	path := filepath.Join(t.TempDir(), "agent.json")
	cfg := Default()
	cfg.DeviceID = "device-123"
	cfg.DeviceSecret = "secret-123"
	cfg.APIBaseURL = "http://example.test/api"

	if err := SaveToFile(path, cfg); err != nil {
		t.Fatalf("SaveToFile() error = %v", err)
	}
	info, err := os.Stat(path)
	if err != nil {
		t.Fatalf("stat saved config: %v", err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("config permissions = %v, want 0600", info.Mode().Perm())
	}
	loaded, err := LoadFromFile(path)
	if err != nil {
		t.Fatalf("LoadFromFile() error = %v", err)
	}
	if loaded.DeviceID != cfg.DeviceID || loaded.DeviceSecret != cfg.DeviceSecret || loaded.APIBaseURL != cfg.APIBaseURL {
		t.Fatalf("loaded config mismatch: %#v", loaded)
	}
}
