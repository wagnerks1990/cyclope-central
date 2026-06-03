"use client";

import { AppShell } from "@/components/app-shell";

export default function CustomerPortalPage() {
  return (
    <AppShell>
      <section className="space-y-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <p className="text-sm uppercase tracking-wide text-cyan-300">Production Readiness</p>
          <h1 className="mt-2 text-3xl font-bold">Customer Portal</h1>
          <p className="mt-2 max-w-3xl text-slate-400">Customer-facing ticket, asset, device, documentation, and report access is tenant-scoped and separate from operator accounts.</p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {["Tenant scoped", "Audited", "No secrets stored"].map((item) => <div key={item} className="rounded-xl bg-slate-900 p-4 text-slate-300">{item}</div>)}
        </div>
      </section>
    </AppShell>
  );
}
