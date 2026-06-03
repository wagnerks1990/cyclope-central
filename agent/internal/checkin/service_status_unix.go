//go:build !windows

package checkin

import "fmt"

func serviceStatus(name string) (string, error) {
	if name == "" {
		return "", fmt.Errorf("service_name is required")
	}
	return "service status collection is a Windows-first handler; Linux support is a future placeholder", nil
}
