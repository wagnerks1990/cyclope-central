package main

import (
	"strings"
	"testing"

	"github.com/cyclope-central/agent/internal/config"
)

func TestRedactedConfigJSONDoesNotExposeSecrets(t *testing.T) {
	cfg := config.Default()
	cfg.DeviceID = "device-123"
	cfg.DeviceSecret = "device-secret-value"
	cfg.AgentToken = "legacy-agent-token-value"

	output, err := redactedConfigJSON(cfg)
	if err != nil {
		t.Fatalf("redactedConfigJSON() returned error: %v", err)
	}
	if strings.Contains(output, cfg.DeviceSecret) {
		t.Fatal("redacted config output exposed the device secret")
	}
	if strings.Contains(output, cfg.AgentToken) {
		t.Fatal("redacted config output exposed the agent token")
	}
	if !strings.Contains(output, "***redacted***") {
		t.Fatal("redacted config output did not include a redaction marker")
	}
	if !strings.Contains(output, cfg.DeviceID) {
		t.Fatal("redacted config output should preserve non-secret device identifiers")
	}
}
