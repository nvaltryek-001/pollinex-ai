import { useState } from "react";
import { DistBars, TimeLine } from "../components/Charts";
import { Card, ErrorBanner, Loading, PageHeader, Stat } from "../components/ui";
import { useAuth } from "../lib/auth";
import { label, pct, useApi } from "../lib/hooks";
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
