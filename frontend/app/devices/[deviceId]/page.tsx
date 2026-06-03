"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import {
  type AgentJob,
  type Alert,
  type DeviceDetail,
  type DeviceInventory,
  type SecurityStatus,
  type SoftwareInventory,
  type UpdateStatus,
  fetchJson,
  postJson,
  postJsonBody
} from "@/lib/api";

const tabs = ["Overview", "Hardware", "Network", "Software", "Security", "Updates", "Alerts", "Jobs", "Check-ins"] as const;
type Tab = (typeof tabs)[number];

type InventoryState = {
  detail: DeviceDetail | null;
  inventory: DeviceInventory | null;
  software: SoftwareInventory | null;
  security: SecurityStatus | null;
  updates: UpdateStatus | null;
  alerts: Alert[];
  jobs: AgentJob[];
};

function formatDate(value?: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "medium" }).format(new Date(value));
}

function formatBytes(value?: number | null) {
  if (!value) return "Unknown";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1, style: "unit", unit: "gigabyte" }).format(value / 1_000_000_000);
}

function boolLabel(value?: boolean | null) {
  if (value === true) return "Enabled";
  if (value === false) return "Disabled";
  return "Unknown";
}

function Stat({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-slate-950 p-4"><dt className="text-sm text-slate-400">{label}</dt><dd className="mt-1 font-medium">{value}</dd></div>;
}

export default function DeviceDetailPage({ params }: { params: Promise<{ deviceId: string }> }) {
  const { deviceId } = use(params);
  const [activeTab, setActiveTab] = useState<Tab>("Overview");
  const [state, setState] = useState<InventoryState>({ detail: null, inventory: null, software: null, security: null, updates: null, alerts: [], jobs: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [detail, inventory, software, security, updates, alerts, jobs] = await Promise.all([
          fetchJson<DeviceDetail>(`/devices/${deviceId}`),
          fetchJson<DeviceInventory>(`/devices/${deviceId}/inventory`).catch(() => null),
          fetchJson<SoftwareInventory>(`/devices/${deviceId}/software`).catch(() => null),
          fetchJson<SecurityStatus>(`/devices/${deviceId}/security`).catch(() => null),
          fetchJson<UpdateStatus>(`/devices/${deviceId}/updates`).catch(() => null),
          fetchJson<Alert[]>(`/devices/${deviceId}/alerts`).catch(() => []),
          fetchJson<AgentJob[]>(`/devices/${deviceId}/jobs`).catch(() => [])
        ]);
        if (mounted) setState({ detail, inventory, software, security, updates, alerts, jobs });
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        if (mounted) setLoading(false);
      }
    }
    load();
    return () => { mounted = false; };
  }, [deviceId]);

  const { detail, inventory, software, security, updates, alerts, jobs } = state;

  async function createJob(job_type: string) {
    const payload = job_type === "get_service_status" ? { service_name: window.prompt("Service name", "Spooler") ?? "" } : {};
    await postJsonBody<AgentJob>(`/devices/${deviceId}/jobs`, { job_type, payload });
    const refreshed = await fetchJson<AgentJob[]>(`/devices/${deviceId}/jobs`);
    setState((current) => ({ ...current, jobs: refreshed }));
  }

  async function cancelJob(jobId: string) {
    await postJson<AgentJob>(`/jobs/${jobId}/cancel`);
    const refreshed = await fetchJson<AgentJob[]>(`/devices/${deviceId}/jobs`);
    setState((current) => ({ ...current, jobs: refreshed }));
  }

  return (
    <AppShell>
      <div className="mb-4"><Button asChild variant="ghost"><Link href="/devices">← Back to devices</Link></Button></div>
      {loading && <p className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-slate-300">Loading device inventory…</p>}
      {error && <p className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-200">Unable to load device: {error}</p>}
      {detail && (
        <section className="space-y-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div><h1 className="text-3xl font-bold">{detail.hostname}</h1><p className="mt-2 text-slate-400">{detail.operating_system} · {detail.architecture ?? "unknown architecture"}</p></div>
              <span className={detail.is_online ? "rounded-full bg-emerald-400/10 px-3 py-1 text-sm text-emerald-300" : "rounded-full bg-slate-700 px-3 py-1 text-sm text-slate-300"}>{detail.status}</span>
            </div>
            <div className="mt-6 flex flex-wrap gap-2">{tabs.map((tab) => <button key={tab} onClick={() => setActiveTab(tab)} className={activeTab === tab ? "rounded-md bg-cyan-400 px-3 py-2 text-sm font-medium text-slate-950" : "rounded-md bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700"}>{tab}</button>)}</div>
          </div>

          {activeTab === "Overview" && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><Stat label="IP address" value={detail.ip_address ?? "Unknown"} /><Stat label="Agent version" value={detail.agent_version ?? "Unknown"} /><Stat label="Last seen" value={formatDate(detail.last_seen_at)} /><Stat label="Last inventory" value={formatDate(inventory?.inventory_refreshed_at)} /></div>}
          {activeTab === "Hardware" && <div className="space-y-4"><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><Stat label="CPU" value={inventory?.cpu_model ?? "Unknown"} /><Stat label="CPU cores" value={String(inventory?.cpu_cores ?? "Unknown")} /><Stat label="RAM" value={formatBytes(inventory?.memory_total_bytes)} /><Stat label="System" value={[inventory?.system_manufacturer, inventory?.system_model].filter(Boolean).join(" ") || "Unknown"} /></div><InventoryTableEmpty show={!inventory} label="No hardware inventory has been reported yet." />{inventory?.disks.map((disk) => <div key={disk.id} className="rounded-xl bg-slate-900 p-4"><p className="font-medium">{disk.name}</p><p className="text-sm text-slate-400">{disk.filesystem ?? "Unknown FS"} · {formatBytes(disk.free_bytes)} free of {formatBytes(disk.size_bytes)}</p></div>)}</div>}
          {activeTab === "Network" && <div className="space-y-3"><InventoryTableEmpty show={!inventory || inventory.network_interfaces.length === 0} label="No network interfaces have been reported yet." />{inventory?.network_interfaces.map((adapter) => <div key={adapter.id} className="rounded-xl bg-slate-900 p-4"><p className="font-medium">{adapter.name}</p><p className="text-sm text-slate-400">MAC {adapter.mac_address ?? "Unknown"}</p><p className="mt-2 text-sm">{adapter.ip_addresses.join(", ") || "No IPs reported"}</p></div>)}</div>}
          {activeTab === "Software" && <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4"><InventoryTableEmpty show={!software || software.software.length === 0} label="No installed software inventory has been reported yet." />{software && software.software.length > 0 && <div className="overflow-auto"><table className="w-full text-sm"><thead className="text-left text-slate-400"><tr><th className="p-2">Name</th><th className="p-2">Version</th><th className="p-2">Publisher</th></tr></thead><tbody>{software.software.map((item) => <tr key={item.id} className="border-t border-slate-800"><td className="p-2">{item.name}</td><td className="p-2">{item.version ?? ""}</td><td className="p-2">{item.publisher ?? ""}</td></tr>)}</tbody></table></div>}</div>}
          {activeTab === "Security" && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4"><Stat label="Antivirus" value={security?.antivirus_product ?? "Unknown"} /><Stat label="AV enabled" value={boolLabel(security?.antivirus_enabled)} /><Stat label="Defender" value={boolLabel(security?.defender_enabled)} /><Stat label="Firewall" value={boolLabel(security?.firewall_enabled)} /></div>}
          {activeTab === "Updates" && <div className="grid gap-4 md:grid-cols-3"><Stat label="Pending reboot" value={updates?.pending_reboot === true ? "Yes" : updates?.pending_reboot === false ? "No" : "Unknown"} /><Stat label="Update status" value={updates?.update_status ?? "Unknown"} /><Stat label="Last checked" value={formatDate(updates?.last_update_check_at)} /></div>}

          {activeTab === "Alerts" && <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4">{alerts.length === 0 ? <p className="text-slate-400">No alerts have been generated for this device.</p> : <div className="space-y-3">{alerts.map((alert) => <div key={alert.id} className="rounded-xl bg-slate-950 p-4"><div className="flex flex-wrap items-center gap-2"><span className="font-medium">{alert.title}</span><span className="rounded-full bg-slate-800 px-2 py-1 text-xs uppercase text-slate-300">{alert.severity}</span><span className="rounded-full bg-slate-800 px-2 py-1 text-xs uppercase text-slate-300">{alert.status}</span></div><p className="mt-2 text-sm text-slate-400">{alert.message}</p><p className="mt-1 text-xs text-slate-500">Last seen {formatDate(alert.last_seen_at)}</p></div>)}</div>}</div>}

          {activeTab === "Jobs" && <div className="rounded-2xl border border-slate-800 bg-slate-900 p-4"><div className="mb-4 flex flex-wrap gap-2">{["ping", "refresh_inventory", "collect_agent_logs", "get_service_status"].map((type) => <Button key={type} variant="secondary" type="button" onClick={() => createJob(type)}>{type}</Button>)}</div>{jobs.length === 0 ? <p className="text-slate-400">No jobs have been created for this device.</p> : <div className="space-y-3">{jobs.map((job) => <div key={job.id} className="rounded-xl bg-slate-950 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-medium">{job.job_type}</p><p className="text-sm text-slate-400">{job.status} · created {formatDate(job.created_at)}</p><p className="text-xs text-slate-500">Started {formatDate(job.started_at)} · completed {formatDate(job.completed_at)}</p></div>{!["succeeded", "failed", "canceled", "expired"].includes(job.status) && <Button variant="secondary" type="button" onClick={() => cancelJob(job.id)}>Cancel</Button>}</div>{job.result_summary && <p className="mt-2 text-sm text-slate-300">{job.result_summary}</p>}{job.events.length > 0 && <div className="mt-3 space-y-1 text-xs text-slate-500">{job.events.map((event) => <p key={event.id}>{event.event_type}: {event.message}</p>)}</div>}</div>)}</div>}</div>}
          {activeTab === "Check-ins" && <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6"><h2 className="text-xl font-semibold">Latest check-in</h2>{detail.latest_checkin ? <div className="mt-4 space-y-3 text-sm text-slate-300"><p>Checked in at {formatDate(detail.latest_checkin.checked_in_at)}</p><p>Status: {detail.latest_checkin.status}</p><pre className="overflow-auto rounded-xl bg-slate-950 p-4 text-xs">{JSON.stringify(detail.latest_checkin.payload, null, 2)}</pre></div> : <p className="mt-4 text-slate-400">No check-ins recorded yet.</p>}</div>}
        </section>
      )}
    </AppShell>
  );
}

function InventoryTableEmpty({ show, label }: { show: boolean; label: string }) {
  return show ? <p className="rounded-xl border border-slate-800 bg-slate-950 p-4 text-slate-300">{label}</p> : null;
}
