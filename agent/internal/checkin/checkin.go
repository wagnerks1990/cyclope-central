package checkin

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log/slog"
	"net"
	"net/http"
	"os"
	"runtime"
	"strconv"
	"strings"
	"time"

	"github.com/cyclope-central/agent/internal/config"
)

const AgentVersion = "0.2.0"

type Client struct {
	cfg        config.Config
	logger     *slog.Logger
	httpClient *http.Client
}

type EnrollmentRequest struct {
	EnrollmentToken string `json:"enrollment_token"`
	Hostname        string `json:"hostname"`
	OperatingSystem string `json:"operating_system"`
	Architecture    string `json:"architecture"`
	AgentVersion    string `json:"agent_version"`
	MachineID       string `json:"machine_identifier"`
}

type EnrollmentResponse struct {
	DeviceID     string `json:"device_id"`
	DeviceSecret string `json:"device_secret"`
}

type Payload struct {
	DeviceID         string    `json:"device_id"`
	DeviceSecret     string    `json:"device_secret"`
	Hostname         string    `json:"hostname"`
	OperatingSystem  string    `json:"operating_system"`
	Architecture     string    `json:"architecture"`
	AgentVersion     string    `json:"agent_version"`
	IPAddress        string    `json:"ip_address,omitempty"`
	LocalIPs         []string  `json:"local_ips"`
	UptimeSeconds    *int64    `json:"uptime_seconds,omitempty"`
	CPUCount         int       `json:"cpu_count"`
	MemoryTotalBytes *uint64   `json:"memory_total_bytes,omitempty"`
	MemoryUsedBytes  *uint64   `json:"memory_used_bytes,omitempty"`
	HealthStatus     string    `json:"health_status"`
	Inventory        Inventory `json:"inventory"`
}

type CheckinResponse struct {
	Status      string `json:"status"`
	DeviceID    string `json:"device_id"`
	CheckedInAt string `json:"checked_in_at"`
}

func NewClient(cfg config.Config, logger *slog.Logger) *Client {
	return &Client{cfg: cfg, logger: logger, httpClient: &http.Client{Timeout: 15 * time.Second}}
}

func (c *Client) Run(ctx context.Context, interval time.Duration) error {
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	if err := c.Checkin(ctx); err != nil {
		c.logger.Warn("agent check-in failed", slog.String("error", err.Error()))
	}
	if err := c.ProcessJobs(ctx); err != nil {
		c.logger.Warn("agent job processing failed", slog.String("error", err.Error()))
	}
	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-ticker.C:
			if err := c.Checkin(ctx); err != nil {
				c.logger.Warn("agent check-in failed", slog.String("error", err.Error()))
			}
			if err := c.ProcessJobs(ctx); err != nil {
				c.logger.Warn("agent job processing failed", slog.String("error", err.Error()))
			}
		}
	}
}

func (c *Client) Enroll(ctx context.Context, enrollmentToken string) (EnrollmentResponse, error) {
	machineID, err := MachineIdentifier()
	if err != nil {
		return EnrollmentResponse{}, err
	}
	hostname, err := os.Hostname()
	if err != nil {
		return EnrollmentResponse{}, err
	}
	request := EnrollmentRequest{
		EnrollmentToken: enrollmentToken,
		Hostname:        hostname,
		OperatingSystem: runtime.GOOS,
		Architecture:    runtime.GOARCH,
		AgentVersion:    AgentVersion,
		MachineID:       machineID,
	}
	var response EnrollmentResponse
	if err := c.postJSON(ctx, "/agent/enroll", request, &response); err != nil {
		return EnrollmentResponse{}, err
	}
	return response, nil
}

func (c *Client) Checkin(ctx context.Context) error {
	payload, err := BuildPayload(c.cfg)
	if err != nil {
		return err
	}
	var response CheckinResponse
	if err := c.postJSON(ctx, "/agent/checkin", payload, &response); err != nil {
		return err
	}
	c.logger.Info("agent check-in accepted", slog.String("device_id", response.DeviceID), slog.String("checked_in_at", response.CheckedInAt))
	return nil
}

func (c *Client) postJSON(ctx context.Context, path string, in any, out any) error {
	body, err := json.Marshal(in)
	if err != nil {
		return err
	}
	request, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(c.cfg.APIBaseURL, "/")+path, bytes.NewReader(body))
	if err != nil {
		return err
	}
	request.Header.Set("Content-Type", "application/json")
	response, err := c.httpClient.Do(request)
	if err != nil {
		return err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		_, _ = io.Copy(io.Discard, response.Body)
		return fmt.Errorf("server returned status %d", response.StatusCode)
	}
	return json.NewDecoder(response.Body).Decode(out)
}

func BuildPayload(cfg config.Config) (Payload, error) {
	if cfg.DeviceID == "" || cfg.DeviceSecret == "" {
		return Payload{}, errors.New("device is not enrolled")
	}
	hostname, err := os.Hostname()
	if err != nil {
		return Payload{}, err
	}
	localIPs := LocalIPs()
	primaryIP := ""
	if len(localIPs) > 0 {
		primaryIP = localIPs[0]
	}
	return Payload{
		DeviceID:         cfg.DeviceID,
		DeviceSecret:     cfg.DeviceSecret,
		Hostname:         hostname,
		OperatingSystem:  runtime.GOOS,
		Architecture:     runtime.GOARCH,
		AgentVersion:     AgentVersion,
		IPAddress:        primaryIP,
		LocalIPs:         localIPs,
		UptimeSeconds:    UptimeSeconds(),
		CPUCount:         runtime.NumCPU(),
		MemoryTotalBytes: MemoryTotalBytes(),
		MemoryUsedBytes:  MemoryUsedBytes(),
		HealthStatus:     "healthy",
		Inventory:        BuildInventory(),
	}, nil
}

func LocalIPs() []string {
	interfaces, err := net.Interfaces()
	if err != nil {
		return nil
	}
	var ips []string
	for _, item := range interfaces {
		if item.Flags&net.FlagUp == 0 || item.Flags&net.FlagLoopback != 0 {
			continue
		}
		addresses, err := item.Addrs()
		if err != nil {
			continue
		}
		for _, address := range addresses {
			ipNet, ok := address.(*net.IPNet)
			if !ok || ipNet.IP.IsLoopback() {
				continue
			}
			ip := ipNet.IP.To4()
			if ip == nil {
				continue
			}
			ips = append(ips, ip.String())
		}
	}
	return ips
}

func MachineIdentifier() (string, error) {
	hostname, err := os.Hostname()
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("%s-%s-%s", hostname, runtime.GOOS, runtime.GOARCH), nil
}

func UptimeSeconds() *int64 {
	data, err := os.ReadFile("/proc/uptime")
	if err != nil {
		return nil
	}
	first := strings.Fields(string(data))
	if len(first) == 0 {
		return nil
	}
	secondsFloat, err := strconv.ParseFloat(first[0], 64)
	if err != nil {
		return nil
	}
	seconds := int64(secondsFloat)
	return &seconds
}

func MemoryTotalBytes() *uint64 {
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return nil
	}
	for _, line := range strings.Split(string(data), "\n") {
		if !strings.HasPrefix(line, "MemTotal:") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 2 {
			return nil
		}
		kib, err := strconv.ParseUint(fields[1], 10, 64)
		if err != nil {
			return nil
		}
		bytes := kib * 1024
		return &bytes
	}
	return nil
}
