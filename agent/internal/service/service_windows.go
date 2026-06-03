//go:build windows

package service

// WindowsServiceName is the default service name for installers.
// Future expansion point: wire this runner into golang.org/x/sys/windows/svc for SCM integration.
const WindowsServiceName = "CyclopeCentralAgent"
