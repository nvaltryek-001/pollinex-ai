import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { label } from "../lib/hooks";

export const SERIES = ["rgb(var(--leaf))", "rgb(var(--pollen))", "rgb(var(--petal))", "rgb(var(--sky))", "rgb(var(--muted))", "rgb(var(--alert))"];
const axis = { stroke: "rgb(var(--muted))", fontSize: 11, tickLine: false, axisLine: false } as const;
const tooltip = { contentStyle: { background: "rgb(var(--surface))", border: "1px solid rgb(var(--line))", borderRadius: 8, fontSize: 12, color: "rgb(var(--ink))" } };

export function DistBars({ data, height = 220, color, horizontal = false }: { data: Record<string, number>; height?: number; color?: string; horizontal?: boolean }) {
  const rows = Object.entries(data).map(([k, v]) => ({ name: label(k), value: v })).sort((a, b) => b.value - a.value);
  if (!rows.length) return <div className="py-10 text-center text-sm text-muted">No records yet.</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={rows} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: horizontal ? 20 : 0, right: 8, top: 8, bottom: 0 }}>
        <CartesianGrid stroke="rgb(var(--line))" vertical={horizontal} horizontal={!horizontal} />
        {horizontal ? <><XAxis type="number" {...axis} allowDecimals={false} /><YAxis type="category" dataKey="name" {...axis} width={100} /></>
          : <><XAxis dataKey="name" {...axis} interval={0} /><YAxis {...axis} allowDecimals={false} width={32} /></>}
        <Tooltip {...tooltip} cursor={{ fill: "rgb(var(--raised))" }} />
        <Bar dataKey="value" radius={[4, 4, 4, 4]}>
          {rows.map((_, i) => <Cell key={i} fill={color ?? SERIES[i % SERIES.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TimeLine({ data, height = 200 }: { data: Record<string, number>; height?: number }) {
  const rows = Object.entries(data).map(([day, n]) => ({ day: day.slice(5), n }));
  if (!rows.length) return <div className="py-10 text-center text-sm text-muted">No scans in the last 30 days.</div>;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={rows} margin={{ left: 0, right: 8, top: 8, bottom: 0 }}>
        <CartesianGrid stroke="rgb(var(--line))" vertical={false} />
        <XAxis dataKey="day" {...axis} /><YAxis {...axis} allowDecimals={false} width={32} />
        <Tooltip {...tooltip} />
        <Line type="monotone" dataKey="n" name="scans" stroke="rgb(var(--leaf))" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
