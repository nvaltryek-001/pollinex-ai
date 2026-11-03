import { useEffect, useState } from "react";
import { CheckCircle2, Info, X, XCircle } from "lucide-react";

/** Tiny global notification system (no context needed): toast.success("..."), toast.error("...") */
type Kind = "success" | "error" | "info";
interface Item { id: number; kind: Kind; text: string }
let seq = 0;
const listeners = new Set<(i: Item) => void>();
const emit = (kind: Kind, text: string) => listeners.forEach((l) => l({ id: ++seq, kind, text }));
export const toast = {
  success: (t: string) => emit("success", t),
  error: (t: string) => emit("error", t),
  info: (t: string) => emit("info", t),
};

export function Toaster() {
  const [items, setItems] = useState<Item[]>([]);
  useEffect(() => {
    const add = (i: Item) => {
      setItems((xs) => [...xs.slice(-3), i]);
      window.setTimeout(() => setItems((xs) => xs.filter((x) => x.id !== i.id)), i.kind === "error" ? 7000 : 4000);
    };
    listeners.add(add);
    return () => { listeners.delete(add); };
  }, []);
  const icon = { success: <CheckCircle2 size={16} className="text-leaf" />, error: <XCircle size={16} className="text-alert" />, info: <Info size={16} className="text-sky" /> };
  return (
    <div aria-live="polite" className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-[min(92vw,360px)] flex-col gap-2">
      {items.map((i) => (
        <div key={i.id} role={i.kind === "error" ? "alert" : "status"} className="card pointer-events-auto flex items-start gap-2 px-3 py-2.5 text-sm animate-rise">
          {icon[i.kind]}<span className="flex-1">{i.text}</span>
          <button aria-label="Dismiss notification" onClick={() => setItems((xs) => xs.filter((x) => x.id !== i.id))}><X size={14} /></button>
        </div>
      ))}
    </div>
  );
}
