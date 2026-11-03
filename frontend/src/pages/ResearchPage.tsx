import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Card, ErrorBanner, Loading, PageHeader, Pill } from "../components/ui";
import { useApi } from "../lib/hooks";
import { Markdown } from "../components/Markdown";

interface Ref { id: string; title: string; authors: string; year: number; venue: string; doi_or_url: string; evidence_type: string; relevance: string }
const DOCS = [["literature_review", "Literature review"], ["research_gaps", "Research gaps"], ["research_comparison", "Comparison"], ["methodology", "Methodology"]] as const;

export default function ResearchPage() {
  const refs = useApi<Ref[]>("/research/references");
  const [doc, setDoc] = useState<string>("research_gaps");
  const md = useApi<{ markdown: string }>(`/research/documents/${doc}`, [doc]);
  return (
    <div>
      <PageHeader kicker="Research centre" title="Evidence behind the platform">
        Verified references (PR = peer-reviewed, PP = preprint, DS = dataset documentation) and the research documents shipped with the repository.
      </PageHeader>
      <div className="grid gap-5 xl:grid-cols-[1fr_1.2fr]">
        <Card title={`References (${refs.data?.length ?? 0})`}>
          <ErrorBanner error={refs.error} />
          {refs.loading && <Loading />}
          <ul className="divide-y divide-line">
            {refs.data?.map((r) => (
              <li key={r.id} className="py-3">
                <div className="flex items-start justify-between gap-2"><div className="font-medium leading-snug">{r.title}</div><Pill tone={r.evidence_type === "PR" ? "good" : "info"}>{r.evidence_type}</Pill></div>
                <div className="mt-0.5 text-xs text-muted">{r.authors} · {r.venue} · {r.year}</div>
                <div className="mt-1 text-xs">{r.relevance}</div>
                <a className="mt-1 inline-flex items-center gap-1 text-xs underline" href={r.doi_or_url} target="_blank" rel="noreferrer">{r.doi_or_url}<ExternalLink size={11} /></a>
              </li>
            ))}
          </ul>
        </Card>
        <Card title="Documents" right={
          <select aria-label="Document" className="input !w-48 !py-1 text-xs" value={doc} onChange={(e) => setDoc(e.target.value)}>{DOCS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>}>
          {md.loading ? <Loading /> : md.data && <Markdown text={md.data.markdown} />}
        </Card>
      </div>
    </div>
  );
}
