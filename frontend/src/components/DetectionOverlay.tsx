import type { Flower } from "../lib/types";

interface Box { box: [number, number, number, number]; score: number; low_confidence: boolean; label?: string; method?: string }

/** SVG overlay in image coordinates; scales with the image via viewBox. */
export function DetectionOverlay({ width, height, boxes, selected, onSelect, showCentres = false, flowers }: {
  width: number; height: number; boxes: Box[]; selected?: number | null; onSelect?: (i: number) => void; showCentres?: boolean; flowers?: Flower[];
}) {
  const sw = Math.max(1.5, Math.max(width, height) / 400);
  return (
    <svg className="absolute inset-0 h-full w-full" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" aria-label={`${boxes.length} detections`}>
      {boxes.map((b, i) => {
        const [x1, y1, x2, y2] = b.box;
        const fallback = b.method === "closeup_fallback";
        const color = fallback ? "rgb(var(--alert))" : b.low_confidence ? "rgb(var(--pollen))" : "rgb(var(--leaf))";
        const isSel = selected === i;
        return (
          <g key={i} onClick={() => onSelect?.(i)} style={{ cursor: onSelect ? "pointer" : "default" }}>
            <rect x={x1} y={y1} width={x2 - x1} height={y2 - y1} fill={isSel ? "rgb(var(--pollen) / 0.12)" : "transparent"}
              stroke={color} strokeWidth={isSel ? sw * 2 : sw} strokeDasharray={b.low_confidence || fallback ? `${sw * 3} ${sw * 2}` : undefined} />
            {(isSel || boxes.length <= 30) && (
              <text x={x1 + sw} y={Math.max(y1 - sw * 2, sw * 8)} fontSize={sw * 7} fill={color} fontFamily="IBM Plex Mono, monospace"
                paintOrder="stroke" stroke="rgb(0 0 0 / 0.55)" strokeWidth={sw * 1.5}>
                {b.label ? `${b.label} ` : ""}{fallback ? "fallback" : (b.score * 100).toFixed(0) + "%"}
              </text>
            )}
          </g>
        );
      })}
      {showCentres && flowers?.map((f, i) => f.pose && (
        <circle key={`c${i}`} cx={f.pose.center_px[0]} cy={f.pose.center_px[1]} r={sw * 2.5} fill="rgb(var(--petal))" />
      ))}
    </svg>
  );
}
