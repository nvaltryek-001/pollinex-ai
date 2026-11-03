import { useState, type FormEvent } from "react";
import { DistBars } from "../components/Charts";
import { ReadinessCard } from "../components/ScanResults";
import { Card, ErrorBanner, Notice, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import type { Dashboard, Readiness, SpeciesKB } from "../lib/types";

const STAGES = ["bud", "early_bloom", "partially_open", "fully_open", "senescent"];

export default function ReadinessPage() {
  const kb = useApi<{ species: SpeciesKB[] }>("/ai/species");
  const dash = useApi<Dashboard>("/analytics/dashboard");
  const [form, setForm] = useState({ species_id: "tomato", stage: "fully_open", stage_score: 0.75, yellow_cluster_visible: true,
    temperature_c: "", relative_humidity_pct: "", rain_mm_h: "", wind_kmh: "" });
  const [res, setRes] = useState<Readiness | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const set = (k: string, v: unknown) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErr(null);
    const n = (x: string) => (x === "" ? null : Number(x));
    try {
      setRes(await api.post<Readiness>("/ai/readiness", { ...form, temperature_c: n(form.temperature_c), relative_humidity_pct: n(form.relative_humidity_pct),
        rain_mm_h: n(form.rain_mm_h), wind_kmh: n(form.wind_kmh) }));
    } catch (x) { setErr((x as Error).message); }
  };

  return (
    <div>
      <PageHeader kicker="Module 5 · decision support" title="Pollination readiness">
        A transparent rule engine combining species biology, estimated stage, visible cues and environment. Explore how each input changes the estimate.
      </PageHeader>
      <div className="grid gap-5 lg:grid-cols-[360px_1fr]">
        <div className="space-y-4">
          <Card title="Inputs">
            <form onSubmit={submit} className="space-y-3">
              <div><label className="label" htmlFor="sp">Species</label>
                <select id="sp" className="input" value={form.species_id} onChange={(e) => set("species_id", e.target.value)}>
                  {kb.data?.species.map((s) => <option key={s.id} value={s.id}>{s.common_name}</option>)}
                </select></div>
              <div><label className="label" htmlFor="st">Stage</label>
                <select id="st" className="input" value={form.stage} onChange={(e) => set("stage", e.target.value)}>
                  {STAGES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
                </select></div>
              <div><label className="label" htmlFor="sc">Stage score {form.stage_score.toFixed(2)}</label>
                <input id="sc" type="range" min={0} max={1} step={0.05} value={form.stage_score} onChange={(e) => set("stage_score", +e.target.value)} className="w-full" /></div>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.yellow_cluster_visible} onChange={(e) => set("yellow_cluster_visible", e.target.checked)} />Pollen-like cluster visible</label>
              <div className="grid grid-cols-2 gap-2">
                {([["temperature_c", "Temp °C"], ["relative_humidity_pct", "Humidity %"], ["rain_mm_h", "Rain mm/h"], ["wind_kmh", "Wind km/h"]] as const).map(([k, l]) => (
                  <div key={k}><label className="label" htmlFor={k}>{l}</label><input id={k} className="input" inputMode="decimal" value={form[k]} onChange={(e) => set(k, e.target.value)} placeholder="optional" /></div>
                ))}
              </div>
              <button className="btn-primary w-full">Estimate</button>
            </form>
          </Card>
          <Card title="Readiness across your scans"><DistBars data={dash.data?.readiness_distribution ?? {}} color="rgb(var(--sky))" /></Card>
        </div>
        <div className="space-y-4">
          <ErrorBanner error={err} />
          <Notice>Without biological ground truth this is a <strong>visual readiness estimate</strong>, not a validated prediction of stigma receptivity or fertilisation.</Notice>
          {res && <ReadinessCard r={res} />}
        </div>
      </div>
    </div>
  );
}
