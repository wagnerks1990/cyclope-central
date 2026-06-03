"use client";

import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/button";
import {
  type NotificationChannel,
  type NotificationDelivery,
  type NotificationRule,
  fetchJson,
  postJsonBody,
  patchJsonBody
} from "@/lib/api";

const defaultOrganizationId = process.env.NEXT_PUBLIC_DEFAULT_ORGANIZATION_ID ?? "";

export default function SettingsPage() {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [deliveries, setDeliveries] = useState<NotificationDelivery[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [organizationId, setOrganizationId] = useState(defaultOrganizationId);
  const [channelType, setChannelType] = useState<"email" | "webhook">("email");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [loadedChannels, loadedRules, loadedDeliveries] = await Promise.all([
        fetchJson<NotificationChannel[]>("/notification-channels"),
        fetchJson<NotificationRule[]>("/notification-rules"),
        fetchJson<NotificationDelivery[]>("/notifications/deliveries")
      ]);
      setChannels(loadedChannels);
      setRules(loadedRules);
      setDeliveries(loadedDeliveries);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  async function createChannel() {
    if (!organizationId) {
      setError("Set an organization ID before creating notification settings.");
      return;
    }
    const name = window.prompt("Channel name", channelType === "email" ? "Ops Email" : "Ops Webhook") ?? "";
    if (!name) return;
    const config = channelType === "email"
      ? { recipients: (window.prompt("Recipients, comma separated", "ops@example.com") ?? "").split(",").map((item) => item.trim()).filter(Boolean) }
      : { url: window.prompt("Webhook URL", "https://example.com/alerts") ?? "", headers: { Authorization: window.prompt("Optional Authorization header", "") ?? "" } };
    await postJsonBody<NotificationChannel>("/notification-channels", { organization_id: organizationId, name, channel_type: channelType, config });
    await load();
  }

  async function createRule() {
    if (!organizationId || channels.length === 0) {
      setError("Create a channel and set an organization ID before creating a rule.");
      return;
    }
    const name = window.prompt("Rule name", "Critical and warning alerts") ?? "";
    if (!name) return;
    const severities = (window.prompt("Severity filter, comma separated", "warning,critical") ?? "").split(",").map((item) => item.trim()).filter(Boolean);
    const ruleTypes = (window.prompt("Optional alert rule keys, comma separated", "") ?? "").split(",").map((item) => item.trim()).filter(Boolean);
    await postJsonBody<NotificationRule>("/notification-rules", { organization_id: organizationId, name, severity_filter: severities, alert_rule_type_filter: ruleTypes, channel_ids: [channels[0].id] });
    await load();
  }

  async function toggleChannel(channel: NotificationChannel) {
    await patchJsonBody<NotificationChannel>(`/notification-channels/${channel.id}`, { enabled: !channel.enabled });
    await load();
  }

  async function toggleRule(rule: NotificationRule) {
    await patchJsonBody<NotificationRule>(`/notification-rules/${rule.id}`, { enabled: !rule.enabled });
    await load();
  }

  return (
    <AppShell>
      <section className="space-y-6">
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="mt-2 text-slate-400">Manage tenant notification channels and rules for alert delivery. Webhook secret headers are masked in API responses and are never executed.</p>
          <label className="mt-4 block text-sm text-slate-300">Organization ID</label>
          <input value={organizationId} onChange={(event) => setOrganizationId(event.target.value)} placeholder="Organization UUID" className="mt-2 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100" />
        </div>

        {loading && <p className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-slate-300">Loading notification settings…</p>}
        {error && <p className="rounded-xl border border-red-900 bg-red-950/40 p-4 text-red-200">{error}</p>}

        <div className="grid gap-6 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold">Notification channels</h2><div className="flex gap-2"><select value={channelType} onChange={(event) => setChannelType(event.target.value as "email" | "webhook")} className="rounded-md bg-slate-950 px-3 py-2 text-sm"><option value="email">email</option><option value="webhook">webhook</option></select><Button onClick={createChannel}>Add channel</Button></div></div>
            {channels.length === 0 ? <p className="mt-4 text-slate-400">No notification channels configured.</p> : <div className="mt-4 space-y-3">{channels.map((channel) => <div key={channel.id} className="rounded-xl bg-slate-950 p-4"><div className="flex items-center justify-between gap-3"><div><p className="font-medium">{channel.name}</p><p className="text-sm text-slate-400">{channel.channel_type} · {channel.enabled ? "enabled" : "disabled"}</p></div><Button variant="secondary" onClick={() => toggleChannel(channel)}>{channel.enabled ? "Disable" : "Enable"}</Button></div><pre className="mt-3 overflow-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-400">{JSON.stringify(channel.config, null, 2)}</pre></div>)}</div>}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
            <div className="flex items-center justify-between gap-3"><h2 className="text-xl font-semibold">Notification rules</h2><Button onClick={createRule}>Add rule</Button></div>
            {rules.length === 0 ? <p className="mt-4 text-slate-400">No notification rules configured.</p> : <div className="mt-4 space-y-3">{rules.map((rule) => <div key={rule.id} className="rounded-xl bg-slate-950 p-4"><div className="flex items-center justify-between gap-3"><div><p className="font-medium">{rule.name}</p><p className="text-sm text-slate-400">{rule.enabled ? "enabled" : "disabled"} · severities {rule.severity_filter.join(", ") || "all"}</p><p className="text-xs text-slate-500">Rule keys {rule.alert_rule_type_filter.join(", ") || "all"}</p></div><Button variant="secondary" onClick={() => toggleRule(rule)}>{rule.enabled ? "Disable" : "Enable"}</Button></div></div>)}</div>}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-6">
          <h2 className="text-xl font-semibold">Recent delivery history</h2>
          {deliveries.length === 0 ? <p className="mt-4 text-slate-400">No notification deliveries have been queued.</p> : <div className="mt-4 overflow-auto"><table className="w-full text-sm"><thead className="text-left text-slate-400"><tr><th className="p-2">Channel</th><th className="p-2">Status</th><th className="p-2">Attempts</th><th className="p-2">Sent</th><th className="p-2">Last error</th></tr></thead><tbody>{deliveries.map((delivery) => <tr key={delivery.id} className="border-t border-slate-800"><td className="p-2">{delivery.channel_name ?? delivery.channel_id}</td><td className="p-2">{delivery.status}</td><td className="p-2">{delivery.attempts}</td><td className="p-2">{delivery.sent_at ?? "Not sent"}</td><td className="p-2 text-slate-400">{delivery.last_error ?? ""}</td></tr>)}</tbody></table></div>}
        </div>
      </section>
    </AppShell>
  );
}
