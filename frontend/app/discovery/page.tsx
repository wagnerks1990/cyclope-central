"use client";

import { AppShell } from "@/components/app-shell";

export default function DiscoveryPage() {
  return (
    <AppShell>
      <section className="space-y-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm uppercase tracking-wide text-cyan-300">MSP Operations</p>
          <h1 className="mt-2 text-3xl font-bold">Discovery</h1>
          <p className="mt-2 max-w-3xl text-slate-400">Schedule and review discovery-only network scans without exploitation or credential harvesting.</p>
        </div>
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6 text-slate-300">
          This Phase 2 module is backed by tenant-scoped APIs and RBAC. Rich workflows can be expanded here without adding credential vaults, arbitrary command execution, PowerShell execution, remote shell, or custom remote desktop.
        </div>
      </section>
    </AppShell>
  );
}
