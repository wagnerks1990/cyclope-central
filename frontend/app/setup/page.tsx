"use client";

import { useEffect, useState } from "react";

import { Button } from "@/components/button";
import { bootstrapSetup, type BootstrapStatus, fetchJson } from "@/lib/api";

function passwordError(password: string) {
  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((pattern) => pattern.test(password)).length;
  if (password.length < 12) return "Password must be at least 12 characters.";
  if (classes < 3) return "Password must include at least three character classes.";
  return null;
}

export default function SetupPage() {
  const [organizationName, setOrganizationName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchJson<BootstrapStatus>("/bootstrap/status").then((status) => {
      if (!status.setup_required) window.location.href = "/login";
    }).catch(() => undefined);
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const validation = passwordError(password);
    if (validation) {
      setError(validation);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await bootstrapSetup({ organization_name: organizationName, owner_name: ownerName, owner_email: ownerEmail, owner_password: password });
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Setup failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <section className="w-full max-w-xl rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-300">First-run setup</p>
        <h1 className="mt-4 text-3xl font-bold">Create your first organization owner</h1>
        <p className="mt-3 text-sm text-slate-400">This setup can only run before the first owner exists. Password strength is validated locally and by the backend.</p>
        {error && <p className="mt-4 rounded-md border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
        <form className="mt-8 space-y-4" onSubmit={submit}>
          <input value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" placeholder="Organization name" required />
          <input value={ownerName} onChange={(event) => setOwnerName(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" placeholder="Owner name" required />
          <input value={ownerEmail} onChange={(event) => setOwnerEmail(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" placeholder="Owner email" type="email" required />
          <input value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2" placeholder="Strong password" type="password" required />
          <p className="text-xs text-slate-400">Use 12+ characters and at least three of lowercase, uppercase, number, and symbol.</p>
          <Button className="w-full" type="submit" disabled={loading}>{loading ? "Creating owner…" : "Complete setup"}</Button>
        </form>
      </section>
    </main>
  );
}
