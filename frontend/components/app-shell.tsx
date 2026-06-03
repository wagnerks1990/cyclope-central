import Link from "next/link";
import { ShieldCheck } from "lucide-react";

import { Button } from "@/components/button";

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/devices", label: "Devices" },
  { href: "/alerts", label: "Alerts" },
  { href: "/settings", label: "Settings" }
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between lg:px-8">
          <Link href="/" className="flex items-center gap-3">
            <span className="rounded-xl bg-cyan-400/10 p-2 text-cyan-300">
              <ShieldCheck aria-hidden="true" size={24} />
            </span>
            <span>
              <span className="block text-lg font-semibold">Cyclope Central</span>
              <span className="block text-xs text-slate-400">Private MSP/RMM foundation</span>
            </span>
          </Link>
          <nav className="flex flex-wrap gap-2">
            {navItems.map((item) => (
              <Button key={item.href} asChild variant="ghost">
                <Link href={item.href}>{item.label}</Link>
              </Button>
            ))}
            <Button asChild variant="secondary">
              <Link href="/login">Login</Link>
            </Button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 lg:px-8">{children}</main>
    </div>
  );
}
