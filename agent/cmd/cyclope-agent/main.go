package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/cyclope-central/agent/internal/checkin"
	"github.com/cyclope-central/agent/internal/config"
	"github.com/cyclope-central/agent/internal/logging"
	"github.com/cyclope-central/agent/internal/service"
)

const defaultConfigPath = "cyclope-agent.json"

func main() {
	args, configPath := parseArgs(os.Args[1:])
	if configPath == "" {
		configPath = os.Getenv("CYCLOPE_AGENT_CONFIG")
	}
	if configPath == "" {
		configPath = defaultConfigPath
	}

	cfg, err := config.LoadFromFile(configPath)
	if err != nil {
		cfg = config.Default()
	}

	logger, logFile, err := newLogger(cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open agent log: %v\n", err)
		os.Exit(1)
	}
	if logFile != nil {
		defer logFile.Close()
	}

	client := checkin.NewClient(cfg, logger)
	ctx := context.Background()
	command := commandName(args)

	switch command {
	case "version":
		fmt.Printf("Cyclope Central Agent %s\n", checkin.AgentVersion)
	case "enroll":
		token := os.Getenv("CYCLOPE_ENROLLMENT_TOKEN")
		if len(args) > 1 {
			token = args[1]
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
		if err := ensureParentDir(configPath); err != nil {
			logger.Error("failed to create config directory", slog.String("error", err.Error()))
			os.Exit(1)
		}
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
		checkinInterval := intervalFromSeconds(cfg.CheckinIntervalSeconds, 300)
		jobInterval := intervalFromSeconds(cfg.JobIntervalSeconds, 60)
		if err := service.RunWindowsService(ctx, cfg.ServiceName, logger, func(ctx context.Context) error {
			return client.RunWithIntervals(ctx, checkinInterval, jobInterval)
		}); err != nil {
			logger.Error("agent stopped", slog.String("error", err.Error()))
			os.Exit(1)
		}
	case "service":
		handleServiceCommand(args, configPath, cfg, logger)
	case "config":
		handleConfigCommand(args, cfg)
	case "rustdesk":
		handleRustDeskCommand(args, logger)
	default:
		printUsage()
		os.Exit(2)
	}
}

func parseArgs(raw []string) ([]string, string) {
	args := make([]string, 0, len(raw))
	configPath := ""
	for i := 0; i < len(raw); i++ {
		arg := raw[i]
		if arg == "--config" && i+1 < len(raw) {
			configPath = raw[i+1]
			i++
			continue
		}
		if strings.HasPrefix(arg, "--config=") {
			configPath = strings.TrimPrefix(arg, "--config=")
			continue
		}
		args = append(args, arg)
	}
	return args, configPath
}

func commandName(args []string) string {
	if len(args) < 1 {
		return "run"
	}
	return args[0]
}

func newLogger(cfg config.Config) (*slog.Logger, *os.File, error) {
	if cfg.LogPath == "" {
		return logging.New(cfg.LogLevel), nil, nil
	}
	if err := ensureParentDir(cfg.LogPath); err != nil {
		return nil, nil, err
	}
	file, err := os.OpenFile(cfg.LogPath, os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o600)
	if err != nil {
		return nil, nil, err
	}
	return logging.NewWithOutput(cfg.LogLevel, file), file, nil
}

func ensureParentDir(path string) error {
	dir := filepath.Dir(path)
	if dir == "." || dir == "" {
		return nil
	}
	return os.MkdirAll(dir, 0o700)
}

func intervalFromSeconds(seconds int, fallback int) time.Duration {
	if seconds <= 0 {
		seconds = fallback
	}
	return time.Duration(seconds) * time.Second
}

func handleServiceCommand(args []string, configPath string, cfg config.Config, logger *slog.Logger) {
	if len(args) < 2 {
		printUsage()
		os.Exit(2)
	}
	exePath, err := os.Executable()
	if err != nil {
		logger.Error("failed to resolve agent executable path", slog.String("error", err.Error()))
		os.Exit(1)
	}
	serviceName := cfg.ServiceName
	if serviceName == "" {
		serviceName = config.Default().ServiceName
	}
	switch args[1] {
	case "install":
		displayName := "Cyclope Central Agent"
		description := "Cyclope Central endpoint agent for authenticated check-ins, inventory, and approved built-in jobs."
		if err := service.Install(serviceName, displayName, description, exePath, configPath); err != nil {
			logger.Error("Windows service install failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
		fmt.Println("agent service installed")
	case "start":
		if err := service.Start(serviceName); err != nil {
			logger.Error("Windows service start failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
		fmt.Println("agent service started")
	case "stop":
		if err := service.Stop(serviceName); err != nil {
			logger.Error("Windows service stop failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
		fmt.Println("agent service stopped")
	case "uninstall":
		if err := service.Uninstall(serviceName); err != nil {
			logger.Error("Windows service uninstall failed", slog.String("error", err.Error()))
			os.Exit(1)
		}
		fmt.Println("agent service uninstalled")
	default:
		printUsage()
		os.Exit(2)
	}
}

func handleRustDeskCommand(args []string, logger *slog.Logger) {
	if len(args) < 3 || args[1] != "configure" {
		printUsage()
		os.Exit(2)
	}
	serverHost, relayHost, publicKey := "", "", ""
	for i := 2; i < len(args); i++ {
		switch args[i] {
		case "--server-host":
			if i+1 < len(args) {
				serverHost = args[i+1]
				i++
			}
		case "--relay-host":
			if i+1 < len(args) {
				relayHost = args[i+1]
				i++
			}
		case "--public-key":
			if i+1 < len(args) {
				publicKey = args[i+1]
				i++
			}
		}
	}
	if publicKey == "" {
		publicKey = os.Getenv("CYCLOPE_RUSTDESK_PUBLIC_KEY")
	}
	if err := checkin.ConfigureRustDesk(serverHost, relayHost, publicKey); err != nil {
		logger.Error("RustDesk local configuration failed", slog.String("error", err.Error()))
		os.Exit(1)
	}
	fmt.Println("RustDesk local settings written")
}

func handleConfigCommand(args []string, cfg config.Config) {
	if len(args) != 2 || args[1] != "show" {
		printUsage()
		os.Exit(2)
	}
	output, err := redactedConfigJSON(cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to render config: %v\n", err)
		os.Exit(1)
	}
	fmt.Println(output)
}

func redactedConfigJSON(cfg config.Config) (string, error) {
	data, err := json.MarshalIndent(cfg.Redacted(), "", "  ")
	if err != nil {
		return "", err
	}
	return string(data), nil
}

func printUsage() {
	fmt.Fprintf(os.Stderr, `usage: %s [--config path] <command>

Commands:
  version                         Print the agent version.
  enroll [token]                  Enroll using CYCLOPE_ENROLLMENT_TOKEN or a token argument.
  checkin                         Send one authenticated check-in.
  jobs                            Poll and process safe built-in jobs once.
  run                             Run continuous check-ins and job polling.
  service install                 Install the Windows service with automatic startup.
  service start                   Start the Windows service.
  service stop                    Stop the Windows service.
  service uninstall               Remove the Windows service.
  config show                     Print configuration with stored secrets redacted.
  rustdesk configure              Write local RustDesk server settings from installer-provided arguments.
`, os.Args[0])
}
