//go:build windows

package checkin

import (
	"strings"
	"syscall"
	"unsafe"

	"golang.org/x/sys/windows/registry"
)

func collectPlatformInventory(inventory *Inventory) {
	inventory.InstalledSoftware = installedSoftwareFromRegistry()
	inventory.OSVersion, inventory.OSBuild = windowsVersionFromRegistry()
	inventory.Security = windowsSecurityStatus()
	inventory.Updates = windowsUpdateStatus()
	inventory.Disks = windowsDisks()
}

func installedSoftwareFromRegistry() []InstalledSoftware {
	paths := []struct {
		key  registry.Key
		path string
	}{
		{registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall`},
		{registry.LOCAL_MACHINE, `SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall`},
	}
	seen := map[string]struct{}{}
	var software []InstalledSoftware
	for _, source := range paths {
		root, err := registry.OpenKey(source.key, source.path, registry.READ)
		if err != nil {
			continue
		}
		names, err := root.ReadSubKeyNames(-1)
		root.Close()
		if err != nil {
			continue
		}
		for _, name := range names {
			itemKey, err := registry.OpenKey(source.key, source.path+`\`+name, registry.READ)
			if err != nil {
				continue
			}
			displayName, _, _ := itemKey.GetStringValue("DisplayName")
			version, _, _ := itemKey.GetStringValue("DisplayVersion")
			publisher, _, _ := itemKey.GetStringValue("Publisher")
			itemKey.Close()
			displayName = strings.TrimSpace(displayName)
			if displayName == "" {
				continue
			}
			fingerprint := displayName + "|" + version + "|" + publisher
			if _, ok := seen[fingerprint]; ok {
				continue
			}
			seen[fingerprint] = struct{}{}
			software = append(software, InstalledSoftware{Name: displayName, Version: version, Publisher: publisher})
		}
	}
	return software
}

func windowsVersionFromRegistry() (string, string) {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows NT\CurrentVersion`, registry.READ)
	if err != nil {
		return "", ""
	}
	defer key.Close()
	product, _, _ := key.GetStringValue("ProductName")
	displayVersion, _, _ := key.GetStringValue("DisplayVersion")
	build, _, _ := key.GetStringValue("CurrentBuildNumber")
	version := strings.TrimSpace(product + " " + displayVersion)
	return version, build
}

func windowsSecurityStatus() SecurityStatus {
	status := SecurityStatus{Details: map[string]any{"source": "registry", "collection": "read-only"}}
	if key, err := registry.OpenKey(registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows Defender`, registry.READ); err == nil {
		defer key.Close()
		disableAntiSpyware, _, _ := key.GetIntegerValue("DisableAntiSpyware")
		defenderEnabled := disableAntiSpyware == 0
		status.DefenderEnabled = &defenderEnabled
		status.AntivirusProduct = "Microsoft Defender"
		status.AntivirusEnabled = &defenderEnabled
	}
	firewallEnabled := firewallProfileEnabled(`SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\DomainProfile`) ||
		firewallProfileEnabled(`SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\PublicProfile`) ||
		firewallProfileEnabled(`SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile`)
	status.FirewallEnabled = &firewallEnabled
	return status
}

func firewallProfileEnabled(path string) bool {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, path, registry.READ)
	if err != nil {
		return false
	}
	defer key.Close()
	enableFirewall, _, err := key.GetIntegerValue("EnableFirewall")
	return err == nil && enableFirewall == 1
}

func windowsUpdateStatus() UpdateStatus {
	pending := registryKeyExists(`SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending`) ||
		registryKeyExists(`SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired`) ||
		registryKeyExists(`SYSTEM\CurrentControlSet\Control\Session Manager\PendingFileRenameOperations`)
	status := "unknown"
	if pending {
		status = "pending_reboot"
	}
	return UpdateStatus{
		PendingReboot: &pending,
		UpdateStatus:  status,
		Details:       map[string]any{"source": "registry", "collection": "read-only_no_scan"},
	}
}

func registryKeyExists(path string) bool {
	key, err := registry.OpenKey(registry.LOCAL_MACHINE, path, registry.READ)
	if err != nil {
		return false
	}
	key.Close()
	return true
}

func windowsDisks() []Disk {
	kernel32 := syscall.NewLazyDLL("kernel32.dll")
	getDiskFreeSpaceEx := kernel32.NewProc("GetDiskFreeSpaceExW")
	var disks []Disk
	for letter := 'A'; letter <= 'Z'; letter++ {
		root := string(letter) + `:\`
		rootPtr, _ := syscall.UTF16PtrFromString(root)
		var freeBytesAvailable, totalBytes, totalFreeBytes uint64
		ret, _, _ := getDiskFreeSpaceEx.Call(
			uintptr(unsafe.Pointer(rootPtr)),
			uintptr(unsafe.Pointer(&freeBytesAvailable)),
			uintptr(unsafe.Pointer(&totalBytes)),
			uintptr(unsafe.Pointer(&totalFreeBytes)),
		)
		if ret == 0 {
			continue
		}
		disks = append(disks, Disk{Name: strings.TrimRight(root, `\`), Filesystem: "unknown", SizeBytes: &totalBytes, FreeBytes: &totalFreeBytes})
	}
	return disks
}
