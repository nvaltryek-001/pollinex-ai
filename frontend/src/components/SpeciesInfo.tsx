import { BookOpen } from "lucide-react";
import { label, useApi } from "../lib/hooks";
import type { SpeciesKB, SpeciesKBResponse } from "../lib/types";
import { Card, Pill } from "./ui";

const SUPPORT: Record<string, { tone: "good" | "warn" | "bad" | "neutral"; text: string }> = {
  validated: { tone: "good", text: "AI-supported · validated on held-out photos" },
  limited_evidence: { tone: "warn", text: "AI-supported · limited test evidence" },
  not_supported: { tone: "bad", text: "not AI-supported · species must be selected manually" },
  not_evaluated: { tone: "neutral", text: "AI support not evaluated" },
};

/** General botanical reference for a species - knowledge-base data, never inferred from the uploaded image. */
export function SpeciesInfoPanel({ speciesId, compact }: { speciesId: string; compact?: boolean }) {
  const kb = useApi<SpeciesKBResponse>("/ai/species");
  const sp: SpeciesKB | undefined = kb.data?.species.find((s) => s.id === speciesId);
  if (speciesId === "unknown") {
    return (
      <Card title="Species information">
        <p className="text-sm text-muted">The species was not recognised, so no species information is shown. Choose the species with
          <em> Wrong species?</em> above if you know it.</p>
      </Card>
    );
  }
  if (!sp) return null;
  const b = sp.botany;
  const sup = SUPPORT[sp.ai_support ?? "not_evaluated"];
  return (
    <Card title={`About ${sp.common_name}`} subtitle={`${sp.scientific_name}${b ? ` · ${b.family}` : ""}`} right={<BookOpen size={16} className="text-muted" />}>
      <div className="mb-3 flex flex-wrap gap-1"><Pill tone={sup.tone}>{sup.text}</Pill><Pill tone="info">reference knowledge · not from this image</Pill></div>
      {b ? (
        <dl className="grid grid-cols-[130px_1fr] gap-x-3 gap-y-1.5 text-sm">
          <dt className="text-muted">Flower</dt><dd>{b.flower}</dd>
          <dt className="text-muted">Petals</dt><dd>{b.petals}</dd>
          <dt className="text-muted">Reproductive parts</dt><dd>{b.reproductive_structures}</dd>
          {!compact && <><dt className="text-muted">Flowering</dt><dd>{b.flowering}</dd></>}
          <dt className="text-muted">Flowering period</dt><dd>{b.flowering_period}</dd>
          <dt className="text-muted">Pollination</dt><dd>{b.pollination_mechanism} <span className="text-muted">({label(sp.primary_mechanism)})</span></dd>
          <dt className="text-muted">Pollinators</dt><dd>{b.pollinators.join(", ")}</dd>
          <dt className="text-muted">Self / cross</dt><dd>{b.breeding_system}</dd>
          <dt className="text-muted">Fruit</dt><dd><strong>{b.fruit.name}</strong> - {b.fruit.type}. {b.fruit.characteristics}</dd>
          {!compact && <><dt className="text-muted">Agriculture</dt><dd>{b.agricultural_relevance}</dd></>}
        </dl>
      ) : <p className="text-sm text-muted">{sp.flower_type}</p>}
      <p className="mt-3 text-[11px] text-muted">{kb.data?.botany_scope}</p>
      <p className="mt-1 text-[11px] text-muted">{kb.data?.fruit_recognition}</p>
      {b && <p className="mt-1 text-[11px] text-muted">Sources: {b.sources.map((s, i) => <span key={s.id}>{i > 0 && " · "}<a className="underline" href={s.url} target="_blank" rel="noreferrer">{s.title}</a></span>)}</p>}
    </Card>
  );
}
