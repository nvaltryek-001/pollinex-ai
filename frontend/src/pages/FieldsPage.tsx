import { useState, type FormEvent } from "react";
import { MapPin, Trash2 } from "lucide-react";
import { Card, Empty, ErrorBanner, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useApi } from "../lib/hooks";
import type { FieldLoc, Page, Plant } from "../lib/types";

export default function FieldsPage() {
  const fields = useApi<FieldLoc[]>("/fields");
  const plants = useApi<Page<Plant>>("/plants?page_size=200");
  const [f, setF] = useState({ name: "", latitude: "", longitude: "", area_m2: "", notes: "" });
  const [err, setErr] = useState<string | null>(null);
  const n = (x: string) => (x === "" ? null : Number(x));
  const save = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try { await api.post("/fields", { ...f, latitude: n(f.latitude), longitude: n(f.longitude), area_m2: n(f.area_m2) }); setF({ name: "", latitude: "", longitude: "", area_m2: "", notes: "" }); fields.reload(); }
    catch (x) { setErr((x as Error).message); }
  };
  const count = (id: number) => plants.data?.items.filter((p) => p.field_id === id).length ?? 0;
  return (
    <div>
      <PageHeader kicker="Smart field management" title="Fields & blocks">Organise plants, scans and environment records by location.</PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-5 lg:grid-cols-[340px_1fr]">
        <Card title="Add field">
          <form onSubmit={save} className="space-y-2">
            <input aria-label="Name" required className="input" placeholder="Name (e.g. Greenhouse 2)" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <input aria-label="Latitude" className="input" placeholder="Latitude" value={f.latitude} onChange={(e) => setF({ ...f, latitude: e.target.value })} />
              <input aria-label="Longitude" className="input" placeholder="Longitude" value={f.longitude} onChange={(e) => setF({ ...f, longitude: e.target.value })} />
            </div>
            <input aria-label="Area" className="input" placeholder="Area m²" value={f.area_m2} onChange={(e) => setF({ ...f, area_m2: e.target.value })} />
            <textarea aria-label="Notes" className="input" rows={2} placeholder="Notes" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />
            <button className="btn-primary w-full">Save field</button>
          </form>
        </Card>
        <div className="grid content-start gap-3 md:grid-cols-2">
          {fields.data?.length === 0 && <div className="md:col-span-2"><Empty title="No fields yet">Create one to group plants and weather records.</Empty></div>}
          {fields.data?.map((x) => (
            <Card key={x.id} title={x.name} subtitle={x.latitude != null ? <><MapPin size={11} className="inline" /> {x.latitude}, {x.longitude}</> : "no coordinates"}
              right={<button aria-label={`Delete ${x.name}`} onClick={async () => { if (confirm(`Delete field ${x.name}?`)) { await api.del(`/fields/${x.id}`); fields.reload(); } }}><Trash2 size={14} /></button>}>
              <div className="text-sm"><span className="font-display text-2xl">{count(x.id)}</span> <span className="text-muted">plants</span>{x.area_m2 != null && <span className="text-muted"> · {x.area_m2} m²</span>}</div>
              {x.notes && <p className="mt-2 text-xs text-muted">{x.notes}</p>}
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
