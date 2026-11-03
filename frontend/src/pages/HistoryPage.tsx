import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Card, Empty, ErrorBanner, Loading, Notice, PageHeader, Pill } from "../components/ui";
import { api } from "../lib/api";
import { label, num, useApi, when } from "../lib/hooks";
import type { Page, Plant, PollinationRecord, Scan, SpeciesKB } from "../lib/types";

const METHODS = ["natural", "manual_brush", "vibration", "air_assisted", "cross_pollen_transfer", "other"];
const OUTCOMES = ["pending", "fruit_set", "no_set", "partial", "unknown"];

export default function HistoryPage() {
  const [page, setPage] = useState(1);
  const scans = useApi<Page<Scan>>(`/scans?page=${page}&page_size=15`, [page]);
  const recs = useApi<Page<PollinationRecord>>("/pollination-records?page_size=100");
  const plants = useApi<Page<Plant>>("/plants?page_size=200");
  const kb = useApi<{ species: SpeciesKB[] }>("/ai/species");
  const [f, setF] = useState({ method: "vibration", performed_at: new Date().toISOString().slice(0, 16), species_id: "", plant_id: "", flowers_treated: "1", outcome_observed: "pending", notes: "" });
  const [err, setErr] = useState<string | null>(null);
  const save = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      await api.post("/pollination-records", { ...f, performed_at: new Date(f.performed_at).toISOString(), species_id: f.species_id || null,
        plant_id: f.plant_id ? +f.plant_id : null, flowers_treated: +f.flowers_treated });
      recs.reload();
    } catch (x) { setErr((x as Error).message); }
  };
  const updateOutcome = async (r: PollinationRecord, outcome: string) => {
    await api.put(`/pollination-records/${r.id}`, { ...r, outcome_observed: outcome });
    recs.reload();
  };
  const pages = scans.data ? Math.max(1, Math.ceil(scans.data.total / scans.data.page_size)) : 1;
  return (
    <div>
      <PageHeader kicker="Records" title="Pollination history">
        Your scan history and the real pollination actions you logged. Logged outcomes (e.g. fruit set) are your field observations — the app never infers them.
      </PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-5 xl:grid-cols-[340px_1fr]">
        <Card title="Log a pollination action">
          <form onSubmit={save} className="space-y-2">
            <select aria-label="Method" className="input" value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}>{METHODS.map((m) => <option key={m} value={m}>{label(m)}</option>)}</select>
            <input aria-label="Performed at" type="datetime-local" className="input" value={f.performed_at} onChange={(e) => setF({ ...f, performed_at: e.target.value })} />
            <select aria-label="Species" className="input" value={f.species_id} onChange={(e) => setF({ ...f, species_id: e.target.value })}><option value="">Species…</option>{kb.data?.species.map((s) => <option key={s.id} value={s.id}>{s.common_name}</option>)}</select>
            <select aria-label="Plant" className="input" value={f.plant_id} onChange={(e) => setF({ ...f, plant_id: e.target.value })}><option value="">Plant…</option>{plants.data?.items.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}</select>
            <input aria-label="Flowers treated" type="number" min={1} className="input" value={f.flowers_treated} onChange={(e) => setF({ ...f, flowers_treated: e.target.value })} />
            <select aria-label="Outcome" className="input" value={f.outcome_observed} onChange={(e) => setF({ ...f, outcome_observed: e.target.value })}>{OUTCOMES.map((o) => <option key={o} value={o}>{label(o)}</option>)}</select>
            <textarea aria-label="Notes" className="input" rows={2} placeholder="Notes" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />
            <button className="btn-primary w-full">Save record</button>
          </form>
        </Card>
        <div className="space-y-5">
          <Card title="Pollination log">
            {recs.data?.items.length ? (
              <div className="overflow-x-auto"><table className="table-base"><thead><tr><th>When</th><th>Method</th><th>Species</th><th>Flowers</th><th>Observed outcome</th></tr></thead>
                <tbody>{recs.data.items.map((r) => (
                  <tr key={r.id}><td>{when(r.performed_at)}</td><td>{label(r.method)}</td><td>{r.species_id ?? "—"}</td><td>{r.flowers_treated}</td>
                    <td><select aria-label="Update outcome" className="input !py-1 text-xs" value={r.outcome_observed ?? "pending"} onChange={(e) => updateOutcome(r, e.target.value)}>{OUTCOMES.map((o) => <option key={o} value={o}>{label(o)}</option>)}</select></td></tr>
                ))}</tbody></table></div>
            ) : <Empty title="No pollination actions logged" />}
            <div className="mt-3"><Notice>These records support the comparison plan in <code>docs/RESEARCH_METHODOLOGY.md</code> (natural vs manual vs assisted pollination) if physical trials become possible.</Notice></div>
          </Card>
          <Card title={`Scan history (${scans.data?.total ?? 0})`}>
            {scans.loading && <Loading />}
            {scans.data?.items.length ? (
              <>
                <div className="overflow-x-auto"><table className="table-base"><thead><tr><th>Scan</th><th>When</th><th>Source</th><th>Flowers</th><th>Species</th><th>Readiness</th><th>Latency</th></tr></thead>
                  <tbody>{scans.data.items.map((s) => (
                    <tr key={s.id}><td><Link className="underline" to={`/app/scans/${s.id}`}>#{s.id}</Link></td><td>{when(s.created_at)}</td><td>{s.source}</td><td>{s.flower_count}</td>
                      <td className="text-xs">{Object.entries(s.summary.species_counts ?? {}).map(([k, v]) => `${k}×${v}`).join(", ") || "—"}</td>
                      <td>{Object.entries(s.summary.readiness_counts ?? {}).map(([k, v]) => <Pill key={k}>{label(k)} {v}</Pill>)}</td>
                      <td className="font-mono text-xs">{num(s.latency_ms, 0)} ms</td></tr>
                  ))}</tbody></table></div>
                <div className="mt-3 flex items-center justify-end gap-2 text-sm">
                  <button className="btn-ghost !py-1" disabled={page <= 1} onClick={() => setPage(page - 1)}>Prev</button>
                  <span className="text-muted">{page} / {pages}</span>
                  <button className="btn-ghost !py-1" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
                </div>
              </>
            ) : !scans.loading && <Empty title="No scans yet"><Link className="underline" to="/app/scanner">Open the scanner</Link></Empty>}
          </Card>
        </div>
      </div>
    </div>
  );
}
