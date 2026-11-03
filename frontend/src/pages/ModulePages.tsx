import { CropAnalyzer } from "../components/CropAnalyzer";
import { DistBars } from "../components/Charts";
import { Bar, Card, MethodBadge, Notice, PageHeader, Pill } from "../components/ui";
import { label, pct, useApi } from "../lib/hooks";
import type { Dashboard, Flower, StageResult } from "../lib/types";

type Structure = NonNullable<Flower["structure"]>;
type Health = NonNullable<Flower["health"]>;

export function StructurePage() {
  return (
    <div>
      <PageHeader kicker="Module 3 · reproductive structures" title="Flower structure analysis">
        Locates the visually distinct centre region of an open flower and checks for a pollen-like yellow cluster.
      </PageHeader>
      <div className="space-y-5">
        <Notice>
          <strong>Honest scope:</strong> no openly licensed anther/stigma annotations exist for these nine crops, so Pollinex does
          <em> not</em> detect anthers, stigma, stamens or pistil individually. This module is a labelled heuristic. A CVAT annotation
          workflow and YOLO training recipe are included (<code>datasets/annotation/</code>) so a real structure model can be trained;
          once its ONNX file is installed, its detections replace this heuristic.
        </Notice>
        <CropAnalyzer<Structure> endpoint="/ai/structure" title="Analyse a flower centre" render={(r) => (
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2"><MethodBadge method={r.method} /><Pill tone={r.yellow_cluster_visible ? "good" : "neutral"}>yellow cluster {r.yellow_cluster_visible ? "visible" : "not visible"}</Pill></div>
            {r.centre_region ? <p>Centre region at {r.centre_region.center.map((v) => v.toFixed(0)).join(", ")} px covering {pct(r.centre_region.area_fraction_of_flower)} of the flower.</p> : <p>No distinct centre region found.</p>}
            {r.structures && (
              <table className="table-base mt-2"><thead><tr><th>Structure</th><th>Status</th><th>Visible</th><th>Detail</th></tr></thead>
                <tbody>{r.structures.map((x) => (
                  <tr key={x.structure}><td className="capitalize">{label(x.structure)}</td>
                    <td><Pill tone={x.status === "not_ai_validated" ? "warn" : "info"}>{label(x.status)}</Pill></td>
                    <td>{x.visible == null ? "—" : x.visible ? "yes" : "no"}</td><td className="text-xs text-muted">{x.detail}</td></tr>
                ))}</tbody></table>
            )}
            <p className="text-xs text-muted">{r.note}</p>
          </div>
        )} />
      </div>
    </div>
  );
}

export function MaturityPage() {
  const dash = useApi<Dashboard>("/analytics/dashboard");
  return (
    <div>
      <PageHeader kicker="Module 4 · developmental stage" title="Flower maturity analysis">
        Five visible stages — bud, early bloom, partially open, fully open, senescent — scored from interpretable shape and colour cues.
      </PageHeader>
      <div className="space-y-5">
        <Notice>Stage is a <strong>heuristic</strong> (no stage-labelled training data was available) and says nothing about pollen viability.</Notice>
        <CropAnalyzer<StageResult> endpoint="/ai/maturity" title="Estimate stage" render={(r) => (
          <div className="space-y-2">
            <div className="flex items-center gap-2"><span className="font-display text-2xl">{label(r.stage)}</span><MethodBadge method={r.method} />{r.uncertain && <Pill tone="warn">uncertain</Pill>}</div>
            {Object.entries(r.distribution).map(([k, v]) => <div key={k} className="grid grid-cols-[120px_1fr_44px] items-center gap-2 text-xs"><span>{label(k)}</span><Bar value={v} tone="pollen" /><span className="text-right font-mono">{pct(v, 0)}</span></div>)}
            <details className="text-xs text-muted"><summary className="cursor-pointer">Cues used</summary>
              <pre className="mt-1 overflow-x-auto font-mono">{JSON.stringify(r.cues, null, 1)}</pre></details>
          </div>
        )} />
        <Card title="Stages across your scans"><DistBars data={dash.data?.stage_distribution ?? {}} color="rgb(var(--pollen))" /></Card>
      </div>
    </div>
  );
}

export function HealthPage() {
  return (
    <div>
      <PageHeader kicker="Module 7 · visual health" title="Plant health analysis">
        Measures visible browning, dark spots, discolouration and outline irregularity on a flower.
      </PageHeader>
      <div className="space-y-5">
        <Notice>These are <strong>observable indicators only</strong>. The same symptom can come from frost, sunscald, pests, pathogens or age — Pollinex never names a disease.</Notice>
        <CropAnalyzer<Health> endpoint="/ai/health" title="Check visible anomalies" render={(r) => (
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2"><MethodBadge method="heuristic" /><Pill tone={r.indicators.length ? "warn" : "good"}>{label(r.status)}</Pill></div>
            {r.indicators.map((i) => <div key={i.type}><Pill tone="warn">{label(i.type)}</Pill> <span className="font-mono text-xs">value {i.value} · threshold {i.threshold}</span></div>)}
            {r.measurements && <table className="table-base"><tbody>{Object.entries(r.measurements).map(([k, v]) => <tr key={k}><td className="text-muted">{label(k)}</td><td className="font-mono">{v}</td></tr>)}</tbody></table>}
            <p className="text-xs text-muted">{r.note}</p>
          </div>
        )} />
      </div>
    </div>
  );
}
