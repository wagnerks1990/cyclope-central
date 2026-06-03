package checkin

import (
	"runtime"
	"testing"

	"github.com/cyclope-central/agent/internal/config"
)

func TestBuildPayloadRequiresEnrollment(t *testing.T) {
	_, err := BuildPayload(config.Default())
	if err == nil {
		t.Fatal("BuildPayload() expected enrollment error")
	}
}

func TestBuildPayloadIncludesSystemHealth(t *testing.T) {
	cfg := config.Default()
	cfg.DeviceID = "device-123"
	cfg.DeviceSecret = "secret-123"

	payload, err := BuildPayload(cfg)
	if err != nil {
		t.Fatalf("BuildPayload() error = %v", err)
	}
	if payload.DeviceID != cfg.DeviceID || payload.DeviceSecret != cfg.DeviceSecret {
		t.Fatalf("payload credentials mismatch")
	}
	if payload.Hostname == "" {
		t.Fatal("payload hostname is empty")
	}
	if payload.OperatingSystem != runtime.GOOS {
		t.Fatalf("payload OS = %q, want %q", payload.OperatingSystem, runtime.GOOS)
	}
	if payload.Architecture != runtime.GOARCH {
		t.Fatalf("payload architecture = %q, want %q", payload.Architecture, runtime.GOARCH)
	}
	if payload.AgentVersion == "" {
		t.Fatal("payload agent version is empty")
	}
	if payload.CPUCount <= 0 {
		t.Fatalf("payload CPU count = %d, want > 0", payload.CPUCount)
	}
	if payload.HealthStatus != "healthy" {
		t.Fatalf("payload health = %q, want healthy", payload.HealthStatus)
	}
	if payload.Inventory.CPUCores <= 0 {
		t.Fatalf("inventory CPU cores = %d, want > 0", payload.Inventory.CPUCores)
	}
	if payload.Inventory.NetworkInterfaces == nil {
		t.Fatal("inventory network interfaces should be an initialized slice")
	}
	if payload.Inventory.Disks == nil {
		t.Fatal("inventory disks should be an initialized slice")
	}
	if payload.Inventory.Security.Details == nil || payload.Inventory.Updates.Details == nil {
		t.Fatal("inventory security/update details should be initialized")
	}
}
