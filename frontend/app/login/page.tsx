"use client";

import { useState } from "react";

import { Button } from "@/components/button";
import { login } from "@/lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      window.location.href = "/";
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to sign in");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <section className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-300">Operator access</p>
        <h1 className="mt-4 text-3xl font-bold">Sign in to Cyclope Central</h1>
        <p className="mt-3 text-sm text-slate-400">Use your organization-scoped operator account. Access is controlled by role-based permissions.</p>
        {error && <p className="mt-4 rounded-md border border-red-900 bg-red-950/40 p-3 text-sm text-red-200">{error}</p>}
        <form className="mt-8 space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium">
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300" type="email" placeholder="operator@example.com" autoComplete="email" />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input value={password} onChange={(event) => setPassword(event.target.value)} className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300" type="password" placeholder="••••••••" autoComplete="current-password" />
          </label>
          <Button className="w-full" type="submit" disabled={loading}>{loading ? "Signing in…" : "Continue"}</Button>
        </form>
      </section>
    </main>
  );
}
