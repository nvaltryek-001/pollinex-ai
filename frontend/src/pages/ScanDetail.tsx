import { useNavigate, useParams } from "react-router-dom";
import { Download, Trash2 } from "lucide-react";
import { ScanResults } from "../components/ScanResults";
import { ErrorBanner, Loading, PageHeader } from "../components/ui";
import { api, download } from "../lib/api";
import { useApi, when } from "../lib/hooks";
import type { Scan } from "../lib/types";

export default function ScanDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { data, error, loading, reload } = useApi<Scan>(`/scans/${id}`, [id]);
  return (
    <div>
      <PageHeader kicker="Scan record" title={`Scan #${id}`}
        actions={data && <>
          <button className="btn-ghost" onClick={() => download(`/reports/scans/${id}.json`, `pollinex_scan_${id}.json`)}><Download size={16} />JSON</button>
          <button className="btn-ghost text-alert" onClick={async () => { if (confirm("Delete this scan and its analyses?")) { await api.del(`/scans/${id}`); nav("/app/history"); } }}><Trash2 size={16} />Delete</button>
        </>}>
        {data && `${when(data.created_at)} · source: ${data.source} · mode: ${data.mode}`}
      </PageHeader>
      <ErrorBanner error={error} onRetry={reload} />
      {loading && <Loading />}
      {data && <ScanResults scan={data} />}
    </div>
  );
}
