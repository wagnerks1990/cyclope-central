//go:build !windows

package checkin

import (
	"os"
	"path/filepath"
)

func rustDeskConfigPaths() []string {
	paths := []string{}
	if configDir, err := os.UserConfigDir(); err == nil {
		paths = append(paths, filepath.Join(configDir, "rustdesk", "RustDesk2.toml"))
		paths = append(paths, filepath.Join(configDir, "RustDesk", "RustDesk2.toml"))
	}
	paths = append(paths, "/etc/rustdesk/RustDesk2.toml")
	return paths
}

func rustDeskWritableConfigPath() string {
	if configDir, err := os.UserConfigDir(); err == nil {
		return filepath.Join(configDir, "rustdesk", "CyclopeCentral.toml")
	}
	return filepath.Join(os.TempDir(), "cyclope-rustdesk.toml")
}

func rustDeskInstalled() bool {
	candidates := []string{"/usr/bin/rustdesk", "/usr/local/bin/rustdesk", "/opt/rustdesk/rustdesk"}
	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			return true
		}
	}
	return false
}
