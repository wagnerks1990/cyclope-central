package config

import (
	"encoding/json"
	"os"
)

// Config contains safe agent settings. Future Linux support should keep this schema portable.
type Config struct {
	TenantID     string `json:"tenant_id"`
	InstallID    string `json:"install_id"`
	DeviceID     string `json:"device_id"`
	DeviceSecret string `json:"device_secret"`
	APIBaseURL   string `json:"api_base_url"`
	AgentToken   string `json:"agent_token"`
	LogLevel     string `json:"log_level"`
	ServiceName  string `json:"service_name"`
}

func Default() Config {
	return Config{
		APIBaseURL:  "http://localhost:8000/api",
		LogLevel:    "INFO",
		ServiceName: "CyclopeCentralAgent",
	}
}

func LoadFromFile(path string) (Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return Config{}, err
	}
	cfg := Default()
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func SaveToFile(path string, cfg Config) error {
	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o600)
}
