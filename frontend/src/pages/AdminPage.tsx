import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { Card, ErrorBanner, Loading, PageHeader, Pill } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useApi, when } from "../lib/hooks";
import type { Page, Role, User } from "../lib/types";

/* eslint-disable @typescript-eslint/no-explicit-any */
export default function AdminPage() {
  const { user: me } = useAuth();
  const users = useApi<Page<User>>("/admin/users?page_size=200");
  const health = useApi<Record<string, any>>("/health");
  const models = useApi<Record<string, any>>("/admin/models");
  const activity = useApi<Page<Record<string, any>>>("/admin/activity?page_size=30");
  const [err, setErr] = useState<string | null>(null);

  const update = async (id: number, body: Partial<{ role: Role; is_active: boolean }>) => {
    setErr(null);
    try { await api.patch(`/admin/users/${id}`, body); users.reload(); activity.reload(); } catch (e) { setErr((e as Error).message); }
  };
  const reloadModels = async () => {
    setErr(null);
    try { await api.post("/admin/models/reload"); models.reload(); health.reload(); } catch (e) { setErr((e as Error).message); }
  };

  return (
    <div>
      <PageHeader kicker="Administration" title="Admin settings">User roles, model management, system health and audit log.</PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-5 xl:grid-cols-2">
        <Card title="System health" right={<button className="btn-ghost !px-2 !py-1" aria-label="Refresh health" onClick={health.reload}><RefreshCw size={14} /></button>}>
          {health.loading ? <Loading /> : health.data && (
            <div className="space-y-2 text-sm">
              <Pill tone={health.data.status === "ok" ? "good" : "bad"}>{health.data.status}</Pill>
              <table className="table-base"><tbody>{Object.entries(health.data.checks as Record<string, string>).map(([k, v]) => <tr key={k}><td>{k}</td><td className="font-mono text-xs">{v}</td></tr>)}</tbody></table>
              <p className="text-xs text-muted">env {health.data.environment} · python {health.data.python} · {when(health.data.time)}</p>
            </div>
          )}
        </Card>
        <Card title="Models" right={<button className="btn-ghost !py-1 text-xs" onClick={reloadModels}><RefreshCw size={14} />Reload from disk</button>}>
          {models.data && (
            <div className="space-y-2 text-sm">
              <p>Active detector: <span className="font-mono">{models.data.active.detector_backend} · {models.data.active.detector_version}</span></p>
              <p>Gallery: <span className="font-mono text-xs">{JSON.stringify(models.data.active.gallery_species)}</span> · threshold {models.data.active.gallery_threshold}</p>
              <div className="kicker mt-3">Evaluation runs</div>
              <table className="table-base"><tbody>{models.data.evaluation_runs.map((e: any) => <tr key={e.id}><td>{e.task}</td><td>{e.dataset_id}/{e.split}</td><td className="font-mono text-xs">{Object.entries(e.metrics).map(([k, v]) => `${k}=${Number(v).toFixed(3)}`).join(" ")}</td></tr>)}</tbody></table>
              <p className="text-xs text-muted">To deploy a retrained model, replace the file in <code>ai-engine/models/</code> and press reload.</p>
            </div>
          )}
        </Card>
        <Card title={`Users (${users.data?.total ?? 0})`} className="xl:col-span-2">
          <div className="overflow-x-auto"><table className="table-base">
            <thead><tr><th>Email</th><th>Name</th><th>Role</th><th>Active</th><th>Joined</th></tr></thead>
            <tbody>{users.data?.items.map((u) => (
              <tr key={u.id}><td>{u.email}</td><td>{u.full_name || "—"}</td>
                <td><select aria-label={`Role for ${u.email}`} className="input !py-1 text-xs" value={u.role} disabled={u.id === me?.id} onChange={(e) => update(u.id, { role: e.target.value as Role })}>
                  {(["admin", "researcher", "user"] as Role[]).map((r) => <option key={r} value={r}>{r}</option>)}</select></td>
                <td><input type="checkbox" aria-label={`Active ${u.email}`} checked={u.is_active} disabled={u.id === me?.id} onChange={(e) => update(u.id, { is_active: e.target.checked })} /></td>
                <td className="text-xs">{when(u.created_at)}</td></tr>
            ))}</tbody></table></div>
        </Card>
        <Card title="Activity log" className="xl:col-span-2">
          <div className="max-h-80 overflow-y-auto"><table className="table-base">
            <thead><tr><th>When</th><th>User</th><th>Action</th><th>Entity</th></tr></thead>
            <tbody>{activity.data?.items.map((a) => <tr key={a.id}><td className="text-xs">{when(a.created_at)}</td><td>{a.user_id ?? "—"}</td><td className="font-mono text-xs">{a.action}</td><td className="text-xs">{a.entity} {a.entity_id}</td></tr>)}</tbody></table></div>
        </Card>
      </div>
    </div>
  );
}
