//go:build !windows

package checkin

import "syscall"

func collectPlatformInventory(_ *Inventory) {
	// Future Linux expansion point: add distro-specific package, update, and security posture readers.
}

func Disks() []Disk {
	var stat syscall.Statfs_t
	if err := syscall.Statfs("/", &stat); err != nil {
		return nil
	}
	size := uint64(stat.Blocks) * uint64(stat.Bsize)
	free := uint64(stat.Bavail) * uint64(stat.Bsize)
	return []Disk{{Name: "/", Filesystem: "unknown", SizeBytes: &size, FreeBytes: &free}}
}
