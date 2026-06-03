//go:build windows

package checkin

import (
	"os"
	"path/filepath"
)

func rustDeskConfigPaths() []string {
	paths := []string{}
	if appData := os.Getenv("APPDATA"); appData != "" {
		paths = append(paths, filepath.Join(appData, "RustDesk", "config", "RustDesk2.toml"))
	}
	if programData := os.Getenv("ProgramData"); programData != "" {
		paths = append(paths, filepath.Join(programData, "RustDesk", "config", "RustDesk2.toml"))
		paths = append(paths, filepath.Join(programData, "RustDesk", "config", "CyclopeCentral.toml"))
	}
	paths = append(paths, `C:\Windows\ServiceProfiles\LocalService\AppData\Roaming\RustDesk\config\RustDesk2.toml`)
	return paths
}

func rustDeskWritableConfigPath() string {
	if programData := os.Getenv("ProgramData"); programData != "" {
		return filepath.Join(programData, "RustDesk", "config", "CyclopeCentral.toml")
	}
	return `C:\ProgramData\RustDesk\config\CyclopeCentral.toml`
}

func rustDeskInstalled() bool {
	candidates := []string{
		`C:\Program Files\RustDesk\rustdesk.exe`,
		`C:\Program Files (x86)\RustDesk\rustdesk.exe`,
	}
	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			return true
		}
	}
	return false
}
