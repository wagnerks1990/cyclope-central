package checkin

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/cyclope-central/agent/internal/config"
)

type Job struct {
	ID      string         `json:"id"`
	Type    string         `json:"job_type"`
	Status  string         `json:"status"`
	Payload map[string]any `json:"payload"`
}

type JobCompleteRequest struct {
	DeviceID     string         `json:"device_id"`
	DeviceSecret string         `json:"device_secret"`
	Succeeded    bool           `json:"succeeded"`
	Output       string         `json:"output"`
	Error        *string        `json:"error,omitempty"`
	ExitCode     *int           `json:"exit_code,omitempty"`
	Metadata     map[string]any `json:"metadata"`
}

type JobAuthRequest struct {
	DeviceID     string `json:"device_id"`
	DeviceSecret string `json:"device_secret"`
}

func (c *Client) ProcessJobs(ctx context.Context) error {
	jobs, err := c.PollJobs(ctx)
	if err != nil {
		return err
	}
	for _, job := range jobs {
		if err := c.StartJob(ctx, job.ID); err != nil {
			return err
		}
		result := ExecuteJob(c.cfg, job)
		if job.Type == "refresh_inventory" && result.Succeeded {
			if err := c.Checkin(ctx); err != nil {
				result = failedJobResult(c.cfg, job, err)
			}
		}
		if err := c.CompleteJob(ctx, job.ID, result); err != nil {
			return err
		}
	}
	return nil
}

func (c *Client) PollJobs(ctx context.Context) ([]Job, error) {
	if c.cfg.DeviceID == "" || c.cfg.DeviceSecret == "" {
		return nil, errors.New("device is not enrolled")
	}
	request, err := http.NewRequestWithContext(
		ctx,
		http.MethodGet,
		strings.TrimRight(c.cfg.APIBaseURL, "/")+"/agent/jobs",
		nil,
	)
	if err != nil {
		return nil, err
	}
	request.Header.Set("X-Cyclope-Device-Id", c.cfg.DeviceID)
	request.Header.Set("X-Cyclope-Device-Secret", c.cfg.DeviceSecret)
	response, err := c.httpClient.Do(request)
	if err != nil {
		return nil, err
	}
	defer response.Body.Close()
	if response.StatusCode < 200 || response.StatusCode >= 300 {
		_, _ = io.Copy(io.Discard, response.Body)
		return nil, fmt.Errorf("server returned status %d", response.StatusCode)
	}
	var jobs []Job
	return jobs, json.NewDecoder(response.Body).Decode(&jobs)
}

func (c *Client) StartJob(ctx context.Context, jobID string) error {
	var response Job
	return c.postJSON(ctx, "/agent/jobs/"+jobID+"/start", JobAuthRequest{
		DeviceID:     c.cfg.DeviceID,
		DeviceSecret: c.cfg.DeviceSecret,
	}, &response)
}

func (c *Client) CompleteJob(ctx context.Context, jobID string, result JobCompleteRequest) error {
	var response Job
	return c.postJSON(ctx, "/agent/jobs/"+jobID+"/complete", result, &response)
}

func ExecuteJob(cfg config.Config, job Job) JobCompleteRequest {
	result := JobCompleteRequest{
		DeviceID:     cfg.DeviceID,
		DeviceSecret: cfg.DeviceSecret,
		Succeeded:    true,
		Metadata:     map[string]any{"handler": job.Type},
	}
	exitCode := 0
	result.ExitCode = &exitCode
	switch job.Type {
	case "ping":
		result.Output = "pong " + time.Now().UTC().Format(time.RFC3339)
	case "refresh_inventory":
		payload, err := BuildPayload(cfg)
		if err != nil {
			return failedJobResult(cfg, job, err)
		}
		encoded, _ := json.Marshal(payload.Inventory)
		result.Output = string(encoded)
		result.Metadata["inventory_collected"] = true
	case "collect_agent_logs":
		result.Output = collectAgentLogs(job.Payload)
	case "get_service_status":
		name, _ := job.Payload["service_name"].(string)
		status, err := serviceStatus(name)
		if err != nil {
			return failedJobResult(cfg, job, err)
		}
		result.Output = status
	default:
		return failedJobResult(cfg, job, fmt.Errorf("unsupported job type %q", job.Type))
	}
	return result
}

func failedJobResult(cfg config.Config, job Job, err error) JobCompleteRequest {
	exitCode := 1
	message := err.Error()
	return JobCompleteRequest{
		DeviceID:     cfg.DeviceID,
		DeviceSecret: cfg.DeviceSecret,
		Succeeded:    false,
		Error:        &message,
		ExitCode:     &exitCode,
		Metadata:     map[string]any{"handler": job.Type},
	}
}

func collectAgentLogs(payload map[string]any) string {
	lineCount := 100
	if value, ok := payload["line_count"].(float64); ok && value > 0 && value <= 200 {
		lineCount = int(value)
	}
	return fmt.Sprintf("agent log collection is configured for last %d structured log lines; persistent local log file is not configured", lineCount)
}
