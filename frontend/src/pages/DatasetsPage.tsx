import { Card, ErrorBanner, Loading, PageHeader, Pill } from "../components/ui";
import { label, useApi } from "../lib/hooks";

/* eslint-disable @typescript-eslint/no-explicit-any */
interface DS { id: string; name: string; url: string; license: string; task_support: string; status: string; details: Record<string, any> }
const tone = (s: string) => (({ integrated: "good", script_only: "info", documented_only: "neutral", unverified: "warn", audited_not_used: "neutral", unreachable: "warn" } as const)[s as "integrated"] ?? "neutral");

export default function DatasetsPage() {
  const { data, error, loading, reload } = useApi<{ datasets: DS[]; prepared_report: Record<string, any> | null }>("/datasets");
  const rep = data?.prepared_report;
  return (
    <div>
      <PageHeader kicker="Dataset engineering" title="Dataset management">
        Every dataset investigated for the project, with its verified licence, task support and integration status. Nothing is invented; unavailable data is listed as such.
      </PageHeader>
      <ErrorBanner error={error} onRetry={reload} />
      {loading && <Loading />}
      {rep && (
        <Card title="Integrated training data · usda_fruit_flower" subtitle={`upstream commit ${String(rep.upstream_commit).slice(0, 12)} · ${rep.license} · DOI ${rep.doi}`} className="mb-5">
          <div className="grid gap-4 md:grid-cols-3">
            <table className="table-base"><thead><tr><th>Split</th><th>Images</th><th>Instances</th></tr></thead>
              <tbody>{Object.entries(rep.per_split as Record<string, any>).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.images}</td><td>{v.boxes}</td></tr>)}</tbody></table>
            <table className="table-base"><thead><tr><th>Species</th><th>Images</th><th>Instances</th></tr></thead>
              <tbody>{Object.entries(rep.per_species as Record<string, any>).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v.images}</td><td>{v.boxes}</td></tr>)}</tbody></table>
            <div className="space-y-1 text-xs">
              <p><strong>Split policy:</strong> {rep.split_policy}</p>
              <p><strong>Near-duplicates across splits:</strong> {rep.near_duplicates_across_splits_dhash_le6.length}</p>
              <p><strong>Excluded:</strong> {JSON.stringify(rep.excluded)}</p>
              <p><strong>Ground truth:</strong> {rep.ground_truth_policy}</p>
              <p className="text-alert"><strong>Upstream box audit:</strong> {rep.upstream_box_audit?.conclusion}</p>
            </div>
          </div>
        </Card>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {data?.datasets.map((d) => (
          <Card key={d.id} title={d.name} right={<Pill tone={tone(d.status)}>{label(d.status)}</Pill>}>
            <dl className="grid grid-cols-[100px_1fr] gap-x-3 gap-y-1 text-xs">
              <dt className="text-muted">Licence</dt><dd>{d.license}</dd>
              <dt className="text-muted">Supports</dt><dd>{d.task_support}</dd>
              {d.details.species && <><dt className="text-muted">Species</dt><dd>{Array.isArray(d.details.species) ? d.details.species.join(", ") : d.details.species}</dd></>}
              {d.details.original_images != null && <><dt className="text-muted">Images</dt><dd>{String(d.details.original_images)}</dd></>}
              {d.details.reason && <><dt className="text-muted">Decision</dt><dd>{d.details.reason}</dd></>}
              {d.details.leakage_warning && <><dt className="text-muted">Leakage</dt><dd className="text-pollen">{d.details.leakage_warning}</dd></>}
              {d.details.prepare_script && <><dt className="text-muted">Script</dt><dd className="font-mono">{d.details.prepare_script}</dd></>}
              {d.url && <><dt className="text-muted">Source</dt><dd className="break-all">{d.url.split(" ; ").map((u) => <a key={u} className="underline" href={u} target="_blank" rel="noreferrer">{u} </a>)}</dd></>}
            </dl>
            {d.details.issues && <ul className="mt-2 list-disc pl-4 text-xs text-muted">{(d.details.issues as string[]).map((x) => <li key={x}>{x}</li>)}</ul>}
          </Card>
        ))}
      </div>
    </div>
  );
}
