//go:build !windows

package service

import (
	"context"
	"errors"
	"log/slog"
)

// UnixServiceName reserves a future systemd/launchd integration point for Linux support.
const UnixServiceName = "cyclope-central-agent"

func RunWindowsService(ctx context.Context, _ string, logger *slog.Logger, work WorkFunc) error {
	return NewRunner(logger, work).Run(ctx)
}

func Install(_ string, _ string, _ string, _ string, _ string) error {
	return errors.New("Windows service installation is only supported on Windows")
}

func Start(_ string) error {
	return errors.New("Windows service start is only supported on Windows")
}

func Stop(_ string) error {
	return errors.New("Windows service stop is only supported on Windows")
}

func Uninstall(_ string) error {
	return errors.New("Windows service uninstall is only supported on Windows")
}
