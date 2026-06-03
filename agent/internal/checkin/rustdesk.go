package checkin

import (
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strings"
)

const RustDeskProviderType = "rustdesk_oss"

type RemoteAccessStatus struct {
	ProviderType string `json:"provider_type"`
	Installed    bool   `json:"installed"`
	DeviceID     string `json:"device_id,omitempty"`
	Status       string `json:"status"`
}

func DetectRustDesk() RemoteAccessStatus {
	paths := rustDeskConfigPaths()
	if override := os.Getenv("CYCLOPE_RUSTDESK_CONFIG_PATH"); override != "" {
		paths = append([]string{override}, paths...)
	}
	installed := rustDeskInstalled()
	for _, path := range paths {
		data, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		installed = true
		deviceID := parseRustDeskID(string(data))
		status := "installed"
		if deviceID != "" {
			status = "ready"
		}
		return RemoteAccessStatus{ProviderType: RustDeskProviderType, Installed: installed, DeviceID: deviceID, Status: status}
	}
	status := "not_installed"
	if installed {
		status = "installed"
	}
	return RemoteAccessStatus{ProviderType: RustDeskProviderType, Installed: installed, Status: status}
}

func ConfigureRustDesk(serverHost string, relayHost string, publicKey string) error {
	serverHost = strings.TrimSpace(serverHost)
	if serverHost == "" {
		return errors.New("RustDesk server host is required")
	}
	path := rustDeskWritableConfigPath()
	if override := os.Getenv("CYCLOPE_RUSTDESK_CONFIG_PATH"); override != "" {
		path = override
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	content := fmt.Sprintf("rendezvous_server = %q\nrelay_server = %q\nkey = %q\n", serverHost, strings.TrimSpace(relayHost), strings.TrimSpace(publicKey))
	return os.WriteFile(path, []byte(content), 0o600)
}

func parseRustDeskID(configText string) string {
	patterns := []*regexp.Regexp{
		regexp.MustCompile(`(?m)^\s*id\s*=\s*["']?([A-Za-z0-9_-]{4,128})["']?\s*$`),
		regexp.MustCompile(`(?m)^\s*rustdesk_id\s*=\s*["']?([A-Za-z0-9_-]{4,128})["']?\s*$`),
	}
	for _, pattern := range patterns {
		matches := pattern.FindStringSubmatch(configText)
		if len(matches) == 2 {
			return matches[1]
		}
	}
	return ""
}
