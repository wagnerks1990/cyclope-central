"use client";

import Link from "next/link";
import { AlertTriangle, MonitorCheck, MonitorX, Server, ShieldAlert } from "lucide-react";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { type DashboardSummary, fetchJson } from "@/lib/api";

function formatDate(value?: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [operations, setOperations] = useState<Record<string, number> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchJson<DashboardSummary>("/dashboard/summary"),
      fetchJson<{ widgets: Record<string, number> }>("/dashboard/operations").catch(() => ({ widgets: {} }))
    ])
      .then(([dashboard, ops]) => { setSummary(dashboard); setOperations(ops.widgets); })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    { label: "Total devices", value: summary?.total_devices ?? 0, icon: Server },
    { label: "Online", value: summary?.online_devices ?? 0, icon: MonitorCheck },
    { label: "Offline", value: summary?.offline_devices ?? 0, icon: MonitorX },
    { label: "Warnings", value: summary?.active_warning_alerts ?? 0, icon: AlertTriangle },
    { label: "Critical", value: summary?.active_critical_alerts ?? 0, icon: ShieldAlert },
    { label: "Need attention", value: summary?.devices_needing_attention ?? 0, icon: AlertTriangle }
  ];

  return (
    <AppShell>
      <section className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6 shadow-2xl sm:p-10">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-300">Monitoring overview</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-6xl">Cyclope Central health dashboard.</h1>
        <p className="mt-6 max-w-2xl text-lg text-slate-300">Unified MSP operations across devices, alerts, tickets, assets, discovery, reports, platform health, and audited remote sessions.</p>
      </section>
      {loading && <p className="mt-6 rounded-xl border border-slate-800 bg-slate-900 p-4 text-slate-300">Loading dashboard summary…</p>}
      {error && <p className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-200">Unable to load dashboard: {error}</p>}
      <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        {cards.map((card) => (
          <article key={card.label} className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <card.icon className="text-cyan-300" aria-hidden="true" />
            <p className="mt-4 text-sm text-slate-400">{card.label}</p>
            <p className="mt-1 text-3xl font-semibold">{card.value}</p>
          </article>
        ))}
      </section>
      <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {["open_tickets", "discovered_devices", "assets", "warranty_expiring", "report_runs", "recent_remote_sessions", "recent_documentation_updates", "ai_insights"].map((key) => (
          <article key={key} className="rounded-2xl border border-slate-800 bg-slate-900 p-5">
            <p className="text-sm capitalize text-slate-400">{key.replaceAll("_", " ")}</p>
            <p className="mt-2 text-2xl font-semibold">{operations?.[key] ?? 0}</p>
          </article>
        ))}
      </section>
      <section className="mt-8 rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-semibold">Recent alerts</h2>
          <Link href="/alerts" className="text-sm text-cyan-300 hover:text-cyan-200">View all</Link>
        </div>
        {!summary || summary.recent_alerts.length === 0 ? <p className="mt-4 text-slate-400">No alerts have been generated yet.</p> : (
          <div className="mt-4 overflow-auto"><table className="w-full text-sm"><thead className="text-left text-slate-400"><tr><th className="p-2">Severity</th><th className="p-2">Status</th><th className="p-2">Device</th><th className="p-2">Alert</th><th className="p-2">Last seen</th></tr></thead><tbody>{summary.recent_alerts.map((alert) => <tr key={alert.id} className="border-t border-slate-800"><td className="p-2 uppercase">{alert.severity}</td><td className="p-2">{alert.status}</td><td className="p-2">{alert.device_hostname ?? alert.device_id}</td><td className="p-2">{alert.title}</td><td className="p-2">{formatDate(alert.last_seen_at)}</td></tr>)}</tbody></table></div>
        )}
      </section>
    </AppShell>
  );
}
