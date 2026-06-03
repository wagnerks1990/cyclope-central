//go:build windows

package service

import (
	"context"
	"errors"
	"log/slog"
	"time"

	"golang.org/x/sys/windows/svc"
	"golang.org/x/sys/windows/svc/mgr"
)

// WindowsServiceName is the default service name for installers.
const WindowsServiceName = "CyclopeCentralAgent"

type windowsHandler struct {
	logger *slog.Logger
	work   WorkFunc
}

func RunWindowsService(ctx context.Context, name string, logger *slog.Logger, work WorkFunc) error {
	isService, err := svc.IsWindowsService()
	if err != nil {
		return err
	}
	if !isService {
		return NewRunner(logger, work).Run(ctx)
	}
	return svc.Run(name, &windowsHandler{logger: logger, work: work})
}

func (h *windowsHandler) Execute(_ []string, requests <-chan svc.ChangeRequest, status chan<- svc.Status) (bool, uint32) {
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)

	status <- svc.Status{State: svc.StartPending}
	go func() { done <- h.work(ctx) }()
	status <- svc.Status{State: svc.Running, Accepts: svc.AcceptStop | svc.AcceptShutdown}

	for {
		select {
		case request := <-requests:
			switch request.Cmd {
			case svc.Interrogate:
				status <- request.CurrentStatus
			case svc.Stop, svc.Shutdown:
				status <- svc.Status{State: svc.StopPending}
				cancel()
				select {
				case err := <-done:
					if err != nil && !errors.Is(err, context.Canceled) {
						h.logger.Warn("agent service stopped with error", slog.String("error", err.Error()))
					}
				case <-time.After(20 * time.Second):
					h.logger.Warn("agent service shutdown timed out")
				}
				status <- svc.Status{State: svc.Stopped}
				return false, 0
			}
		case err := <-done:
			if err != nil && !errors.Is(err, context.Canceled) {
				h.logger.Error("agent service worker exited", slog.String("error", err.Error()))
				status <- svc.Status{State: svc.Stopped}
				return false, 1
			}
			status <- svc.Status{State: svc.Stopped}
			return false, 0
		}
	}
}

func Install(name string, displayName string, description string, exePath string, configPath string) error {
	manager, err := mgr.Connect()
	if err != nil {
		return err
	}
	defer manager.Disconnect()

	serviceHandle, err := manager.CreateService(
		name,
		exePath,
		mgr.Config{StartType: mgr.StartAutomatic, DisplayName: displayName, Description: description},
		"--config", configPath, "run",
	)
	if err != nil {
		return err
	}
	return serviceHandle.Close()
}

func Start(name string) error {
	serviceHandle, err := openService(name)
	if err != nil {
		return err
	}
	defer serviceHandle.Close()
	return serviceHandle.Start()
}

func Stop(name string) error {
	serviceHandle, err := openService(name)
	if err != nil {
		return err
	}
	defer serviceHandle.Close()
	status, err := serviceHandle.Control(svc.Stop)
	if err != nil {
		return err
	}
	deadline := time.Now().Add(30 * time.Second)
	for status.State != svc.Stopped {
		if time.Now().After(deadline) {
			return errors.New("timed out waiting for Windows service to stop")
		}
		time.Sleep(500 * time.Millisecond)
		status, err = serviceHandle.Query()
		if err != nil {
			return err
		}
	}
	return nil
}

func Uninstall(name string) error {
	serviceHandle, err := openService(name)
	if err != nil {
		return err
	}
	defer serviceHandle.Close()
	return serviceHandle.Delete()
}

func openService(name string) (*mgr.Service, error) {
	manager, err := mgr.Connect()
	if err != nil {
		return nil, err
	}
	serviceHandle, err := manager.OpenService(name)
	manager.Disconnect()
	return serviceHandle, err
}
