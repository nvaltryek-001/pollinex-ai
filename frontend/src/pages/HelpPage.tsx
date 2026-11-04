import { Link } from "react-router-dom";
import { Card, Notice, PageHeader, Pill } from "../components/ui";

const STEPS: [string, string][] = [
  ["Open the scanner", "Upload a JPEG/PNG/WebP photo or use the camera. Images are validated (type, size, decodable) before analysis."],
  ["Choose a mode", "Auto lets the detector find flowers. Close-up treats the whole photo as one flower when it fills the frame. A species hint skips recognition."],
  ["Read the result", "Boxes come from the YOLO11 detector; species from the reference gallery; stage, centre and health from heuristics; readiness from rules over those findings."],
  ["Correct and save", "Fix a wrong species with “Wrong species?” - readiness is re-estimated. Every scan is saved to Scan history."],
  ["Export", "Open a scan from history and download its PDF report, the CSV of all scans, or the raw JSON."],
];

const MODULES: [string, string, string][] = [
  ["/app/scanner", "Scanner", "Upload or capture a photo and run the full pipeline."],
  ["/app/history", "Scan history", "Every saved scan, with filters, detail pages and exports."],
  ["/app/species", "Species recognition", "Classify a crop and read the species knowledge base (botany, pollination, fruit)."],
  ["/app/structure", "Flower structure", "Centre-region heuristic: is a pollen-like yellow cluster visible?"],
  ["/app/maturity", "Maturity stages", "Bud / opening / open / senescent stage from colour and shape heuristics."],
  ["/app/readiness", "Pollination readiness", "Rule-based visual estimate with its inputs, uncertainty and limitations."],
  ["/app/health", "Plant health", "Visible colour anomalies only - not disease diagnosis."],
  ["/app/simulator", "Virtual simulator", "Simulated pollen transfer; results are simulations, never field measurements."],
  ["/app/environment", "Environment", "Temperature/humidity records used as readiness context."],
  ["/app/fields", "Field management", "Fields and plants that scans and records can be linked to."],
  ["/app/inventory", "Inventory", "Pollination tools and supplies."],
  ["/app/analytics", "Analytics", "Charts computed from your own database records."],
  ["/app/evaluation", "Model evaluation", "Held-out test metrics for the deployed models, with detection and classification kept separate."],
  ["/app/datasets", "Datasets", "Image counts, licences and attribution for every dataset."],
  ["/app/research", "Research centre", "The research papers behind the methods."],
  ["/app/reports", "Reports", "Summary PDF and CSV exports."],
  ["/app/settings", "User settings", "Display name, password change (signs out other sessions) and theme."],
];

const CAN = ["Detect flowers (YOLO11n, ONNX, 960 px)", "Recognise 8 species from a reference gallery, or answer unknown (strawberry is answered as unknown - looks like strawberry)",
  "Estimate stage, visible centre region and visible colour anomalies with heuristics", "Estimate visual pollination readiness with rules",
  "Show general botanical information about the identified species", "Save scans and export PDF / CSV / JSON"];
const CANNOT = ["Recognise strawberry automatically (too few reference photos)", "Detect or identify fruit - no fruit model is trained",
  "Diagnose disease", "Measure pollen viability or stigma receptivity", "Prove that a flower has been pollinated or fertilised", "Predict yield"];

export default function HelpPage() {
  return (
    <div>
      <PageHeader kicker="Help" title="Help & documentation">
        How to use POLLINEX AI, what each module does, and what the AI can and cannot tell you.
      </PageHeader>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card title="Scanning a flower, step by step">
          <ol className="space-y-3">
            {STEPS.map(([t, d], i) => (
              <li key={t} className="grid grid-cols-[28px_1fr] gap-2 text-sm">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-ink font-mono text-xs text-paper">{i + 1}</span>
                <span><strong>{t}.</strong> <span className="text-muted">{d}</span></span>
              </li>
            ))}
          </ol>
          <Link to="/app/scanner" className="btn-primary mt-4">Open the scanner</Link>
        </Card>
        <Card title="What the AI can and cannot do">
          <div className="kicker mb-1">Can</div>
          <ul className="mb-3 space-y-1 text-sm">{CAN.map((x) => <li key={x}><Pill tone="good">yes</Pill> {x}</li>)}</ul>
          <div className="kicker mb-1">Cannot</div>
          <ul className="space-y-1 text-sm">{CANNOT.map((x) => <li key={x}><Pill tone="bad">no</Pill> {x}</li>)}</ul>
        </Card>
        <Card title="Reading the method badges">
          <dl className="grid grid-cols-[150px_1fr] gap-x-3 gap-y-2 text-sm">
            <dt><Pill tone="good">trained model</Pill></dt><dd className="text-muted">Output of a trained network evaluated on held-out data.</dd>
            <dt><Pill tone="info">reference gallery</Pill></dt><dd className="text-muted">Nearest-neighbour vote against labelled reference photos; below threshold it says unknown.</dd>
            <dt><Pill tone="warn">heuristic</Pill></dt><dd className="text-muted">Hand-written colour/shape rules. Useful hints, not measurements.</dd>
            <dt><Pill tone="neutral">rule-based</Pill></dt><dd className="text-muted">Readiness rules that combine the findings above with species biology.</dd>
            <dt><Pill tone="bad">close-up fallback</Pill></dt><dd className="text-muted">No detection - the whole image was treated as one flower.</dd>
          </dl>
        </Card>
        <Card title="Modules">
          <ul className="space-y-1.5 text-sm">
            {MODULES.map(([to, t, d]) => <li key={to}><Link className="font-medium underline" to={to}>{t}</Link> <span className="text-muted">- {d}</span></li>)}
          </ul>
        </Card>
        <Card title="Getting better results">
          <ul className="list-disc space-y-1 pl-4 text-sm text-muted">
            <li>Shoot in even daylight; avoid strong back-light and heavy shadow.</li>
            <li>Fill at least a quarter of the frame with the flower, or use close-up mode.</li>
            <li>Keep the flower facing the camera and in focus.</li>
            <li>One crop species per photo gives the clearest species votes.</li>
          </ul>
        </Card>
        <Card title="Roles and data">
          <ul className="list-disc space-y-1 pl-4 text-sm text-muted">
            <li><strong>User</strong> - scans, records and exports of their own data.</li>
            <li><strong>Researcher</strong> - adds species reference photos and sees aggregate analytics.</li>
            <li><strong>Admin</strong> - user management, detector selection and the activity log.</li>
            <li>Scans are private to the account that made them.</li>
          </ul>
        </Card>
      </div>
      <Notice>
        Full documentation, dataset licences and evaluation reports are in the project repository on{" "}
        <a className="underline" href="https://github.com/nvaltryek-001/pollinex-ai" target="_blank" rel="noreferrer">GitHub</a>.
      </Notice>
    </div>
  );
}
