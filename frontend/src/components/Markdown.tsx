import type { ReactNode } from "react";

/** Minimal, safe markdown renderer (headings, lists, tables, bold/italic/code, links). No HTML injection. */
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const t = m[0];
    if (t.startsWith("**")) out.push(<strong key={k++}>{t.slice(2, -2)}</strong>);
    else if (t.startsWith("`")) out.push(<code key={k++} className="rounded bg-raised px-1 font-mono text-[0.85em]">{t.slice(1, -1)}</code>);
    else if (t.startsWith("[")) {
      const [, label, href] = /\[([^\]]+)\]\(([^)]+)\)/.exec(t)!;
      const safe = /^https?:\/\//.test(href) ? href : undefined;
      out.push(safe ? <a key={k++} href={safe} target="_blank" rel="noreferrer" className="underline">{label}</a> : label);
    } else out.push(<em key={k++}>{t.slice(1, -1)}</em>);
    last = m.index + t.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ text }: { text: string }) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const l = lines[i];
    if (/^#{1,4} /.test(l)) {
      const level = l.match(/^#+/)![0].length;
      const cls = ["", "font-display text-2xl mt-4", "font-display text-xl mt-5", "font-semibold mt-4", "font-semibold mt-3"][level];
      blocks.push(<div key={i} className={cls}>{inline(l.replace(/^#+ /, ""))}</div>);
      i++;
    } else if (l.startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        if (!/^\|[\s:-]+\|/.test(lines[i]) || /[a-z0-9]/i.test(lines[i])) rows.push(lines[i].split("|").slice(1, -1).map((c) => c.trim()));
        i++;
      }
      blocks.push(<div key={i} className="my-3 overflow-x-auto"><table className="table-base"><thead><tr>{rows[0]?.map((c, j) => <th key={j}>{inline(c)}</th>)}</tr></thead>
        <tbody>{rows.slice(1).map((r, a) => <tr key={a}>{r.map((c, j) => <td key={j}>{inline(c)}</td>)}</tr>)}</tbody></table></div>);
    } else if (/^\s*[-*] /.test(l) || /^\d+\. /.test(l)) {
      const items: string[] = [];
      while (i < lines.length && (/^\s*[-*] /.test(lines[i]) || /^\d+\. /.test(lines[i]))) { items.push(lines[i].replace(/^\s*([-*]|\d+\.) /, "")); i++; }
      blocks.push(<ul key={i} className="my-2 list-disc space-y-1 pl-5 text-sm">{items.map((t, j) => <li key={j}>{inline(t)}</li>)}</ul>);
    } else if (l.startsWith("```")) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) code.push(lines[i++]);
      i++;
      blocks.push(<pre key={i} className="my-2 overflow-x-auto rounded-lg bg-raised p-3 font-mono text-xs">{code.join("\n")}</pre>);
    } else if (l.trim() === "" || l.trim() === "---") {
      i++;
    } else {
      blocks.push(<p key={i} className="my-2 text-sm leading-relaxed">{inline(l)}</p>);
      i++;
    }
  }
  return <div className="max-h-[70vh] overflow-y-auto pr-2">{blocks}</div>;
}
