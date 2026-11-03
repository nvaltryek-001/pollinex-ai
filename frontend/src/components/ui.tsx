import type { ReactNode } from "react";
import { AlertTriangle, Info, Loader2 } from "lucide-react";

export function PageHeader({ kicker, title, children, actions }: { kicker?: string; title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-end md:justify-between animate-rise">
      <div className="max-w-3xl">
        {kicker && <div className="kicker mb-1">{kicker}</div>}
        <h1 className="font-display text-3xl leading-tight md:text-4xl">{title}</h1>
        {children && <div className="mt-2 text-sm text-muted">{children}</div>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}

export function Card({ title, subtitle, children, className = "", right }: { title?: string; subtitle?: ReactNode; children: ReactNode; className?: string; right?: ReactNode }) {
  return (
    <section className={`card p-4 md:p-5 ${className}`}>
      {(title || right) && (
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-semibold">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
          </div>
          {right}
        </div>
      )}
      {children}
    </section>
  );
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="card p-4">
      <div className="kicker">{label}</div>
      <div className="mt-1 font-display text-3xl tabular-nums">{value}</div>
      {hint && <div className="mt-1 text-xs text-muted">{hint}</div>}
    </div>
  );
}

const METHOD_STYLE: Record<string, string> = {
  trained_model: "bg-leaf/15 text-leaf border-leaf/30",
  trained_reference_gallery: "bg-leaf/15 text-leaf border-leaf/30",
  heuristic: "bg-pollen/15 text-pollen border-pollen/40",
  rule_engine: "bg-sky/15 text-sky border-sky/30",
  simulation: "bg-petal/15 text-petal border-petal/30",
  closeup_fallback: "bg-alert/10 text-alert border-alert/30",
  user_declared: "bg-raised text-muted border-line",
  user_corrected: "bg-raised text-ink border-ink/40",
};
const METHOD_TEXT: Record<string, string> = {
  trained_model: "trained model",
  trained_reference_gallery: "reference gallery",
  heuristic: "heuristic",
  rule_engine: "rule engine",
  simulation: "simulation",
  closeup_fallback: "close-up fallback",
  user_declared: "user declared",
  user_corrected: "user corrected",
};

/** Every AI output in the UI carries one of these so evidence type is never ambiguous. */
export function MethodBadge({ method }: { method: string }) {
  return (
    <span title={`Provenance: ${method}`} className={`inline-flex items-center rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${METHOD_STYLE[method] ?? "border-line text-muted"}`}>
      {METHOD_TEXT[method] ?? method}
    </span>
  );
}

export function Pill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "good" | "warn" | "bad" | "info" }) {
  const t = { neutral: "bg-raised text-ink", good: "bg-leaf/15 text-leaf", warn: "bg-pollen/20 text-pollen", bad: "bg-alert/15 text-alert", info: "bg-sky/15 text-sky" }[tone];
  return <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium ${t}`}>{children}</span>;
}

export const readinessTone = (c: string) =>
  (({ likely_ready: "good", approaching: "info", past_window: "warn", not_ready: "neutral", indeterminate: "bad" } as const)[c as "likely_ready"] ?? "neutral");

export function Loading({ text = "Loading" }: { text?: string }) {
  return <div className="flex items-center gap-2 py-8 text-sm text-muted" role="status"><Loader2 className="h-4 w-4 animate-spin" />{text}…</div>;
}

export function ErrorBanner({ error, onRetry }: { error: string | null; onRetry?: () => void }) {
  if (!error) return null;
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-alert/40 bg-alert/10 px-4 py-3 text-sm text-alert">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
      <div className="flex-1">{error}</div>
      {onRetry && <button className="underline" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Notice({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-line bg-raised/60 px-4 py-3 text-xs text-muted">
      <Info className="mt-0.5 h-4 w-4 shrink-0" />
      <div>{children}</div>
    </div>
  );
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-line px-6 py-10 text-center">
      <div className="font-display text-lg">{title}</div>
      {children && <div className="mx-auto mt-2 max-w-md text-sm text-muted">{children}</div>}
    </div>
  );
}

export function Bar({ value, tone = "leaf" }: { value: number; tone?: "leaf" | "pollen" | "petal" | "sky" }) {
  return (
    <div className="h-1.5 w-full overflow-hidden rounded-full bg-raised" aria-hidden>
      <div className={`h-full ${{ leaf: "bg-leaf", pollen: "bg-pollen", petal: "bg-petal", sky: "bg-sky" }[tone]}`} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  );
}
