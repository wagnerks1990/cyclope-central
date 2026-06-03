export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export type DeviceSummary = {
  id: string;
  hostname: string;
  operating_system: string;
  architecture?: string | null;
  ip_address?: string | null;
  agent_version?: string | null;
  health_status: string;
  status: string;
  is_online: boolean;
  last_seen_at?: string | null;
};

export type CheckinSummary = {
  checked_in_at: string;
  status: string;
  ip_address?: string | null;
  agent_version?: string | null;
  payload: Record<string, unknown>;
};

export type DeviceDetail = DeviceSummary & {
  machine_identifier: string;
  latest_checkin?: CheckinSummary | null;
};

export type DiskInventory = {
  id: string;
  name: string;
  filesystem?: string | null;
  size_bytes?: number | null;
  free_bytes?: number | null;
};

export type NetworkInterfaceInventory = {
  id: string;
  name: string;
  mac_address?: string | null;
  ip_addresses: string[];
};

export type DeviceInventory = {
  device_id: string;
  hostname: string;
  operating_system: string;
  os_version?: string | null;
  os_build?: string | null;
  architecture?: string | null;
  agent_version?: string | null;
  cpu_model?: string | null;
  cpu_cores?: number | null;
  memory_total_bytes?: number | null;
  bios_vendor?: string | null;
  bios_version?: string | null;
  system_manufacturer?: string | null;
  system_model?: string | null;
  inventory_refreshed_at: string;
  disks: DiskInventory[];
  network_interfaces: NetworkInterfaceInventory[];
};

export type InstalledSoftware = {
  id: string;
  name: string;
  version?: string | null;
  publisher?: string | null;
  installed_at?: string | null;
};

export type SoftwareInventory = {
  device_id: string;
  inventory_refreshed_at?: string | null;
  software: InstalledSoftware[];
};

export type SecurityStatus = {
  device_id: string;
  antivirus_product?: string | null;
  antivirus_enabled?: boolean | null;
  antivirus_up_to_date?: boolean | null;
  defender_enabled?: boolean | null;
  firewall_enabled?: boolean | null;
  details: Record<string, unknown>;
  refreshed_at: string;
};

export type UpdateStatus = {
  device_id: string;
  pending_reboot?: boolean | null;
  update_status?: string | null;
  last_update_check_at?: string | null;
  details: Record<string, unknown>;
  refreshed_at: string;
};

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type AlertEvent = {
  id: string;
  event_type: string;
  message: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type Alert = {
  id: string;
  organization_id: string;
  device_id: string;
  rule_id: string;
  severity: "info" | "warning" | "critical";
  status: "active" | "acknowledged" | "resolved";
  title: string;
  message: string;
  first_seen_at: string;
  last_seen_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
  device_hostname?: string | null;
  rule_key?: string | null;
  events: AlertEvent[];
};

export type DashboardSummary = {
  total_devices: number;
  online_devices: number;
  offline_devices: number;
  active_warning_alerts: number;
  active_critical_alerts: number;
  devices_needing_attention: number;
  recent_alerts: Alert[];
};

export async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { method: "POST" });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type AgentJobEvent = {
  id: string;
  event_type: string;
  message: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type AgentJobResult = {
  id: string;
  status: string;
  output: string;
  error?: string | null;
  exit_code?: number | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
};

export type AgentJob = {
  id: string;
  organization_id: string;
  device_id: string;
  assigned_agent_id?: string | null;
  job_type: string;
  status: string;
  payload: Record<string, unknown>;
  expires_at: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  result_summary?: string | null;
  result?: AgentJobResult | null;
  events: AgentJobEvent[];
};

export async function postJsonBody<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export type NotificationChannel = {
  id: string;
  organization_id: string;
  name: string;
  channel_type: "email" | "webhook";
  enabled: boolean;
  config: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type NotificationRule = {
  id: string;
  organization_id: string;
  name: string;
  enabled: boolean;
  severity_filter: string[];
  alert_rule_type_filter: string[];
  channel_ids: string[];
  created_at: string;
  updated_at: string;
};

export type NotificationDelivery = {
  id: string;
  organization_id: string;
  alert_id: string;
  channel_id: string;
  channel_name?: string | null;
  channel_type?: string | null;
  status: string;
  attempts: number;
  last_error?: string | null;
  created_at: string;
  sent_at?: string | null;
};

export async function patchJsonBody<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}
