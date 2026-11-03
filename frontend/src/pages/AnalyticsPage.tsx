import { useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { DistBars, TimeLine } from "../components/Charts";
import { Card, ErrorBanner, Loading, PageHeader, Stat } from "../components/ui";
import { useAuth } from "../lib/auth";
import { label, pct, useApi, when } from "../lib/hooks";
import type { Dashboard } from "../lib/types";

type SpeciesStats = Record<string, { count: number; mean_species_confidence: number; stages: Record<string, number>; readiness: Record<string, number> }>;

export default function AnalyticsPage() {
  const { hasRole } = useAuth();
  const [scope, setScope] = useState<"mine" | "all">("mine");
  const dash = useApi<Dashboard>(`/analytics/dashboard?scope=${scope}`, [scope]);
  const sp = useApi<SpeciesStats>(`/analytics/species?scope=${scope}`, [scope]);
  return (
    <div>
      <PageHeader kicker={dash.data?.provenance ?? "analytics"} title="Analytics"
        actions={hasRole("admin", "researcher") && (
          <div role="tablist" className="inline-flex rounded-lg border border-line p-1 text-sm">
            {(["mine", "all"] as const).map((s) => <button key={s} role="tab" aria-selected={scope === s} onClick={() => setScope(s)} className={`rounded-md px-3 py-1 ${scope === s ? "bg-ink text-paper" : ""}`}>{s === "mine" ? "My data" : "All accounts"}</button>)}
          </div>
        )}>
        Aggregations over stored scans, detections, simulations and records.
      </PageHeader>
      <ErrorBanner error={dash.error ?? sp.error} onRetry={() => { dash.reload(); sp.reload(); }} />
      {dash.loading && <Loading />}
      {dash.data && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {Object.entries(dash.data.totals).slice(0, 8).map(([k, v]) => <Stat key={k} label={label(k)} value={v} />)}
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Scans per day"><TimeLine data={dash.data.scans_per_day_30d} /></Card>
            <Card title="Detection method used (30 d)" subtitle="trained model vs close-up fallback"><DistBars data={dash.data.detection_methods_30d} /></Card>
          </div>
          <div className="grid gap-5 lg:grid-cols-2">
            <Card title="Environmental trends (30 d)" subtitle="daily means of stored records (manual + Open-Meteo)">
              {dash.data.environment_trend_30d && dash.data.environment_trend_30d.length > 0 ? (
                <ResponsiveContainer width="100%" height={220}>
                  <LineChart data={dash.data.environment_trend_30d.map((d) => ({ ...d, day: d.day.slice(5) }))}>
                    <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
                    <XAxis dataKey="day" stroke="rgb(var(--muted))" fontSize={11} /><YAxis stroke="rgb(var(--muted))" fontSize={11} />
                    <Tooltip /><Legend />
                    <Line dataKey="temperature_c" name="°C" stroke="rgb(var(--alert))" connectNulls />
                    <Line dataKey="relative_humidity_pct" name="RH %" stroke="rgb(var(--sky))" connectNulls />
                    <Line dataKey="wind_kmh" name="wind km/h" stroke="rgb(var(--leaf))" connectNulls />
                    <Line dataKey="rain_mm_h" name="rain mm/h" stroke="rgb(var(--pollen))" connectNulls />
                  </LineChart>
                </ResponsiveContainer>
              ) : <p className="text-sm text-muted">No environmental records in the last 30 days.</p>}
            </Card>
            <Card title="Simulation history" subtitle="computational results only">
              {dash.data.simulation_history && dash.data.simulation_history.length > 0 ? (
                <div className="max-h-56 overflow-y-auto"><table className="table-base">
                  <thead><tr><th>#</th><th>Species</th><th>Mode</th><th>When</th><th>Sim. efficiency</th></tr></thead>
                  <tbody>{dash.data.simulation_history.map((s) => <tr key={s.id}><td>{s.id}</td><td>{s.species_id}</td><td className="text-xs">{label(s.mode ?? "")}</td><td className="text-xs">{when(s.created_at)}</td><td className="font-mono">{s.status === "completed" ? pct(s.efficiency) : s.status}</td></tr>)}</tbody>
                </table></div>
              ) : <p className="text-sm text-muted">No simulations yet. <Link className="underline" to="/app/simulator">Open the simulator</Link></p>}
            </Card>
          </div>
          <Card title="Per-species breakdown">
            {sp.data && Object.keys(sp.data).length ? (
              <div className="overflow-x-auto"><table className="table-base">
                <thead><tr><th>Species</th><th>Flowers</th><th>Mean species conf.</th><th>Stages (heuristic)</th><th>Readiness (rule engine)</th></tr></thead>
                <tbody>{Object.entries(sp.data).sort((a, b) => b[1].count - a[1].count).map(([k, v]) => (
                  <tr key={k}><td className="font-medium">{k}</td><td>{v.count}</td><td className="font-mono">{pct(v.mean_species_confidence)}</td>
                    <td className="text-xs">{Object.entries(v.stages).map(([s, n]) => `${label(s)} ${n}`).join(" · ")}</td>
                    <td className="text-xs">{Object.entries(v.readiness).map(([s, n]) => `${label(s)} ${n}`).join(" · ")}</td></tr>
                ))}</tbody></table></div>
            ) : <p className="text-sm text-muted">No analysed flowers yet.</p>}
          </Card>
        </div>
      )}
    </div>
  );
}
