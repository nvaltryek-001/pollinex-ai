import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { authedImage } from "../lib/api";
import { label, num, pct } from "../lib/hooks";
import type { Flower, Readiness, Scan } from "../lib/types";
import { DetectionOverlay } from "./DetectionOverlay";
import { Bar, Card, MethodBadge, Notice, Pill, readinessTone } from "./ui";

export function ScanResults({ scan, localPreview }: { scan: Scan; localPreview?: string | null }) {
  const [src, setSrc] = useState<string | null>(localPreview ?? null);
  const [sel, setSel] = useState<number | null>(scan.flowers?.length ? 0 : null);
  useEffect(() => {
    if (localPreview) { setSrc(localPreview); return; }
    let url: string | null = null;
    authedImage(scan.image_url).then((u) => { url = u; setSrc(u); }).catch(() => setSrc(null));
    return () => { if (url) URL.revokeObjectURL(url); };
  }, [scan.image_url, localPreview]);
  const flowers = scan.flowers ?? [];
  const f = sel != null ? flowers[sel] : undefined;

  return (
    <div className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
      <div className="space-y-4">
        <Card title={`Scan #${scan.id}`} subtitle={`${scan.flower_count} flower${scan.flower_count === 1 ? "" : "s"} · ${num(scan.latency_ms, 0)} ms · ${scan.summary.model?.detector_backend ?? ""} ${scan.summary.model?.detector_version ?? ""}`}
          right={<MethodBadge method={scan.detection_method} />}>
          <div className="relative overflow-hidden rounded-lg bg-raised" style={{ aspectRatio: `${scan.image_width} / ${scan.image_height}` }}>
            {src && <img src={src} alt={`Scan ${scan.id}`} className="absolute inset-0 h-full w-full object-fill" />}
            <DetectionOverlay width={scan.image_width} height={scan.image_height} selected={sel} onSelect={setSel} showCentres flowers={flowers}
              boxes={flowers.map((x) => ({ box: x.detection.box, score: x.detection.score, low_confidence: x.detection.low_confidence, method: x.detection.method, label: x.species.species !== "unknown" ? x.species.species : undefined }))} />
          </div>
          {scan.warnings.length > 0 && (
            <ul className="mt-3 space-y-1">
              {scan.warnings.map((w, i) => <li key={i} className="flex gap-2 text-xs text-pollen"><AlertTriangle size={14} className="mt-0.5 shrink-0" />{w}</li>)}
            </ul>
          )}
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-muted">
            <span><span className="inline-block h-2 w-3 bg-leaf align-middle" /> confident</span>
            <span><span className="inline-block h-2 w-3 border border-dashed border-pollen align-middle" /> low confidence</span>
            <span><span className="inline-block h-2 w-3 border border-dashed border-alert align-middle" /> close-up fallback (not a detection)</span>
          </div>
        </Card>
        {flowers.length > 0 && (
          <Card title="Flowers" subtitle={scan.flower_count > flowers.length ? `Detailed analysis for the top ${flowers.length} of ${scan.flower_count} by confidence` : undefined}>
            <div className="max-h-72 overflow-y-auto">
              <table className="table-base">
                <thead><tr><th>#</th><th>Species</th><th>Stage</th><th>Readiness</th><th>Det.</th></tr></thead>
                <tbody>
                  {flowers.map((x, i) => (
                    <tr key={i} onClick={() => setSel(i)} className={`cursor-pointer ${sel === i ? "bg-raised" : "hover:bg-raised/60"}`}>
                      <td className="font-mono">{i}</td>
                      <td>{x.species.species}{x.species.species !== "unknown" && <span className="ml-1 text-muted">{pct(x.species.confidence, 0)}</span>}</td>
                      <td>{x.stage ? label(x.stage.stage) : "—"}</td>
                      <td>{x.readiness ? <Pill tone={readinessTone(x.readiness.category)}>{label(x.readiness.category)}</Pill> : "—"}</td>
                      <td className="font-mono">{x.detection.method === "closeup_fallback" ? "n/a" : pct(x.detection.score, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}
      </div>
      <div>{f ? <FlowerDetail f={f} /> : <Notice>No flowers to analyse. Try close-up mode, a closer photo, or better lighting.</Notice>}</div>
    </div>
  );
}

export function FlowerDetail({ f }: { f: Flower }) {
  const r = f.readiness;
  return (
    <div className="space-y-4">
      <Card title={`Flower #${f.id}`} right={<MethodBadge method={f.detection.method} />}>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-muted">Detection score</dt><dd className="font-mono">{f.detection.method === "closeup_fallback" ? "not a detection" : pct(f.detection.score)}</dd>
          <dt className="text-muted">Box (px)</dt><dd className="font-mono text-xs">{f.detection.box.map((v) => v.toFixed(0)).join(", ")}</dd>
          {f.pose && <><dt className="text-muted">Centre (image)</dt><dd className="font-mono text-xs">{f.pose.center_px.join(", ")}</dd>
            <dt className="text-muted">Facing</dt><dd>{f.pose.facing_estimate} ({num(f.pose.facing_ratio)})</dd>
            <dt className="text-muted">Approach</dt><dd className="text-xs">{f.pose.alignment.guidance}</dd></>}
        </dl>
        {f.pose && <p className="mt-2 text-[11px] text-muted">{f.pose.note}</p>}
      </Card>

      <Card title="Species" right={<MethodBadge method={f.species.method} />}>
        <div className="flex items-baseline justify-between"><span className="font-display text-2xl capitalize">{f.species.species}</span><span className="font-mono text-sm">{pct(f.species.confidence)}</span></div>
        {f.species.reason && <p className="mt-1 text-xs text-muted">{f.species.reason}</p>}
        {f.species.candidates && f.species.candidates.length > 0 && (
          <div className="mt-2 space-y-1">{f.species.candidates.map((c) => (
            <div key={c.species} className="grid grid-cols-[90px_1fr_48px] items-center gap-2 text-xs"><span>{c.species}</span><Bar value={c.vote_share} /><span className="text-right font-mono">{pct(c.vote_share, 0)}</span></div>
          ))}</div>
        )}
      </Card>

      {f.stage && (
        <Card title="Developmental stage" right={<MethodBadge method={f.stage.method} />} subtitle={f.stage.note}>
          <div className="mb-2 flex items-center gap-2"><span className="font-display text-xl">{label(f.stage.stage)}</span>{f.stage.uncertain && <Pill tone="warn">uncertain</Pill>}</div>
          <div className="space-y-1">{Object.entries(f.stage.distribution).map(([k, v]) => (
            <div key={k} className="grid grid-cols-[110px_1fr_44px] items-center gap-2 text-xs"><span>{label(k)}</span><Bar value={v} tone="pollen" /><span className="text-right font-mono">{pct(v, 0)}</span></div>
          ))}</div>
        </Card>
      )}

      {f.structure && (
        <Card title="Centre region" right={<MethodBadge method={f.structure.method} />} subtitle={f.structure.note}>
          <p className="text-sm">Pollen-like yellow cluster: <strong>{f.structure.yellow_cluster_visible ? "visible" : "not visible"}</strong>
            {f.structure.yellow_fraction_in_centre != null && <span className="text-muted"> ({pct(f.structure.yellow_fraction_in_centre)})</span>}</p>
        </Card>
      )}

      {f.health && (
        <Card title="Visible health indicators" right={<MethodBadge method="heuristic" />} subtitle={f.health.note}>
          {f.health.indicators.length === 0 ? <p className="text-sm">No visible anomaly detected.</p> : (
            <ul className="space-y-1 text-sm">{f.health.indicators.map((i) => <li key={i.type}><Pill tone="warn">{label(i.type)}</Pill> <span className="font-mono text-xs">{i.value} (threshold {i.threshold})</span></li>)}</ul>
          )}
        </Card>
      )}

      {r && <ReadinessCard r={r} />}
    </div>
  );
}

export function ReadinessCard({ r }: { r: Readiness }) {
  return (
    <Card title="Pollination readiness" right={<MethodBadge method={r.method} />} subtitle={r.label}>
      <div className="flex items-center justify-between"><Pill tone={readinessTone(r.category)}>{label(r.category)}</Pill><span className="font-mono text-sm">confidence {pct(r.confidence)}</span></div>
      {r.strategy && <div className="mt-3 rounded-lg bg-raised p-3 text-sm"><div className="kicker mb-1">Strategy · {label(r.strategy.mechanism)}</div>{r.strategy.recommendation}</div>}
      <Section title="Supporting observations" items={r.supporting_observations} />
      <Section title="Uncertainty" items={r.uncertainty_warnings} tone="warn" />
      <Section title="Biological limitations" items={r.biological_limitations} />
      {r.research_sources.length > 0 && <Section title="Sources" items={r.research_sources} small />}
      <Link to="/app/simulator" state={{ species: r.species }} className="btn-ghost mt-3 w-full">Simulate pollen transfer for {r.species}</Link>
    </Card>
  );
}

function Section({ title, items, tone, small }: { title: string; items: string[]; tone?: "warn"; small?: boolean }) {
  if (!items.length) return null;
  return (
    <div className="mt-3">
      <div className="kicker mb-1">{title}</div>
      <ul className={`list-disc space-y-0.5 pl-4 ${small ? "text-[11px]" : "text-xs"} ${tone === "warn" ? "text-pollen" : "text-muted"}`}>{items.map((x, i) => <li key={i}>{x}</li>)}</ul>
    </div>
  );
}
