import { useState, type FormEvent } from "react";
import { CloudDownload, Trash2 } from "lucide-react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Card, ErrorBanner, Loading, Notice, PageHeader, Pill } from "../components/ui";
import { api } from "../lib/api";
import { useApi, when } from "../lib/hooks";
import { toast } from "../lib/toast";
import type { EnvRecord, FieldLoc, Page, SpeciesKB } from "../lib/types";

export default function EnvironmentPage() {
  const list = useApi<Page<EnvRecord>>("/environment?page_size=100");
  const fields = useApi<FieldLoc[]>("/fields");
  const kb = useApi<{ species: SpeciesKB[] }>("/ai/species");
  const [f, setF] = useState({ observed_at: new Date().toISOString().slice(0, 16), temperature_c: "", relative_humidity_pct: "", rain_mm_h: "", wind_kmh: "", observation: "", field_id: "" });
  const [geo, setGeo] = useState({ latitude: "", longitude: "" });
  const [err, setErr] = useState<string | null>(null);
  const [assess, setAssess] = useState<{ id: number; species: string; factors: { factor: string; effect: string; detail?: string; value?: number }[] } | null>(null);
  const n = (x: string) => (x === "" ? null : Number(x));

  const save = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      await api.post("/environment", { observed_at: new Date(f.observed_at).toISOString(), temperature_c: n(f.temperature_c), relative_humidity_pct: n(f.relative_humidity_pct),
        rain_mm_h: n(f.rain_mm_h), wind_kmh: n(f.wind_kmh), observation: f.observation, field_id: f.field_id ? +f.field_id : null });
      list.reload();
      toast.success("Observation saved");
    } catch (x) { setErr((x as Error).message); }
  };
  const fetchWeather = async () => {
    setErr(null);
    const fld = fields.data?.find((x) => String(x.id) === f.field_id);
    const lat = geo.latitude || fld?.latitude, lon = geo.longitude || fld?.longitude;
    if (lat == null || lon == null || lat === "" || lon === "") { setErr("Enter coordinates or pick a field that has coordinates."); return; }
    try { await api.post("/environment/fetch", { latitude: Number(lat), longitude: Number(lon), field_id: f.field_id ? +f.field_id : null }); list.reload(); toast.success("Weather fetched from Open-Meteo"); }
    catch (x) { setErr((x as Error).message); }
  };
  const useMyLocation = () => navigator.geolocation?.getCurrentPosition(
    (p) => setGeo({ latitude: p.coords.latitude.toFixed(4), longitude: p.coords.longitude.toFixed(4) }),
    () => setErr("Location permission denied - enter coordinates manually."));

  const chart = [...(list.data?.items ?? [])].reverse().map((r) => ({ t: new Date(r.observed_at).toLocaleDateString(), temp: r.temperature_c, rh: r.relative_humidity_pct, wind: r.wind_kmh }));

  return (
    <div>
      <PageHeader kicker="Part 8 · decision support" title="Environmental intelligence">
        Record conditions manually or fetch them from Open-Meteo. Each record keeps its source and timestamp; nothing is invented.
      </PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-5 lg:grid-cols-[360px_1fr]">
        <div className="space-y-4">
          <Card title="Manual observation">
            <form onSubmit={save} className="grid grid-cols-2 gap-2">
              <div className="col-span-2"><label className="label" htmlFor="obs">Observed at</label><input id="obs" type="datetime-local" className="input" required value={f.observed_at} onChange={(e) => setF({ ...f, observed_at: e.target.value })} /></div>
              {([["temperature_c", "Temp °C"], ["relative_humidity_pct", "Humidity %"], ["rain_mm_h", "Rain mm/h"], ["wind_kmh", "Wind km/h"]] as const).map(([k, l]) => (
                <div key={k}><label className="label" htmlFor={k}>{l}</label><input id={k} className="input" inputMode="decimal" value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} /></div>
              ))}
              <div className="col-span-2"><label className="label" htmlFor="fld">Field</label>
                <select id="fld" className="input" value={f.field_id} onChange={(e) => setF({ ...f, field_id: e.target.value })}>
                  <option value="">—</option>{fields.data?.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
                </select></div>
              <div className="col-span-2"><label className="label" htmlFor="note">Weather-related observation</label><textarea id="note" className="input" rows={2} value={f.observation} onChange={(e) => setF({ ...f, observation: e.target.value })} /></div>
              <button className="btn-primary col-span-2">Save observation</button>
            </form>
          </Card>
          <Card title="Fetch current weather" subtitle="Open-Meteo (free, no key). Uses the selected field's coordinates if set.">
            <div className="grid grid-cols-2 gap-2">
              <input aria-label="Latitude" className="input" placeholder="lat" value={geo.latitude} onChange={(e) => setGeo({ ...geo, latitude: e.target.value })} />
              <input aria-label="Longitude" className="input" placeholder="lon" value={geo.longitude} onChange={(e) => setGeo({ ...geo, longitude: e.target.value })} />
              <button className="btn-ghost text-xs" onClick={useMyLocation}>Use my location</button>
              <button className="btn-accent text-xs" onClick={fetchWeather}><CloudDownload size={14} />Fetch</button>
            </div>
          </Card>
        </div>
        <div className="space-y-4">
          <Card title="Historical observations">
            {chart.length > 1 ? (
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={chart}><CartesianGrid stroke="rgb(var(--line))" vertical={false} /><XAxis dataKey="t" stroke="rgb(var(--muted))" fontSize={11} /><YAxis stroke="rgb(var(--muted))" fontSize={11} /><Tooltip /><Legend />
                  <Line dataKey="temp" name="°C" stroke="rgb(var(--alert))" connectNulls /><Line dataKey="rh" name="RH %" stroke="rgb(var(--sky))" connectNulls /><Line dataKey="wind" name="km/h" stroke="rgb(var(--leaf))" connectNulls /></LineChart>
              </ResponsiveContainer>
            ) : <p className="text-sm text-muted">Add at least two observations to see a trend.</p>}
          </Card>
          {assess && (
            <Card title={`Assessment for ${assess.species} · record #${assess.id}`}>
              <ul className="space-y-1 text-sm">{assess.factors.map((x, i) => <li key={i}><Pill tone={x.effect === "unfavourable" ? "warn" : x.effect === "info" ? "neutral" : "good"}>{x.factor}</Pill> <span className="text-xs text-muted">{x.detail ?? x.value}</span></li>)}</ul>
              <p className="mt-2 text-xs text-muted">Decision support only; not a substitute for species-specific biological validation.</p>
            </Card>
          )}
          <Card title="Records">
            {list.loading ? <Loading /> : list.data?.items.length ? (
              <div className="overflow-x-auto"><table className="table-base">
                <thead><tr><th>Observed</th><th>°C</th><th>RH</th><th>Rain</th><th>Wind</th><th>Conditions</th><th>Source</th><th>Assess</th><th /></tr></thead>
                <tbody>{list.data.items.map((r) => (
                  <tr key={r.id}><td>{when(r.observed_at)}</td><td>{r.temperature_c ?? "—"}</td><td>{r.relative_humidity_pct ?? "—"}</td><td>{r.rain_mm_h ?? "—"}</td><td>{r.wind_kmh ?? "—"}</td>
                    <td className="text-xs">{r.observation || "—"}{[r.temperature_c, r.relative_humidity_pct, r.rain_mm_h, r.wind_kmh].some((v) => v == null) && <div className="text-[10px] text-pollen">some readings missing</div>}</td>
                    <td><Pill tone={r.source === "manual" ? "neutral" : "info"}>{r.source}</Pill>{r.source !== "manual" && <div className="text-[10px] text-muted">retrieved {String(r.source_detail.retrieved_at ?? "").slice(0, 16)}</div>}</td>
                    <td><select aria-label="Assess for species" className="input !py-1 text-xs" defaultValue="" onChange={async (e) => { if (!e.target.value) return; const a = await api.get<{ factors: never[] }>(`/environment/${r.id}/assessment?species_id=${e.target.value}`); setAssess({ id: r.id, species: e.target.value, factors: a.factors }); }}>
                      <option value="">species…</option>{kb.data?.species.map((s) => <option key={s.id} value={s.id}>{s.common_name}</option>)}</select></td>
                    <td><button aria-label="Delete record" onClick={async () => { await api.del(`/environment/${r.id}`); list.reload(); }}><Trash2 size={14} /></button></td></tr>
                ))}</tbody></table></div>
            ) : <p className="text-sm text-muted">No environmental records yet.</p>}
          </Card>
          <Notice>Weather data: Open-Meteo (CC BY 4.0). If the provider is unreachable you get an explicit error — readings are never fabricated.</Notice>
        </div>
      </div>
    </div>
  );
}
