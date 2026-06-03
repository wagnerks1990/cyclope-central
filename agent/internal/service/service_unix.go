//go:build !windows

package service

// UnixServiceName reserves a future systemd/launchd integration point for Linux support.
const UnixServiceName = "cyclope-central-agent"
