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
