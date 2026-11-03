import { useState, type FormEvent } from "react";
import { Trash2 } from "lucide-react";
import { Card, Empty, ErrorBanner, PageHeader } from "../components/ui";
import { api } from "../lib/api";
import { useApi, when } from "../lib/hooks";
import type { FieldLoc, Page, Plant, SpeciesKB } from "../lib/types";

export default function InventoryPage() {
  const [filter, setFilter] = useState("");
  const plants = useApi<Page<Plant>>(`/plants?page_size=200${filter ? `&species_id=${filter}` : ""}`, [filter]);
  const fields = useApi<FieldLoc[]>("/fields");
  const kb = useApi<{ species: SpeciesKB[] }>("/ai/species");
  const [f, setF] = useState({ label: "", species_id: "", field_id: "", cultivar: "", planted_on: "", notes: "" });
  const [err, setErr] = useState<string | null>(null);
  const save = async (e: FormEvent) => {
    e.preventDefault(); setErr(null);
    try {
      await api.post("/plants", { ...f, species_id: f.species_id || null, field_id: f.field_id ? +f.field_id : null, planted_on: f.planted_on || null });
      setF({ ...f, label: "", notes: "" }); plants.reload();
    } catch (x) { setErr((x as Error).message); }
  };
  const fieldName = (id: number | null) => fields.data?.find((x) => x.id === id)?.name ?? "—";
  return (
    <div>
      <PageHeader kicker="Records" title="Flower & plant inventory">Track individual plants so scans and pollination logs can be linked to them.</PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-5 lg:grid-cols-[340px_1fr]">
        <Card title="Add plant">
          <form onSubmit={save} className="space-y-2">
            <input aria-label="Label" required className="input" placeholder="Label (e.g. T-014)" value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} />
            <select aria-label="Species" className="input" value={f.species_id} onChange={(e) => setF({ ...f, species_id: e.target.value })}>
              <option value="">Species…</option>{kb.data?.species.map((s) => <option key={s.id} value={s.id}>{s.common_name}</option>)}</select>
            <select aria-label="Field" className="input" value={f.field_id} onChange={(e) => setF({ ...f, field_id: e.target.value })}>
              <option value="">Field…</option>{fields.data?.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select>
            <input aria-label="Cultivar" className="input" placeholder="Cultivar" value={f.cultivar} onChange={(e) => setF({ ...f, cultivar: e.target.value })} />
            <input aria-label="Planted on" type="date" className="input" value={f.planted_on} onChange={(e) => setF({ ...f, planted_on: e.target.value })} />
            <textarea aria-label="Notes" className="input" rows={2} placeholder="Notes" value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} />
            <button className="btn-primary w-full">Add plant</button>
          </form>
        </Card>
        <Card title={`Plants (${plants.data?.total ?? 0})`} right={
          <select aria-label="Filter by species" className="input !w-44 !py-1 text-xs" value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="">All species</option>{kb.data?.species.map((s) => <option key={s.id} value={s.id}>{s.common_name}</option>)}</select>}>
          {plants.data?.items.length ? (
            <div className="overflow-x-auto"><table className="table-base">
              <thead><tr><th>Label</th><th>Species</th><th>Cultivar</th><th>Field</th><th>Planted</th><th>Added</th><th /></tr></thead>
              <tbody>{plants.data.items.map((p) => (
                <tr key={p.id}><td className="font-medium">{p.label}</td><td>{p.species_id ?? "—"}</td><td>{p.cultivar || "—"}</td><td>{fieldName(p.field_id)}</td><td>{p.planted_on ?? "—"}</td><td className="text-xs">{when(p.created_at)}</td>
                  <td><button aria-label={`Delete ${p.label}`} onClick={async () => { await api.del(`/plants/${p.id}`); plants.reload(); }}><Trash2 size={14} /></button></td></tr>
              ))}</tbody></table></div>
          ) : <Empty title="No plants recorded" />}
        </Card>
      </div>
    </div>
  );
}
