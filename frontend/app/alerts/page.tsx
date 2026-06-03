"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import { type Alert, fetchJson, postJson } from "@/lib/api";

function formatDate(value?: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState<Alert | null>(null);
  const [severity, setSeverity] = useState("");
  const [status, setStatus] = useState("active");
  const [deviceId, setDeviceId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (severity) params.set("severity", severity);
    if (status) params.set("status", status);
    if (deviceId) params.set("device_id", deviceId);
    return params.toString();
  }, [severity, status, deviceId]);

  useEffect(() => {
    setLoading(true);
    fetchJson<Alert[]>(`/alerts${query ? `?${query}` : ""}`)
      .then(setAlerts)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [query]);

  async function refreshDetail(alertId: string) {
    const detail = await fetchJson<Alert>(`/alerts/${alertId}`);
    setSelected(detail);
    return detail;
  }

  async function transition(alert: Alert, action: "acknowledge" | "resolve") {
    const updated = await postJson<Alert>(`/alerts/${alert.id}/${action}`);
    setAlerts((current) => current.map((item) => item.id === updated.id ? updated : item));
    await refreshDetail(alert.id);
  }

  return (
    <AppShell>
      <section className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <h1 className="text-3xl font-bold">Alerts</h1>
        <p className="mt-2 text-slate-400">Read-only monitoring alerts generated from check-ins and inventory.</p>
        <div className="mt-6 grid gap-3 md:grid-cols-3">
          <select className="rounded-md border border-slate-700 bg-slate-950 p-2" value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="">All severities</option><option value="info">Info</option><option value="warning">Warning</option><option value="critical">Critical</option></select>
          <select className="rounded-md border border-slate-700 bg-slate-950 p-2" value={status} onChange={(event) => setStatus(event.target.value)}><option value="">All statuses</option><option value="active">Active</option><option value="acknowledged">Acknowledged</option><option value="resolved">Resolved</option></select>
          <input className="rounded-md border border-slate-700 bg-slate-950 p-2" value={deviceId} onChange={(event) => setDeviceId(event.target.value)} placeholder="Filter by device ID" />
        </div>
      </section>
      {loading && <p className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4 text-slate-300">Loading alerts…</p>}
      {error && <p className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-200">Unable to load alerts: {error}</p>}
      <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_420px]">
        <section className="rounded-2xl border border-slate-800 bg-slate-900 p-4">
          {alerts.length === 0 ? <p className="p-4 text-slate-400">No alerts match the current filters.</p> : alerts.map((alert) => (
            <article key={alert.id} className="border-b border-slate-800 p-4 last:border-b-0">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <button className="text-left" onClick={() => refreshDetail(alert.id)}><p className="font-semibold">{alert.title}</p><p className="mt-1 text-sm text-slate-400">{alert.device_hostname ?? alert.device_id} · {alert.message}</p><p className="mt-1 text-xs uppercase text-slate-500">{alert.severity} · {alert.status} · {formatDate(alert.last_seen_at)}</p></button>
                <div className="flex gap-2"><Button variant="secondary" type="button" onClick={() => transition(alert, "acknowledge")}>Acknowledge</Button><Button variant="secondary" type="button" onClick={() => transition(alert, "resolve")}>Resolve</Button></div>
              </div>
            </article>
          ))}
        </section>
        <aside className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-semibold">Event history</h2>
          {!selected ? <p className="mt-4 text-slate-400">Select an alert to view lifecycle events.</p> : (
            <div className="mt-4 space-y-3"><Link href={`/devices/${selected.device_id}`} className="text-sm text-cyan-300">Open device</Link>{selected.events.length === 0 ? <p className="text-slate-400">No events loaded.</p> : selected.events.map((event) => <div key={event.id} className="rounded-xl bg-slate-950 p-3"><p className="font-medium">{event.event_type}</p><p className="text-sm text-slate-400">{event.message}</p><p className="mt-1 text-xs text-slate-500">{formatDate(event.created_at)}</p></div>)}</div>
          )}
        </aside>
      </div>
    </AppShell>
  );
}
