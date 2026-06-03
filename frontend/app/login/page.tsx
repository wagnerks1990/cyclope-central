import { Button } from "@/components/button";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 text-slate-100">
      <section className="w-full max-w-md rounded-3xl border border-slate-800 bg-slate-900 p-8 shadow-2xl">
        <p className="text-sm font-medium uppercase tracking-[0.3em] text-cyan-300">Operator access</p>
        <h1 className="mt-4 text-3xl font-bold">Sign in to Cyclope Central</h1>
        <p className="mt-3 text-sm text-slate-400">
          Authentication is wired as a JWT-ready framework stub for future identity integration.
        </p>
        <form className="mt-8 space-y-4">
          <label className="block text-sm font-medium">
            Email
            <input className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300" type="email" placeholder="operator@example.com" />
          </label>
          <label className="block text-sm font-medium">
            Password
            <input className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-slate-100 outline-none focus:border-cyan-300" type="password" placeholder="••••••••" />
          </label>
          <Button className="w-full" type="button">Continue</Button>
        </form>
      </section>
    </main>
  );
}
