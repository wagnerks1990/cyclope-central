package checkin

import (
	"strings"
	"testing"

	"github.com/cyclope-central/agent/internal/config"
)

func enrolledConfig() config.Config {
	cfg := config.Default()
	cfg.DeviceID = "device-123"
	cfg.DeviceSecret = "secret-123"
	return cfg
}

func TestExecutePingJob(t *testing.T) {
	result := ExecuteJob(enrolledConfig(), Job{Type: "ping", Payload: map[string]any{}})
	if !result.Succeeded {
		t.Fatalf("ping should succeed: %#v", result)
	}
	if !strings.Contains(result.Output, "pong") {
		t.Fatalf("ping output = %q, want pong", result.Output)
	}
}

func TestExecuteRefreshInventoryJob(t *testing.T) {
	result := ExecuteJob(enrolledConfig(), Job{Type: "refresh_inventory", Payload: map[string]any{}})
	if !result.Succeeded {
		t.Fatalf("refresh_inventory should build payload: %#v", result)
	}
	if !strings.Contains(result.Output, "network_interfaces") {
		t.Fatalf("inventory output missing network_interfaces: %s", result.Output)
	}
}

func TestExecuteCollectAgentLogsJob(t *testing.T) {
	result := ExecuteJob(enrolledConfig(), Job{Type: "collect_agent_logs", Payload: map[string]any{"line_count": float64(25)}})
	if !result.Succeeded || !strings.Contains(result.Output, "25") {
		t.Fatalf("collect_agent_logs result = %#v", result)
	}
}

func TestExecuteUnknownJobFails(t *testing.T) {
	result := ExecuteJob(enrolledConfig(), Job{Type: "run_shell", Payload: map[string]any{"command": "whoami"}})
	if result.Succeeded {
		t.Fatal("unknown job type must fail")
	}
	if result.Error == nil || !strings.Contains(*result.Error, "unsupported job type") {
		t.Fatalf("unexpected error: %#v", result.Error)
	}
}

func TestExecuteDiscoveryJobIsDiscoveryOnly(t *testing.T) {
	cfg := config.Config{DeviceID: "device-1", DeviceSecret: "secret-1234567890123456"}
	job := Job{ID: "job-5", Type: "network_discovery", Payload: map[string]any{"subnet": "local"}}

	result := ExecuteJob(cfg, job)

	if !result.Succeeded {
		t.Fatalf("expected discovery job to succeed: %v", result.Error)
	}
	if !strings.Contains(result.Output, "discovery_only_no_exploitation_no_credentials") {
		t.Fatalf("expected discovery-only boundary in output: %s", result.Output)
	}
}
