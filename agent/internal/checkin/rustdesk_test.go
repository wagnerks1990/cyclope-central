package checkin

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDetectRustDeskReadsConfiguredDeviceID(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "RustDesk2.toml")
	if err := os.WriteFile(configPath, []byte("id = '123456789'\n"), 0o600); err != nil {
		t.Fatalf("failed to write RustDesk fixture: %v", err)
	}
	t.Setenv("CYCLOPE_RUSTDESK_CONFIG_PATH", configPath)

	status := DetectRustDesk()

	if status.ProviderType != RustDeskProviderType {
		t.Fatalf("unexpected provider type: %s", status.ProviderType)
	}
	if !status.Installed {
		t.Fatal("expected RustDesk to be marked installed when config exists")
	}
	if status.DeviceID != "123456789" {
		t.Fatalf("unexpected RustDesk ID: %s", status.DeviceID)
	}
	if status.Status != "ready" {
		t.Fatalf("unexpected RustDesk status: %s", status.Status)
	}
}

func TestConfigureRustDeskWritesLocalSettings(t *testing.T) {
	configPath := filepath.Join(t.TempDir(), "CyclopeCentral.toml")
	t.Setenv("CYCLOPE_RUSTDESK_CONFIG_PATH", configPath)

	if err := ConfigureRustDesk("rustdesk.example.test", "relay.example.test", "PUBLIC_KEY"); err != nil {
		t.Fatalf("ConfigureRustDesk returned error: %v", err)
	}
	content, err := os.ReadFile(configPath)
	if err != nil {
		t.Fatalf("failed to read configured RustDesk settings: %v", err)
	}
	text := string(content)
	for _, expected := range []string{"rustdesk.example.test", "relay.example.test", "PUBLIC_KEY"} {
		if !strings.Contains(text, expected) {
			t.Fatalf("expected configured RustDesk file to contain %q", expected)
		}
	}
}
