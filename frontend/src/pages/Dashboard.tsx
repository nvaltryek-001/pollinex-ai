import { Link } from "react-router-dom";
import { Camera } from "lucide-react";
import { DistBars, TimeLine } from "../components/Charts";
import { Card, Empty, ErrorBanner, Loading, PageHeader, Stat } from "../components/ui";
import { useAuth } from "../lib/auth";
import { label, num, pct, useApi, when } from "../lib/hooks";
import type { Dashboard as D } from "../lib/types";

export default function Dashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useApi<D>("/analytics/dashboard");
  return (
    <div>
      <PageHeader kicker={data?.provenance ?? "dashboard"} title={`Good to see you${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}.`}
        actions={<Link to="/app/scanner" className="btn-accent"><Camera size={16} />New scan</Link>}>
        Every number on this page is computed from your database records or from saved evaluation reports.
      </PageHeader>
      <ErrorBanner error={error} onRetry={reload} />
      {loading && <Loading />}
      {data && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat label="Scanned images" value={data.totals.scanned_images} />
            <Stat label="Detected flowers" value={data.totals.detected_flowers} hint={`${data.totals.analysed_flowers} analysed in detail`} />
            <Stat label="Simulations" value={data.totals.simulation_runs} hint={`${data.totals.completed_simulations} completed`} />
            <Stat label="Pollination logs" value={data.totals.pollination_records} hint={`${data.totals.environment_records} environment records`} />
          </div>
          {data.totals.scanned_images === 0 ? (
            <Empty title="No scans yet">Your dashboard fills in as you scan flowers. <Link className="underline" to="/app/scanner">Run your first scan</Link>.</Empty>
          ) : (
            <div className="grid gap-5 lg:grid-cols-3">
              <Card title="Species distribution" subtitle="per analysed flower" className="lg:col-span-1"><DistBars data={data.species_distribution} horizontal /></Card>
              <Card title="Developmental stages" subtitle="heuristic estimate"><DistBars data={data.stage_distribution} color="rgb(var(--pollen))" /></Card>
              <Card title="Readiness estimates" subtitle="rule-based visual estimate"><DistBars data={data.readiness_distribution} color="rgb(var(--sky))" /></Card>
              <Card title="Scanning activity" subtitle="last 30 days" className="lg:col-span-2"><TimeLine data={data.scans_per_day_30d} /></Card>
              <Card title="Detector performance" subtitle="held-out test split, saved evaluation">
                {data.model_performance ? (
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm"><span className="text-muted">mAP@0.50</span><span className="font-mono">{num(data.model_performance.mAP50, 3)}</span></div>
                    <div className="flex justify-between text-sm"><span className="text-muted">mAP@0.50:0.95</span><span className="font-mono">{num(data.model_performance.mAP50_95, 3)}</span></div>
                    <p className="text-xs text-muted">{data.model_performance.source}</p>
                    <Link to="/app/evaluation" className="text-xs underline">Full evaluation</Link>
                  </div>
                ) : <p className="text-sm text-muted">No evaluation report found.</p>}
              </Card>
            </div>
          )}
          {Object.keys(data.simulations_by_species).length > 0 && (
            <Card title="Simulated transfer efficiency by species" subtitle="computational simulation only — not fruit set">
              <table className="table-base"><thead><tr><th>Species</th><th>Runs</th><th>Mean simulated efficiency</th></tr></thead>
                <tbody>{Object.entries(data.simulations_by_species).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.runs}</td><td className="font-mono">{pct(v.mean_simulated_transfer_efficiency)}</td></tr>)}</tbody>
              </table>
            </Card>
          )}
          {data.recent_scans.length > 0 && (
            <Card title="Recent scans">
              <table className="table-base"><thead><tr><th>Scan</th><th>When</th><th>Source</th><th>Flowers</th><th>Method</th></tr></thead>
                <tbody>{data.recent_scans.map((s) => (
                  <tr key={s.id}><td><Link className="underline" to={`/app/scans/${s.id}`}>#{s.id}</Link></td><td>{when(s.created_at)}</td><td>{s.source}</td><td>{s.flower_count}</td><td className="text-xs">{label(s.detection_method)}</td></tr>
                ))}</tbody>
              </table>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
