package main

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"time"

	"github.com/cyclope-central/agent/internal/checkin"
	"github.com/cyclope-central/agent/internal/config"
	"github.com/cyclope-central/agent/internal/logging"
	"github.com/cyclope-central/agent/internal/service"
)

const defaultConfigPath = "cyclope-agent.json"

func main() {
	configPath := os.Getenv("CYCLOPE_AGENT_CONFIG")
	if configPath == "" {
		configPath = defaultConfigPath
	}

	cfg, err := config.LoadFromFile(configPath)
	if err != nil {
		cfg = config.Default()
	}

	logger := logging.New(cfg.LogLevel)
	client := checkin.NewClient(cfg, logger)
	ctx := context.Background()

	switch command := commandName(); command {
	case "enroll":
		token := os.Getenv("CYCLOPE_ENROLLMENT_TOKEN")
		if len(os.Args) > 2 {
			token = os.Args[2]
		}
		if token == "" {
			logger.Error("enrollment token required via argument or CYCLOPE_ENROLLMENT_TOKEN")
			os.Exit(2)
		}
		response, err := client.Enroll(ctx, token)
		if err != nil {
			logger.Error("agent enrollment failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
		cfg.DeviceID = response.DeviceID
		cfg.DeviceSecret = response.DeviceSecret
		if err := config.SaveToFile(configPath, cfg); err != nil {
			logger.Error("failed to save enrolled config", slog.String("error", err.Error()))
			os.Exit(1)
		}
		fmt.Println("agent enrolled successfully")
	case "checkin":
		if err := client.Checkin(ctx); err != nil {
			logger.Error("agent check-in failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
	case "jobs":
		if err := client.ProcessJobs(ctx); err != nil {
			logger.Error("agent job processing failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
	case "run":
		runner := service.NewRunner(logger, func(ctx context.Context) error {
			return client.Run(ctx, 30*time.Second)
		})
		if err := runner.Run(ctx); err != nil {
			logger.Error("agent stopped", slog.String("error", err.Error()))
			os.Exit(1)
		}
	default:
		fmt.Fprintf(os.Stderr, "usage: %s [run|enroll <token>|checkin|jobs]\n", os.Args[0])
		os.Exit(2)
	}
}

func commandName() string {
	if len(os.Args) < 2 {
		return "run"
	}
	return os.Args[1]
}
