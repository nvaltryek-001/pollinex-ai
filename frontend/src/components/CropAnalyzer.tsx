import { useState, type ReactNode } from "react";
import { Upload } from "lucide-react";
import { api } from "../lib/api";
import { Card, ErrorBanner, Loading } from "./ui";

/** Upload one flower crop to a single-module endpoint and render its JSON result with a custom renderer. */
export function CropAnalyzer<T>({ endpoint, title, render, hint }: { endpoint: string; title: string; render: (r: T) => ReactNode; hint?: string }) {
  const [res, setRes] = useState<T | null>(null);
  const [img, setImg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async (f?: File) => {
    if (!f) return;
    setErr(null); setBusy(true); setRes(null);
    if (img) URL.revokeObjectURL(img);
    setImg(URL.createObjectURL(f));
    const fd = new FormData();
    fd.append("file", f, f.name);
    try { setRes(await api.upload<T>(endpoint, fd)); } catch (e) { setErr((e as Error).message); } finally { setBusy(false); }
  };
  return (
    <Card title={title} subtitle={hint ?? "Upload a close-up crop of a single flower."}>
      <div className="grid gap-4 md:grid-cols-[200px_1fr]">
        <label className="flex aspect-square cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden rounded-lg border-2 border-dashed border-line text-xs text-muted hover:bg-raised/50">
          {img ? <img src={img} alt="Uploaded crop" className="h-full w-full object-cover" /> : <><Upload size={18} />Choose image</>}
          <input type="file" accept="image/*" className="sr-only" onChange={(e) => run(e.target.files?.[0])} />
        </label>
        <div className="min-w-0">
          <ErrorBanner error={err} />
          {busy && <Loading text="Analysing" />}
          {res && render(res)}
          {!res && !busy && !err && <p className="text-sm text-muted">Results appear here. Nothing is saved from this panel.</p>}
        </div>
      </div>
    </Card>
  );
}
