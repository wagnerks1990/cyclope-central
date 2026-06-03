//go:build windows

package checkin

import (
	"fmt"
	"regexp"

	"golang.org/x/sys/windows/svc/mgr"
)

var serviceNamePattern = regexp.MustCompile(`^[A-Za-z0-9_. -]{1,128}$`)

func serviceStatus(name string) (string, error) {
	if !serviceNamePattern.MatchString(name) {
		return "", fmt.Errorf("invalid service_name")
	}
	manager, err := mgr.Connect()
	if err != nil {
		return "", err
	}
	defer manager.Disconnect()
	service, err := manager.OpenService(name)
	if err != nil {
		return "", err
	}
	defer service.Close()
	status, err := service.Query()
	if err != nil {
		return "", err
	}
	return fmt.Sprintf("service %s state %v", name, status.State), nil
}
