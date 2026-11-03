import { useState } from "react";
import { BookMarked, ImagePlus } from "lucide-react";
import { CropAnalyzer } from "../components/CropAnalyzer";
import { Bar, Card, ErrorBanner, Loading, MethodBadge, Notice, PageHeader, Pill } from "../components/ui";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { label, pct, useApi } from "../lib/hooks";
import type { SpeciesKB, SpeciesResult } from "../lib/types";

interface KBResp { version: string; disclaimer: string; evidence_sources: Record<string, string>; species: SpeciesKB[]; gallery_threshold: number }

export default function SpeciesPage() {
  const { hasRole } = useAuth();
  const kb = useApi<KBResp>("/ai/species");
  const stats = useApi<Record<string, { count: number; mean_species_confidence: number }>>("/analytics/species");
  const [open, setOpen] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const addRef = async (sid: string, f?: File) => {
    if (!f) return;
    const fd = new FormData();
    fd.append("file", f, f.name);
    try {
      const r = await api.upload<{ gallery_counts: Record<string, number>; note: string }>(`/ai/species/${sid}/references`, fd);
      setMsg(`Added reference for ${sid} (now ${r.gallery_counts[sid]}). ${r.note}`);
      kb.reload();
    } catch (e) { setMsg((e as Error).message); }
  };

  return (
    <div>
      <PageHeader kicker="Module 2 · open-set recognition" title="Species recognition">
        Species are matched against a reference gallery by nearest-neighbour similarity. Below the calibrated threshold
        ({kb.data ? kb.data.gallery_threshold.toFixed(3) : "…"}) the answer is <em>unknown</em> — the model never forces a flower into a known class.
      </PageHeader>
      <div className="space-y-5">
        <CropAnalyzer<SpeciesResult & { gallery: Record<string, number> }> endpoint="/ai/classify-species" title="Classify a flower crop"
          render={(r) => (
            <div className="space-y-2">
              <div className="flex items-center gap-3"><span className="font-display text-3xl capitalize">{r.species}</span><MethodBadge method="trained_reference_gallery" /></div>
              <p className="text-xs text-muted">{r.reason} · nearest similarity {r.similarity?.toFixed(3)}</p>
              {r.candidates?.map((c) => <div key={c.species} className="grid grid-cols-[100px_1fr_50px] items-center gap-2 text-xs"><span>{c.species}</span><Bar value={c.vote_share} /><span className="text-right font-mono">{pct(c.vote_share, 0)}</span></div>)}
            </div>
          )} />
        {msg && <Notice>{msg}</Notice>}
        <Notice>
          The shipped gallery contains apple, peach and pear references from the USDA orchard dataset. Other crops return
          <em> unknown</em> until researchers add reference images (button on each card) — or select the species manually in the scanner.
          Added species are <strong>not evaluated</strong> until a held-out test set exists.
        </Notice>
        <ErrorBanner error={kb.error} onRetry={kb.reload} />
        {kb.loading && <Loading />}
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {kb.data?.species.map((s) => (
            <Card key={s.id} title={s.common_name} subtitle={<i>{s.scientific_name}</i>}
              right={<Pill tone={s.reference_images > 0 ? "good" : "neutral"}>{s.reference_images} refs</Pill>}>
              <div className="flex flex-wrap gap-1.5 text-xs">
                <Pill tone="info">{label(s.primary_mechanism)}</Pill>
                {s.pollination_types.map((t) => <Pill key={t}>{label(t)}</Pill>)}
              </div>
              <p className="mt-3 text-sm">{s.compatibility}</p>
              <p className="mt-1 text-xs text-muted">Seen in your scans: {stats.data?.[s.id]?.count ?? 0}</p>
              {open === s.id && (
                <div className="mt-3 space-y-2 text-xs">
                  <p><strong>Flower:</strong> {s.flower_type}</p>
                  <p><strong>Mechanism:</strong> {s.mechanism_detail}</p>
                  <p><strong>Strategy:</strong> {s.strategy}</p>
                  <p><strong>Ready stages:</strong> {s.ready_stages.map(label).join(", ")}</p>
                  <p><strong>Limitations:</strong> {s.limitations.join(" ")}</p>
                  <p className="text-muted"><BookMarked size={12} className="inline" /> {s.evidence.map((e) => kb.data!.evidence_sources[e]).join(" · ")} ({s.evidence_level})</p>
                </div>
              )}
              <div className="mt-3 flex gap-2">
                <button className="btn-ghost !px-3 !py-1 text-xs" onClick={() => setOpen(open === s.id ? null : s.id)}>{open === s.id ? "Less" : "Biology & evidence"}</button>
                {hasRole("admin", "researcher") && (
                  <label className="btn-ghost cursor-pointer !px-3 !py-1 text-xs"><ImagePlus size={14} />Add reference
                    <input type="file" accept="image/*" className="sr-only" onChange={(e) => addRef(s.id, e.target.files?.[0])} /></label>
                )}
              </div>
            </Card>
          ))}
        </div>
        {kb.data && <p className="text-xs text-muted">Knowledge base {kb.data.version}. {kb.data.disclaimer}</p>}
      </div>
    </div>
  );
}
