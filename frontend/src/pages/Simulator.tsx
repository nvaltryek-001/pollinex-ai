import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Pause, Play, RotateCcw } from "lucide-react";
import { SimScene2D, SimScene3D, webglAvailable } from "../components/SimScene";
import { Card, ErrorBanner, Loading, MethodBadge, Notice, PageHeader, Pill } from "../components/ui";
import { api } from "../lib/api";
import { label, num, pct, useApi, when } from "../lib/hooks";
import { toast } from "../lib/toast";
import type { Page, Replay, Simulation, SpeciesKB } from "../lib/types";

interface Params { vibration_hz: number; wind_kmh: number; wind_dir_deg: number; offx: number; offy: number; particle_count: number; pollen_release_rate: number; humidity_pct: number; seed: number }

export default function Simulator() {
  const loc = useLocation() as { state?: { species?: string } };
  const kb = useApi<{ species: SpeciesKB[] }>("/ai/species");
  const sims = useApi<Page<Simulation>>("/simulations?page_size=10");
  const [species, setSpecies] = useState(loc.state?.species && loc.state.species !== "unknown" ? loc.state.species : "tomato");
  const profile = useMemo(() => kb.data?.species.find((s) => s.id === species)?.simulation_profile, [kb.data, species]);
  const [p, setP] = useState<Params>({ vibration_hz: 175, wind_kmh: 0, wind_dir_deg: 0, offx: 0, offy: 0, particle_count: 150, pollen_release_rate: 0.5, humidity_pct: 60, seed: 42 });
  const [replay, setReplay] = useState<Replay | null>(null);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [use3d, setUse3d] = useState(() => webglAvailable());
  const [speed, setSpeed] = useState(1);
  const [sweep, setSweep] = useState<{ x: string; efficiency: number }[] | null>(null);
  const raf = useRef<number>(0);

  useEffect(() => {
    if (!profile) return;
    setP((o) => ({ ...o, vibration_hz: Number(profile.vibration_hz ?? 0), particle_count: Number(profile.particle_count ?? 150),
      pollen_release_rate: Number(profile.pollen_release_rate ?? 0.5) }));
  }, [profile]);

  useEffect(() => {
    if (!playing || !replay) return;
    let last = performance.now();
    const step = (t: number) => {
      if (t - last > 50 / speed) {
        last = t;
        setFrame((f) => { if (f + 1 >= replay.frames.length) { setPlaying(false); return f; } return f + 1; });
      }
      raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [playing, replay, speed]);

  const overrides = () => ({ vibration_hz: p.vibration_hz, wind_kmh: p.wind_kmh, wind_dir_deg: p.wind_dir_deg, effector_offset_mm: [p.offx, p.offy],
    particle_count: p.particle_count, pollen_release_rate: p.pollen_release_rate, humidity_pct: p.humidity_pct, seed: p.seed });

  const loadReplay = async (id: number) => {
    const r = await api.get<Replay>(`/simulations/${id}/replay`);
    setReplay(r); setFrame(0); setPlaying(true);
  };

  const run = async () => {
    setErr(null); setBusy(true);
    try {
      const sim = await api.post<Simulation>("/simulations", { species_id: species, overrides: overrides() });
      const done = await api.post<Simulation>(`/simulations/${sim.id}/execute`);
      if (done.status !== "completed") throw new Error(done.result_summary.error ?? `simulation ${done.status}`);
      await loadReplay(sim.id);
      sims.reload();
      toast.success(`Simulation #${sim.id} completed (computational result)`);
    } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };

  const runSweep = async (parameter: string, values: unknown[]) => {
    setErr(null);
    try {
      const r = await api.post<{ rows: Record<string, unknown>[] }>("/simulations/sweep", { species_id: species, parameter, values, overrides: overrides() });
      setSweep(r.rows.map((row) => ({ x: Array.isArray(row[parameter]) ? `${(row[parameter] as number[])[0]} mm` : String(row[parameter]), efficiency: Number(row.efficiency) })));
    } catch (e) { setErr((e as Error).message); }
  };

  const s = replay?.summary;
  const offset: [number, number] = replay ? ((replay.params.effector_offset_mm as [number, number]) ?? [0, 0]) : [p.offx, p.offy];
  const slider = (k: keyof Params, l: string, min: number, max: number, step: number, unit = "") => (
    <div key={k}><label className="label" htmlFor={k}>{l}: <span className="font-mono normal-case">{p[k]}{unit}</span></label>
      <input id={k} type="range" min={min} max={max} step={step} value={p[k]} onChange={(e) => setP({ ...p, [k]: +e.target.value })} className="w-full" /></div>
  );

  return (
    <div>
      <PageHeader kicker="Part 7 · digital twin" title="Virtual pollination simulator">
        A seeded particle model of pollen release, drift and capture by a virtual stigma, with species-specific profiles from the knowledge base.
      </PageHeader>
      <Notice>Computational simulation of transfer geometry only — <strong>not</strong> evidence of fertilisation, fruit set or yield.</Notice>
      <div className="mt-4 grid gap-5 xl:grid-cols-[320px_1fr]">
        <Card title="Scenario">
          <div className="space-y-3">
            <div><label className="label" htmlFor="species">Species profile</label>
              <select id="species" className="input" value={species} onChange={(e) => setSpecies(e.target.value)}>
                {kb.data?.species.map((x) => <option key={x.id} value={x.id}>{x.common_name} · {label(String(x.simulation_profile.mode))}</option>)}
              </select></div>
            {profile?.mode === "vibration" && slider("vibration_hz", "Vibration", 0, 500, 5, " Hz")}
            {slider("particle_count", "Particles", 20, 600, 10)}
            {slider("pollen_release_rate", "Release rate", 0, 1, 0.05)}
            {slider("offx", "Effector offset x", -5, 5, 0.25, " mm")}
            {slider("offy", "Effector offset y", -5, 5, 0.25, " mm")}
            {slider("wind_kmh", "Wind", 0, 40, 1, " km/h")}
            {slider("wind_dir_deg", "Wind direction", 0, 359, 5, "°")}
            {slider("humidity_pct", "Humidity", 10, 100, 1, " %")}
            {slider("seed", "Random seed", 1, 999, 1)}
            <button className="btn-primary w-full" onClick={run} disabled={busy}>{busy ? "Simulating…" : "Run simulation"}</button>
            <div className="flex flex-wrap gap-2">
              <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => runSweep("effector_offset_mm", [[0, 0], [0.5, 0], [1, 0], [2, 0], [3, 0], [4, 0]])}>Sweep alignment</button>
              <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => runSweep("wind_kmh", [0, 5, 10, 20, 30])}>Sweep wind</button>
              {profile?.mode === "vibration" && <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => runSweep("vibration_hz", [50, 100, 150, 175, 200, 250, 350])}>Sweep Hz</button>}
            </div>
          </div>
        </Card>
        <div className="space-y-4">
          <ErrorBanner error={err} />
          <Card title={replay ? `Simulation #${replay.id} · ${replay.species_id}` : "Scene"} right={<div className="flex items-center gap-2">
            <MethodBadge method="simulation" />
            <button className="btn-ghost !px-2 !py-1 text-xs" onClick={() => setUse3d(!use3d)} disabled={!webglAvailable()}>{use3d ? "2D view" : "3D view"}</button></div>}>
            <div className="relative h-[380px] overflow-hidden rounded-lg bg-raised md:h-[460px]">
              {replay ? (use3d ? <SimScene3D replay={replay} frameIdx={frame} offset={offset} /> : <SimScene2D replay={replay} frameIdx={frame} offset={offset} />)
                : <div className="grid h-full place-items-center text-sm text-muted">{busy ? <Loading text="Running" /> : "Run a simulation to see the replay."}</div>}
            </div>
            {replay && (
              <div className="mt-3 flex items-center gap-3">
                <button className="btn-ghost !px-2 !py-1" aria-label={playing ? "Pause" : "Play"} onClick={() => { if (frame >= replay.frames.length - 1) setFrame(0); setPlaying(!playing); }}>{playing ? <Pause size={16} /> : <Play size={16} />}</button>
                <button className="btn-ghost !px-2 !py-1" aria-label="Replay from start" onClick={() => { setFrame(0); setPlaying(true); }}><RotateCcw size={16} /></button>
                <input aria-label="Timeline" type="range" min={0} max={replay.frames.length - 1} value={frame} onChange={(e) => { setPlaying(false); setFrame(+e.target.value); }} className="flex-1" />
                <span className="w-16 text-right font-mono text-xs">{replay.frames[frame]?.t.toFixed(2)} s</span>
                <select aria-label="Playback speed" className="input !w-20 !py-1 text-xs" value={speed} onChange={(e) => setSpeed(+e.target.value)}>
                  {[0.25, 0.5, 1, 2, 4].map((v) => <option key={v} value={v}>{v}×</option>)}
                </select>
              </div>
            )}
            <p className="mt-2 text-xs text-muted">Yellow: pollen in flight (with short trails) · green: captured · translucent green: receptive targets (stigma / pistils / florets) · red ring: virtual effector aim point{replay?.params.mode === "cross_transfer" ? " · upper flower: compatible donor cultivar" : ""}. Drag to orbit (3D).</p>
            {replay && <p className="mt-1 text-xs text-muted"><strong>Model:</strong> {MODE_TEXT[String(replay.params.mode)] ?? String(replay.params.mode)}</p>}
          </Card>
          {s && (
            <div className="grid gap-3 md:grid-cols-4">
              <Metric t="Detection accuracy" v="n/a here" d="See Model evaluation; the simulator does not use camera detections." />
              <Metric t="Simulation completion" v={replay ? "completed" : "—"} d={`${s.released} released · ${s.lost} lost`} />
              <Metric t="Simulated transfer efficiency" v={pct(s.simulated_transfer_efficiency)} d={`${s.captured} captured${s.target_coverage != null ? ` · coverage ${pct(s.target_coverage)}` : ""} · offset ${num(s.alignment_error_mm)} mm`} />
              <Metric t="Biological outcome" v="not measured" d="Requires a physical trial (see evaluation plan in docs)." />
            </div>
          )}
          {s?.notes && s.notes.length > 0 && <div className="flex flex-wrap gap-1">{s.notes.map((n) => <Pill key={n}>{n}</Pill>)}</div>}
          {sweep && (
            <Card title="Sensitivity sweep" subtitle="simulated transfer efficiency vs parameter (same seed)">
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={sweep}><CartesianGrid stroke="rgb(var(--line))" vertical={false} />
                  <XAxis dataKey="x" stroke="rgb(var(--muted))" fontSize={11} /><YAxis stroke="rgb(var(--muted))" fontSize={11} domain={[0, 1]} tickFormatter={(v) => `${Math.round(v * 100)}%`} />
                  <Tooltip formatter={(v) => pct(Number(v))} /><Line dataKey="efficiency" stroke="rgb(var(--petal))" strokeWidth={2} /></LineChart>
              </ResponsiveContainer>
            </Card>
          )}
          <Card title="Previous simulations">
            {sims.data?.items.length ? (
              <table className="table-base"><thead><tr><th>#</th><th>Species</th><th>When</th><th>Status</th><th>Sim. efficiency</th><th /></tr></thead>
                <tbody>{sims.data.items.map((x) => (
                  <tr key={x.id}><td>{x.id}</td><td>{x.species_id}</td><td>{when(x.created_at)}</td><td>{x.status}</td>
                    <td className="font-mono">{pct(x.result_summary.simulated_transfer_efficiency)}</td>
                    <td>{x.status === "completed" && <button className="underline" onClick={() => loadReplay(x.id)}>Replay</button>}</td></tr>
                ))}</tbody></table>
            ) : <p className="text-sm text-muted">No simulations yet.</p>}
          </Card>
        </div>
      </div>
    </div>
  );
}

const MODE_TEXT: Record<string, string> = {
  vibration: "pendant flower; pollen leaves the poricidal anther cone when vibrated (release peaks near 150–200 Hz) and falls onto the stigma at the cone tip.",
  cross_transfer: "pollen from a separate, compatible donor flower is carried by the effector/insect to the target stigma (self-pollen is not modelled as effective).",
  brush: "brush/contact transfer from the anther ring to the central stigma within the same flower.",
  air_assisted: "air movement spreads pollen over many pistils on the receptacle; coverage matters (misshapen fruit if pistils are missed).",
  ring_progression: "capitulum with many florets: pollen-presenting outer ring, receptive ring just inside (protandry, centripetal opening).",
  column_transfer: "anthers along the staminal column; pollen is moved up onto the five stigma pads at its tip.",
};

function Metric({ t, v, d }: { t: string; v: string; d: string }) {
  return <div className="card p-3"><div className="kicker">{t}</div><div className="mt-1 font-display text-xl">{v}</div><div className="mt-1 text-[11px] text-muted">{d}</div></div>;
}
