package checkin

import (
	"net"
	"os"
	"runtime"
	"strconv"
	"strings"
)

type Inventory struct {
	OSVersion          string              `json:"os_version,omitempty"`
	OSBuild            string              `json:"os_build,omitempty"`
	CPUModel           string              `json:"cpu_model,omitempty"`
	CPUCores           int                 `json:"cpu_cores,omitempty"`
	MemoryTotalBytes   *uint64             `json:"memory_total_bytes,omitempty"`
	BIOSVendor         string              `json:"bios_vendor,omitempty"`
	BIOSVersion        string              `json:"bios_version,omitempty"`
	SystemManufacturer string              `json:"system_manufacturer,omitempty"`
	SystemModel        string              `json:"system_model,omitempty"`
	Disks              []Disk              `json:"disks"`
	NetworkInterfaces  []NetworkInterface  `json:"network_interfaces"`
	InstalledSoftware  []InstalledSoftware `json:"installed_software"`
	Security           SecurityStatus      `json:"security"`
	Updates            UpdateStatus        `json:"updates"`
}

type Disk struct {
	Name       string  `json:"name"`
	Filesystem string  `json:"filesystem,omitempty"`
	SizeBytes  *uint64 `json:"size_bytes,omitempty"`
	FreeBytes  *uint64 `json:"free_bytes,omitempty"`
}

type NetworkInterface struct {
	Name        string   `json:"name"`
	MACAddress  string   `json:"mac_address,omitempty"`
	IPAddresses []string `json:"ip_addresses"`
}

type InstalledSoftware struct {
	Name      string `json:"name"`
	Version   string `json:"version,omitempty"`
	Publisher string `json:"publisher,omitempty"`
}

type SecurityStatus struct {
	AntivirusProduct  string         `json:"antivirus_product,omitempty"`
	AntivirusEnabled  *bool          `json:"antivirus_enabled,omitempty"`
	AntivirusUpToDate *bool          `json:"antivirus_up_to_date,omitempty"`
	DefenderEnabled   *bool          `json:"defender_enabled,omitempty"`
	FirewallEnabled   *bool          `json:"firewall_enabled,omitempty"`
	Details           map[string]any `json:"details"`
}

type UpdateStatus struct {
	PendingReboot *bool          `json:"pending_reboot,omitempty"`
	UpdateStatus  string         `json:"update_status,omitempty"`
	Details       map[string]any `json:"details"`
}

func BuildInventory() Inventory {
	inventory := Inventory{
		CPUModel:          CPUModel(),
		CPUCores:          runtime.NumCPU(),
		MemoryTotalBytes:  MemoryTotalBytes(),
		Disks:             Disks(),
		NetworkInterfaces: NetworkInterfaces(),
		Security: SecurityStatus{
			Details: map[string]any{"collection": "read-only"},
		},
		Updates: UpdateStatus{
			Details: map[string]any{"collection": "read-only"},
		},
	}
	collectPlatformInventory(&inventory)
	return inventory
}

func CPUModel() string {
	data, err := os.ReadFile("/proc/cpuinfo")
	if err != nil {
		return ""
	}
	for _, line := range strings.Split(string(data), "\n") {
		if strings.HasPrefix(strings.ToLower(line), "model name") {
			parts := strings.SplitN(line, ":", 2)
			if len(parts) == 2 {
				return strings.TrimSpace(parts[1])
			}
		}
	}
	return ""
}

func NetworkInterfaces() []NetworkInterface {
	interfaces, err := net.Interfaces()
	if err != nil {
		return nil
	}
	var result []NetworkInterface
	for _, item := range interfaces {
		if item.Flags&net.FlagUp == 0 || item.Flags&net.FlagLoopback != 0 {
			continue
		}
		addresses, err := item.Addrs()
		if err != nil {
			continue
		}
		var ips []string
		for _, address := range addresses {
			ipNet, ok := address.(*net.IPNet)
			if !ok || ipNet.IP.IsLoopback() {
				continue
			}
			ips = append(ips, ipNet.IP.String())
		}
		result = append(result, NetworkInterface{
			Name:        item.Name,
			MACAddress:  item.HardwareAddr.String(),
			IPAddresses: ips,
		})
	}
	return result
}

func MemoryUsedBytes() *uint64 {
	total := MemoryTotalBytes()
	if total == nil {
		return nil
	}
	data, err := os.ReadFile("/proc/meminfo")
	if err != nil {
		return nil
	}
	var available *uint64
	for _, line := range strings.Split(string(data), "\n") {
		if !strings.HasPrefix(line, "MemAvailable:") {
			continue
		}
		fields := strings.Fields(line)
		if len(fields) < 2 {
			return nil
		}
		kib, err := strconv.ParseUint(fields[1], 10, 64)
		if err != nil {
			return nil
		}
		bytes := kib * 1024
		available = &bytes
	}
	if available == nil || *total < *available {
		return nil
	}
	used := *total - *available
	return &used
}
