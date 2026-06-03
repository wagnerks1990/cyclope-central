"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import { type DeviceSummary, fetchJson } from "@/lib/api";

function formatLastSeen(value?: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<DeviceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchJson<DeviceSummary[]>("/devices")
      .then((data) => {
        if (mounted) setDevices(data);
      })
      .catch((err: Error) => {
        if (mounted) setError(err.message);
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <AppShell>
      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold">Devices</h1>
            <p className="mt-2 text-slate-400">Live enrolled endpoint inventory from authenticated agent check-ins.</p>
          </div>
          <Button variant="secondary" type="button">Enrollment tokens managed via API</Button>
        </div>

        {loading && <p className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-4 text-slate-300">Loading devices…</p>}
        {error && <p className="mt-6 rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-200">Unable to load devices: {error}</p>}
        {!loading && !error && devices.length === 0 && (
          <p className="mt-6 rounded-xl border border-slate-800 bg-slate-950 p-4 text-slate-300">No devices are enrolled yet.</p>
        )}
        {!loading && !error && devices.length > 0 && (
          <div className="mt-6 overflow-hidden rounded-xl border border-slate-800">
            {devices.map((device) => (
              <Link key={device.id} href={`/devices/${device.id}`} className="grid gap-2 border-b border-slate-800 p-4 transition hover:bg-slate-800/60 last:border-b-0 md:grid-cols-[1fr_auto] md:items-center">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">{device.hostname}</span>
                    <span className={device.is_online ? "rounded-full bg-emerald-400/10 px-2 py-1 text-xs text-emerald-300" : "rounded-full bg-slate-700 px-2 py-1 text-xs text-slate-300"}>
                      {device.status}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-400">{device.operating_system} · {device.architecture ?? "unknown arch"} · {device.ip_address ?? "no IP"}</p>
                </div>
                <div className="text-sm text-slate-400 md:text-right">
                  <p>Agent {device.agent_version ?? "unknown"}</p>
                  <p>Last seen {formatLastSeen(device.last_seen_at)}</p>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
