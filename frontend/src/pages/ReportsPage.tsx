import { useState } from "react";
import { FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { Card, ErrorBanner, Notice, PageHeader } from "../components/ui";
import { download } from "../lib/api";

export default function ReportsPage() {
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const get = async (key: string, path: string, name: string) => {
    setErr(null); setBusy(key);
    try { await download(path, name); } catch (e) { setErr((e as Error).message); } finally { setBusy(null); }
  };
  const stamp = new Date().toISOString().slice(0, 10);
  return (
    <div>
      <PageHeader kicker="Exports" title="Downloadable reports">Generated on demand from your database records.</PageHeader>
      <ErrorBanner error={err} />
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        <Card title="Summary report (PDF)" subtitle="Totals, distributions, recent scans, simulations and the detector's test metrics.">
          <button className="btn-primary w-full" disabled={busy !== null} onClick={() => get("pdf", "/reports/summary.pdf", `pollinex_report_${stamp}.pdf`)}><FileText size={16} />{busy === "pdf" ? "Generating…" : "Download PDF"}</button>
        </Card>
        <Card title="Detections (CSV)" subtitle="One row per analysed flower: species, stage, readiness, scores, boxes, provenance.">
          <button className="btn-primary w-full" disabled={busy !== null} onClick={() => get("csv", "/reports/scans.csv", `pollinex_scans_${stamp}.csv`)}><FileSpreadsheet size={16} />{busy === "csv" ? "Generating…" : "Download CSV"}</button>
        </Card>
        <Card title="Single scan (JSON)" subtitle="Full machine-readable output for one scan — open a scan and use its JSON button.">
          <div className="flex items-center gap-2 text-sm text-muted"><FileJson size={16} />Available on each scan page.</div>
        </Card>
      </div>
      <div className="mt-5"><Notice>Reports label every output by method. Simulated transfer efficiency is reported separately from detection metrics and is never presented as fruit set or yield.</Notice></div>
    </div>
  );
}
